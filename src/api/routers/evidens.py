"""Evidens-router — templates + per-case evidens-CRUD.

Endpoints:
  - GET /api/v3/evidence/templates           → list 28 curerede templates
  - GET /api/v3/evidence/templates/{id}      → hent én template
  - GET /api/v3/cases/{case_id}/evidence     → list udfyldte evidens for sag
  - PUT /api/v3/cases/{case_id}/evidence/{artifact_id} → upsert evidens

Bemærk: templates-routes har prefix /api/v3/evidence, men per-case-routes
sidder under /api/v3/cases (case-scope). Implementeret som én router
uden prefix og fulde stier på hver dekoratør for klarhed.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from src.api.rate_limiting import limiter, ADMIN_WRITE

logger = logging.getLogger("bifrost.evidens")

router = APIRouter(tags=["evidens"])


class EvidenceSavePayload(BaseModel):
    """Sagsbehandlerens udfyldte indhold for ét artefakt."""

    content: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dict {section_key: value} med svar pr. sektion.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Valgfri intern note (ikke vist i auditrapporten).",
    )
    user: Optional[str] = Field(
        default=None,
        description="Bruger der gemte (audit-trail).",
    )


# ---- Templates ------------------------------------------------------------


@router.get("/api/v3/evidence/templates")
async def list_templates_endpoint():
    """List alle curerede artefakt-skabeloner.

    Returnerer fuld template-spec inkl. sections, lovhjemmel og eksterne
    ressourcer. Bruges af /drift og evidens-katalog.
    """
    from src.services.evidence_artifacts import list_templates, all_known_ids
    templates = list_templates()
    return {
        "count": len(templates),
        "all_known_artifact_ids_count": len(all_known_ids()),
        "templates": templates,
    }


@router.get("/api/v3/evidence/templates/{artifact_id}")
async def get_template_endpoint(artifact_id: str):
    """Hent én skabelon — fallback til generic hvis ikke curated."""
    from src.services.evidence_artifacts import get_template
    return get_template(artifact_id).to_dict()


# ---- Per-case evidens -----------------------------------------------------


@router.get("/api/v3/cases/{case_id}/evidence")
async def list_for_case(case_id: str, request: Request):
    """List sagsbehandlerens udfyldte artefakter for én sag."""
    from src.database.connection import SessionLocal
    from src.database.evidence import list_evidence_for_case
    from src.database.audit_access_log import record_access

    db = SessionLocal()
    try:
        rows = list_evidence_for_case(db, case_id)
        record_access(
            db,
            target_type="case_evidence",
            target_id=case_id,
            actor=request.headers.get("X-Bifrost-User"),
            actor_ip=(request.client.host if request.client else None),
            user_agent=request.headers.get("user-agent"),
            action="read",
            request_id=getattr(request.state, "request_id", None),
        )
        db.commit()
        return {
            "case_id": case_id,
            "count": len(rows),
            "items": [r.to_dict() for r in rows],
        }
    finally:
        db.close()


@router.put("/api/v3/cases/{case_id}/evidence/{artifact_id}")
@limiter.limit(ADMIN_WRITE)
async def upsert_evidence_endpoint(
    request: Request,
    response: Response,
    case_id: str,
    artifact_id: str,
    body: EvidenceSavePayload,
):
    """Gem/opdatér ét artefakt-indhold.

    Status beregnes server-side baseret på hvilke required-sektioner der
    har indhold (mangler / i_gang / faerdig). Når status går til 'faerdig'
    første gang sættes `completed_at` + `completed_by` automatisk.

    Emitterer notifikation når en evidens skifter til faerdig første gang.
    """
    from src.database.connection import SessionLocal
    from src.database.evidence import upsert_evidence, get_evidence
    from src.database.audit_access_log import record_access
    from src.database import notifications as notif_svc
    from src.services.evidence_artifacts import compute_status, get_template

    template = get_template(artifact_id)
    computed = compute_status(template, body.content)

    db = SessionLocal()
    try:
        # Pre-check: var artefaktet allerede færdigt? Hvis ja, ingen notifikation
        prev = get_evidence(db, case_id, artifact_id)
        was_already_completed = prev is not None and prev.status in ("faerdig", "godkendt")

        row = upsert_evidence(
            db,
            case_id=case_id,
            artifact_id=artifact_id,
            content=body.content,
            computed_status=computed,
            user=body.user,
            notes=body.notes,
        )
        record_access(
            db,
            target_type="case_evidence",
            target_id=f"{case_id}/{artifact_id}",
            actor=body.user or request.headers.get("X-Bifrost-User"),
            actor_ip=(request.client.host if request.client else None),
            user_agent=request.headers.get("user-agent"),
            action="write",
            request_id=getattr(request.state, "request_id", None),
        )

        # Auto-emit notifikation når et artefakt skifter til faerdig første gang
        if computed in ("faerdig", "godkendt") and not was_already_completed:
            try:
                notif_svc.emit(
                    db,
                    kind="evidens_completed",
                    title=f"Evidens færdig: {artifact_id.replace('_', ' ')}",
                    message=f"Artefaktet '{template.title}' er nu udfyldt på sag {case_id}.",
                    case_id=case_id,
                    link_url=f"/sag/{case_id}?tab=evidens",
                    severity="success",
                    actor=body.user,
                )
            except Exception as exc:
                logger.warning(f"notification emit failed: {exc}")

        db.commit()
        return {
            **row.to_dict(),
            "computed_status": computed,
            "required_section_keys": sorted(template.required_section_keys()),
        }
    finally:
        db.close()
