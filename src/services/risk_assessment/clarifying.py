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
    SystemFacts,
)


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
        options=[
            "Under 1,6 mio. kr.",
            "1,6 - 5 mio. kr.",
            "Over 5 mio. kr.",
            "Ved ikke endnu",
        ],
        default="Ved ikke endnu",
        reason="Tærskel kr. 1.601.944 (2022) afgør EU-udbudspligt jf. Retningslinjer for IT-anskaffelser.",
    ))

    questions.append(ClarifyingQuestion(
        key="anskaffelsesvej",
        question="Hvilken anskaffelsesvej er valgt?",
        type="radio",
        options=[
            "SKI - direkte tildeling",
            "SKI - mini-udbud",
            "Under tærskel (ingen udbudspligt)",
            "EU-udbud",
            "Bygge- og anlægsprojekt",
            "Endnu ikke afklaret",
        ],
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
        options=[
            "Digitalisering og IT adviseret tidligt",
            "CIO har underskrevet kontrakt + DBA",
            "Databehandleraftale indgået",
            "Styregruppe etableret (EU-udbud)",
            "Tilmeldt fortegnelse art. 30 (via IT-sikkerhedsambassadør)",
            "Oplysningspligt opfyldt (art. 13-14)",
            "DPIA-udkast sendt til DPO",
            "AI-færdigheder dokumenteret (AI-forord. art. 4)",
            "Contract Management-plan klar",
        ],
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

    # ---- Kalundborg-specifikke svar ----

    if "kontraktvaerdi_bucket" in answers and answers["kontraktvaerdi_bucket"]:
        v = str(answers["kontraktvaerdi_bucket"]).lower()
        # Konvertér bucket → repræsentativ midt-værdi (bruges af tærskel-tjek)
        if "under 1,6" in v:
            data.kontraktvaerdi_4aar_kr = 800_000          # under tærskel
        elif "1,6 - 5" in v or "1,6-5" in v:
            data.kontraktvaerdi_4aar_kr = 3_000_000        # over tærskel
        elif "over 5" in v:
            data.kontraktvaerdi_4aar_kr = 7_500_000        # langt over tærskel
        # "Ved ikke endnu" → bevarer None / eksisterende værdi

    if "anskaffelsesvej" in answers and answers["anskaffelsesvej"]:
        v = str(answers["anskaffelsesvej"]).lower()
        if "direkte tildeling" in v:
            data.anskaffelsesvej = Anskaffelsesvej.SKI_DIREKTE
        elif "mini-udbud" in v:
            data.anskaffelsesvej = Anskaffelsesvej.SKI_MINIUDBUD
        elif "under tærskel" in v:
            data.anskaffelsesvej = Anskaffelsesvej.UNDER_TAERSKEL
        elif "eu-udbud" in v:
            data.anskaffelsesvej = Anskaffelsesvej.EU_UDBUD
        elif "bygge" in v:
            data.anskaffelsesvej = Anskaffelsesvej.BYGGE_ANLAEG

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
        items_lower = [str(x).lower() for x in items]

        def _has(substr: str) -> bool:
            return any(substr in i for i in items_lower)

        data.dit_involveret_tidligt = _has("digitalisering og it adviseret")
        data.cio_har_underskrevet = _has("cio har underskrevet")
        data.databehandleraftale_indgaaet = _has("databehandleraftale indgået")
        data.styregruppe_etableret = _has("styregruppe etableret")
        data.fortegnelse_art30_opdateret = _has("fortegnelse art. 30")
        data.oplysningspligt_opfyldt = _has("oplysningspligt opfyldt")
        data.dpia_sendt_til_dpo = _has("dpia-udkast sendt til dpo")
        data.ai_faerdigheder_dokumenteret = _has("ai-færdigheder dokumenteret")
        data.contract_management_plan = _has("contract management-plan")

    return data
