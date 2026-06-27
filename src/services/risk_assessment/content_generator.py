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


# Faste forhold for Kalundborg Kommune (hard-coded — ikke LLM-genereret).
# Bygger på Retningslinjer for IT-anskaffelser + Tjekliste for AI-løsninger.
FASTE_FORHOLD = {
    "dataansvarlig": "Kalundborg Kommune (CVR 29189595)",
    "teknisk_ansvarlig": "Partheepan Vijayamohan, AI Program Lead",
    "organisatorisk_ansvarlig": "Anne Dandanell",
    # Indkøbsproces — jf. Retningslinjer for IT-anskaffelser
    "kontrakt_underskriver": "Digitaliserings- og IT-chefen (underskriver altid kontraktgrundlaget og databehandleraftalen)",
    "team_oekonomi_udbud": "Team Økonomi og Udbud (vurderer udbudspligt + bistår udbudsproces)",
    # Databeskyttelse + AI-tjekliste
    "dpo": "Databeskyttelsesrådgiver (DPO) — modtager udkast til konsekvensanalyse (DPIA)",
    "ai_gruppen": "AI-gruppen (juridisk + teknisk afklaring af AI-tjeklistens punkter)",
    "it_sikkerhedsambassadoer": "Afdelingens IT-sikkerhedsambassadør (kender fortegnelsen over behandlingsaktiviteter, art. 30)",
    # Arkitektur-baseline
    "arkitektur_baseline": (
        "Løsningen skal indpasses i Den Fælleskommunale Rammearkitektur og i størst muligt "
        "omfang anvende Den Fælleskommunale Serviceplatform til adgang til data og funktionalitet"
    ),
    # Procesreference
    "proces_reference": (
        "Anskaffelsen følger Kalundborg Kommunes Retningslinjer for IT-anskaffelser "
        "samt Tjekliste for indkøb og anvendelse af AI-løsninger"
    ),
    # Udbudsterskel (2022) — set over 4 år
    "udbudsterskel_kr": 1601944,
}

# De 14 felter der skal genereres + kort instruks pr. felt.
# Tiltag/interessenter/ansvarlige refererer eksplicit til Kalundborg-aktører.
FIELD_SPECS = {
    "formaal_tekst": "Formål-feltet. 4-6 sætninger. Begynd: 'Formålet med denne risikovurdering er at identificere, vurdere og håndtere databeskyttelsesretlige risici forbundet med Kalundborg Kommunes anvendelse af {systemnavn} – ...'. Beskriv kort hvad systemet er. Slut med standard-formulering om GDPR + databeskyttelsesloven + ISO 27001/27005-principper.",
    "omfang_tekst": "Omfang-feltet. 2-4 sætninger. Hvilke dele af projektet dækker vurderingen (hele systemet / specifikke moduler / POC vs bred udrulning afhængig af scope). Hvis kontraktværdien overstiger udbudsterskel (1.601.944 kr. over 4 år), nævn at vurderingen indgår i en EU-udbudsproces.",
    "ansvarlige_tekst": "Ansvarlige for udarbejdelsen. Nævn teknisk ansvarlig (Partheepan Vijayamohan, AI Program Lead) og organisatorisk ansvarlig (Anne Dandanell). Nævn at Digitaliserings- og IT-chefen underskriver kontrakt + databehandleraftale, at DPO inddrages, og at AI-gruppen bistår med juridisk/teknisk afklaring jf. AI-tjeklisten.",
    "baggrund_tekst": "Projektets baggrund. 3-5 sætninger om hvorfor systemet anskaffes/udvikles og hvilken kontekst det indgår i. Referér til Kalundborg Kommunes Retningslinjer for IT-anskaffelser hvis anskaffelsesvejen er kendt.",
    "funktionalitet_tekst": "Systemets funktionalitet. 3-5 sætninger teknisk beskrivelse: hvad systemet gør, integrationer, dataflows. Nævn indpasning i Den Fælleskommunale Rammearkitektur og brug af Serviceplatformen hvis relevant.",
    "interessenter_tekst": "Interessenter. Start med 'Dataansvarlig: Kalundborg Kommune'. Nævn: relevante interne afdelinger (Digitalisering og IT, Team Økonomi og Udbud, DPO, fagenheden), eksterne leverandører + underdatabehandlere, og de registrerede grupper. Hvis ekstra interessenter er angivet, inkludér dem.",
    "personoplysninger_tekst": "Hvilke personoplysninger behandles (almindelige/følsomme/CPR/strafbare) og om hvem. Vær konkret ud fra fakta.",
    "lokationer_tekst": "Lokationer og it-systemer. Hosting (fx Azure EU-region), hvilke systemer data flyder gennem.",
    "adgangsrettigheder_tekst": "Styring af adgangsrettigheder. Authentication (Entra ID/MFA), rollebaseret adgang, hvem har adgang.",
    "saarbarheder_tekst": "Relevante sårbarheder/manglende foranstaltninger. Vær ærlig om svagheder; hvis idealiseret opsætning, nævn restrisici. Inkludér procesrisici (fx manglende tidlig involvering af Digitalisering og IT, manglende styregruppe ved EU-udbud) hvis fakta indikerer det.",
    "tiltag_tekst": "Tekniske og organisatoriske foranstaltninger. Vær konkret og nummereret. Referér til de vigtigste risici. Inkludér ALTID følgende Kalundborg-obligatoriske tiltag hvor de er relevante: (1) tidlig advisering af Digitalisering og IT; (2) vurdering af udbudspligt med Team Økonomi og Udbud; (3) indpasning i Den Fælleskommunale Rammearkitektur + Serviceplatform; (4) databehandleraftale underskrevet af Digitaliserings- og IT-chefen; (5) tilmelding til fortegnelse efter art. 30 via IT-sikkerhedsambassadøren; (6) opfyldelse af oplysningspligt efter art. 13-14; (7) vurdering af DPIA-behov + fremsendelse af udkast til DPO; (8) dokumenteret AI-færdigheds-træning iht. AI-forordningens art. 4; (9) Contract Management-plan for driftsperioden.",
    "ansvarlige_tiltag_tekst": "Hvem er ansvarlig for implementeringen af tiltagene. Partheepan Vijayamohan ansvarlig for tekniske tiltag. Digitaliserings- og IT-chefen underskriver kontrakt + databehandleraftale. DPO involveres i konsekvensanalyse. Anne Dandanell ansvarlig for organisatoriske tiltag og MED-/TR-inddragelse hvis relevant.",
    "kontrolmekanismer_tekst": "Hvordan risici løbende overvåges (logning via Azure Monitor, audits, periodiske reviews, Contract Management). MÅ IKKE starte med 'Kontrolmekanismer:'.",
    "opdatering_tekst": "Hvornår og hvordan risikovurderingen opdateres. Som minimum årligt; ved væsentlige ændringer i behandlingsaktiviteter, leverandørforhold, særlovgivning eller efter henstilling fra DPO. MÅ IKKE starte med 'Opdatering af risikovurdering:'.",
}


SYSTEM_PROMPT = """Du er en compliance-konsulent for Kalundborg Kommune der skriver
en databeskyttelsesretlig risikovurdering. Du skriver de tekstfelter der ikke er
selve risikoskemaet.

KOMMUNALE FASTE FORHOLD (brug disse — opfind dem ikke):
- Dataansvarlig: Kalundborg Kommune (CVR 29189595)
- Teknisk ansvarlig: Partheepan Vijayamohan, AI Program Lead
- Organisatorisk ansvarlig: Anne Dandanell
- Kontrakt-underskriver: Digitaliserings- og IT-chefen (underskriver altid kontrakten
  + databehandleraftalen — jf. Retningslinjer for IT-anskaffelser)
- DPO: skal modtage udkast til konsekvensanalyse (DPIA)
- AI-gruppen: bistår med juridisk og teknisk afklaring (jf. AI-tjeklisten)
- IT-sikkerhedsambassadør: ansvarlig for afdelingens fortegnelse efter art. 30
- Team Økonomi og Udbud: vurderer udbudspligt og bistår udbudsproces
- Hosting (idealiseret hvis ikke andet oplyst): Microsoft Azure i EU-region, sikret bag
  Entra ID, credentials i Azure Key Vault

KOMMUNAL ARKITEKTUR-BASELINE:
- Løsningen skal indpasses i Den Fælleskommunale Rammearkitektur
- Skal i størst muligt omfang anvende Den Fælleskommunale Serviceplatform til adgang
  til data og funktionalitet

KOMMUNAL INDKØBSPROCES (jf. Retningslinjer for IT-anskaffelser):
- Tærskel for EU-udbudspligt: kr. 1.601.944 (2022), beregnet over 4 år
- 6 obligatoriske procespunkter: tidlig advisering til Digitalisering og IT, rådgivning
  før markedsdialog, vurdering af udbudspligt, IT-arkitektur-krav, CIO-underskrift,
  Contract Management
- Ved EU-udbud kræves: projektorganisering, business case til Direktionen, styregruppe

KOMMUNAL AI-TJEKLISTE (særligt vigtige punkter):
- Særlovgivning: fagområdets relevante særlov skal kortlægges og overholdelse dokumenteres
- National lovhjemmel: behandling kræver national hjemmel UDOVER GDPR-grundlag
- Formålsbegrænsning (art. 5(1)(b)), behandlingsgrundlag (art. 6/9), oplysningspligt
  (art. 13-14), fortegnelse (art. 30)
- AI-færdigheder hos brugerne (AI-forordningens art. 4) skal dokumenteres

Skriv sagligt, konkret og myndighedsegnet dansk — IKKE konsulent-glat, ingen floskler.
Hvert felt skal kunne stå i et officielt kommunalt dokument. Brug systemets faktiske
navn og egenskaber. Nævn relevante kommunale aktører + frameworks hvor de hører hjemme.

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
        # sensitivity="metadata": kun strukturerede facts + risiko-titler i prompten
        # — ingen rå dokumenter. Må bruge Nemotron hvis konfigureret.
        data = chat_json(
            SYSTEM_PROMPT, user_message, temperature=0.2, timeout=timeout,
            expect="object", sensitivity="metadata",
        )
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

    udbud_status = facts.er_over_udbudsterskel()
    udbud_line = (
        f"OVER tærskel — {facts.kontraktvaerdi_label()}" if udbud_status is True
        else f"under tærskel — {facts.kontraktvaerdi_label()}" if udbud_status is False
        else "ukendt"
    )
    proces_done, proces_total = facts.proces_status_count()

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

KOMMUNAL INDKØBSPROCES (jf. Retningslinjer + AI-tjekliste):
Anskaffelsesvej: {facts.anskaffelsesvej.value}
Kontraktværdi over 4 år: {udbud_line}
Fagområde: {facts.fagomraade or "(ikke angivet)"}
Særlovgivning: {", ".join(facts.saerlovgivning) or "(ikke angivet — nævn at den skal kortlægges)"}
National lovhjemmel: {facts.national_lovhjemmel or "(ikke angivet — nævn at den kræves UDOVER GDPR)"}
Procesforhold: {proces_done}/{proces_total} gennemført
  - D&IT tidlig involvering: {"ja" if facts.dit_involveret_tidligt else "MANGLER"}
  - CIO-underskrift: {"ja" if facts.cio_har_underskrevet else "MANGLER"}
  - DBA indgået: {"ja" if facts.databehandleraftale_indgaaet else "MANGLER"}
  - Styregruppe (EU-udbud): {"ja" if facts.styregruppe_etableret else "MANGLER"}
  - Fortegnelse art. 30: {"ja" if facts.fortegnelse_art30_opdateret else "MANGLER"}
  - Oplysningspligt art. 13-14: {"ja" if facts.oplysningspligt_opfyldt else "MANGLER"}
  - DPIA sendt til DPO: {"ja" if facts.dpia_sendt_til_dpo else "MANGLER"}
  - AI-færdigheder art. 4: {"ja" if facts.ai_faerdigheder_dokumenteret else "MANGLER"}
  - Contract Management-plan: {"ja" if facts.contract_management_plan else "MANGLER"}

DATATILSYN-SKABELON — afklarede DPIA-forhold (brug i de relevante felttekster):
{chr(10).join(f"  - {k}: {v}" for k, v in facts.datatilsyn_svar.items()) or "  (ingen afklaret)"}

IDENTIFICEREDE RISICI (referér de vigtigste i tiltag-feltet):
{risk_summary}

SKRIV DISSE FELTER (JSON-nøgle: instruks):
{field_instructions}

Tiltag-feltet skal eksplicit referere de MANGLENDE procesforhold som konkrete handlinger.
Indarbejd Datatilsyn-svarene i de relevante felter: behandlingsgrundlag i
personoplysninger_tekst/baggrund, automatiske afgørelser + nødvendighed i
saarbarheder_tekst, opbevaring i personoplysninger_tekst.
Returnér JSON-dict med alle 14 felter."""
