"""Afklarende spørgsmål — beregn hvilke spørgsmål brugeren skal svare på.

Standard-spørgsmål stilles altid (scope, tilgang, kontraktværdi, anskaffelsesvej).
Yderligere spørgsmål vises betinget (fx hosting-land kun hvis ukendt).

Spørgsmålene populerer både GDPR-fakta (kategorier, overvågning) og de Kalundborg-
specifikke procesforhold (kontraktværdi, anskaffelsesvej, fagområde, processtatus).
"""

from src.services.risk_assessment.models import (
    Anskaffelsesvej,
    ClarifyingQuestion,
    DataKategori,
    PROCES_PUNKTER,
    SystemFacts,
)

# Centrale option-maps — options genereres herfra OG svar matches mod dem.
# Exact match (normaliseret) først, substring som fallback for robusthed.
KONTRAKTVAERDI_BUCKETS: list[tuple[str, int | None]] = [
    ("Under 1,6 mio. kr.", 800_000),
    ("1,6 - 5 mio. kr.", 3_000_000),
    ("Over 5 mio. kr.", 7_500_000),
    ("Ved ikke endnu", None),
]

ANSKAFFELSESVEJ_OPTIONS: list[tuple[str, Anskaffelsesvej]] = [
    ("SKI - direkte tildeling", Anskaffelsesvej.SKI_DIREKTE),
    ("SKI - mini-udbud", Anskaffelsesvej.SKI_MINIUDBUD),
    ("Under tærskel (ingen udbudspligt)", Anskaffelsesvej.UNDER_TAERSKEL),
    ("EU-udbud", Anskaffelsesvej.EU_UDBUD),
    ("Bygge- og anlægsprojekt", Anskaffelsesvej.BYGGE_ANLAEG),
    ("Endnu ikke afklaret", Anskaffelsesvej.UKENDT),
]


def _norm(s) -> str:
    return str(s).strip().lower()


def build_questions(facts: SystemFacts) -> list[ClarifyingQuestion]:
    """Returnér de spørgsmål der skal stilles ud fra huller i facts."""
    questions: list[ClarifyingQuestion] = []

    # ---- GDPR-/vurderings-spørgsmål (altid) ----
    questions.append(ClarifyingQuestion(
        key="scope",
        question="Hvilket scenarie skal vurderes?",
        type="radio",
        options=["POC / pilot", "Bred udrulning", "Begge"],
        default="Begge",
        reason="Scope påvirker sandsynlighedsvurderingen og hvilke risici der er relevante.",
    ))

    questions.append(ClarifyingQuestion(
        key="tilgang",
        question="Idealiseret eller realistisk vurdering?",
        type="radio",
        options=["Idealiseret (best practices på plads)", "Realistisk (nuværende tilstand)"],
        default="Idealiseret (best practices på plads)",
        reason="Idealiseret antager Entra ID, Key Vault, EU-region, databehandleraftaler på plads.",
    ))

    detected = [k.value for k in facts.persondata_kategorier]
    questions.append(ClarifyingQuestion(
        key="persondata_kategorier",
        question="Hvilke kategorier af personoplysninger behandles?",
        type="multiselect",
        options=["almindelige", "følsomme", "cpr", "strafbare", "ingen"],
        default=",".join(detected) if detected else None,
        reason="Følsomme/CPR/strafbare hæver risikoniveauet og kan udløse DPIA-krav.",
    ))

    questions.append(ClarifyingQuestion(
        key="medarbejder_overvaagning",
        question="Overvåger systemet medarbejderadfærd?",
        type="radio",
        options=["Ja", "Nej"],
        default="Ja" if facts.medarbejder_overvaagning else "Nej",
        reason="Medarbejderovervågning kræver TR/MED-inddragelse og oplysning efter art. 13.",
    ))

    # ---- Kalundborg-specifikke procesforhold (jf. Retningslinjer + AI-tjekliste) ----

    questions.append(ClarifyingQuestion(
        key="kontraktvaerdi_bucket",
        question="Estimeret kontraktværdi over 4 år?",
        type="radio",
        options=[label for label, _ in KONTRAKTVAERDI_BUCKETS],
        default="Ved ikke endnu",
        reason="Tærskel kr. 1.601.944 (2022) afgør EU-udbudspligt jf. Retningslinjer for IT-anskaffelser.",
    ))

    questions.append(ClarifyingQuestion(
        key="anskaffelsesvej",
        question="Hvilken anskaffelsesvej er valgt?",
        type="radio",
        options=[label for label, _ in ANSKAFFELSESVEJ_OPTIONS],
        default="Endnu ikke afklaret",
        reason="Forskellige indkøbsveje udløser forskellige procesrisici.",
    ))

    questions.append(ClarifyingQuestion(
        key="fagomraade_saerlov",
        question="Hvilket fagområde + relevant særlovgivning?",
        type="text",
        default=facts.fagomraade or None,
        reason="Fx 'Beskæftigelse — LAB §17a', 'Sundhed — sundhedsloven kap. 9'. AI-tjeklisten kræver kortlægning.",
    ))

    questions.append(ClarifyingQuestion(
        key="proces_status",
        question="Hvilke procespunkter er allerede gennemført? (sæt kryds)",
        type="multiselect",
        options=[label for _, label in PROCES_PUNKTER],
        default=None,
        reason="Manglende procespunkter bliver til konkrete tiltag i vurderingen.",
    ))

    # ---- Betinget — kun hvis fakta mangler ----
    if not facts.hosting_lokation:
        questions.append(ClarifyingQuestion(
            key="hosting_lokation",
            question="Hvor hostes systemet?",
            type="text",
            reason="Kunne ikke udledes fra dokumenterne — afgørende for tredjelandsvurdering.",
        ))

    return questions  # ingen hård loft — typisk 8-9 spørgsmål


def apply_answers(facts: SystemFacts, answers: dict) -> SystemFacts:
    """Flet bruger-svar ind i SystemFacts. Returnér opdateret kopi."""
    data = facts.model_copy(deep=True)

    if "scope" in answers:
        v = str(answers["scope"]).lower()
        if "poc" in v or "pilot" in v:
            data.scope = "poc"
        elif "bred" in v:
            data.scope = "bred_udrulning"
        else:
            data.scope = "begge"

    if "tilgang" in answers:
        v = str(answers["tilgang"]).lower()
        data.tilgang = "realistisk" if "realistisk" in v else "idealiseret"

    if "persondata_kategorier" in answers:
        raw = answers["persondata_kategorier"]
        items = raw.split(",") if isinstance(raw, str) else (raw or [])
        kats = []
        for it in items:
            key = _norm(it)
            for kat in DataKategori:
                if kat.value == key and kat not in kats:
                    kats.append(kat)
        # Konflikt-resolution: "ingen" sammen med rigtige kategorier er selvmodsigende
        # — de konkrete kategorier vinder, INGEN droppes.
        if DataKategori.INGEN in kats and len(kats) > 1:
            kats = [k for k in kats if k != DataKategori.INGEN]
        if kats:
            data.persondata_kategorier = kats

    if "medarbejder_overvaagning" in answers:
        v = str(answers["medarbejder_overvaagning"]).lower()
        data.medarbejder_overvaagning = v in ("ja", "true", "yes", "1")

    if "hosting_lokation" in answers and answers["hosting_lokation"]:
        data.hosting_lokation = str(answers["hosting_lokation"]).strip()

    if "ekstra_interessenter" in answers and answers["ekstra_interessenter"]:
        raw = answers["ekstra_interessenter"]
        items = raw.split(",") if isinstance(raw, str) else (raw or [])
        data.ekstra_interessenter = [str(x).strip() for x in items if str(x).strip()]

    # ---- Kalundborg-specifikke svar ----

    if "kontraktvaerdi_bucket" in answers and answers["kontraktvaerdi_bucket"]:
        v = _norm(answers["kontraktvaerdi_bucket"])
        # Exact match mod centrale buckets (normaliseret), substring-fallback
        matched = next(
            (pair for pair in KONTRAKTVAERDI_BUCKETS if _norm(pair[0]) == v),
            None,
        ) or next(
            (pair for pair in KONTRAKTVAERDI_BUCKETS
             if pair[1] is not None and _norm(pair[0])[:9] in v),
            None,
        )
        if matched and matched[1] is not None:
            label, value = matched
            data.kontraktvaerdi_4aar_kr = value
            data.kontraktvaerdi_er_estimat = True   # repræsentativ værdi — IKKE faktisk beløb
            data.kontraktvaerdi_bucket_label = label
        # "Ved ikke endnu" / no match → bevarer None / eksisterende værdi

    if "anskaffelsesvej" in answers and answers["anskaffelsesvej"]:
        v = _norm(answers["anskaffelsesvej"])
        matched_vej = next(
            (vej for label, vej in ANSKAFFELSESVEJ_OPTIONS if _norm(label) == v),
            None,
        )
        if matched_vej is None:
            # Substring-fallback (robusthed mod label-varianter)
            if "direkte tildeling" in v:
                matched_vej = Anskaffelsesvej.SKI_DIREKTE
            elif "mini-udbud" in v:
                matched_vej = Anskaffelsesvej.SKI_MINIUDBUD
            elif "under tærskel" in v:
                matched_vej = Anskaffelsesvej.UNDER_TAERSKEL
            elif "eu-udbud" in v:
                matched_vej = Anskaffelsesvej.EU_UDBUD
            elif "bygge" in v:
                matched_vej = Anskaffelsesvej.BYGGE_ANLAEG
        if matched_vej is not None and matched_vej != Anskaffelsesvej.UKENDT:
            data.anskaffelsesvej = matched_vej

    if "fagomraade_saerlov" in answers and answers["fagomraade_saerlov"]:
        raw = str(answers["fagomraade_saerlov"]).strip()
        # Heuristik: alt før " - " eller " — " er fagområde, resten er særlov-stikord
        for sep in (" — ", " - ", ":"):
            if sep in raw:
                left, right = raw.split(sep, 1)
                data.fagomraade = left.strip()
                # Saml særlovgivning som liste — split på komma
                data.saerlovgivning = [
                    s.strip() for s in right.split(",") if s.strip()
                ]
                break
        else:
            data.fagomraade = raw  # ingen separator → kun fagområde

    if "proces_status" in answers and answers["proces_status"]:
        raw = answers["proces_status"]
        items = raw.split(",") if isinstance(raw, str) else (raw or [])
        items_norm = [_norm(x) for x in items if _norm(x)]

        # Match mod PROCES_PUNKTER-labels (single source of truth):
        # exact normaliseret match først, substring-fallback (begge retninger)
        # for robusthed mod afkortede/let ændrede labels.
        for attr, label in PROCES_PUNKTER:
            ln = _norm(label)
            hit = any(i == ln or ln in i or (len(i) >= 12 and i in ln) for i in items_norm)
            setattr(data, attr, hit)

    # ---- Datatilsyn-skabelon-svar (dynamiske dt_-spørgsmål) ----
    # Samles i datatilsyn_svar-dict (uden dt_-præfiks) så de kan bruges som
    # ekstra kontekst i risiko- og indholdsgenereringen.
    dt = dict(data.datatilsyn_svar)
    for k, v in answers.items():
        if k.startswith("dt_") and v not in (None, "", []):
            dt[k[3:]] = v if isinstance(v, str) else ", ".join(map(str, v)) if isinstance(v, list) else str(v)
    if dt:
        data.datatilsyn_svar = dt

    return data
