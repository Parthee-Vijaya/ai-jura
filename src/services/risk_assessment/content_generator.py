"""Indholds-generering — generér tekst til hvert skabelon-felt via LLM.

Genererer de 14 prosa-felter (Table 0,1,2,6,7) i ét sammenhængende struktureret
kald, så felterne er konsistente (formål refererer systemet, interessenter matcher
ansvarlige osv.). Risikoskemaet genereres separat (risk_identifier.py).

Faste forhold for Kalundborg Kommune injiceres som kontekst — ikke som noget
LLM'en skal opfinde.
"""

import logging
from typing import Any

from src.services.risk_assessment.llm_client import chat_json, RiskLLMError
from src.services.risk_assessment.models import Risiko, SystemFacts

logger = logging.getLogger("bifrost.risk_assessment.content")


# Faste forhold (hard-coded — ikke LLM-genereret)
FASTE_FORHOLD = {
    "dataansvarlig": "Kalundborg Kommune (CVR 29189595)",
    "teknisk_ansvarlig": "Partheepan Vijayamohan, AI Program Lead",
    "organisatorisk_ansvarlig": "Anne Dandanell",
}

# De 14 felter der skal genereres + kort instruks pr. felt
FIELD_SPECS = {
    "formaal_tekst": "Formål-feltet. 4-6 sætninger. Begynd: 'Formålet med denne risikovurdering er at identificere, vurdere og håndtere databeskyttelsesretlige risici forbundet med Kalundborg Kommunes anvendelse af {systemnavn} – ...'. Beskriv kort hvad systemet er. Slut med standard-formulering om GDPR + databeskyttelsesloven + ISO 27001/27005-principper.",
    "omfang_tekst": "Omfang-feltet. 2-4 sætninger. Hvilke dele af projektet dækker vurderingen (hele systemet / specifikke moduler / POC vs bred udrulning afhængig af scope).",
    "ansvarlige_tekst": "Ansvarlige for udarbejdelsen. Nævn teknisk ansvarlig (Partheepan Vijayamohan) og organisatorisk ansvarlig (Anne Dandanell) samt DPO-inddragelse.",
    "baggrund_tekst": "Projektets baggrund. 3-5 sætninger om hvorfor systemet anskaffes/udvikles og hvilken kontekst det indgår i.",
    "funktionalitet_tekst": "Systemets funktionalitet. 3-5 sætninger teknisk beskrivelse: hvad systemet gør, integrationer, dataflows.",
    "interessenter_tekst": "Interessenter. Start med 'Dataansvarlig: Kalundborg Kommune'. Nævn relevante interne afdelinger, eksterne leverandører, og de registrerede grupper.",
    "personoplysninger_tekst": "Hvilke personoplysninger behandles (almindelige/følsomme/CPR/strafbare) og om hvem. Vær konkret ud fra fakta.",
    "lokationer_tekst": "Lokationer og it-systemer. Hosting (fx Azure EU-region), hvilke systemer data flyder gennem.",
    "adgangsrettigheder_tekst": "Styring af adgangsrettigheder. Authentication (Entra ID/MFA), rollebaseret adgang, hvem har adgang.",
    "saarbarheder_tekst": "Relevante sårbarheder/manglende foranstaltninger. Vær ærlig om svagheder; hvis idealiseret opsætning, nævn restrisici.",
    "tiltag_tekst": "Tekniske og organisatoriske foranstaltninger der skal implementeres for at reducere de identificerede risici. Konkret, nummereret hvis muligt. Referér til de vigtigste risici.",
    "ansvarlige_tiltag_tekst": "Hvem er ansvarlig for implementeringen af tiltagene. Nævn Partheepan (tekniske) og relevante organisatoriske ansvarlige.",
    "kontrolmekanismer_tekst": "Hvordan risici løbende overvåges (logning, audits, rapportering, reviews). MÅ IKKE starte med 'Kontrolmekanismer:'.",
    "opdatering_tekst": "Hvornår og hvordan risikovurderingen opdateres (fx ved væsentlige ændringer, minimum årligt). MÅ IKKE starte med 'Opdatering af risikovurdering:'.",
}


SYSTEM_PROMPT = """Du er en compliance-konsulent for Kalundborg Kommune der skriver
en databeskyttelsesretlig risikovurdering. Du skriver de tekstfelter der ikke er
selve risikoskemaet.

Faste forhold (brug disse — opfind dem ikke):
- Dataansvarlig: Kalundborg Kommune (CVR 29189595)
- Teknisk ansvarlig: Partheepan Vijayamohan, AI Program Lead
- Organisatorisk ansvarlig: Anne Dandanell
- Hosting (idealiseret hvis ikke andet oplyst): Microsoft Azure i EU-region, sikret bag
  Entra ID, credentials i Azure Key Vault

Skriv sagligt, konkret og myndighedsegnet dansk — IKKE konsulent-glat, ingen floskler.
Hvert felt skal kunne stå i et officielt kommunalt dokument. Brug systemets faktiske
navn og egenskaber.

Du svarer KUN med valid JSON: en dict med præcis disse nøgler (én streng pr. felt):
formaal_tekst, omfang_tekst, ansvarlige_tekst, baggrund_tekst, funktionalitet_tekst,
interessenter_tekst, personoplysninger_tekst, lokationer_tekst, adgangsrettigheder_tekst,
saarbarheder_tekst, tiltag_tekst, ansvarlige_tiltag_tekst, kontrolmekanismer_tekst,
opdatering_tekst.

KRITISK JSON-FORMAT: Hver feltværdi skal være ÉN sammenhængende string på én linje
— brug ALDRIG rå linjeskift inde i en string (skriv mellemrum i stedet). Ingen
trailing commas. Ingen kommentarer. Kun gyldig JSON."""


def generate_content(
    facts: SystemFacts,
    risks: list[Risiko],
    *,
    timeout: float = 120.0,
) -> dict[str, str]:
    """Generér de 14 prosa-felttekster. Returnér dict {feltnavn: tekst}."""
    user_message = _build_user_prompt(facts, risks)
    try:
        data = chat_json(SYSTEM_PROMPT, user_message, temperature=0.2, timeout=timeout, expect="object")
    except RiskLLMError:
        raise
    except Exception as exc:  # pragma: no cover
        raise RiskLLMError(f"Indholds-generering fejlede: {exc}") from exc

    if not isinstance(data, dict):
        raise RiskLLMError("Indholds-generering returnerede ikke et JSON-object")

    out: dict[str, str] = {}
    for key in FIELD_SPECS:
        val = data.get(key)
        out[key] = str(val).strip() if val else ""
    return out


def _build_user_prompt(facts: SystemFacts, risks: list[Risiko]) -> str:
    field_instructions = "\n".join(
        f"- {key}: {spec.format(systemnavn=facts.systemnavn or 'systemet')}"
        for key, spec in FIELD_SPECS.items()
    )
    risk_summary = "\n".join(
        f"  - [{r.score.value}] {r.risiko}" for r in risks[:12]
    ) or "  (ingen risici identificeret endnu)"

    kats = ", ".join(k.value for k in facts.persondata_kategorier) or "ukendt"
    return f"""SYSTEMFAKTA:
Systemnavn: {facts.systemnavn}
Leverandør: {"INTERNT UDVIKLET" if facts.internt_udviklet else (facts.leverandoer_navn or "ukendt")} ({facts.leverandoer_land})
Formål: {facts.formaal_kort}
Funktionalitet: {facts.funktionalitet}
Hosting: {facts.hosting_lokation or "(antag Azure EU-region, idealiseret)"}
Persondata: {kats} — typer: {", ".join(facts.persondata_typer) or "ukendt"}
Registrerede: {", ".join(facts.registrerede) or "ukendt"}
Authentication: {facts.authentication or "(antag Entra ID + MFA)"}
Medarbejderovervågning: {"JA — kræver TR/MED-inddragelse" if facts.medarbejder_overvaagning else "nej"}
Scope: {facts.scope} | Tilgang: {facts.tilgang}
Ekstra interessenter: {", ".join(facts.ekstra_interessenter) or "(ingen ud over standard)"}

IDENTIFICEREDE RISICI (referér de vigtigste i tiltag-feltet):
{risk_summary}

SKRIV DISSE FELTER (JSON-nøgle: instruks):
{field_instructions}

Returnér JSON-dict med alle 14 felter."""
