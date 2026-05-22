"""Afklarende spørgsmål — beregn hvilke 3-5 spørgsmål brugeren skal svare på.

Standard-spørgsmål stilles altid (scope, tilgang). Yderligere spørgsmål vises
KUN hvis fact-ekstraktionen har huller (fx hosting-land ukendt).
"""

from src.services.risk_assessment.models import ClarifyingQuestion, DataKategori, SystemFacts


def build_questions(facts: SystemFacts) -> list[ClarifyingQuestion]:
    """Returnér de spørgsmål der skal stilles ud fra huller i facts."""
    questions: list[ClarifyingQuestion] = []

    # 1. Scenarie (altid)
    questions.append(ClarifyingQuestion(
        key="scope",
        question="Hvilket scenarie skal vurderes?",
        type="radio",
        options=["POC / pilot", "Bred udrulning", "Begge"],
        default="Begge",
        reason="Scope påvirker sandsynlighedsvurderingen og hvilke risici der er relevante.",
    ))

    # 2. Tilgang (altid)
    questions.append(ClarifyingQuestion(
        key="tilgang",
        question="Idealiseret eller realistisk vurdering?",
        type="radio",
        options=["Idealiseret (best practices på plads)", "Realistisk (nuværende tilstand)"],
        default="Idealiseret (best practices på plads)",
        reason="Idealiseret antager Entra ID, Key Vault, EU-region, databehandleraftaler på plads.",
    ))

    # 3. Datakategorier — forudfyld fra DBA-ekstraktion, men lad bruger bekræfte
    detected = [k.value for k in facts.persondata_kategorier]
    questions.append(ClarifyingQuestion(
        key="persondata_kategorier",
        question="Hvilke kategorier af personoplysninger behandles?",
        type="multiselect",
        options=["almindelige", "følsomme", "cpr", "strafbare", "ingen"],
        default=",".join(detected) if detected else None,
        reason="Følsomme/CPR/strafbare hæver risikoniveauet og kan udløse DPIA-krav.",
    ))

    # 4. Medarbejderovervågning — auto-detect, men bekræft hvis usikkert
    questions.append(ClarifyingQuestion(
        key="medarbejder_overvaagning",
        question="Overvåger systemet medarbejderadfærd?",
        type="radio",
        options=["Ja", "Nej"],
        default="Ja" if facts.medarbejder_overvaagning else "Nej",
        reason="Medarbejderovervågning kræver TR/MED-inddragelse og oplysning efter art. 13.",
    ))

    # 5. Betingede huller — kun hvis fakta mangler
    if not facts.hosting_lokation:
        questions.append(ClarifyingQuestion(
            key="hosting_lokation",
            question="Hvor hostes systemet?",
            type="text",
            reason="Kunne ikke udledes fra dokumenterne — afgørende for tredjelandsvurdering.",
        ))
    elif not facts.ekstra_interessenter:
        # Hvis vi allerede har hosting, brug 5. plads til interessent-spørgsmål
        questions.append(ClarifyingQuestion(
            key="ekstra_interessenter",
            question="Specifikke interessenter ud over standard? (valgfrit)",
            type="text",
            reason="Fx specifikke afdelinger, fagforeninger eller eksterne parter.",
        ))

    return questions[:5]


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
            key = str(it).strip().lower()
            for kat in DataKategori:
                if kat.value == key and kat not in kats:
                    kats.append(kat)
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

    return data
