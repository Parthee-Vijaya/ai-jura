"""Risikovurderingsmotor-router — automatiseret databeskyttelsesretlig risikovurdering.

Endpoints:
  - POST /api/v3/risk-assessment/analyze   (multipart: files[] + systemnavn)
        → {facts, questions, documents}
  - POST /api/v3/risk-assessment/generate  (JSON: {facts, answers})
        → {risikovurdering} (komplet — facts + risici + felttekster)
  - POST /api/v3/risk-assessment/render     (JSON: {risikovurdering})
        → DOCX-download

Flow: frontend kalder analyze, viser afklarende spørgsmål, kalder generate,
viser risiko-preview, og kalder til sidst render for at hente Word-filen.
Render-trinet er deterministisk (ingen LLM) så det er hurtigt + reproducerbart.
"""

import asyncio
import logging

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from src.api.error_envelope import AppError
from src.api.rate_limiting import limiter, LLM_HEAVY, READ_GENEROUS
from src.services.risk_assessment import orchestrator
from src.services.risk_assessment.docx_assembler import (
    assemble_docx,
    get_template_path,
    output_filename,
)
from src.services.risk_assessment.document_extract import MAX_BYTES
from src.services.risk_assessment.llm_client import RiskLLMError
from src.services.risk_assessment.models import Risikovurdering, SystemFacts
from src.services.risk_assessment.verifier import verify_docx

logger = logging.getLogger("bifrost.risk_assessment.router")
router = APIRouter(prefix="/api/v3/risk-assessment", tags=["risk-assessment"])

MAX_FILES = 10


class GeneratePayload(BaseModel):
    facts: SystemFacts
    answers: dict = Field(default_factory=dict)


class RenderPayload(BaseModel):
    risikovurdering: Risikovurdering


@router.post("/analyze")
@limiter.limit(LLM_HEAVY)
async def analyze_endpoint(request: Request, response: Response):
    """Fase 1-3: upload dokumenter → udled SystemFacts + afklarende spørgsmål.

    Multipart/form-data:
      - files: 1-10 filer (.pdf .docx .txt .md, max 10 MB hver)
      - systemnavn: valgfrit string
    """
    form = await request.form()
    systemnavn = (form.get("systemnavn") or "").strip()

    files: list[tuple[str, bytes]] = []
    # Saml alle upload-felter (kan hedde 'files' gentaget eller 'file')
    for key in form:
        for item in form.getlist(key):
            if hasattr(item, "read") and hasattr(item, "filename") and item.filename:
                data = await item.read()
                if len(data) > MAX_BYTES:
                    raise AppError(
                        "file_too_large",
                        f"{item.filename}: for stor (max 10 MB)",
                        status=413,
                    )
                files.append((item.filename, data))
            if len(files) >= MAX_FILES:
                break

    if not files and not systemnavn:
        raise AppError(
            "no_input",
            "Upload mindst ét dokument eller angiv et systemnavn",
            status=400,
        )

    try:
        result = await asyncio.to_thread(
            orchestrator.analyze, files, systemnavn=systemnavn
        )
    except RiskLLMError as exc:
        raise AppError(
            "llm_failed", str(exc), status=502,
            hint="Tjek LM_STUDIO_BASE_URL eller OPENAI_API_KEY",
        )

    return {
        "facts": result.facts.model_dump(),
        "questions": [q.model_dump() for q in result.questions],
        "documents": result.documents,
        "disclaimer": (
            "AI-udtrukne fakta — gennemgå og ret før du fortsætter. "
            "Manglende felter besvares via spørgsmålene."
        ),
    }


@router.post("/generate")
@limiter.limit(LLM_HEAVY)
async def generate_endpoint(request: Request, response: Response, body: GeneratePayload):
    """Fase 4-5: facts + svar → komplet Risikovurdering (risici + felttekster)."""
    try:
        rv = await asyncio.to_thread(orchestrator.generate, body.facts, body.answers)
    except RiskLLMError as exc:
        raise AppError(
            "llm_failed", str(exc), status=502,
            hint="Tjek LM_STUDIO_BASE_URL eller OPENAI_API_KEY",
        )

    if not rv.risici:
        raise AppError(
            "no_risks",
            "LLM identificerede ingen risici — prøv igen eller tilføj flere dokumenter",
            status=502,
        )

    return {
        "risikovurdering": rv.model_dump(),
        "n_risici": len(rv.risici),
        "disclaimer": (
            "AI-genereret FØRSTEUDKAST. Skal efterredigeres af AI Program Lead + DPO "
            "før det er en gyldig risikovurdering."
        ),
    }


@router.post("/render")
@limiter.limit(READ_GENEROUS)
async def render_endpoint(request: Request, response: Response, body: RenderPayload):
    """Fase 6-7: Risikovurdering JSON → udfyldt DOCX (deterministisk, ingen LLM)."""
    rv = body.risikovurdering
    if not get_template_path() or not _template_exists():
        raise AppError(
            "template_missing",
            "Master-template ikke fundet på serveren",
            status=500,
        )

    try:
        data = await asyncio.to_thread(assemble_docx, rv)
    except FileNotFoundError as exc:
        raise AppError("template_missing", str(exc), status=500)
    except Exception as exc:  # pragma: no cover
        raise AppError("render_failed", f"DOCX-assembly fejlede: {exc}", status=500)

    # Verifikation — log problemer men blokér ikke download (det er et udkast).
    # facts gives med så Kalundborg-compliance-tjekkene også køres.
    res = verify_docx(
        data,
        expected_n_risks=len(rv.risici),
        systemnavn=rv.facts.systemnavn,
        facts=rv.facts,
    )
    if not res.valid:
        logger.warning("Render-verifikation fandt problemer: %s", res.problems)

    filename = output_filename(rv.facts.systemnavn)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Verify-Valid": "true" if res.valid else "false",
            "X-Risk-Rows": str(res.n_risk_rows),
        },
    )


def _template_exists() -> bool:
    import os
    return os.path.exists(get_template_path())
