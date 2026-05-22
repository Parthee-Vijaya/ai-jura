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
   - Manglende awareness-træning"""


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

    return f"""SYSTEMFAKTA:
Systemnavn: {facts.systemnavn}
Leverandør: {facts.leverandoer_navn or "(internt udviklet)" if not facts.internt_udviklet else "INTERNT UDVIKLET"} ({facts.leverandoer_land}){f", CVR {facts.leverandoer_cvr}" if facts.leverandoer_cvr else ""}{f", stiftet {facts.leverandoer_stiftet_aar}" if facts.leverandoer_stiftet_aar else ""}
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

Generér nu 8-12 systemspecifikke risici som JSON."""
