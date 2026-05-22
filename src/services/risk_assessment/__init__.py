"""Risikovurderingsmotor — automatiseret databeskyttelsesretlig risikovurdering.

Porteret fra den manuelle Cowork-skill (skill-risikovurdering) til en Bifrost-
feature. Bruger uploadede dokumenter (MSA, DBA, produkt-PDF, SCC m.v.) + et par
afklarende spørgsmål til at generere et færdigt Word-udkast baseret på Kalundborg
Kommunes officielle skabelon.

Pipeline (se orchestrator.py):
  1. document_extract  — pdf/docx → tekst
  2. fact_extractor    — LLM → SystemFacts (struktureret)
  3. clarifying        — beregn hvilke spørgsmål der mangler
  4. risk_identifier   — LLM → 8-12 systemspecifikke risici
  5. content_generator — LLM → tekst pr. skabelon-felt
  6. docx_assembler    — deterministisk DOCX-udfyldning (gul-highlight markører)
  7. verifier          — sanity-check af færdigt dokument

LLM-provider: lokal LM Studio → Azure OpenAI → OpenAI (samme kæde som resten af
Bifrost). Lokal-først af GDPR-hensyn — dokumenterne indeholder netop de persondata
som værktøjet vurderer, så de må ikke sendes til en US-cloud-API.

Output er et FØRSTEUDKAST som AI Program Lead + DPO efterredigerer.
"""

from src.services.risk_assessment.models import (
    DataKategori,
    Niveau,
    Risiko,
    Risikovurdering,
    SystemFacts,
    Underdatabehandler,
)

__all__ = [
    "DataKategori",
    "Niveau",
    "Risiko",
    "Risikovurdering",
    "SystemFacts",
    "Underdatabehandler",
]
