"""Dynamisk opfølgnings-motor forankret i Datatilsynets skabeloner.

Hvorfor: De statiske afklarende spørgsmål (clarifying.py) dækker scope, proces
og Kalundborg-forhold. Men en fyldestgørende databeskyttelsesretlig vurdering /
konsekvensanalyse (DPIA) kræver de elementer Datatilsynets skabelon oplister —
jf. databeskyttelsesforordningens art. 35, stk. 7. Denne motor læser de fakta
der er udtrukket FRA de uploadede dokumenter og stiller KUN de opfølgende
spørgsmål, hvor skabelonens elementer endnu ikke er dækket.

To lag:
  1. Deterministisk hul-detektion (build_datatilsyn_questions) — for hvert
     skabelon-element tjekkes om de relevante fakta er på plads; hvis ikke,
     stilles et spørgsmål formuleret efter Datatilsynets terminologi.
  2. LLM-lag (llm_followup_questions) — læser fakta + Datatilsynets
     skabelon-struktur og foreslår op til N sag-specifikke opfølgende spørgsmål
     som en DPO ville stille. Bruger sensitivity="metadata" (kun strukturerede
     fakta, ingen rå dokumenttekst). Falder stille tilbage hvis LLM fejler.

Datatilsynets DPIA-skabelon (art. 35, stk. 7) har fire kerneafsnit:
  (a) systematisk beskrivelse af behandlingen og formålene
  (b) vurdering af nødvendighed og proportionalitet
  (c) vurdering af risici for de registreredes rettigheder
  (d) planlagte foranstaltninger til at imødegå risici
Hertil de generelle risikovurderings-elementer (behandlingsgrundlag, modtagere,
opbevaring, tredjelandsoverførsel, automatiske afgørelser, rettigheder).
"""

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from src.services.risk_assessment.models import (
    ClarifyingQuestion,
    DataKategori,
    SystemFacts,
)
from src.services.risk_assessment.llm_client import chat_json, RiskLLMError

logger = logging.getLogger("bifrost.risk_assessment.datatilsyn")

# Præfiks så svar kan adskilles fra de øvrige clarifying-svar i apply_answers
DT_PREFIX = "dt_"


@dataclass
class DatatilsynElement:
    """Et element fra Datatilsynets skabelon + hvordan vi tjekker om det er dækket."""
    id: str
    sektion: str                                  # hvilket skabelon-afsnit
    covered: Callable[[SystemFacts], bool]        # er elementet allerede dækket af fakta?
    relevant: Callable[[SystemFacts], bool]       # er spørgsmålet overhovedet relevant?
    question: str
    reason: str
    type: str = "radio"
    options: list = field(default_factory=list)
    default: Optional[str] = None


def _har_foelsomme(f: SystemFacts) -> bool:
    return any(
        k in (DataKategori.FOELSOMME, DataKategori.CPR, DataKategori.STRAFBARE)
        for k in f.persondata_kategorier
    )


def _udenfor_eu(f: SystemFacts) -> bool:
    """True hvis hosting eller en underdatabehandler ligger uden for EU/EØS."""
    eu_ord = ("eu", "eø", "danmark", "frankrig", "tyskland", "nederland", "irland",
              "sverige", "norge", "finland", "europa", "west europe", "north europe")
    host = (f.hosting_lokation or "").lower()
    host_udenfor = bool(host) and not any(o in host for o in eu_ord)
    udb_udenfor = any(
        u.land and not any(o in u.land.lower() for o in eu_ord)
        for u in f.underdatabehandlere
    )
    return host_udenfor or udb_udenfor


def _naevner_borgere(f: SystemFacts) -> bool:
    tekst = " ".join(f.registrerede).lower()
    return any(o in tekst for o in ("borger", "barn", "børn", "elev", "patient", "klient", "udsat"))


# ---- Datatilsynet-skabelonens elementer (rækkefølge ~ skabelonens afsnit) ----
DATATILSYN_ELEMENTER: list[DatatilsynElement] = [
    DatatilsynElement(
        id="behandlingsgrundlag",
        sektion="Behandlingsgrundlag (art. 6)",
        covered=lambda f: bool(f.national_lovhjemmel.strip()),
        relevant=lambda f: DataKategori.INGEN not in f.persondata_kategorier or len(f.persondata_kategorier) > 1,
        question="Hvad er behandlingsgrundlaget efter databeskyttelsesforordningens art. 6?",
        type="radio",
        options=[
            "Myndighedsudøvelse / opgave i samfundets interesse (art. 6(1)(e))",
            "Retlig forpligtelse (art. 6(1)(c))",
            "Samtykke (art. 6(1)(a))",
            "Aftale (art. 6(1)(b))",
            "Ved ikke endnu",
        ],
        reason="Datatilsynets skabelon kræver angivelse af behandlingsgrundlag for hver behandling.",
    ),
    DatatilsynElement(
        id="foelsom_undtagelse",
        sektion="Behandlingsgrundlag (art. 9)",
        covered=lambda f: False,
        relevant=_har_foelsomme,
        question="Der behandles følsomme oplysninger eller CPR — hvad er undtagelsen efter art. 9, stk. 2?",
        type="radio",
        options=[
            "Væsentlig samfundsinteresse (art. 9(2)(g))",
            "Social-/sundhedsformål (art. 9(2)(h))",
            "Retskrav (art. 9(2)(f))",
            "Udtrykkeligt samtykke (art. 9(2)(a))",
            "Ved ikke endnu",
        ],
        reason="Følsomme oplysninger kræver både art. 6- OG art. 9-grundlag jf. Datatilsynets skabelon.",
    ),
    DatatilsynElement(
        id="automatiske_afgoerelser",
        sektion="De registreredes rettigheder (art. 22)",
        covered=lambda f: False,
        relevant=lambda f: True,
        question="Træffer systemet helt eller delvist automatiske afgørelser med retsvirkning eller væsentlig betydning for borgeren?",
        type="radio",
        options=[
            "Nej — kun beslutningsstøtte, mennesket afgør",
            "Ja, men med reel menneskelig kontrol (human-in-the-loop)",
            "Ja, helt automatisk",
            "Ved ikke",
        ],
        default="Nej — kun beslutningsstøtte, mennesket afgør",
        reason="Art. 22 forbyder som udgangspunkt helt automatiske afgørelser med væsentlig betydning — kernespørgsmål for AI.",
    ),
    DatatilsynElement(
        id="noedvendighed",
        sektion="Nødvendighed og proportionalitet (art. 35(7)(b))",
        covered=lambda f: False,
        relevant=lambda f: True,
        question="Kunne formålet opnås uden AI eller med et mindre indgribende middel?",
        type="radio",
        options=[
            "Nej — AI er nødvendig for at løse opgaven",
            "Delvist — AI effektiviserer, men alternativ findes",
            "Ja — formålet kan nås uden AI",
            "Ikke vurderet endnu",
        ],
        reason="Datatilsynet kræver en udtrykkelig vurdering af nødvendighed og proportionalitet.",
    ),
    DatatilsynElement(
        id="modtagere",
        sektion="Systematisk beskrivelse — modtagere (art. 35(7)(a))",
        covered=lambda f: False,
        relevant=lambda f: True,
        question="Videregives personoplysninger til modtagere uden for kommunen?",
        type="multiselect",
        options=[
            "Nej — behandles kun internt",
            "Til leverandøren som databehandler",
            "Til andre myndigheder",
            "Til andre tredjeparter",
        ],
        reason="Skabelonen kræver en beskrivelse af modtagere/videregivelse af oplysningerne.",
    ),
    DatatilsynElement(
        id="opbevaring",
        sektion="Systematisk beskrivelse — opbevaring (art. 5(1)(e))",
        covered=lambda f: bool(f.retention_efter_ophoer),
        relevant=lambda f: True,
        question="Hvad er slette-/opbevaringsfristen for personoplysningerne?",
        type="radio",
        options=[
            "Slettes ved sagens afslutning",
            "Fast frist (fx 5 år) jf. særlovgivning",
            "Følger kommunens journaliseringspligt",
            "Ikke fastlagt endnu",
        ],
        reason="Opbevaringsbegrænsning (art. 5(1)(e)) skal fremgå af vurderingen.",
    ),
    DatatilsynElement(
        id="tredjeland",
        sektion="Tredjelandsoverførsel (kap. V)",
        covered=lambda f: False,
        relevant=_udenfor_eu,
        question="Hosting eller en underdatabehandler ser ud til at ligge uden for EU/EØS — hvad er overførselsgrundlaget?",
        type="radio",
        options=[
            "EU-Kommissionens standardkontraktbestemmelser (SCC)",
            "Tilstrækkeligheds-afgørelse (fx EU-US Data Privacy Framework)",
            "Ingen overførsel til tredjeland trods placering",
            "Ved ikke endnu",
        ],
        reason="Overførsel til tredjeland kræver et gyldigt overførselsgrundlag jf. kap. V.",
    ),
    DatatilsynElement(
        id="saarbare",
        sektion="Risici for de registrerede (art. 35(7)(c))",
        covered=lambda f: False,
        relevant=_naevner_borgere,
        question="Omfatter behandlingen sårbare grupper (børn, socialt udsatte, patienter)?",
        type="radio",
        options=[
            "Ja — i væsentligt omfang",
            "Ja — i begrænset omfang",
            "Nej",
            "Ved ikke",
        ],
        reason="Sårbare registrerede hæver risikoen og vægter i konsekvensanalysen.",
    ),
    DatatilsynElement(
        id="oplysningspligt",
        sektion="De registreredes rettigheder (art. 13-14)",
        covered=lambda f: False,
        relevant=lambda f: True,
        question="Hvordan opfyldes oplysningspligten over for de registrerede?",
        type="radio",
        options=[
            "Via kommunens generelle privatlivspolitik",
            "Særskilt information ved denne behandling",
            "Ikke afklaret endnu",
        ],
        reason="Oplysningspligten efter art. 13-14 skal beskrives i vurderingen.",
    ),
]


def build_datatilsyn_questions(facts: SystemFacts) -> list[ClarifyingQuestion]:
    """Deterministisk lag: ét spørgsmål pr. udækket, relevant skabelon-element."""
    out: list[ClarifyingQuestion] = []
    for el in DATATILSYN_ELEMENTER:
        try:
            if el.relevant(facts) and not el.covered(facts):
                out.append(ClarifyingQuestion(
                    key=f"{DT_PREFIX}{el.id}",
                    question=el.question,
                    type=el.type,
                    options=el.options,
                    default=el.default,
                    reason=f"{el.reason} (Datatilsynets skabelon: {el.sektion})",
                ))
        except Exception as exc:
            logger.warning("Datatilsyn-element %s fejlede: %s", el.id, exc)
    return out


_LLM_SYSTEM = """Du er kommunens databeskyttelsesrådgiver (DPO). Du hjælper med at
forberede en databeskyttelsesretlig risikovurdering / konsekvensanalyse efter
Datatilsynets skabelon (databeskyttelsesforordningens art. 35, stk. 7).

Ud fra de oplyste systemfakta skal du formulere KONKRETE opfølgende spørgsmål,
som mangler at blive afklaret, før vurderingen er fyldestgørende. Spørg KUN om
det, fakta ikke allerede afslører. Hold dig til Datatilsynets skabelon-afsnit:
systematisk beskrivelse, nødvendighed/proportionalitet, risici for de
registrerede, og planlagte foranstaltninger.

Svar KUN med valid JSON — et array af op til 4 objekter:
[{"key":"dt_llm_<kort_id>","question":"...","type":"radio|text|multiselect",
  "options":["..."],"reason":"hvorfor det er nødvendigt jf. skabelonen"}]
For type "text": udelad options. Skriv på dansk, myndighedsegnet. Ingen
spørgsmål der gentager de allerede kendte fakta."""


def _facts_oversigt(facts: SystemFacts) -> str:
    kats = ", ".join(k.value for k in facts.persondata_kategorier) or "ukendt"
    udb = ", ".join(f"{u.navn} ({u.land})" for u in facts.underdatabehandlere) or "ingen oplyst"
    return (
        f"Systemnavn: {facts.systemnavn}\n"
        f"Formål: {facts.formaal_kort or 'ukendt'}\n"
        f"Funktionalitet: {facts.funktionalitet or 'ukendt'}\n"
        f"Persondata-kategorier: {kats}\n"
        f"Typer: {', '.join(facts.persondata_typer) or 'ukendt'}\n"
        f"Registrerede: {', '.join(facts.registrerede) or 'ukendt'}\n"
        f"Hosting: {facts.hosting_lokation or 'ukendt'}\n"
        f"Underdatabehandlere: {udb}\n"
        f"Opbevaring efter ophør: {facts.retention_efter_ophoer or 'ukendt'}\n"
        f"National hjemmel: {facts.national_lovhjemmel or 'ukendt'}\n"
        f"Medarbejderovervågning: {'ja' if facts.medarbejder_overvaagning else 'nej'}"
    )


def llm_followup_questions(facts: SystemFacts, *, timeout: float = 60.0) -> list[ClarifyingQuestion]:
    """LLM-lag: sag-specifikke opfølgende spørgsmål. Tom liste ved fejl."""
    try:
        data = chat_json(
            _LLM_SYSTEM,
            "SYSTEMFAKTA:\n" + _facts_oversigt(facts) + "\n\nFormulér de manglende opfølgende spørgsmål som JSON-array.",
            temperature=0.2, timeout=timeout, expect="array", sensitivity="metadata",
            max_attempts=2,
        )
    except RiskLLMError as exc:
        logger.warning("LLM-opfølgningsspørgsmål fejlede (fortsætter uden): %s", str(exc)[:120])
        return []

    out: list[ClarifyingQuestion] = []
    for item in (data or [])[:4]:
        if not isinstance(item, dict) or not item.get("question"):
            continue
        key = str(item.get("key") or f"{DT_PREFIX}llm_{len(out)}")
        if not key.startswith(DT_PREFIX):
            key = DT_PREFIX + "llm_" + key
        qtype = item.get("type") if item.get("type") in ("radio", "text", "multiselect") else "text"
        opts = item.get("options") or []
        out.append(ClarifyingQuestion(
            key=key[:64],
            question=str(item["question"])[:300],
            type=qtype,
            options=[str(o)[:120] for o in opts][:6] if isinstance(opts, list) else [],
            reason=str(item.get("reason") or "Opfølgning jf. Datatilsynets skabelon."),
        ))
    return out


def build_dynamic_questions(
    facts: SystemFacts,
    *,
    use_llm: bool = True,
    timeout: float = 60.0,
    existing_keys: Optional[set] = None,
) -> list[ClarifyingQuestion]:
    """Saml deterministiske + (valgfrit) LLM-genererede opfølgnings-spørgsmål.

    existing_keys: nøgler der allerede stilles af clarifying.build_questions, så
    vi ikke spørger om det samme to gange.
    """
    seen = set(existing_keys or set())
    merged: list[ClarifyingQuestion] = []

    for q in build_datatilsyn_questions(facts):
        if q.key not in seen:
            seen.add(q.key)
            merged.append(q)

    if use_llm:
        for q in llm_followup_questions(facts, timeout=timeout):
            if q.key not in seen:
                seen.add(q.key)
                merged.append(q)

    return merged
