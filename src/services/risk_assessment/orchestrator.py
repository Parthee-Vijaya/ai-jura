"""Orchestrator — binder risikovurderings-pipelinens faser sammen.

To indgange svarende til frontend-flowet:

  analyze(files, systemnavn)
      → ekstrahér dokumenter → udled SystemFacts → beregn afklarende spørgsmål
      → returnér (facts, questions)

  generate(facts, answers)
      → flet svar ind → identificér risici → generér felttekster
      → returnér komplet Risikovurdering (klar til render)

Render (deterministisk DOCX) ligger i docx_assembler.assemble_docx og kaldes
separat så render-trinet ikke kræver flere LLM-kald.
"""

import logging
from dataclasses import dataclass

from src.services.risk_assessment import clarifying
from src.services.risk_assessment.content_generator import generate_content
from src.services.risk_assessment.document_extract import (
    ExtractedDoc,
    combine_for_prompt,
    extract_many,
)
from src.services.risk_assessment.fact_extractor import extract_facts
from src.services.risk_assessment.models import (
    ClarifyingQuestion,
    Risikovurdering,
    SystemFacts,
)
from src.services.risk_assessment.risk_identifier import identify_risks

logger = logging.getLogger("bifrost.risk_assessment.orchestrator")


@dataclass
class AnalyzeResult:
    facts: SystemFacts
    questions: list[ClarifyingQuestion]
    documents: list[str]  # filnavne der blev læst


def analyze(
    files: list[tuple[str, bytes]],
    *,
    systemnavn: str = "",
    timeout: float = 90.0,
) -> AnalyzeResult:
    """Fase 1-3: ekstrahér dokumenter, udled fakta, beregn spørgsmål."""
    docs: list[ExtractedDoc] = extract_many(files) if files else []
    combined = combine_for_prompt(docs) if docs else ""

    facts = extract_facts(combined, systemnavn=systemnavn, timeout=timeout)
    # Sørg for systemnavn er sat (bruger-input vinder)
    if systemnavn:
        facts.systemnavn = systemnavn

    questions = clarifying.build_questions(facts)
    return AnalyzeResult(
        facts=facts,
        questions=questions,
        documents=[d.filename for d in docs],
    )


def generate(
    facts: SystemFacts,
    answers: dict,
    *,
    timeout: float = 120.0,
) -> Risikovurdering:
    """Fase 4-5: flet svar, identificér risici, generér felttekster."""
    merged = clarifying.apply_answers(facts, answers or {})

    risks = identify_risks(merged, timeout=timeout)
    field_texts = generate_content(merged, risks, timeout=timeout)

    return Risikovurdering(
        facts=merged,
        risici=risks,
        formaal_tekst=field_texts.get("formaal_tekst", ""),
        omfang_tekst=field_texts.get("omfang_tekst", ""),
        ansvarlige_tekst=field_texts.get("ansvarlige_tekst", ""),
        baggrund_tekst=field_texts.get("baggrund_tekst", ""),
        funktionalitet_tekst=field_texts.get("funktionalitet_tekst", ""),
        interessenter_tekst=field_texts.get("interessenter_tekst", ""),
        personoplysninger_tekst=field_texts.get("personoplysninger_tekst", ""),
        lokationer_tekst=field_texts.get("lokationer_tekst", ""),
        adgangsrettigheder_tekst=field_texts.get("adgangsrettigheder_tekst", ""),
        saarbarheder_tekst=field_texts.get("saarbarheder_tekst", ""),
        tiltag_tekst=field_texts.get("tiltag_tekst", ""),
        ansvarlige_tiltag_tekst=field_texts.get("ansvarlige_tiltag_tekst", ""),
        kontrolmekanismer_tekst=field_texts.get("kontrolmekanismer_tekst", ""),
        opdatering_tekst=field_texts.get("opdatering_tekst", ""),
    )
