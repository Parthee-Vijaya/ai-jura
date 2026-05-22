"""Fact-ekstraktion — uddrag SystemFacts fra uploadede dokumenter via LLM.

Læser den kombinerede dokumenttekst (MSA, DBA, produkt-PDF m.v.) og returnerer
struktureret SystemFacts. Felter der ikke kan udledes sættes til tom/None —
det udløser et afklarende spørgsmål (se clarifying.py).
"""

import logging
from typing import Any

from src.services.risk_assessment.llm_client import chat_json, RiskLLMError
from src.services.risk_assessment.models import (
    DataKategori,
    SystemFacts,
    Underdatabehandler,
)

logger = logging.getLogger("bifrost.risk_assessment.facts")


SYSTEM_PROMPT = """Du er en GDPR-ekspert der læser leverandøraftaler og produkt-
dokumentation for at udtrække strukturerede fakta til en databeskyttelsesretlig
risikovurdering for Kalundborg Kommune.

Læs alle vedlagte dokumenter grundigt. Vær særligt opmærksom på:

1. MSA / Master Service Agreement — kig efter:
   - Brede licens-klausuler der giver leverandøren ret til at bruge Customer Data
     til AI-træning, produktudvikling, R&D, eller "improve the Service"
   - Ansvarsloft (limitation of liability — typisk § 13)
   - Indemnification caps (typisk § 14)
   - Retention-perioder efter ophør

2. Databehandleraftale (DBA) — kig efter:
   - Bilag A: typer af personoplysninger (almindelige / følsomme / CPR / strafbare)
   - Bilag B: underdatabehandlere — navn, land, rolle
   - Bilag E: databehandlerkæde

3. Produktdokumentation — kig efter:
   - Hosting (cloud, on-prem, hvilket land/region)
   - Hvilke moduler/agenter findes
   - Browser-extension / desktop-agent? (relevant for medarbejderovervågning)

Du svarer KUN med valid JSON i præcis dette format:

{
  "systemnavn": "...",
  "leverandoer_navn": "...",
  "leverandoer_cvr": "... eller null",
  "leverandoer_land": "...",
  "leverandoer_stiftet_aar": 2024 eller null,
  "formaal_kort": "1-2 sætninger om hvad systemet gør",
  "funktionalitet": "teknisk beskrivelse, 3-5 sætninger",
  "hosting_lokation": "fx 'Microsoft Azure EU-region' eller 'Scaleway FR/NL'",
  "underdatabehandlere": [{"navn":"...","cvr_eller_id":"... eller null","land":"...","rolle":"..."}],
  "persondata_kategorier": ["almindelige","følsomme","cpr","strafbare"],  // kun de relevante
  "persondata_typer": ["navn","e-mail","IP","CPR i fritekst"],
  "registrerede": ["medarbejdere","borgere via fritekst"],
  "authentication": "fx 'Entra ID SSO + MFA'",
  "msa_risiko_klausuler": ["§6.2 worldwide license til AI-træning", ...],
  "ansvarsloft": "fx '12 mdr. fees ≈ DKK 180.000' eller null",
  "ip_indemnification_cap": "fx 'EUR 10.000' eller null",
  "retention_efter_ophoer": "fx '90 dage' eller null",
  "internt_udviklet": true/false,
  "medarbejder_overvaagning": true/false
}

Hvis et felt ikke kan udledes med rimelig sikkerhed, sæt det til null (eller tom
liste/streng). Gæt ALDRIG på CVR-numre, datoer eller paragraf-numre — angiv kun
hvad der faktisk står i dokumenterne. internt_udviklet=true hvis det er kommunens
eget system uden ekstern SaaS-leverandør."""


_KAT_MAP = {
    "almindelige": DataKategori.ALMINDELIGE,
    "følsomme": DataKategori.FOELSOMME,
    "foelsomme": DataKategori.FOELSOMME,
    "cpr": DataKategori.CPR,
    "strafbare": DataKategori.STRAFBARE,
    "ingen": DataKategori.INGEN,
}


def extract_facts(
    documents_text: str,
    *,
    systemnavn: str = "",
    timeout: float = 90.0,
) -> SystemFacts:
    """Uddrag SystemFacts fra kombineret dokumenttekst.

    Args:
        documents_text: output fra document_extract.combine_for_prompt()
        systemnavn: bruger-angivet systemnavn (overstyrer LLM hvis sat)
    """
    if not documents_text or not documents_text.strip():
        # Ingen dokumenter — returnér tomt fakta-skelet (alt udledes via spørgsmål)
        return SystemFacts(systemnavn=systemnavn)

    user_message = f"""Systemnavn (hvis kendt): {systemnavn or "(udled fra dokumenter)"}

DOKUMENTER:
{documents_text}

Uddrag SystemFacts nu som JSON."""

    try:
        data = chat_json(SYSTEM_PROMPT, user_message, temperature=0.1, timeout=timeout, expect="object")
    except RiskLLMError:
        raise
    except Exception as exc:  # pragma: no cover - defensiv
        raise RiskLLMError(f"Fact-ekstraktion fejlede: {exc}") from exc

    return _coerce_facts(data, systemnavn_override=systemnavn)


def _coerce_facts(data: dict[str, Any], *, systemnavn_override: str = "") -> SystemFacts:
    """Konvertér rå LLM-dict til SystemFacts med robust normalisering."""
    if not isinstance(data, dict):
        raise RiskLLMError("Fact-ekstraktion returnerede ikke et JSON-object")

    # Datakategorier → enum (skip ukendte)
    kats = []
    for k in data.get("persondata_kategorier", []) or []:
        key = str(k).strip().lower()
        if key in _KAT_MAP and _KAT_MAP[key] not in kats:
            kats.append(_KAT_MAP[key])

    # Underdatabehandlere
    udb = []
    for u in data.get("underdatabehandlere", []) or []:
        if isinstance(u, dict) and u.get("navn"):
            udb.append(Underdatabehandler(
                navn=str(u.get("navn", "")).strip(),
                cvr_eller_id=(str(u["cvr_eller_id"]).strip() if u.get("cvr_eller_id") else None),
                land=str(u.get("land") or "Ukendt").strip(),
                rolle=str(u.get("rolle") or "").strip(),
            ))

    def _str_list(key):
        return [str(x).strip() for x in (data.get(key) or []) if str(x).strip()]

    def _opt_str(key):
        v = data.get(key)
        return str(v).strip() if v not in (None, "", "null") else None

    aar = data.get("leverandoer_stiftet_aar")
    try:
        aar = int(aar) if aar not in (None, "", "null") else None
    except (ValueError, TypeError):
        aar = None

    return SystemFacts(
        systemnavn=(systemnavn_override or str(data.get("systemnavn") or "")).strip(),
        leverandoer_navn=str(data.get("leverandoer_navn") or "").strip(),
        leverandoer_cvr=_opt_str("leverandoer_cvr"),
        leverandoer_land=str(data.get("leverandoer_land") or "Ukendt").strip(),
        leverandoer_stiftet_aar=aar,
        formaal_kort=str(data.get("formaal_kort") or "").strip(),
        funktionalitet=str(data.get("funktionalitet") or "").strip(),
        hosting_lokation=str(data.get("hosting_lokation") or "").strip(),
        underdatabehandlere=udb,
        persondata_kategorier=kats,
        persondata_typer=_str_list("persondata_typer"),
        registrerede=_str_list("registrerede"),
        authentication=str(data.get("authentication") or "").strip(),
        msa_risiko_klausuler=_str_list("msa_risiko_klausuler"),
        ansvarsloft=_opt_str("ansvarsloft"),
        ip_indemnification_cap=_opt_str("ip_indemnification_cap"),
        retention_efter_ophoer=_opt_str("retention_efter_ophoer"),
        internt_udviklet=bool(data.get("internt_udviklet", False)),
        medarbejder_overvaagning=bool(data.get("medarbejder_overvaagning", False)),
    )
