"""Risiko-identifikation — generér 8-12 systemspecifikke risici via LLM.

Bruger SystemFacts + et risiko-bibliotek-katalog som INSPIRATION (ikke en
tjekliste at brute-force). LLM'en vælger de relevante risici og scorer dem.
"""

import logging
from typing import Any

from src.services.risk_assessment.llm_client import chat_json, RiskLLMError
from src.services.risk_assessment.models import (
    Niveau,
    Risiko,
    SystemFacts,
    normalize_niveau,
)

logger = logging.getLogger("bifrost.risk_assessment.risks")


# Risiko-bibliotek — kategoriseret inspiration. LLM VÆLGER relevante, fyrer ikke alle af.
# Kategori F + G er Kalundborg-specifikke (jf. Retningslinjer for IT-anskaffelser
# + Tjekliste for AI-løsninger).
RISK_LIBRARY = """A. Leverandør-/kontraktrelaterede
   - MSA-klausuler der tillader brug af kundedata til AI-træning/R&D
   - Lavt ansvarsloft / lav indemnification
   - Lille/nystiftet leverandør → kontinuitetsrisiko
   - Manglende exit-plan / vendor lock-in
   - Retention-periode efter ophør

B. Data og overførsel
   - Tredjelandsoverførsel (kap. V)
   - Underdatabehandlerkæde uden for EU
   - Uklare formålsangivelser
   - Utilsigtet eksponering af følsomme oplysninger/CPR i fritekst
   - Manglende eller forsinket sletning

C. Adgang og autentifikation
   - Manglende MFA / SSO
   - For brede roller / manglende RBAC
   - Leverandør-support-adgang uden logning

D. Teknisk arkitektur
   - Browser-extension/desktop-agent som angrebsflade
   - Sårbarheder i tredjepartsbiblioteker
   - Konfigurationsfejl (for løse eller for stramme politikker)
   - Manglende kryptering at rest/in transit

E. Organisatoriske
   - Medarbejderovervågning uden TR/MED-inddragelse
   - Manglende oplysning efter art. 13
   - Manglende DPIA før bred udrulning
   - Manglende awareness-træning

F. Kommunal proces og indkøbs-compliance (Kalundborg Retningslinjer for IT-anskaffelser)
   - Kontraktværdi over 4 år nær eller over tærsklen (kr. 1.601.944, 2022) uden EU-udbud
     → potentielt ulovligt indkøb / udbudsklage
   - Digitalisering og IT ikke involveret tidligt → arkitektur-mismatch + omarbejde
   - Manglende indpasning i Den Fælleskommunale Rammearkitektur
   - Manglende anvendelse af Den Fælleskommunale Serviceplatform til adgang til data
   - Kontrakt ikke underskrevet af Digitaliserings- og IT-chefen
     → ikke formelt indgået handel / uklart kontraktejerskab
   - Manglende ledelsesforankret styregruppe ved EU-udbud
   - Manglende business case / Direktion-godkendelse (EU-udbud)
   - Manglende Contract Management i driftsperioden → kontraktforpligtelser glider

G. Forvaltningsret + særlovgivning (AI-tjeklistens punkter)
   - Manglende national lovhjemmel (GDPR-grundlag alene er ikke tilstrækkeligt)
   - Manglende kortlægning af fagområdets særlovgivning
     (fx serviceloven, sundhedsloven, folkeskoleloven, beskæftigelseslovgivning)
   - Manglende vurdering af forvaltningsretlige principper
     (saglighed, ligebehandling, proportionalitet)
   - Manglende tilmelding til fortegnelse efter art. 30
     (kontakt afdelingens IT-sikkerhedsambassadør)
   - Manglende opfyldelse af oplysningspligt efter art. 13-14
   - DPIA-udkast ikke fremsendt til DPO
   - Manglende dokumenterede AI-færdigheder hos brugerne (AI-forordningens art. 4)
   - Risiko for ulovlig viderebehandling til formål uforenelige med oprindeligt formål"""


SYSTEM_PROMPT = f"""Du er en GDPR- og informationssikkerhedsekspert der identificerer
databeskyttelsesretlige risici for Kalundborg Kommunes brug af et IT-system.

Du får strukturerede fakta om systemet. Generér 8-12 KONKRETE, systemspecifikke
risici. Brug nedenstående risiko-bibliotek som inspiration — VÆLG de relevante,
fyr IKKE alle af. Tilpas hver risiko til det konkrete system og dets fakta.

RISIKO-BIBLIOTEK:
{RISK_LIBRARY}

For hver risiko angiv:
- risiko: kort identifikation (referér konkrete klausuler/komponenter hvor relevant,
  fx "MSA § 6.2 – ...")
- konsekvens_beskrivelse: hel sætning om konkrete konsekvenser FOR DE REGISTREREDE
- sandsynlighed: ét af "Lav", "Lav-middel", "Middel", "Middel-høj", "Høj"
- score: samlet bedømmelse, ét af samme skala
- hvorfor: 2-4 sætninger der begrunder scoren + nævner mitigation

SCORING-VEJLEDNING:
KONSEKVENS (for de registrerede):
  Lav=mindre gene · Lav-middel=afhjælpelig begrænset skade · Middel=væsentlig
  krænkelse der kan afhjælpes · Middel-høj=alvorlig, svær at afhjælpe fuldt ·
  Høj=kritisk (særlig kategori-lækage, CPR-tab, ikke-tilbagekaldelig)
SANDSYNLIGHED (antag IDEALISERET — best practices på plads — medmindre andet oplyst):
  Lav<5%/3år · Lav-middel=5-15% · Middel=15-50% · Middel-høj=50-75% · Høj>75%
SCORE (kombinér med skøn, ikke ren multiplikation):
  Høj konsekvens × Middel sandsynlighed = Høj
  Høj konsekvens × Lav sandsynlighed = Middel-høj
  Middel konsekvens × Middel sandsynlighed = Middel-høj

Du svarer KUN med valid JSON:
{{
  "risici": [
    {{"risiko":"...","konsekvens_beskrivelse":"...","sandsynlighed":"Middel","score":"Høj","hvorfor":"..."}}
  ]
}}

Tonen skal være saglig og myndighedsegnet — IKKE konsulent-glat. 8-12 risici."""


def identify_risks(facts: SystemFacts, *, timeout: float = 120.0) -> list[Risiko]:
    """Generér systemspecifikke risici ud fra SystemFacts."""
    user_message = _build_user_prompt(facts)
    try:
        data = chat_json(SYSTEM_PROMPT, user_message, temperature=0.3, timeout=timeout, expect="object")
    except RiskLLMError:
        raise
    except Exception as exc:  # pragma: no cover
        raise RiskLLMError(f"Risiko-identifikation fejlede: {exc}") from exc

    raw = data.get("risici") if isinstance(data, dict) else data
    if not isinstance(raw, list):
        raise RiskLLMError("Risiko-identifikation returnerede ikke en liste")

    risks: list[Risiko] = []
    for r in raw:
        if not isinstance(r, dict) or not r.get("risiko"):
            continue
        risks.append(Risiko(
            risiko=str(r.get("risiko", "")).strip(),
            konsekvens_beskrivelse=str(r.get("konsekvens_beskrivelse", "")).strip(),
            sandsynlighed=normalize_niveau(r.get("sandsynlighed")),
            score=normalize_niveau(r.get("score")),
            hvorfor=str(r.get("hvorfor", "")).strip(),
        ))
    return risks


def _build_user_prompt(facts: SystemFacts) -> str:
    udb_lines = "\n".join(
        f"  - {u.navn} ({u.land}): {u.rolle}" for u in facts.underdatabehandlere
    ) or "  (ingen angivet)"
    kats = ", ".join(k.value for k in facts.persondata_kategorier) or "ukendt"
    flags = "\n".join(f"  - {c}" for c in facts.msa_risiko_klausuler) or "  (ingen identificeret)"

    # Kalundborg-procesblok. kontraktvaerdi_label() bruger bucket-intervallet
    # ved estimater så LLM aldrig citerer et opdigtet repræsentativt beløb.
    udbud_status = facts.er_over_udbudsterskel()
    udbud_label = (
        f"OVER tærskel — {facts.kontraktvaerdi_label()}" if udbud_status is True
        else f"under tærskel — {facts.kontraktvaerdi_label()}" if udbud_status is False
        else "ukendt værdi"
    )
    mismatch_flag = " ⚠ MISMATCH (værdi over tærskel uden EU-udbud — compliance-risiko)" if facts.udbudspligt_mismatch() else ""
    proces_done, proces_total = facts.proces_status_count()
    proces_missing = []
    if not facts.dit_involveret_tidligt: proces_missing.append("D&IT tidlig involvering")
    if not facts.cio_har_underskrevet: proces_missing.append("CIO-underskrift")
    if not facts.databehandleraftale_indgaaet: proces_missing.append("DBA indgået")
    if not facts.styregruppe_etableret: proces_missing.append("styregruppe")
    if not facts.fortegnelse_art30_opdateret: proces_missing.append("art. 30-fortegnelse")
    if not facts.oplysningspligt_opfyldt: proces_missing.append("art. 13-14 oplysningspligt")
    if not facts.dpia_sendt_til_dpo: proces_missing.append("DPIA til DPO")
    if not facts.ai_faerdigheder_dokumenteret: proces_missing.append("AI-færdigheder art. 4")
    if not facts.contract_management_plan: proces_missing.append("Contract Management-plan")

    # NB: betinget udtryk i parentes — `x or y if cond else z` parser som
    # `(x or y) if cond else z` og gav tidligere "(internt udviklet)"-label
    # til eksterne leverandører med tomt navn.
    leverandoer_label = (
        "INTERNT UDVIKLET" if facts.internt_udviklet
        else (facts.leverandoer_navn or "ukendt leverandør")
    )

    return f"""SYSTEMFAKTA:
Systemnavn: {facts.systemnavn}
Leverandør: {leverandoer_label} ({facts.leverandoer_land}){f", CVR {facts.leverandoer_cvr}" if facts.leverandoer_cvr else ""}{f", stiftet {facts.leverandoer_stiftet_aar}" if facts.leverandoer_stiftet_aar else ""}
Formål: {facts.formaal_kort}
Funktionalitet: {facts.funktionalitet}
Hosting: {facts.hosting_lokation or "ukendt"}
Persondata-kategorier: {kats}
Persondata-typer: {", ".join(facts.persondata_typer) or "ukendt"}
Registrerede: {", ".join(facts.registrerede) or "ukendt"}
Authentication: {facts.authentication or "ukendt"}
Medarbejderovervågning: {"JA" if facts.medarbejder_overvaagning else "nej"}
Internt udviklet: {"JA" if facts.internt_udviklet else "nej"}
Scope: {facts.scope} | Tilgang: {facts.tilgang}

Underdatabehandlere:
{udb_lines}

MSA-røde flag:
{flags}
Ansvarsloft: {facts.ansvarsloft or "ikke angivet"}
IP-indemnification cap: {facts.ip_indemnification_cap or "ikke angivet"}
Retention efter ophør: {facts.retention_efter_ophoer or "ikke angivet"}

KOMMUNAL INDKØBSPROCES (jf. Retningslinjer for IT-anskaffelser + AI-tjekliste):
Anskaffelsesvej: {facts.anskaffelsesvej.value}
Kontraktværdi over 4 år: {udbud_label}{mismatch_flag}
Fagområde: {facts.fagomraade or "(ikke angivet)"}
Særlovgivning nævnt: {", ".join(facts.saerlovgivning) or "(ingen)"}
National lovhjemmel: {facts.national_lovhjemmel or "(ikke angivet — kræves UDOVER GDPR)"}
Procesforhold ({proces_done}/{proces_total} på plads): {"mangler: " + ", ".join(proces_missing) if proces_missing else "alt på plads"}

Generér nu 8-12 systemspecifikke risici som JSON. Inkludér nødvendigvis kategori F-
og G-risici (kommunal proces + forvaltningsret/særlov) når procesforhold mangler
eller når der er udbudspligt-mismatch."""
