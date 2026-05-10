"""Evidence-artefakt-skabeloner for Bifrosts vurderingsmotor.

Hver regel i Bifrost's korpus producerer en `evidens_påkrævet`-liste med IDs
som `risikostyringsplan`, `dpia_dokument`, `partshoringsbrev` osv.
Hidtil har det bare været en checkliste — sagsbehandleren vidste at de
manglede dokumenterne men måtte selv finde ud af hvad indholdet skulle være.

Denne service leverer en **struktureret skabelon** per artefakt-ID:

  * `title` — dansk display-navn
  * `summary` — 1-2 sætnings forklaring
  * `legal_basis` — liste af lovhjemler ({lov, artikel, citat, url})
  * `external_resources` — links til Datatilsynet, Digitaliseringsstyrelsen,
    EU-AI Office osv. så sagsbehandleren kan slå op
  * `sections` — formular-felter der skal udfyldes (heading + prompt +
    optionel default-tekst + required-flag + felt-type)

Frontend renderer modal'en dynamisk fra `sections`. Backend gemmer svarene
som JSON i `evidence_artifacts`-tabellen og beregner status:

  * `mangler` — ingen sektioner udfyldt
  * `i_gang` — mindst én sektion udfyldt, ikke alle required
  * `faerdig` — alle required-sektioner udfyldt
  * `godkendt` — manuelt sat af jurist/leder (fremtid)

De 19 højest-prioriterede artefakter har detaljerede skabeloner baseret
på aktuel lov + Datatilsynets vejledninger; de øvrige 47 falder tilbage
til en generisk skabelon der lister regelhjemlen og beder om fri tekst.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LegalReference:
    """En enkelt lovhjemmel for en artefakt."""

    lov: str
    artikel: str
    citat: str
    url: str

    def to_dict(self) -> dict:
        return {
            "lov": self.lov,
            "artikel": self.artikel,
            "citat": self.citat,
            "url": self.url,
        }


@dataclass
class ExternalResource:
    """Et eksternt vejledning/standard-link."""

    title: str
    publisher: str  # fx "Datatilsynet", "EU-Kommissionen", "Digitaliseringsstyrelsen"
    url: str
    description: str | None = None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "publisher": self.publisher,
            "url": self.url,
            "description": self.description,
        }


@dataclass
class Section:
    """Et felt i artefakt-formularen."""

    key: str  # snake_case identifier
    heading: str  # vist label
    prompt: str  # forklaring af hvad sagsbehandleren skal skrive
    field_type: str = "textarea"  # textarea | text | enum | boolean | date
    enum_values: list[str] | None = None
    placeholder: str | None = None
    default_text: str | None = None  # pre-fyldt skabelon-tekst
    required: bool = True
    help_url: str | None = None

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "heading": self.heading,
            "prompt": self.prompt,
            "field_type": self.field_type,
            "enum_values": self.enum_values,
            "placeholder": self.placeholder,
            "default_text": self.default_text,
            "required": self.required,
            "help_url": self.help_url,
        }


@dataclass
class ArtifactTemplate:
    """En komplet skabelon-spec for et evidens-artefakt."""

    id: str
    title: str
    summary: str
    category: str  # ai_act | gdpr | forvaltning | sektorlov | sikkerhed | gpai | generic
    legal_basis: list[LegalReference] = field(default_factory=list)
    external_resources: list[ExternalResource] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    estimated_minutes: int = 30  # rough effort-estimat

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "category": self.category,
            "legal_basis": [lr.to_dict() for lr in self.legal_basis],
            "external_resources": [er.to_dict() for er in self.external_resources],
            "sections": [s.to_dict() for s in self.sections],
            "estimated_minutes": self.estimated_minutes,
        }

    def required_section_keys(self) -> set[str]:
        return {s.key for s in self.sections if s.required}


# ============================================================================
# Curated skabeloner — de 19 højest-prioriterede artefakter
# ============================================================================
#
# Hver artefakt er researched mod aktuel lovgivning + Datatilsynets
# vejledninger. Citater er sidst-verificeret 2026-05-09.

_AI_ACT_URL = "https://eur-lex.europa.eu/eli/reg/2024/1689/oj/dan"
_GDPR_URL = "https://eur-lex.europa.eu/eli/reg/2016/679/oj/dan"
_FVL_URL = "https://www.retsinformation.dk/eli/lta/2014/433"


# ---- AI Act-baserede artefakter (6) ---------------------------------------

_RISIKOSTYRINGSPLAN = ArtifactTemplate(
    id="risikostyringsplan",
    title="Risikostyringsplan (AI Act Art. 9)",
    summary=(
        "Et kontinuerligt iterativt risikostyringssystem for hele AI-systemets "
        "livscyklus. Skal identificere kendte og forudsigelige risici mod "
        "sundhed, sikkerhed og grundlæggende rettigheder, samt vurdere risici "
        "der opstår når systemet bruges som tilsigtet eller i forudsigelig misbrug."
    ),
    category="ai_act",
    estimated_minutes=120,
    legal_basis=[
        LegalReference(
            lov="EU AI-forordningen (Forordning 2024/1689)",
            artikel="Artikel 9, stk. 1-9",
            citat=(
                "Der oprettes, gennemføres, dokumenteres og opretholdes et "
                "risikostyringssystem i forbindelse med højrisiko-AI-systemer."
            ),
            url=_AI_ACT_URL,
        ),
    ],
    external_resources=[
        ExternalResource(
            title="ISO/IEC 23894:2023 — AI risk management",
            publisher="ISO",
            url="https://www.iso.org/standard/77304.html",
            description=(
                "Internationalt rammeværk for AI-risikostyring (6 kapitler + 3 bilag). "
                "Bygger på ISO 31000:2018. Annex C kortlægger risikostyring "
                "gennem AI-systemets livscyklus — direkte anvendelig som rygrad."
            ),
        ),
        ExternalResource(
            title="Højrisiko-AI-systemer — Digitaliseringsstyrelsen",
            publisher="Digitaliseringsstyrelsen",
            url="https://digst.dk/tilsyn/ai-forordningen/reglerne-i-ai-forordningen/hoejrisiko-ai-systemer/",
            description="Officiel dansk myndighedsvejledning om AI Act-krav (gælder fra 2. august 2026).",
        ),
        ExternalResource(
            title="Reglerne i AI-forordningen",
            publisher="Digitaliseringsstyrelsen",
            url="https://digst.dk/tilsyn/ai-forordningen/reglerne-i-ai-forordningen/",
        ),
    ],
    sections=[
        Section(
            key="systembeskrivelse",
            heading="Systembeskrivelse",
            prompt="Kort beskrivelse af AI-systemet, dets formål og den tilsigtede anvendelse.",
            placeholder="AI-systemet bruges af sagsbehandlere til at...",
            required=True,
        ),
        Section(
            key="identificerede_risici",
            heading="Identificerede risici (kendte + forudsigelige)",
            prompt=(
                "Liste alle kendte og forudsigelige risici mod sundhed, sikkerhed, "
                "grundlæggende rettigheder. For hver: konsekvens (lav/mellem/høj) + "
                "sandsynlighed (lav/mellem/høj)."
            ),
            default_text=(
                "1. **Risiko:** [beskrivelse]\n"
                "   - Konsekvens: [lav/mellem/høj]\n"
                "   - Sandsynlighed: [lav/mellem/høj]\n"
                "   - Påvirkede rettigheder: [fx ret til ikke-diskrimination, "
                "databeskyttelse, retfærdig sagsbehandling]\n\n"
                "2. **Risiko:** [...]"
            ),
            required=True,
        ),
        Section(
            key="afboedende_foranstaltninger",
            heading="Afbødende foranstaltninger",
            prompt=(
                "Per identificeret risiko: hvilke tekniske og organisatoriske "
                "foranstaltninger reducerer risikoen til acceptabelt niveau?"
            ),
            required=True,
        ),
        Section(
            key="restrisiko_vurdering",
            heading="Restrisiko-vurdering",
            prompt=(
                "Efter foranstaltninger — er restrisikoen acceptabel? "
                "Begrund per risiko."
            ),
            required=True,
        ),
        Section(
            key="post_market_overvaagning",
            heading="Overvågning efter idriftsættelse",
            prompt=(
                "Hvordan overvåges systemet efter ibrugtagning? Hvilke metrikker "
                "indsamles? Hvem har ansvaret? Frekvens for revurdering."
            ),
            required=True,
        ),
        Section(
            key="ansvarlig_person",
            heading="Ansvarlig person/team",
            prompt="Hvem er overordnet ansvarlig for risikostyringsplanen?",
            field_type="text",
            placeholder="Fx: Pavi Vijaya, IT-sikkerhedschef",
            required=True,
        ),
        Section(
            key="naeste_revurdering",
            heading="Næste revurdering",
            prompt="Dato for næste planlagte revurdering (mindst årligt).",
            field_type="date",
            required=True,
        ),
    ],
)

_DATASAET_DOKUMENTATION = ArtifactTemplate(
    id="datasaet_dokumentation",
    title="Datasæt-dokumentation (AI Act Art. 10)",
    summary=(
        "Dokumentation af træning-, validerings- og testdatasæt — herunder "
        "indsamling, kvalitetsegenskaber, bias-vurdering og eventuelle "
        "særlige kategorier af persondata."
    ),
    category="ai_act",
    estimated_minutes=90,
    legal_basis=[
        LegalReference(
            lov="EU AI-forordningen (Forordning 2024/1689)",
            artikel="Artikel 10, stk. 1-6",
            citat=(
                "Højrisiko-AI-systemer der gør brug af teknikker, der involverer "
                "træning af AI-modeller med data, skal udvikles på grundlag af "
                "trænings-, validerings- og testdatasæt, der opfylder kvalitetskriterierne."
            ),
            url=_AI_ACT_URL,
        ),
    ],
    external_resources=[
        ExternalResource(
            title="Datatilsynets vejledning om persondata i AI",
            publisher="Datatilsynet",
            url="https://www.datatilsynet.dk/hvad-siger-reglerne/vejledning",
            description="Krav til persondata-håndtering i AI-systemer.",
        ),
        ExternalResource(
            title="Datasheets for Datasets (Gebru et al.)",
            publisher="Google AI",
            url="https://arxiv.org/abs/1803.09010",
            description="International best-practice for datasæt-dokumentation.",
        ),
    ],
    sections=[
        Section(
            key="datakilder",
            heading="Datakilder",
            prompt=(
                "Hvor stammer træningsdataene fra? Listen alle kilder og deres "
                "respektive andel."
            ),
            placeholder="Kilde 1: ... (X%); Kilde 2: ... (Y%)",
            required=True,
        ),
        Section(
            key="indsamlingsmetode",
            heading="Indsamlingsmetode + retsgrundlag",
            prompt=(
                "Hvordan blev data indsamlet? Med hvilket GDPR-retsgrundlag? "
                "(samtykke / kontrakt / lov / legitim interesse osv.)"
            ),
            required=True,
        ),
        Section(
            key="dataset_storrelse",
            heading="Datasæt-størrelse",
            prompt="Antal rækker/eksempler i train/val/test split.",
            field_type="text",
            placeholder="Train: X, Val: Y, Test: Z",
            required=True,
        ),
        Section(
            key="repraesentativitet",
            heading="Repræsentativitet",
            prompt=(
                "I hvilken udstrækning repræsenterer data den population systemet "
                "skal anvendes på? Geografisk, aldersmæssigt, socioøkonomisk."
            ),
            required=True,
        ),
        Section(
            key="bias_vurdering",
            heading="Bias-vurdering",
            prompt=(
                "Hvilke potentielle bias er identificeret? Hvordan er de testet? "
                "Hvilke afhjælpende skridt er taget?"
            ),
            required=True,
        ),
        Section(
            key="saerlige_kategorier",
            heading="Særlige kategorier af persondata (GDPR art. 9)",
            prompt=(
                "Indeholder datasættet særlige kategorier (helbred, race, religion, "
                "fagforening, seksuel orientering, biometri)? Hvis ja: retsgrundlag?"
            ),
            required=True,
        ),
        Section(
            key="datakvalitet",
            heading="Datakvalitet og rensning",
            prompt=(
                "Beskriv kvalitetskriterier (fuldstændighed, korrekthed, opdaterethed) "
                "og hvordan data er renset (deduplikering, fejlretning, manglende værdier)."
            ),
            required=True,
        ),
        Section(
            key="opbevaring_og_sletning",
            heading="Opbevaring og sletning",
            prompt=(
                "Hvor opbevares datasættet? Hvilken frist for sletning? "
                "Hvordan beskyttes adgangen?"
            ),
            required=True,
        ),
    ],
)

_TEKNISK_DOKUMENTATION_ART11 = ArtifactTemplate(
    id="teknisk_dokumentation_art11",
    title="Teknisk dokumentation (AI Act Art. 11 + Bilag IV)",
    summary=(
        "Den fulde tekniske dokumentation der skal eksistere INDEN systemet "
        "bringes i omsætning eller idriftsættes. Bilag IV beskriver minimum-"
        "indholdet i 9 sektioner. Skal opdateres løbende."
    ),
    category="ai_act",
    estimated_minutes=240,
    legal_basis=[
        LegalReference(
            lov="EU AI-forordningen (Forordning 2024/1689)",
            artikel="Artikel 11 + Bilag IV",
            citat=(
                "Den tekniske dokumentation udarbejdes på en sådan måde, at det "
                "demonstreres, at højrisiko-AI-systemet overholder kravene i dette "
                "kapitel, og giver de kompetente nationale myndigheder de oplysninger, "
                "der er nødvendige for at vurdere overholdelsen."
            ),
            url=_AI_ACT_URL,
        ),
    ],
    external_resources=[
        ExternalResource(
            title="EU AI Office — Technical documentation guidance",
            publisher="EU-Kommissionen",
            url="https://digital-strategy.ec.europa.eu/en/policies/ai-office",
        ),
    ],
    sections=[
        Section(
            key="generel_systembeskrivelse",
            heading="1. Generel beskrivelse af systemet",
            prompt=(
                "Tilsigtet anvendelse, leverandør, version, hvornår systemet er "
                "ibrugtaget, hardware/infrastruktur."
            ),
            required=True,
        ),
        Section(
            key="detaljeret_design",
            heading="2. Detaljeret beskrivelse af elementer + udviklingsproces",
            prompt=(
                "Metoder og trin til udviklingen, design-valg, optimeringsmål, "
                "antagelser om mennesker eller specifikke grupper."
            ),
            required=True,
        ),
        Section(
            key="overvaagning_funktion",
            heading="3. Detaljerede oplysninger om overvågning, drift og kontrol",
            prompt=(
                "Hvordan overvåges, kontrolleres og kan systemet stoppes? "
                "Tilpassede output-tærskler."
            ),
            required=True,
        ),
        Section(
            key="risikostyring",
            heading="4. Risikostyringssystem",
            prompt=(
                "Reference til risikostyringsplanen + sammendrag af de mest "
                "kritiske risici og afhjælpning."
            ),
            required=True,
        ),
        Section(
            key="aendringsstyring",
            heading="5. Beskrivelse af relevante ændringer foretaget af leverandøren",
            prompt="Versionshistorik over substantielle ændringer i systemets livscyklus.",
            required=True,
        ),
        Section(
            key="harmoniserede_standarder",
            heading="6. Liste over harmoniserede standarder anvendt",
            prompt=(
                "Hvilke standarder følger systemet helt eller delvist? "
                "(Endnu ikke obligatorisk indtil EU offentliggør harmoniserede standarder)"
            ),
            required=False,
        ),
        Section(
            key="overensstemmelseserklaering",
            heading="7. Eksempel på EU-overensstemmelseserklæring",
            prompt="Reference til eller udkast til EU-overensstemmelseserklæringen.",
            required=True,
        ),
        Section(
            key="post_market_plan",
            heading="8. Plan for overvågning efter markedsføring (Art. 72)",
            prompt=(
                "Hvordan indsamles og analyseres data om systemets faktiske drift "
                "efter idriftsættelse?"
            ),
            required=True,
        ),
        Section(
            key="indberetnings_procedure",
            heading="9. Procedure for indberetning af alvorlige hændelser (Art. 73)",
            prompt=(
                "Procedure for indberetning til markedsovervågningsmyndigheder ved "
                "alvorlige hændelser eller fejl."
            ),
            required=True,
        ),
    ],
)

_LOGNINGSSPECIFIKATION = ArtifactTemplate(
    id="logningsspecifikation",
    title="Logningsspecifikation (AI Act Art. 12)",
    summary=(
        "Specifikation af automatisk logning der gør det muligt at spore "
        "systemets funktion gennem hele livscyklussen — særligt input, "
        "outputbeslutninger, og hvilke menneskelige oversighters der har grebet ind."
    ),
    category="ai_act",
    estimated_minutes=60,
    legal_basis=[
        LegalReference(
            lov="EU AI-forordningen (Forordning 2024/1689)",
            artikel="Artikel 12, stk. 1-3",
            citat=(
                "Højrisiko-AI-systemer designes og udvikles således, at det er "
                "teknisk muligt automatisk at registrere hændelser ('logger') i "
                "hele systemets livscyklus."
            ),
            url=_AI_ACT_URL,
        ),
        LegalReference(
            lov="GDPR (Forordning 2016/679)",
            artikel="Artikel 30, stk. 1",
            citat=(
                "Hver dataansvarlig fører fortegnelser over de behandlingsaktiviteter, "
                "der hører under dets ansvar."
            ),
            url=_GDPR_URL,
        ),
    ],
    sections=[
        Section(
            key="logget_data",
            heading="Hvad logges?",
            prompt=(
                "Liste over events der logges (input, output, model-version, "
                "konfidensscore, sagsbehandler-ID, override-events)."
            ),
            default_text=(
                "- Tidspunkt for hver inferens\n"
                "- Sags-ID + sagsbehandler-ID\n"
                "- Input-felter (pseudonymiseret hvor muligt)\n"
                "- Model-version og prompt-template\n"
                "- AI-output + konfidensscore\n"
                "- Sagsbehandlerens endelige afgørelse\n"
                "- Eventuel override-årsag"
            ),
            required=True,
        ),
        Section(
            key="opbevaringsfrist",
            heading="Opbevaringsfrist for logs",
            prompt="Hvor længe opbevares logs? Begrund frist mod GDPR-dataminimering.",
            required=True,
        ),
        Section(
            key="adgangskontrol",
            heading="Adgangskontrol",
            prompt="Hvem har adgang til logs? Hvordan logges denne adgang i sig selv?",
            required=True,
        ),
        Section(
            key="aflaesning_og_audit",
            heading="Aflæsning og audit",
            prompt=(
                "Hvordan kan logs aflæses og audites? Findes der dashboards eller "
                "kun rådata-export?"
            ),
            required=True,
        ),
        Section(
            key="rotation_og_arkivering",
            heading="Rotation og arkivering",
            prompt="Hvordan roteres logs? Sikkerhedskopiering. Tamper-evidence.",
            required=False,
        ),
    ],
)

_HUMAN_OVERSIGHT_PROTOKOL = ArtifactTemplate(
    id="human_oversight_protokol",
    title="Menneskelig overvågnings-protokol (AI Act Art. 14)",
    summary=(
        "Detaljeret protokol for hvordan kompetente fysiske personer "
        "fører tilsyn med AI-systemet under brug — så de kan forstå "
        "kapabiliteterne, opdage fejl, modgå automation bias, og "
        "korrekt fortolke output."
    ),
    category="ai_act",
    estimated_minutes=90,
    legal_basis=[
        LegalReference(
            lov="EU AI-forordningen (Forordning 2024/1689)",
            artikel="Artikel 14, stk. 1-5",
            citat=(
                "Højrisiko-AI-systemer designes og udvikles på en sådan måde, "
                "at de kan overvåges effektivt af fysiske personer i den periode, "
                "hvor de er i brug."
            ),
            url=_AI_ACT_URL,
        ),
        LegalReference(
            lov="Forvaltningsloven",
            artikel="§ 22 + § 24",
            citat=(
                "En afgørelse skal, når den meddeles skriftligt, være ledsaget af "
                "en begrundelse... Begrundelsen skal indeholde en henvisning til "
                "de retsregler, i henhold til hvilke afgørelsen er truffet."
            ),
            url=_FVL_URL,
        ),
    ],
    sections=[
        Section(
            key="oversight_kapabilitet",
            heading="Oversight-kapabilitet",
            prompt="Vælg hvilken oversight-model der anvendes.",
            field_type="enum",
            enum_values=[
                "kontinuerlig_human_in_the_loop",
                "efter_afgoerelse_review_paa_alle",
                "efter_afgoerelse_review_paa_stikproever",
                "kun_alarm_ved_fejl",
            ],
            required=True,
        ),
        Section(
            key="kompetencer",
            heading="Krav til oversight-personalets kompetencer",
            prompt=(
                "Hvilken uddannelse, AI-kyndighed (Art. 4), domæneviden + "
                "regulatorisk indsigt skal personalet have?"
            ),
            required=True,
        ),
        Section(
            key="automation_bias_modgang",
            heading="Modgang af automation bias",
            prompt=(
                "Konkrete tiltag for at undgå at sagsbehandlere blindt "
                "overtager AI-output: kalibreringssessioner, blind 2nd opinion, "
                "stikprøvekontrol, advarsler ved høj-risiko-afgørelser."
            ),
            required=True,
        ),
        Section(
            key="stop_override",
            heading="Stop- og override-mulighed",
            prompt=(
                "Hvordan kan en sagsbehandler tilsidesætte/stoppe systemet? "
                "Hvor er stop-knappen? Hvordan dokumenteres override?"
            ),
            required=True,
        ),
        Section(
            key="eskalations_proces",
            heading="Eskalationsproces ved usikkerhed",
            prompt=(
                "Hvad gør sagsbehandleren ved tvivlsom AI-output? "
                "Hvem kontaktes? Tidsfrister."
            ),
            required=True,
        ),
        Section(
            key="oplaering",
            heading="Oplærings-/onboarding-program",
            prompt=(
                "Hvordan oplæres nye sagsbehandlere i at bruge systemet? "
                "Hvor ofte refresher-træning?"
            ),
            required=True,
        ),
    ],
)

_EU_DATABASE_REGISTRERING = ArtifactTemplate(
    id="eu_database_registrering",
    title="EU-database-registrering (AI Act Art. 49 + 71)",
    summary=(
        "Højrisiko-AI-systemer skal registreres i EU's offentlige database "
        "INDEN ibrugtagning. Udbyder + idriftsætter har hver deres registrerings"
        "-pligt i hver deres del af basen."
    ),
    category="ai_act",
    estimated_minutes=45,
    legal_basis=[
        LegalReference(
            lov="EU AI-forordningen (Forordning 2024/1689)",
            artikel="Artikel 49 + Artikel 71 + Bilag VIII",
            citat=(
                "Inden et højrisiko-AI-system bringes i omsætning eller idriftsættes, "
                "registrerer udbyderen eller, hvor det er relevant, den bemyndigede "
                "repræsentant sig selv og deres system i den i artikel 71 omhandlede "
                "EU-database."
            ),
            url=_AI_ACT_URL,
        ),
    ],
    external_resources=[
        ExternalResource(
            title="EU-database for højrisiko-AI-systemer (kommer 2026)",
            publisher="EU-Kommissionen",
            url="https://digital-strategy.ec.europa.eu/en/policies/ai-act",
        ),
    ],
    sections=[
        Section(
            key="rolle",
            heading="Din rolle",
            prompt="Er I udbyder eller idriftsætter?",
            field_type="enum",
            enum_values=["udbyder", "idriftsaetter", "begge"],
            required=True,
        ),
        Section(
            key="udbyder_navn",
            heading="Udbyderens navn + EU-identifikator",
            prompt="Juridisk navn på udbyderen + EU-identifikator hvis tildelt.",
            field_type="text",
            required=True,
        ),
        Section(
            key="system_handelsnavn",
            heading="AI-systemets handelsnavn + version",
            prompt="Det offentlige navn + version-nummer.",
            field_type="text",
            required=True,
        ),
        Section(
            key="bilag_iii_kategori",
            heading="Bilag III-kategori",
            prompt="Hvilken Bilag III-område passer systemet ind i?",
            field_type="enum",
            enum_values=[
                "biometri",
                "kritisk_infrastruktur",
                "uddannelse",
                "beskaeftigelse_arbejdsledelse",
                "vaesentlige_offentlige_tjenester",
                "retshaandhaevelse",
                "migration_asyl",
                "retspleje_demokrati",
            ],
            required=True,
        ),
        Section(
            key="medlemsstater",
            heading="Medlemsstater hvor systemet anvendes",
            prompt="Liste alle medlemsstater hvor systemet er bragt i omsætning eller idriftsat.",
            placeholder="Danmark, Sverige...",
            required=True,
        ),
        Section(
            key="overensstemmelses_basis",
            heading="Overensstemmelses-basis",
            prompt=(
                "Hvilken overensstemmelsesvurderings-procedure er fulgt? "
                "(Internt selvtjek vs. bemyndiget organ)"
            ),
            field_type="enum",
            enum_values=["internt_selvtjek_bilag_vi", "bemyndiget_organ_bilag_vii"],
            required=True,
        ),
        Section(
            key="registreringsdato",
            heading="Planlagt registreringsdato",
            prompt="Hvornår vil systemet blive registreret? (skal ske inden ibrugtagning)",
            field_type="date",
            required=True,
        ),
    ],
)


# ---- Forvaltningsret-baserede artefakter (7) -------------------------------

_PARTSHORINGSBREV = ArtifactTemplate(
    id="partshoringsbrev",
    title="Partshøringsbrev-skabelon (FVL § 19)",
    summary=(
        "Skabelon for partshøringsbrev — myndigheden skal høre parten over "
        "oplysninger der ligger til grund for en bebyrdende afgørelse, hvis "
        "parten ikke kan antages at være bekendt med dem."
    ),
    category="forvaltning",
    estimated_minutes=30,
    legal_basis=[
        LegalReference(
            lov="Forvaltningsloven",
            artikel="§ 19",
            citat=(
                "Kan en part i en sag ikke antages at være bekendt med, at "
                "myndigheden er i besiddelse af bestemte oplysninger om en "
                "sags faktiske grundlag, må der ikke træffes afgørelse, før "
                "myndigheden har gjort parten bekendt med oplysningerne og "
                "givet denne lejlighed til at fremkomme med en udtalelse."
            ),
            url=_FVL_URL,
        ),
    ],
    external_resources=[
        ExternalResource(
            title="Vejledning om forvaltningsloven (1986)",
            publisher="Justitsministeriet",
            url="https://www.retsinformation.dk/eli/retsinfo/1986/11740",
        ),
        ExternalResource(
            title="Folketingets Ombudsmand — partshøring",
            publisher="Ombudsmanden",
            url="https://www.ombudsmanden.dk/myndighedsguiden/generel-forvaltningsret/partshoering/",
        ),
    ],
    sections=[
        Section(
            key="modtager",
            heading="Modtager",
            prompt="Hvem skal høres? (parten)",
            field_type="text",
            placeholder="Navn + adresse / CPR-nummer (intern reference)",
            required=True,
        ),
        Section(
            key="sagsemne",
            heading="Sagens emne + sagsnummer",
            prompt="Kort beskrivelse af sagen + sagsnummer.",
            field_type="text",
            required=True,
        ),
        Section(
            key="oplysninger_til_horing",
            heading="Oplysninger til høring",
            prompt=(
                "Konkret beskrivelse af de faktiske oplysninger parten skal "
                "have lejlighed til at udtale sig om — herunder eventuelle "
                "AI-genererede vurderinger."
            ),
            required=True,
        ),
        Section(
            key="ai_anvendelse_oplyst",
            heading="Oplysning om AI-anvendelse",
            prompt=(
                "Skriftlig forklaring til parten om at et AI-system har bidraget "
                "til sagsbehandlingen, hvilken rolle det har spillet, og at en "
                "menneskelig sagsbehandler tager den endelige afgørelse."
            ),
            default_text=(
                "I behandlingen af din sag har vi anvendt et AI-baseret beslutnings"
                "støtte-system, der har bidraget med en foreløbig vurdering. "
                "Det endelige indhold af afgørelsen træffes af en sagsbehandler, "
                "men du har ret til at få oplyst, at AI har været involveret."
            ),
            required=True,
        ),
        Section(
            key="frist",
            heading="Svarfrist",
            prompt=(
                "Hvor lang frist får parten? Skal være rimelig — typisk "
                "minimum 14 dage, mere ved komplekse sager."
            ),
            field_type="text",
            placeholder="14 dage fra modtagelse",
            required=True,
        ),
        Section(
            key="kontaktoplysninger",
            heading="Kontaktoplysninger",
            prompt="Hvem skal parten henvende sig til med spørgsmål?",
            field_type="text",
            required=True,
        ),
    ],
)

_FRIST_DOKUMENTATION = ArtifactTemplate(
    id="frist_dokumentation",
    title="Frist-dokumentation (FVL § 19 + god forvaltningsskik)",
    summary=(
        "Dokumentation af de svarfrister myndigheden anvender ved partshøring "
        "+ klager. Skal være rimelige og dokumenterede så ombudsmanden kan "
        "vurdere praksis."
    ),
    category="forvaltning",
    estimated_minutes=20,
    legal_basis=[
        LegalReference(
            lov="Forvaltningsloven",
            artikel="§ 19, stk. 2 + god forvaltningsskik",
            citat=(
                "Bestemmelsen i stk. 1 gælder ikke, hvis... der ved lov eller "
                "i medfør af lov er fastsat særlige bestemmelser, der sikrer "
                "parten adgang til at gøre sig bekendt med grundlaget for den "
                "påtænkte afgørelse og til at afgive en udtalelse til sagen."
            ),
            url=_FVL_URL,
        ),
    ],
    sections=[
        Section(
            key="standardfrist_partshoring",
            heading="Standardfrist for partshøring",
            prompt="Antal dage typisk afsat. Begrund hvorfor det er rimeligt.",
            field_type="text",
            placeholder="14 kalenderdage / 21 dage ved komplekse sager",
            required=True,
        ),
        Section(
            key="forlaengelses_kriterier",
            heading="Kriterier for fristforlængelse",
            prompt=(
                "Under hvilke omstændigheder kan parten få fristforlængelse? "
                "Hvem træffer beslutningen?"
            ),
            required=True,
        ),
        Section(
            key="paamindelses_proces",
            heading="Påmindelses-proces",
            prompt=(
                "Sender myndigheden påmindelse hvis parten ikke svarer i tide? "
                "Hvor lang tid før udløb?"
            ),
            required=False,
        ),
        Section(
            key="ferieperiode_haandtering",
            heading="Håndtering af ferieperioder",
            prompt=(
                "Hvordan håndteres frister der falder i ferieperioder? "
                "Forlænges automatisk eller efter individuel vurdering?"
            ),
            required=False,
        ),
    ],
)

_KVITTERING_FOR_MODTAGELSE = ArtifactTemplate(
    id="kvittering_for_modtagelse",
    title="Kvittering for modtagelse (god forvaltningsskik)",
    summary=(
        "Skabelon for kvittering når parten har afgivet et hørings-svar. "
        "God forvaltningsskik kræver at parten får bekræftet at svaret er "
        "modtaget og hvad næste skridt er."
    ),
    category="forvaltning",
    estimated_minutes=15,
    legal_basis=[
        LegalReference(
            lov="Forvaltningsloven + god forvaltningsskik",
            artikel="Almindelige forvaltningsretlige principper",
            citat=(
                "God forvaltningsskik tilsiger, at en myndighed bekræfter "
                "modtagelsen af henvendelser fra borgere og oplyser om "
                "sagens fortsatte forløb og forventet afgørelsestidspunkt."
            ),
            url="https://www.ombudsmanden.dk/",
        ),
    ],
    sections=[
        Section(
            key="kvitterings_frist",
            heading="Tidsfrist for at sende kvittering",
            prompt="Hvor hurtigt sendes kvittering? (typisk 1-3 hverdage)",
            field_type="text",
            required=True,
        ),
        Section(
            key="kvitterings_skabelon",
            heading="Skabelon-tekst",
            prompt="Den faktiske skabelon-tekst.",
            default_text=(
                "Kære [navn],\n\n"
                "Vi har modtaget dit svar af [dato] vedrørende sag [sagsnummer].\n\n"
                "Vi forventer at træffe afgørelse senest [dato]. Hvis behandlingen "
                "tager længere tid, vil du blive orienteret.\n\n"
                "Har du spørgsmål, er du velkommen til at kontakte mig på [telefon/mail].\n\n"
                "Med venlig hilsen,\n"
                "[Sagsbehandler]"
            ),
            required=True,
        ),
        Section(
            key="kanal",
            heading="Kanal",
            prompt="Sendes kvittering pr. brev, e-Boks, mail eller sms?",
            field_type="text",
            required=True,
        ),
    ],
)

_SAGSBEHANDLER_REVIEW_PROTOKOL = ArtifactTemplate(
    id="sagsbehandler_review_protokol",
    title="Sagsbehandler-review-protokol (FVL § 22 + AI Act Art. 14)",
    summary=(
        "Procedure for hvordan sagsbehandleren reviewer AI-systemets output "
        "INDEN afgørelsen sendes. Skal sikre menneskelig overvågning, modgå "
        "automation bias og bevise at sagsbehandleren reelt har taget afgørelsen."
    ),
    category="forvaltning",
    estimated_minutes=60,
    legal_basis=[
        LegalReference(
            lov="Forvaltningsloven",
            artikel="§ 22",
            citat=(
                "En afgørelse skal, når den meddeles skriftligt, være ledsaget af "
                "en begrundelse, medmindre afgørelsen fuldt ud giver den pågældende part medhold."
            ),
            url=_FVL_URL,
        ),
        LegalReference(
            lov="EU AI-forordningen",
            artikel="Artikel 14, stk. 4",
            citat=(
                "Foranstaltningerne skal sætte de fysiske personer der er tildelt "
                "menneskelig overvågning i stand til at... korrekt at fortolke "
                "højrisiko-AI-systemets output."
            ),
            url=_AI_ACT_URL,
        ),
    ],
    sections=[
        Section(
            key="review_trin",
            heading="Review-trin",
            prompt="Hvilke konkrete trin gennemgår sagsbehandleren?",
            default_text=(
                "1. Læs AI-systemets output + konfidensscore\n"
                "2. Verificér de faktiske oplysninger i sagen\n"
                "3. Vurder om AI-output passer med juridisk grundlag\n"
                "4. Tjek lovhenvisninger\n"
                "5. Skriv begrundelse i egne ord (ikke copy-paste fra AI)\n"
                "6. Marker eventuel uenighed med AI + begrund\n"
                "7. Godkend og send"
            ),
            required=True,
        ),
        Section(
            key="dokumentation_af_review",
            heading="Dokumentation af review",
            prompt=(
                "Hvordan dokumenteres at review er foretaget? (timestamp, "
                "sagsbehandler-ID, fritekst-noter)"
            ),
            required=True,
        ),
        Section(
            key="override_proces",
            heading="Override-proces",
            prompt=(
                "Hvordan logges det når sagsbehandler er uenig med AI? "
                "Skal årsag dokumenteres? Eskaleres til leder?"
            ),
            required=True,
        ),
        Section(
            key="stikproevekontrol",
            heading="Stikprøvekontrol af review-kvalitet",
            prompt=(
                "Hvor ofte stikprøvekontrolleres sagsbehandlerens review? "
                "Af hvem? Hvordan dokumenteres resultater?"
            ),
            required=True,
        ),
    ],
)

_BEGRUNDELSESSKABELON = ArtifactTemplate(
    id="begrundelsesskabelon_godkendt_af_jurist",
    title="Begrundelses-skabelon (FVL § 22-24, jurist-godkendt)",
    summary=(
        "Skabelon for begrundelse af afgørelser. Skal indeholde retsregler, "
        "hovedhensyn ved skøn og en kort gengivelse af de faktiske omstændigheder. "
        "Skal være jurist-godkendt INDEN ibrugtagning."
    ),
    category="forvaltning",
    estimated_minutes=90,
    legal_basis=[
        LegalReference(
            lov="Forvaltningsloven",
            artikel="§ 22 + § 24",
            citat=(
                "Begrundelsen skal indeholde en henvisning til de retsregler, i "
                "henhold til hvilke afgørelsen er truffet. I det omfang, "
                "afgørelsen efter disse regler beror på et administrativt skøn, "
                "skal begrundelsen tillige angive de hovedhensyn, der har været "
                "bestemmende for skønsudøvelsen."
            ),
            url=_FVL_URL,
        ),
    ],
    sections=[
        Section(
            key="skabelon_tekst",
            heading="Skabelon-tekst",
            prompt="Den faktiske begrundelses-skabelon med pladsholdere.",
            default_text=(
                "**Afgørelse**\n\n"
                "Du har søgt om [ydelse/behandling]. Vi har truffet afgørelse "
                "om at [give/afvise] din ansøgning.\n\n"
                "**Faktiske omstændigheder**\n"
                "Vi har lagt vægt på følgende oplysninger: [...]\n\n"
                "**Retsgrundlag**\n"
                "Afgørelsen er truffet i henhold til [lov § paragraf, stk. X].\n\n"
                "**Hovedhensyn ved skøn (hvis relevant)**\n"
                "I vores skønsudøvelse har vi lagt vægt på: [...]\n\n"
                "**Klagevejledning**\n"
                "Du kan klage over denne afgørelse til [klageinstans] inden "
                "[frist] fra modtagelse af afgørelsen.\n\n"
                "Med venlig hilsen,\n"
                "[Sagsbehandler]"
            ),
            required=True,
        ),
        Section(
            key="jurist_godkendelse",
            heading="Jurist-godkendelse",
            prompt="Hvem har godkendt skabelonen? Dato + sagsnummer.",
            field_type="text",
            required=True,
        ),
        Section(
            key="vedligeholdelses_proces",
            heading="Vedligeholdelses-proces",
            prompt="Hvor ofte revurderes skabelonen? Af hvem?",
            required=True,
        ),
        Section(
            key="anvendelses_omraade",
            heading="Anvendelsesområde",
            prompt=(
                "Hvilke sagstyper bruges skabelonen til? Findes der varianter "
                "for forskellige sagstyper?"
            ),
            required=True,
        ),
    ],
)

_PROCEDURE_LOVHENVISNING = ArtifactTemplate(
    id="procedure_til_lovhenvisnings_verifikation",
    title="Procedure til lovhenvisnings-verifikation (FVL § 24)",
    summary=(
        "Procedure der sikrer at lovhenvisninger i AI-genererede begrundelser er "
        "korrekte og opdaterede. Bifrosts egen citation-verifier løser meget af det "
        "automatisk — men der skal være en manuel kontrolproces oveni."
    ),
    category="forvaltning",
    estimated_minutes=45,
    legal_basis=[
        LegalReference(
            lov="Forvaltningsloven",
            artikel="§ 24, stk. 1",
            citat=(
                "Begrundelsen skal indeholde en henvisning til de retsregler, "
                "i henhold til hvilke afgørelsen er truffet."
            ),
            url=_FVL_URL,
        ),
    ],
    external_resources=[
        ExternalResource(
            title="Retsinformation.dk — autoritative lovtekster",
            publisher="Civilstyrelsen",
            url="https://www.retsinformation.dk/",
        ),
    ],
    sections=[
        Section(
            key="automatisk_kontrol",
            heading="Automatisk kontrol",
            prompt=(
                "Beskriv den automatiske lovhenvisnings-verifikation (Bifrosts egen "
                "citation-verifier eller anden process). Frekvens. Hvad sker ved "
                "fejl?"
            ),
            default_text=(
                "Bifrosts citation-verifier kører ugentligt og verificerer alle "
                "lovcitater i regelmotorens kilder ordret mod retsinformation.dk + "
                "EUR-Lex. Flagged citations vises på /lov-overvaagning."
            ),
            required=True,
        ),
        Section(
            key="manuel_kontrol_per_afgoerelse",
            heading="Manuel kontrol per afgørelse",
            prompt=(
                "Procedure for at sagsbehandleren verificerer lovhenvisning i "
                "den konkrete afgørelse INDEN udsendelse."
            ),
            required=True,
        ),
        Section(
            key="hvad_ved_lovaendring",
            heading="Hvad sker der ved lovændring?",
            prompt=(
                "Hvordan opdages og håndteres lovændringer der ramme de regler "
                "AI-systemet bruger?"
            ),
            required=True,
        ),
        Section(
            key="ansvarlig",
            heading="Ansvarlig person",
            prompt="Hvem er ansvarlig for at lovhenvisninger er korrekte?",
            field_type="text",
            required=True,
        ),
    ],
)

_KLAGEVEJLEDNING = ArtifactTemplate(
    id="klagevejledning_skabelon",
    title="Klagevejlednings-skabelon (FVL § 25)",
    summary=(
        "Skabelon for klagevejledning der skal vedlægges enhver bebyrdende "
        "skriftlig afgørelse. Skal angive klageinstans, klagefrist og evt. "
        "særlige formkrav."
    ),
    category="forvaltning",
    estimated_minutes=30,
    legal_basis=[
        LegalReference(
            lov="Forvaltningsloven",
            artikel="§ 25, stk. 1",
            citat=(
                "Afgørelser, som kan påklages til anden forvaltningsmyndighed, "
                "skal, når de meddeles skriftligt, være ledsaget af en vejledning "
                "om klageadgang med angivelse af klageinstans og oplysning om "
                "fremgangsmåden ved indgivelse af klage, herunder om eventuel "
                "tidsfrist."
            ),
            url=_FVL_URL,
        ),
    ],
    sections=[
        Section(
            key="klageinstans",
            heading="Klageinstans",
            prompt=(
                "Hvilken myndighed eller nævn skal klagen sendes til? "
                "Adresse + e-Boks/digital postkasse-info."
            ),
            field_type="text",
            required=True,
        ),
        Section(
            key="klagefrist",
            heading="Klagefrist",
            prompt="Antal uger fra modtagelse af afgørelsen.",
            field_type="text",
            placeholder="4 uger",
            required=True,
        ),
        Section(
            key="formkrav",
            heading="Eventuelle formkrav",
            prompt=(
                "Skal klagen være skriftlig? Findes der formularer? "
                "Skal kopi sendes til afgørende myndighed?"
            ),
            required=True,
        ),
        Section(
            key="vejlednings_tekst",
            heading="Vejlednings-tekst (skabelon)",
            prompt="Den faktiske skabelon-tekst der indsættes i afgørelser.",
            default_text=(
                "**Klagevejledning**\n\n"
                "Du kan klage over denne afgørelse til [klageinstans]. "
                "Klagen skal være modtaget af [klageinstans] senest [frist] fra "
                "den dag, du har modtaget afgørelsen.\n\n"
                "Klagen skal være skriftlig og sendes til:\n"
                "[adresse / e-Boks-ID]\n\n"
                "Vi modtager gerne en kopi af klagen.\n\n"
                "Hvis du klager over en AI-baseret afgørelse, har du særligt ret til "
                "at få menneskelig sagsbehandler til at gennemgå sagen på ny "
                "(jf. GDPR Art. 22, stk. 3)."
            ),
            required=True,
        ),
    ],
)


# ---- GDPR-baserede artefakter (5) ------------------------------------------

_RETSGRUNDLAG_DOKUMENTATION = ArtifactTemplate(
    id="retsgrundlag_dokumentation",
    title="Retsgrundlag-dokumentation (GDPR Art. 6)",
    summary=(
        "Dokumentation af det specifikke retsgrundlag for behandling af "
        "personoplysninger i AI-systemet — herunder for de særlige kategorier "
        "(art. 9) hvis de behandles."
    ),
    category="gdpr",
    estimated_minutes=60,
    legal_basis=[
        LegalReference(
            lov="GDPR (Forordning 2016/679)",
            artikel="Artikel 6, stk. 1 + Art. 9",
            citat=(
                "Behandling er kun lovlig, hvis og i det omfang mindst ét af "
                "følgende forhold gør sig gældende: a) den registrerede har "
                "givet samtykke... e) behandling er nødvendig af hensyn til "
                "udførelse af en opgave i samfundets interesse..."
            ),
            url=_GDPR_URL,
        ),
    ],
    external_resources=[
        ExternalResource(
            title="Datatilsynets vejledning om retsgrundlag",
            publisher="Datatilsynet",
            url="https://www.datatilsynet.dk/hvad-siger-reglerne/grundlaeggende-begreber/lovlig-behandling/",
        ),
    ],
    sections=[
        Section(
            key="retsgrundlag",
            heading="Retsgrundlag (Art. 6)",
            prompt="Hvilket retsgrundlag bruges?",
            field_type="enum",
            enum_values=[
                "samtykke_a",
                "kontrakt_b",
                "retlig_forpligtelse_c",
                "vitale_interesser_d",
                "samfundets_interesse_eller_offentlig_myndighed_e",
                "legitim_interesse_f",
            ],
            required=True,
        ),
        Section(
            key="national_lovhjemmel",
            heading="National lovhjemmel (hvis litra c eller e)",
            prompt=(
                "Hvis retsgrundlaget er retlig forpligtelse (c) eller "
                "samfundets interesse (e): hvilken konkret dansk lovhjemmel?"
            ),
            field_type="text",
            placeholder="Fx: Servicelovens § 102, stk. 1",
            required=False,
        ),
        Section(
            key="formaalsbeskrivelse",
            heading="Formålsbeskrivelse",
            prompt=(
                "Klart, specifikt og legitimt formål med behandlingen "
                "(GDPR art. 5, stk. 1, litra b)."
            ),
            required=True,
        ),
        Section(
            key="saerlige_kategorier",
            heading="Særlige kategorier (Art. 9)",
            prompt=(
                "Behandles særlige kategorier? Hvis ja: hvilke + hvilken "
                "Art. 9, stk. 2-undtagelse?"
            ),
            required=True,
        ),
        Section(
            key="cpr_behandling",
            heading="CPR-nummer-behandling (Databeskyttelsesloven § 11)",
            prompt=(
                "Hvis CPR behandles: angiv lovhjemmel iht. databeskyttelsesloven "
                "§ 11 (offentlige myndigheder) eller § 11, stk. 2 (private)."
            ),
            required=False,
        ),
        Section(
            key="legitim_interesse_test",
            heading="Legitim interesse-test (hvis litra f)",
            prompt=(
                "Hvis retsgrundlaget er legitim interesse: gennemfør "
                "3-trins-testen (legitim interesse + nødvendighed + balancetest)."
            ),
            required=False,
        ),
    ],
)

_MENNESKELIG_INDGRIBEN = ArtifactTemplate(
    id="menneskelig_indgriben_proces",
    title="Menneskelig indgriben-proces (GDPR Art. 22 + AI Act Art. 14)",
    summary=(
        "Procesbeskrivelse for hvordan en registreret kan udøve sin ret til "
        "menneskelig indgriben ved automatiseret afgørelse — krav fra GDPR "
        "art. 22, stk. 3 og forstærket af AI Act art. 14."
    ),
    category="gdpr",
    estimated_minutes=60,
    legal_basis=[
        LegalReference(
            lov="GDPR (Forordning 2016/679)",
            artikel="Artikel 22, stk. 3",
            citat=(
                "I de tilfælde, der er omhandlet i stk. 2, litra a) og c), "
                "gennemfører den dataansvarlige passende foranstaltninger til "
                "beskyttelse af den registreredes rettigheder og frihedsrettigheder "
                "samt legitime interesser, i det mindste den registreredes ret "
                "til menneskelig indgriben fra den dataansvarliges side."
            ),
            url=_GDPR_URL,
        ),
    ],
    sections=[
        Section(
            key="hvordan_anmoder_borger",
            heading="Hvordan anmoder borgeren om menneskelig indgriben?",
            prompt=(
                "Specifikke kanaler (web-formular, brev, telefon, fysisk besøg). "
                "Hvilken information skal borgeren oplyse?"
            ),
            required=True,
        ),
        Section(
            key="responsibility",
            heading="Hvem håndterer anmodningen?",
            prompt=(
                "Hvilken funktion/rolle modtager og behandler anmodningen? "
                "Skal vedkommende være anderledes end den der traf den oprindelige "
                "afgørelse?"
            ),
            required=True,
        ),
        Section(
            key="frist",
            heading="Frist for behandling",
            prompt="Hvor lang tid efter anmodning skal sagsbehandler have besluttet?",
            field_type="text",
            placeholder="Senest 4 uger fra modtagelse",
            required=True,
        ),
        Section(
            key="dokumentation",
            heading="Dokumentation af menneskelig indgriben",
            prompt=(
                "Hvordan dokumenteres at en kompetent person REELT har gennemgået "
                "sagen — ikke bare bekræftet AI-afgørelsen?"
            ),
            required=True,
        ),
        Section(
            key="oplysning_til_borger",
            heading="Oplysning til borger",
            prompt=(
                "Skabelon-tekst der oplyser borger om sin ret til menneskelig "
                "indgriben — skal stå klart i alle automatiserede afgørelser."
            ),
            default_text=(
                "Du har ret til at kræve, at en sagsbehandler gennemgår denne "
                "afgørelse på ny. Hvis du ønsker det, skal du henvende dig til "
                "[kontaktinfo] inden [frist]."
            ),
            required=True,
        ),
    ],
)

_BESTRIDELSESPROCES = ArtifactTemplate(
    id="bestridelsesproces",
    title="Bestridelsesproces (GDPR Art. 22 + AI Act Art. 86)",
    summary=(
        "Procedure for hvordan borgeren kan bestride en automatiseret afgørelse "
        "+ få en forklaring på hvilke faktorer der har påvirket afgørelsen "
        "(retten til forklaring, AI Act Art. 86)."
    ),
    category="gdpr",
    estimated_minutes=60,
    legal_basis=[
        LegalReference(
            lov="GDPR (Forordning 2016/679)",
            artikel="Artikel 22, stk. 3",
            citat=(
                "...den registreredes ret til at... bestride afgørelsen."
            ),
            url=_GDPR_URL,
        ),
        LegalReference(
            lov="EU AI-forordningen (Forordning 2024/1689)",
            artikel="Artikel 86, stk. 1",
            citat=(
                "Enhver berørt person, der er genstand for en afgørelse truffet af "
                "idriftsætteren på grundlag af et output fra et højrisiko-AI-system... "
                "har ret til at få klare og meningsfulde forklaringer fra "
                "idriftsætteren om AI-systemets rolle i beslutningsprocessen."
            ),
            url=_AI_ACT_URL,
        ),
    ],
    sections=[
        Section(
            key="bestridelses_kanal",
            heading="Bestridelses-kanal",
            prompt="Hvor og hvordan kan borgeren bestride afgørelsen?",
            required=True,
        ),
        Section(
            key="forklarings_indhold",
            heading="Forklarings-indhold (AI Act Art. 86)",
            prompt=(
                "Hvilke faktorer i AI-systemet skal kunne forklares? "
                "(input-faktorer, vægtning, kontekst, eventuel konfidens)"
            ),
            required=True,
        ),
        Section(
            key="behandlingstid",
            heading="Behandlingstid",
            prompt="Hvor lang tid tager det fra bestridelse til ny afgørelse?",
            field_type="text",
            required=True,
        ),
        Section(
            key="opsaettende_virkning",
            heading="Opsættende virkning",
            prompt=(
                "Har bestridelse opsættende virkning? "
                "(udsætter den oprindelige afgørelse fuldbyrdelse)"
            ),
            required=True,
        ),
        Section(
            key="oplysning_til_borger",
            heading="Oplysning til borger",
            prompt="Skabelon for hvordan borger oplyses om bestridelses-retten.",
            default_text=(
                "Du har ret til at bestride denne afgørelse og at få oplyst, "
                "hvilke faktorer der har påvirket beslutningen. Send din "
                "bestridelse til [kontaktinfo] inden [frist]."
            ),
            required=True,
        ),
    ],
)

_TRANSPARENSTEKST = ArtifactTemplate(
    id="transparenstekst_til_registrerede",
    title="Transparenstekst til registrerede (GDPR Art. 13/14 + Art. 22)",
    summary=(
        "Den oplysningstekst der gives til den registrerede når personoplysninger "
        "indsamles. Skal særskilt nævne AI/automatiseret afgørelse hvis det "
        "anvendes (GDPR art. 13, stk. 2, litra f)."
    ),
    category="gdpr",
    estimated_minutes=60,
    legal_basis=[
        LegalReference(
            lov="GDPR (Forordning 2016/679)",
            artikel="Artikel 13, stk. 2, litra f + Art. 14",
            citat=(
                "...forekomsten af automatiske afgørelser, herunder profilering, "
                "som omhandlet i artikel 22, stk. 1 og 4, og som minimum meningsfulde "
                "oplysninger om logikken heri samt betydningen og de forventede "
                "konsekvenser af en sådan behandling for den registrerede."
            ),
            url=_GDPR_URL,
        ),
    ],
    sections=[
        Section(
            key="dataansvarlig",
            heading="Dataansvarlig",
            prompt="Navn + kontaktinformation for den dataansvarlige.",
            field_type="text",
            required=True,
        ),
        Section(
            key="dpo_kontakt",
            heading="DPO-kontaktoplysninger",
            prompt="Navn + e-mail/telefon på databeskyttelsesrådgiver (DPO).",
            field_type="text",
            required=True,
        ),
        Section(
            key="formaal",
            heading="Formål med behandlingen",
            prompt="Konkret formål — ikke generelt 'service-forbedring'.",
            required=True,
        ),
        Section(
            key="retsgrundlag",
            heading="Retsgrundlag",
            prompt="Hvilket art. 6-grundlag (+ art. 9 hvis særlige kategorier)?",
            required=True,
        ),
        Section(
            key="modtagere",
            heading="Modtagere af oplysninger",
            prompt="Hvilke kategorier af modtagere får adgang? (intern/ekstern, databehandlere)",
            required=True,
        ),
        Section(
            key="opbevaring",
            heading="Opbevaringsperiode",
            prompt="Konkrete frister + kriterier for sletning.",
            required=True,
        ),
        Section(
            key="ai_oplysning",
            heading="AI/automatiseret afgørelse-oplysning",
            prompt=(
                "Specifik oplysning om AI-anvendelse, beslutningens logik på "
                "højt niveau, betydning og konsekvenser, ret til menneskelig "
                "indgriben + bestridelse."
            ),
            default_text=(
                "I sagsbehandlingen anvender vi et AI-baseret beslutningsstøtte"
                "-system, der bidrager med en foreløbig vurdering. Den endelige "
                "afgørelse træffes af en sagsbehandler.\n\n"
                "Du har ret til at:\n"
                "- Få oplyst at AI har været anvendt\n"
                "- Få menneskelig sagsbehandler til at gennemgå sagen på ny\n"
                "- Bestride afgørelsen\n"
                "- Få en forklaring på hvilke faktorer der har påvirket vurderingen\n\n"
                "Kontakt [kontakt] for at udøve disse rettigheder."
            ),
            required=True,
        ),
        Section(
            key="rettigheder",
            heading="Den registreredes rettigheder",
            prompt=(
                "Standard-tekst der opregner indsigt, berigtigelse, sletning, "
                "begrænsning, indsigelse, dataportabilitet + klage til Datatilsynet."
            ),
            required=True,
        ),
    ],
)

_DPIA_DOKUMENT = ArtifactTemplate(
    id="dpia_dokument",
    title="DPIA — Konsekvensanalyse (GDPR Art. 35 — KL/Datatilsynet 5-trin)",
    summary=(
        "Konsekvensanalyse vedrørende databeskyttelse — struktureret efter "
        "KL's og Datatilsynets fælles 5-trin-skabelon for AI-projekter (sept. 2025). "
        "Obligatorisk når en behandling sandsynligvis vil indebære høj risiko. "
        "Kør først tærskelsvurderingen (artefakt: dpia_taerskelsvurdering)."
    ),
    category="gdpr",
    estimated_minutes=480,  # 8 timer
    legal_basis=[
        LegalReference(
            lov="GDPR (Forordning 2016/679)",
            artikel="Artikel 35, stk. 1-7",
            citat=(
                "Hvis en type behandling, navnlig ved brug af nye teknologier og "
                "i medfør af sin karakter, omfang, sammenhæng og formål, "
                "sandsynligvis vil indebære en høj risiko for fysiske personers "
                "rettigheder og frihedsrettigheder, foretager den dataansvarlige "
                "forud for behandlingen en analyse af de påtænkte behandlings"
                "aktiviteters konsekvenser for beskyttelse af personoplysninger."
            ),
            url=_GDPR_URL,
        ),
    ],
    external_resources=[
        ExternalResource(
            title="KL/Datatilsynets DPIA-skabelon for AI-projekter (sept. 2025)",
            publisher="KL + Datatilsynet",
            url="https://www.kl.dk/media/41xfpieh/vaerktoej-dpia-i-ai-loesninger-skabelon-til-konsekvensanalyse-vedroerende-databeskyttelse-i-ai-projekter-dpia.docx",
            description="Officiel kommunal AI-DPIA-skabelon — 5 trin.",
        ),
        ExternalResource(
            title="Datatilsynets DPIA-skabeloner (maj 2024)",
            publisher="Datatilsynet",
            url="https://www.datatilsynet.dk/presse-og-nyheder/nyhedsarkiv/2024/maj/nye-skabeloner-til-gennemfoerelse-af-konsekvensanalyser",
        ),
        ExternalResource(
            title="WP248 — DPIA guidelines",
            publisher="EDPB / Article 29 WP",
            url="https://ec.europa.eu/newsroom/article29/items/611236",
        ),
        ExternalResource(
            title="Datatilsynets liste over behandlinger der KRÆVER DPIA",
            publisher="Datatilsynet",
            url="https://www.datatilsynet.dk/erhverv/dpia",
        ),
    ],
    sections=[
        # ---- Indledning ---------------------------------------------------
        Section(
            key="taerskelvurdering_reference",
            heading="0. Tærskelsvurdering gennemført",
            prompt=(
                "Bekræft at DPIA-tærskelsvurdering er udfyldt (artefakt: "
                "dpia_taerskelsvurdering) og konkluderet at DPIA er påkrævet."
            ),
            field_type="boolean",
            required=True,
        ),
        Section(
            key="dataansvarlig_kontakt",
            heading="0.1 Dataansvarlig + kontaktpersoner",
            prompt=(
                "Dataansvarlig (typisk Kalundborg Kommune), udfyldt af, "
                "ansvarlig kontaktperson, repræsentant for ledelsen, DPO."
            ),
            required=True,
        ),
        # ---- Trin 1 -------------------------------------------------------
        Section(
            key="trin1_formaal_karakter",
            heading="Trin 1.1 — AI-løsningens formål og karakter",
            prompt=(
                "Beskriv konkret formål med AI-løsningen (henvis til "
                "behandlingshjemmel) + den overordnede karakter af behandlingen."
            ),
            required=True,
        ),
        Section(
            key="trin1_persondata_omfang",
            heading="Trin 1.2 — Behandling af personoplysninger og omfang",
            prompt=(
                "Hvilke personoplysninger behandles, hvor mange registrerede, "
                "hvor stort er datasættet? Inkl. særlige kategorier (art. 9), CPR."
            ),
            required=True,
        ),
        Section(
            key="trin1_sammenhaeng_kontekst",
            heading="Trin 1.3 — Sammenhæng og kontekst",
            prompt=(
                "I hvilken sammenhæng/kontekst behandles oplysningerne? "
                "Forventninger fra de registrerede, magtbalance, sårbare grupper."
            ),
            required=True,
        ),
        Section(
            key="trin1_modtagere",
            heading="Trin 1.4 — Modtagere af personoplysninger",
            prompt="Hvem får adgang til oplysningerne (intern + ekstern + databehandlere)?",
            required=True,
        ),
        Section(
            key="trin1_opbevaring",
            heading="Trin 1.5 — Opbevaringsperiode",
            prompt="Konkrete frister + kriterier for sletning. Nævn arkivlov hvis relevant.",
            required=True,
        ),
        # ---- Trin 2 -------------------------------------------------------
        Section(
            key="trin2_dpo",
            heading="Trin 2.1 — DPO inddraget",
            prompt=(
                "Er DPO inddraget i DPIA'en? Reference til separat artefakt "
                "'dpo_udtalelse'."
            ),
            field_type="boolean",
            required=True,
        ),
        Section(
            key="trin2_hoering_registrerede",
            heading="Trin 2.2 — Høring af registrerede (eller deres repræsentanter)",
            prompt=(
                "Er de registrerede hørt? Hvis nej: begrund (ofte ikke praktisk for "
                "store offentlige systemer, men dokumentér beslutningen)."
            ),
            required=True,
        ),
        # ---- Trin 3 -------------------------------------------------------
        Section(
            key="trin3_lovlighed",
            heading="Trin 3.1 — Lovlighed, rimelighed og gennemsigtighed",
            prompt=(
                "Hvordan sikres at behandlingen er lovlig, rimelig og gennemsigtig "
                "for de registrerede?"
            ),
            required=True,
        ),
        Section(
            key="trin3_formaalsbegraensning",
            heading="Trin 3.2 — Formålsbegrænsning",
            prompt="Er formålet specifikt, sagligt og udtrykkeligt angivet? Genbrug af data?",
            required=True,
        ),
        Section(
            key="trin3_dataminimering",
            heading="Trin 3.3 — Dataminimering",
            prompt=(
                "Er kun de strengt nødvendige personoplysninger inddraget? "
                "Hvilke er fravalgt og hvorfor?"
            ),
            required=True,
        ),
        Section(
            key="trin3_rigtighed",
            heading="Trin 3.4 — Rigtighed",
            prompt=(
                "Hvordan sikres at oplysningerne er korrekte og opdaterede? "
                "Rettelsesproces."
            ),
            required=True,
        ),
        Section(
            key="trin3_opbevaringsbegraensning",
            heading="Trin 3.5 — Opbevaringsbegrænsning",
            prompt="Hvordan sikres at data slettes når formålet er opfyldt?",
            required=True,
        ),
        Section(
            key="trin3_integritet_fortrolighed",
            heading="Trin 3.6 — Integritet og fortrolighed (sikkerhed + robusthed)",
            prompt=(
                "Tekniske + organisatoriske sikkerhedsforanstaltninger. "
                "Pseudonymisering, kryptering, adgangskontrol, sikkerhedstests."
            ),
            required=True,
        ),
        Section(
            key="trin3_behandlingsgrundlag",
            heading="Trin 3.7 — Behandlingsgrundlag (hjemmel)",
            prompt=(
                "GDPR art. 6-grundlag + (hvis relevant) art. 9 + national hjemmel "
                "(databeskyttelseslov §11 for CPR osv.)."
            ),
            required=True,
        ),
        Section(
            key="trin3_rettigheder",
            heading="Trin 3.8 — De registreredes rettigheder",
            prompt=(
                "Hvordan opfyldes oplysningspligt, indsigt, berigtigelse, sletning, "
                "begrænsning, dataportabilitet, indsigelse, og art. 22-rettigheder?"
            ),
            required=True,
        ),
        Section(
            key="trin3_design",
            heading="Trin 3.9 — Databeskyttelse gennem design + standardindstillinger",
            prompt="Hvordan er databeskyttelse indbygget i systemet fra start?",
            required=True,
        ),
        Section(
            key="trin3_databehandlere",
            heading="Trin 3.10 — Databehandlere",
            prompt=(
                "Hvilke databehandlere benyttes? Reference til 'databehandleraftale_dbs' "
                "artefakt."
            ),
            required=True,
        ),
        Section(
            key="trin3_tredjelande",
            heading="Trin 3.11 — Overførsel til tredjelande",
            prompt=(
                "Sker der overførsel til tredjelande? Hvis ja: overførselsgrundlag "
                "(SCC, BCR, adequacy decision)."
            ),
            required=True,
        ),
        # ---- Trin 4 -------------------------------------------------------
        Section(
            key="trin4_evalueringskriterier",
            heading="Trin 4.1 — Valg af evalueringskriterier (sandsynlighed × konsekvens)",
            prompt=(
                "Definér skala for sandsynlighed (lav/mellem/høj) + konsekvens "
                "(lav/mellem/høj). Brug evt. ISO/IEC 31000-tilgang."
            ),
            required=True,
        ),
        Section(
            key="trin4_konkrete_risici",
            heading="Trin 4.2 — Konkrete risici + håndtering",
            prompt=(
                "Per identificeret risiko: beskrivelse + sandsynlighed + konsekvens + "
                "afhjælpende foranstaltninger + restrisiko. Risikokategorier: "
                "identitetstyveri, diskrimination, økonomisk skade, rygteskade, "
                "fysisk skade, ulig adgang til ydelser."
            ),
            required=True,
        ),
        # ---- Trin 5 -------------------------------------------------------
        Section(
            key="trin5_samlet_restrisiko",
            heading="Trin 5.1 — Samlet restrisiko + Datatilsynets høring",
            prompt=(
                "Samlet vurdering af restrisiko efter foranstaltninger. Hvis "
                "restrisiko er HØJ → forhåndshøring af Datatilsynet KRÆVES "
                "(GDPR art. 36)."
            ),
            required=True,
        ),
        Section(
            key="trin5_ledelsesgodkendelse",
            heading="Trin 5.2 — Ledelsesgodkendelse",
            prompt="Navn + funktion + dato for ledelsens godkendelse af DPIA'en.",
            field_type="text",
            required=True,
        ),
        Section(
            key="trin5_offentliggoerelse",
            heading="Trin 5.3 — Offentliggørelse",
            prompt=(
                "Skal DPIA'en offentliggøres? Hvis ja: hvor + i hvilken redigeret form? "
                "(Best practice: ja, med redaktion af følsomme detaljer)"
            ),
            required=False,
        ),
    ],
)

_DPO_UDTALELSE = ArtifactTemplate(
    id="dpo_udtalelse",
    title="DPO-udtalelse om DPIA (GDPR Art. 35, stk. 2)",
    summary=(
        "Skriftlig udtalelse fra databeskyttelsesrådgiveren (DPO) om DPIA'en. "
        "DPO skal være konsulteret når en DPIA udføres, og udtalelsen + "
        "eventuel uenighed mellem DPO og dataansvarlig skal dokumenteres."
    ),
    category="gdpr",
    estimated_minutes=120,
    legal_basis=[
        LegalReference(
            lov="GDPR (Forordning 2016/679)",
            artikel="Artikel 35, stk. 2 + Art. 39, stk. 1, litra c",
            citat=(
                "Den dataansvarlige rådfører sig med en eventuel "
                "databeskyttelsesrådgiver ved gennemførelsen af en konsekvensanalyse "
                "vedrørende databeskyttelse."
            ),
            url=_GDPR_URL,
        ),
    ],
    external_resources=[
        ExternalResource(
            title="WP243 — DPO guidelines",
            publisher="EDPB",
            url="https://ec.europa.eu/newsroom/article29/items/612048",
        ),
    ],
    sections=[
        Section(
            key="dpo_navn",
            heading="DPO's navn + organisation",
            prompt="Navn på den DPO der har givet udtalelsen.",
            field_type="text",
            required=True,
        ),
        Section(
            key="dato",
            heading="Dato for udtalelsen",
            prompt="Dato hvor udtalelsen blev givet.",
            field_type="date",
            required=True,
        ),
        Section(
            key="vurdering_af_dpia",
            heading="Vurdering af DPIA'ens fyldestgørenhed",
            prompt=(
                "Er DPIA'en fyldestgørende? Mangler der noget? Er risikovurderingen "
                "realistisk? Er afhjælpning tilstrækkelig?"
            ),
            required=True,
        ),
        Section(
            key="anbefalinger",
            heading="DPO's anbefalinger",
            prompt="Konkrete anbefalinger til den dataansvarlige.",
            required=True,
        ),
        Section(
            key="uenigheder",
            heading="Eventuelle uenigheder med dataansvarlig",
            prompt=(
                "Er DPO uenig i nogen af de valg dataansvarlig har truffet? "
                "Hvis ja: dokumentér uenigheden + dataansvarliges svar."
            ),
            required=True,
        ),
        Section(
            key="forhaandshoering_anbefalet",
            heading="Anbefales forhåndshøring af Datatilsynet?",
            prompt="DPO's vurdering af om Art. 36 forhåndshøring er nødvendig.",
            field_type="boolean",
            required=True,
        ),
        Section(
            key="opfoelgning",
            heading="Opfølgning",
            prompt=(
                "Hvornår skal DPIA'en revurderes? Hvilke triggere udløser ny DPIA?"
            ),
            required=True,
        ),
    ],
)


# ============================================================================
# Kalundborg-/DBS-/branche-specifikke artefakter (3)
# ============================================================================
#
# Disse 3 artefakter er ikke direkte i regel-korpusets evidens_påkrævet-lister
# i dag, men er Kalundborgs faktiske kommunale skabeloner (DBS-standard +
# Kalundborgs egne tjeklister) som sagsbehandleren ofte SKAL udfylde i
# samme arbejdsgang. De vises som tilgængelige artefakter i evidens-katalog
# og som første-trin i /indkoebsproces-wizarden.

_DPIA_TAERSKELSVURDERING = ArtifactTemplate(
    id="dpia_taerskelsvurdering",
    title="DPIA-tærskelsvurdering (Kalundborg + Art. 29 WP248)",
    summary=(
        "Tærskeltest for hvorvidt en DPIA er påkrævet. Hvis 2 eller flere af "
        "9 kriterier er opfyldt udløses DPIA-pligten i GDPR art. 35. Bygger på "
        "Kalundborg Kommunes egen skabelon + Art. 29-Gruppens WP248 retningslinjer. "
        "Skal udfyldes INDEN DPIA-dokumentet selv."
    ),
    category="gdpr",
    estimated_minutes=20,
    legal_basis=[
        LegalReference(
            lov="GDPR (Forordning 2016/679)",
            artikel="Artikel 35, stk. 1 + stk. 3",
            citat=(
                "Hvis en type behandling, navnlig ved brug af nye teknologier... "
                "sandsynligvis vil indebære en høj risiko for fysiske personers "
                "rettigheder og frihedsrettigheder, foretager den dataansvarlige "
                "forud for behandlingen en konsekvensanalyse."
            ),
            url=_GDPR_URL,
        ),
        LegalReference(
            lov="Datatilsynet — DPIA-vejledning",
            artikel="Tærskelvurderings-kriterier",
            citat=(
                "Hvis bare to kriterier er krydset af, udgør behandlingen som "
                "udgangspunkt en høj risiko for de registrerede, hvorfor der "
                "skal udarbejdes en konsekvensanalyse."
            ),
            url="https://www.datatilsynet.dk/regler-og-vejledning/behandlingssikkerhed/konsekvensanalyse",
        ),
    ],
    external_resources=[
        ExternalResource(
            title="Datatilsynets nye DPIA-skabeloner (maj 2024)",
            publisher="Datatilsynet",
            url="https://www.datatilsynet.dk/presse-og-nyheder/nyhedsarkiv/2024/maj/nye-skabeloner-til-gennemfoerelse-af-konsekvensanalyser",
            description="Datatilsynets opdaterede generic + AI-DPIA xlsx-skabeloner.",
        ),
        ExternalResource(
            title="Art. 29 WP248 — DPIA Guidelines",
            publisher="EDPB (Article 29 WP)",
            url="https://ec.europa.eu/newsroom/article29/items/611236",
            description="Officielle EU-retningslinjer for hvornår DPIA er påkrævet.",
        ),
        ExternalResource(
            title="KAI: Skabelon til databeskyttelsesretlig risikovurdering",
            publisher="Kalundborg Kommune (intern SharePoint)",
            url="https://kalundborg.sharepoint.com/sites/ITsikkerhed",
            description="Kommunens egen skabelon — kræver login.",
        ),
    ],
    sections=[
        Section(
            key="kriterie_1_evaluering",
            heading="1. Evaluering eller analyse af registrerede",
            prompt=(
                "Indebærer behandlingen evaluering, profilering eller forudsigelse "
                "af registreredes personlige aspekter (fx økonomisk situation, "
                "helbred, præferencer, adfærd, lokation eller bevægelser)?"
            ),
            field_type="boolean",
            required=True,
        ),
        Section(
            key="kriterie_2_automatiseret_beslutning",
            heading="2. Automatiseret beslutningstagen med juridisk eller tilsvarende betydelig virkning",
            prompt=(
                "Træffer behandlingen automatiserede afgørelser med retsvirkning "
                "eller tilsvarende betydelige konsekvenser for fysiske personer "
                "(GDPR art. 22)?"
            ),
            field_type="boolean",
            required=True,
        ),
        Section(
            key="kriterie_3_systematisk_overvaagning",
            heading="3. Systematisk overvågning",
            prompt=(
                "Overvåges registrerede systematisk, herunder via offentligt "
                "tilgængelige områder (fx kameraovervågning, log-analyse, sensorer)?"
            ),
            field_type="boolean",
            required=True,
        ),
        Section(
            key="kriterie_4_foelsomme_oplysninger",
            heading="4. Følsomme personoplysninger eller meget personlig karakter",
            prompt=(
                "Behandles særlige kategorier (helbred, race, religion, fagforening, "
                "seksuel orientering, biometri, genetik) eller andre oplysninger af "
                "meget personlig karakter (fx økonomi, lokation, kommunikation)?"
            ),
            field_type="boolean",
            required=True,
        ),
        Section(
            key="kriterie_5_omfattende_behandling",
            heading="5. Personoplysninger der gøres til genstand for omfattende behandling",
            prompt=(
                "Behandles personoplysninger i stort omfang — målt på antal "
                "registrerede, mængde af data, varighed eller geografisk udbredelse?"
            ),
            field_type="boolean",
            required=True,
        ),
        Section(
            key="kriterie_6_matching",
            heading="6. Matching eller kombination af datasæt",
            prompt=(
                "Sammenlignes eller kombineres datasæt, der er indsamlet til "
                "forskellige formål eller af forskellige dataansvarlige?"
            ),
            field_type="boolean",
            required=True,
        ),
        Section(
            key="kriterie_7_saarbare_registrerede",
            heading="7. Oplysninger om sårbare registrerede",
            prompt=(
                "Vedrører behandlingen sårbare registrerede — børn, ansatte, "
                "patienter, ydelsesmodtagere, ældre, mennesker med handicap, "
                "asylansøgere?"
            ),
            field_type="boolean",
            required=True,
        ),
        Section(
            key="kriterie_8_innovativ_teknologi",
            heading="8. Innovativ brug eller anvendelse af ny teknologi",
            prompt=(
                "Anvendes nye teknologiske eller organisatoriske løsninger "
                "(fx AI/ML, generative modeller, IoT, biometri)?"
            ),
            field_type="boolean",
            required=True,
        ),
        Section(
            key="kriterie_9_hindrer_rettighed",
            heading="9. Behandling hindrer registrerede i at udøve en rettighed",
            prompt=(
                "Hindrer eller begrænser behandlingen registrerede i at udøve en "
                "rettighed eller at gøre brug af en tjeneste eller en kontrakt?"
            ),
            field_type="boolean",
            required=True,
        ),
        Section(
            key="konklusion",
            heading="Konklusion: skal der udarbejdes DPIA?",
            prompt=(
                "Tæl JA-svar. Hvis 2+ → DPIA påkrævet. Hvis under 2 → ikke "
                "påkrævet, MEN dokumentér nedenfor hvorfor du vurderer at "
                "behandlingen ikke udgør høj risiko (Datatilsynet kan stille "
                "krav om sådan dokumentation)."
            ),
            field_type="enum",
            enum_values=["dpia_paakraevet", "dpia_ikke_paakraevet", "tvivlsom_indhent_dpo"],
            required=True,
        ),
        Section(
            key="begrundelse",
            heading="Begrundelse for konklusion",
            prompt=(
                "Hvis du har konkluderet 'ikke påkrævet' med 2+ JA-svar (sjældent), "
                "redegør grundigt for hvorfor behandlingen ikke udgør høj risiko."
            ),
            required=True,
        ),
        Section(
            key="udfyldt_af",
            heading="Udfyldt af",
            prompt="Navn + funktion + dato.",
            field_type="text",
            required=True,
        ),
    ],
)


_DATABEHANDLERAFTALE_DBS = ArtifactTemplate(
    id="databehandleraftale_dbs",
    title="Databehandleraftale (DBS-standardskabelon)",
    summary=(
        "Det Fælleskommunale Databehandlersekretariats (DBS) standardiserede "
        "databehandleraftale. Bygger på Datatilsynets standardkontrakt med "
        "kommunale defaults: 24-timers underretning ved brud, 60-dages varsel ved "
        "skift af underdatabehandler, forudgående generel skriftlig godkendelse. "
        "Skal kvalitetstjekkes af IT-sikkerhed@kalundborg.dk inden indgåelse."
    ),
    category="gdpr",
    estimated_minutes=180,
    legal_basis=[
        LegalReference(
            lov="GDPR (Forordning 2016/679)",
            artikel="Artikel 28",
            citat=(
                "Hvis en behandling foretages på vegne af en dataansvarlig, anvender "
                "den dataansvarlige kun databehandlere, der giver tilstrækkelige garantier "
                "for, at de gennemfører passende tekniske og organisatoriske foranstaltninger."
            ),
            url=_GDPR_URL,
        ),
    ],
    external_resources=[
        ExternalResource(
            title="DBS-standardskabelon — Det Fælleskommunale Databehandlersekretariat",
            publisher="DBS / KOMBIT",
            url="https://www.kombit.dk/dbs",
            description=(
                "Officiel kommunal standardskabelon. Datatilsynets standardkontrakt med "
                "kommunale defaults."
            ),
        ),
        ExternalResource(
            title="Datatilsynets standardkontraktbestemmelser (art. 28)",
            publisher="Datatilsynet",
            url="https://www.datatilsynet.dk/databeskyttelse/databehandlere",
        ),
    ],
    sections=[
        Section(
            key="praeambel_system",
            heading="Præambel — system og parter",
            prompt=(
                "Navn på tjenesten/behandlingen/IT-systemet. Den dataansvarlige "
                "(typisk Kalundborg Kommune) + databehandleren (leverandøren)."
            ),
            placeholder="Fx: Borgerassistent-pension v. Acme A/S",
            required=True,
        ),
        Section(
            key="bilag_a_formaal",
            heading="Bilag A.1 — Formål med behandlingen",
            prompt=(
                "Formuleres ift. den konkrete behandling. Henvis til behandlings"
                "hjemlen. Skal være dækkende for det databehandleren skal foretage."
            ),
            required=True,
        ),
        Section(
            key="bilag_a_karakter",
            heading="Bilag A.2 — Karakter af behandlingen",
            prompt="Kort generel beskrivelse af hvad databehandleren skal gøre.",
            required=True,
        ),
        Section(
            key="bilag_a_typer_personoplysninger",
            heading="Bilag A.3-A.4 — Typer + kategorier af registrerede",
            prompt=(
                "Hvilke typer personoplysninger behandles? For hvilke kategorier "
                "af registrerede? Brug DBS-skemaet (tabel-overblik)."
            ),
            default_text=(
                "Personoplysninger:\n"
                "- Almindelige: navn, adresse, kontaktinfo, ...\n"
                "- Følsomme (art. 9): [angiv hvis relevant]\n"
                "- CPR (databeskyttelsesloven §11): [angiv hvis relevant]\n\n"
                "Kategorier af registrerede:\n"
                "- Borgere: [...]\n"
                "- Medarbejdere: [...]"
            ),
            required=True,
        ),
        Section(
            key="bilag_a_varighed",
            heading="Bilag A.5 — Behandlingens varighed",
            prompt=(
                "Hvor længe varer behandlingen? Standard: indtil hovedaftalens "
                "ophør. Andet kan aftales."
            ),
            default_text="Behandlingen påbegyndes ved Bestemmelsernes ikrafttræden og ophører ved hovedaftalens ophør.",
            required=True,
        ),
        Section(
            key="bilag_b_underdatabehandlere",
            heading="Bilag B.1 — Godkendte underdatabehandlere",
            prompt=(
                "Liste over underdatabehandlere der benyttes ved aftalens "
                "indgåelse (navn + CVR + lokation + ydelse)."
            ),
            placeholder="1. Microsoft Ireland (CVR …) — Azure-hosting i EU\n2. ...",
            required=True,
        ),
        Section(
            key="bilag_b_godkendelsestype",
            heading="Bilag B — Godkendelsestype (Pkt. 7.2)",
            prompt=(
                "Standard: forudgående generel skriftlig godkendelse (administrativt "
                "lettere end specifik godkendelse pr. underdatabehandler)."
            ),
            field_type="enum",
            enum_values=[
                "valg_1_specifik_godkendelse_pr_underdatabehandler",
                "valg_2_generel_skriftlig_godkendelse_anbefalet",
            ],
            default_text="valg_2_generel_skriftlig_godkendelse_anbefalet",
            required=True,
        ),
        Section(
            key="bilag_b_varsel_skift",
            heading="Bilag B.2 — Varsel ved skift af underdatabehandler (Pkt. 7.3)",
            prompt=(
                "Standard: minimum 60 dage. Længere varsel pr. konkret "
                "underdatabehandler kan angives her."
            ),
            field_type="text",
            default_text="60 dage",
            required=True,
        ),
        Section(
            key="bilag_c_instruks",
            heading="Bilag C.1 — Behandlingens genstand/instruks",
            prompt="Kort general beskrivelse af hvad databehandleren skal foretage.",
            required=True,
        ),
        Section(
            key="bilag_c_sikkerhedsniveau",
            heading="Bilag C.2 — Sikkerhedsniveau (DBS C.2.1-C.2.11)",
            prompt=(
                "Sikkerhedsniveau fastlægges ud fra risikovurderingen + "
                "Datatilsynets vejledning om tilsyn. DBS har 11 standardkrav til "
                "foranstaltninger. Beskriv niveau (lav/mellem/høj) + relevante "
                "tilpasninger til standard-foranstaltningerne."
            ),
            required=True,
        ),
        Section(
            key="bilag_c_bistand",
            heading="Bilag C.3 — Bistand til den dataansvarlige",
            prompt=(
                "Beskriv hvilken bistand databehandleren skal yde ifm. anmodninger "
                "fra registrerede, sikkerhedsbrud, risikovurderinger og "
                "konsekvensanalyser, samt sikring af tekniske/organisatoriske foranstaltninger."
            ),
            default_text=(
                "Databehandler bistår dataansvarlig med:\n"
                "- Underretning af dataansvarlige om anmodninger fra registrerede\n"
                "- Bistand ved sikkerhedsbrud + underretning af dataansvarlig\n"
                "- Bistand ifm. risikovurderinger og konsekvensanalyser (DPIA)\n"
                "- Sikring af tekniske og organisatoriske foranstaltninger"
            ),
            required=True,
        ),
        Section(
            key="bilag_c_opbevaring_sletning",
            heading="Bilag C.4 — Opbevaring + sletteperiode",
            prompt=(
                "Standard sletterutine + opbevaringsperiode. Vær opmærksom på "
                "bevaringsværdige oplysninger (arkivlov)."
            ),
            required=True,
        ),
        Section(
            key="bilag_c_lokalitet",
            heading="Bilag C.5 — Lokalitet for behandling",
            prompt=(
                "Hvor foregår behandlingen geografisk? Hvis tredjelande involveres: "
                "angiv overførselsgrundlag (SCC, BCR, adequacy decision)."
            ),
            required=True,
        ),
        Section(
            key="bilag_c_tredjelande",
            heading="Bilag C.6 — Overførsel til tredjelande",
            prompt="Vælg om der må ske overførsel til lande uden for EU/EØS.",
            field_type="enum",
            enum_values=["valg_1_tilladt_med_grundlag", "valg_2_ikke_tilladt"],
            required=True,
        ),
        Section(
            key="bilag_c_tilsynskoncept",
            heading="Bilag C.7 — Tilsynskoncept (DBS Koncept 1-6)",
            prompt=(
                "Vælg tilsynskoncept. Standard ved høj/mellem risiko: Koncept 5 "
                "(uafhængig tredjepartsrevisionserklæring)."
            ),
            field_type="enum",
            enum_values=[
                "koncept_1_intet_tilsyn",
                "koncept_2_bekraeftelse",
                "koncept_3_skriftlig_status",
                "koncept_4_certificering_eller_adfaerdskodeks",
                "koncept_5_uafhaengig_revisionserklaering_anbefalet",
                "koncept_6_eget_tilsyn",
            ],
            default_text="koncept_5_uafhaengig_revisionserklaering_anbefalet",
            required=True,
        ),
        Section(
            key="brud_underretningsfrist",
            heading="Pkt. 10.2 — Frist for underretning ved brud",
            prompt=(
                "Standard: 24 timer fra databehandleren er blevet opmærksom på bruddet. "
                "Skal være kort nok til at dataansvarlig kan opfylde sin egen "
                "72-timers underretningspligt overfor Datatilsynet."
            ),
            field_type="text",
            default_text="24 timer",
            required=True,
        ),
        Section(
            key="sletning_eller_returnering",
            heading="Pkt. 11 — Sletning eller returnering ved aftalens ophør",
            prompt=(
                "Vælg mellem (Valg 1) sletning af alle personoplysninger med "
                "bekræftelse, eller (Valg 2) tilbagelevering + sletning af kopier."
            ),
            field_type="enum",
            enum_values=[
                "valg_1_sletning_med_bekraeftelse",
                "valg_2_tilbagelevering_plus_sletning",
            ],
            required=True,
        ),
        Section(
            key="kontaktpersoner",
            heading="Pkt. 15 — Kontaktpersoner",
            prompt=(
                "Kontaktperson hos dataansvarlig + databehandler. Særlig "
                "sikkerhedsbruds-kontakt (24/7-telefon hvis relevant)."
            ),
            required=True,
        ),
        Section(
            key="it_sikkerhed_kvalitetstjek",
            heading="Kvalitetstjek af IT-sikkerhed",
            prompt=(
                "Send udkast til IT-sikkerhed@kalundborg.dk for kvalitetstjek "
                "INDEN kontrakten indgås. Angiv dato + svar."
            ),
            required=True,
        ),
    ],
)


_AI_INDKOEB_TJEKLISTE = ArtifactTemplate(
    id="ai_indkoeb_tjekliste",
    title="Tjekliste — indkøb og anvendelse af AI (Kalundborg)",
    summary=(
        "Kalundborg Kommunes egen tjekliste der gennemgår de retlige forhold ved "
        "indkøb af AI-løsninger. Du kan IKKE nøjes med leverandørens eller andre "
        "kommuners vurderinger — kommunen skal foretage sin egen selvstændige "
        "vurdering. AI-gruppen understøtter med juridisk afklaring."
    ),
    category="forvaltning",
    estimated_minutes=240,
    legal_basis=[
        LegalReference(
            lov="EU AI-forordningen (Forordning 2024/1689)",
            artikel="Artikel 4 + 26",
            citat=(
                "Udbydere og idriftsættere træffer foranstaltninger til at "
                "sikre, at deres personale og andre personer, der er involveret "
                "i drift og anvendelse af AI-systemer, har et tilstrækkeligt "
                "AI-kompetenceniveau."
            ),
            url=_AI_ACT_URL,
        ),
        LegalReference(
            lov="Forvaltningsloven + databeskyttelsesforordningen + sektorlove",
            artikel="Tværgående",
            citat="Kommunen skal foretage sin egen selvstændige retlige vurdering.",
            url=_FVL_URL,
        ),
    ],
    external_resources=[
        ExternalResource(
            title="KAI: IT anskaffelser og databehandleraftaler",
            publisher="Kalundborg Kommune (intern)",
            url="https://kalundborg.sharepoint.com/sites/ITsikkerhed",
        ),
        ExternalResource(
            title="Digitaliseringsstyrelsen — Højrisiko-AI-systemer",
            publisher="Digitaliseringsstyrelsen",
            url="https://digst.dk/tilsyn/ai-forordningen/reglerne-i-ai-forordningen/hoejrisiko-ai-systemer/",
        ),
        ExternalResource(
            title="Reglerne i AI-forordningen",
            publisher="Digitaliseringsstyrelsen",
            url="https://digst.dk/tilsyn/ai-forordningen/reglerne-i-ai-forordningen/",
        ),
    ],
    sections=[
        Section(
            key="behov_identificeret",
            heading="1. Behovsafklaring",
            prompt=(
                "Har I gjort jer klart, hvilke sagstyper, processer og "
                "sagsbehandlingsbehov AI-løsningen skal håndtere? "
                "Beskriv konkret. Bemærk at kommunen har stor fokus på "
                "nedbringelse af dobbeltsystemer."
            ),
            required=True,
        ),
        Section(
            key="dobbeltsystem_check",
            heading="2. Dobbeltsystem-check",
            prompt=(
                "Har I tjekket om kommunen allerede har en lignende løsning? "
                "Konsultér IT-arkitektur."
            ),
            field_type="boolean",
            required=True,
        ),
        Section(
            key="serviceportal_sag_oprettet",
            heading="3. Serviceportal-sag oprettet til AI-enheden",
            prompt=(
                "Er sagen oprettet i Serviceportalen til AI-enheden? Angiv sagsnummer."
            ),
            field_type="text",
            placeholder="Sag #...",
            required=True,
        ),
        Section(
            key="ai_act_klassificering",
            heading="4. AI Act-klassificering",
            prompt=(
                "Er der gennemført klassificering iht. AI-forordningen "
                "(forbudt / højrisiko / begrænset / minimal)? Brug Bifrosts "
                "/eu-checker + /vurdering."
            ),
            required=True,
        ),
        Section(
            key="behandlingsgrundlag",
            heading="5. Lovligt behandlingsgrundlag overvejet",
            prompt=(
                "Hvilket retsgrundlag (GDPR art. 6) bruges? Vær opmærksom på "
                "at samtykke sjældent er praktisk i offentlig sammenhæng — "
                "typisk hjemmel i lov (litra c eller e)."
            ),
            required=True,
        ),
        Section(
            key="oplysningspligt",
            heading="6. Oplysningspligt-overvejelse",
            prompt=(
                "Skal de registrerede informeres om databehandlingen "
                "(GDPR art. 13/14)? Skal AI-anvendelse særskilt nævnes?"
            ),
            field_type="boolean",
            required=True,
        ),
        Section(
            key="fortegnelse_opdateret",
            heading="7. Fortegnelse over behandlingsaktiviteter opdateret",
            prompt=(
                "Er behandlingen tilføjet kommunens fortegnelse over "
                "behandlingsaktiviteter (GDPR art. 30)? Spørg din afdelings "
                "fortegnelses-ansvarlig."
            ),
            field_type="boolean",
            required=True,
        ),
        Section(
            key="risikovurdering_lavet",
            heading="8. Risikovurdering / DPIA",
            prompt=(
                "Er der lavet risikovurdering + (hvis tærskeltest viser det) DPIA? "
                "Brug skabelon på KAI."
            ),
            field_type="enum",
            enum_values=[
                "begge_lavet",
                "kun_risikovurdering",
                "intet_lavet_endnu",
            ],
            required=True,
        ),
        Section(
            key="ai_faerdigheder_dokumenteret",
            heading="9. AI-færdigheder hos personale (Art. 4)",
            prompt=(
                "Har medarbejderne der skal anvende løsningen et dokumenteret "
                "AI-kompetenceniveau? Hvilken oplæring er planlagt?"
            ),
            required=True,
        ),
        Section(
            key="saerlovgivning_tjek",
            heading="10. Særlovgivning",
            prompt=(
                "Er den særlige lovgivning der gælder for det fagområde "
                "AI-løsningen anvendes inden for, blevet tjekket? "
                "(serviceloven, sundhedsloven, beskæftigelseslov osv.)"
            ),
            required=True,
        ),
        Section(
            key="databehandleraftale_indgaaet",
            heading="11. Databehandleraftale med leverandør",
            prompt=(
                "Er der indgået databehandleraftale (DBS-standard)? Send "
                "udkast til IT-sikkerhed@kalundborg.dk for kvalitetstjek "
                "inden kontrakten indgås."
            ),
            field_type="enum",
            enum_values=["indgaaet", "udkast_sendt_til_review", "ikke_paabegyndt"],
            required=True,
        ),
        Section(
            key="indkoeb_eller_udvikling",
            heading="12. Indkøb vs. udvikling",
            prompt=(
                "Er det indkøb af færdig løsning eller udvikling af skræddersyet "
                "løsning? Påvirker krav til support, opdateringer og overensstemmelse."
            ),
            field_type="enum",
            enum_values=["indkoeb_faerdig_loesning", "skraeddersyet_udvikling", "hybrid"],
            required=True,
        ),
        Section(
            key="ai_enheden_endelig_vurdering",
            heading="13. AI-enhedens endelige vurdering",
            prompt=(
                "Har AI-enheden vendt tilbage med endelig vurdering? "
                "Angiv dato + reference."
            ),
            field_type="text",
            required=True,
        ),
        Section(
            key="bemaerkninger",
            heading="Bemærkninger / særlige forhold",
            prompt="Eventuelle bemærkninger til ovenstående punkter.",
            required=False,
        ),
    ],
)


# ============================================================================
# Den fulde katalog
# ============================================================================

ARTIFACT_TEMPLATES: dict[str, ArtifactTemplate] = {
    # AI Act (6)
    "risikostyringsplan": _RISIKOSTYRINGSPLAN,
    "datasaet_dokumentation": _DATASAET_DOKUMENTATION,
    "teknisk_dokumentation_art11": _TEKNISK_DOKUMENTATION_ART11,
    "logningsspecifikation": _LOGNINGSSPECIFIKATION,
    "human_oversight_protokol": _HUMAN_OVERSIGHT_PROTOKOL,
    "eu_database_registrering": _EU_DATABASE_REGISTRERING,
    # Forvaltningsret (7)
    "partshoringsbrev": _PARTSHORINGSBREV,
    "frist_dokumentation": _FRIST_DOKUMENTATION,
    "kvittering_for_modtagelse": _KVITTERING_FOR_MODTAGELSE,
    "sagsbehandler_review_protokol": _SAGSBEHANDLER_REVIEW_PROTOKOL,
    "begrundelsesskabelon_godkendt_af_jurist": _BEGRUNDELSESSKABELON,
    "procedure_til_lovhenvisnings_verifikation": _PROCEDURE_LOVHENVISNING,
    "klagevejledning_skabelon": _KLAGEVEJLEDNING,
    # GDPR (5)
    "retsgrundlag_dokumentation": _RETSGRUNDLAG_DOKUMENTATION,
    "menneskelig_indgriben_proces": _MENNESKELIG_INDGRIBEN,
    "bestridelsesproces": _BESTRIDELSESPROCES,
    "transparenstekst_til_registrerede": _TRANSPARENSTEKST,
    "dpia_dokument": _DPIA_DOKUMENT,
    "dpo_udtalelse": _DPO_UDTALELSE,
    # Kalundborg-/DBS-/branche-specifikke (3) — nye 2026-05-10
    "dpia_taerskelsvurdering": _DPIA_TAERSKELSVURDERING,
    "databehandleraftale_dbs": _DATABEHANDLERAFTALE_DBS,
    "ai_indkoeb_tjekliste": _AI_INDKOEB_TJEKLISTE,
}


# ---- Generic fallback for ikke-curaterede artefakter -----------------------

_HUMAN_LABELS: dict[str, str] = {
    # Map snake_case → fri tekst hvor det giver mening
    "watermark_eller_metadata_specifikation": "Watermark/metadata-specifikation (AI Act Art. 50)",
    "oplysningstekst_til_brugere": "Oplysningstekst til brugere (AI Act Art. 50)",
    "maerkning_af_syntetisk_indhold": "Mærkning af syntetisk indhold (AI Act Art. 50)",
    "udfasningsplan": "Udfasningsplan (AI Act Art. 5 — forbudt praksis)",
    "ledelsesnotat": "Ledelsesnotat (AI Act Art. 5)",
    "brugsanvisning_dansk": "Brugsanvisning på dansk (AI Act Art. 13)",
    "kapabiliteter_og_begraensninger_dokument": "Kapabiliteter + begrænsninger-dokument (AI Act Art. 13)",
    "logging_specifikation": "Logging-specifikation (AI Act Art. 13)",
    "oversight_protokol": "Oversight-protokol (AI Act Art. 14)",
    "stop_override_mekanisme_specifikation": "Stop/override-mekanisme (AI Act Art. 14)",
    "traeningsmateriale_personale": "Træningsmateriale til personale (AI Act Art. 14, Art. 4)",
    "fortegnelses_post": "Fortegnelses-post (GDPR Art. 30)",
    "henvisning_til_national_lovgivning": "Henvisning til national lovgivning (GDPR Art. 6, stk. 3)",
    "oplysningstekst": "Oplysningstekst til registrerede (GDPR Art. 13/14)",
    "retsgrundlags_notat": "Retsgrundlags-notat (GDPR Art. 6)",
    "dataminimerings_vurdering": "Dataminimerings-vurdering (GDPR Art. 5)",
    "formaalsbeskrivelse": "Formålsbeskrivelse (GDPR Art. 5)",
    "opbevaringspolitik": "Opbevaringspolitik (GDPR Art. 5)",
    "rettelsesproces": "Rettelsesproces (GDPR Art. 5, Art. 16)",
    "sikkerhedspolitik": "Sikkerhedspolitik (GDPR Art. 5, Art. 32)",
    "krypteringspolitik": "Krypteringspolitik (GDPR Art. 32)",
    "adgangskontrol_specifikation": "Adgangskontrol-specifikation (GDPR Art. 32)",
    "backup_test_log": "Backup test-log (GDPR Art. 32)",
    "sikkerhedstest_rapport": "Sikkerhedstest-rapport (GDPR Art. 32)",
    "aarlig_evaluering": "Årlig evaluering af sikkerhed (GDPR Art. 32)",
    "brud_anmeldelses_proces": "Brud-anmeldelsesproces (GDPR Art. 33)",
    "behandler_saerlige_kategorier": "Vurdering af særlige kategorier (GDPR Art. 9)",
    "stikproevekontrol_log": "Stikprøvekontrol-log (FVL § 24)",
    "lovhenvisnings_verifikator_specifikation": "Lovhenvisnings-verifikator-specifikation (FVL § 24)",
    "bias_audit_rapport": "Bias-audit-rapport (FVL § 3 + AI Act Art. 9)",
    "leverandor_uafhaengigheds_erklaering": "Leverandør-uafhængigheds-erklæring (FVL § 3)",
    "sagsbehandler_forretningsgang": "Sagsbehandler-forretningsgang (FVL § 3)",
    "aktindsigt_procedure": "Aktindsigt-procedure (Offentlighedsloven)",
    "anonymiseringsprocedure": "Anonymiserings-procedure (Offentlighedsloven § 13)",
    "datasammenstillings_katalog": "Datasammenstillings-katalog (Offentlighedsloven § 13)",
    "kvalitetssikring_proces_sundhedsfaglig": "Kvalitetssikring sundhedsfaglig (Sundhedsloven)",
    "kvalitetssikrings_specifikation": "Kvalitetssikrings-specifikation",
    "vejledningsproces_dokumentation": "Vejledningsproces-dokumentation (Servicelov § 11)",
    "kontaktforloeb_proces_dokumentation": "Kontaktforløb-procesdokumentation (Beskæftigelseslov § 11)",
    "jobplan_indholds_specifikation": "Jobplan-indholdsspecifikation (Beskæftigelseslov § 27)",
    "kvalitetssikrings_proces_jobplan": "Kvalitetssikrings-proces jobplan (Beskæftigelseslov § 27)",
    "dpia_hvis_helbredsdata": "DPIA hvis helbredsdata (Servicelov § 102 + GDPR Art. 35)",
    "dpia_dokument_boerne_screening": "DPIA — børnefaglig screening (Servicelov § 50 + GDPR Art. 35)",
    "bias_evalueringsrapport": "Bias-evalueringsrapport (børneområdet)",
    "faglig_vurderingsproces": "Faglig vurderingsproces (Servicelov § 102)",
    "journal_dokumentation_specifikation": "Journal-dokumentationsspecifikation (Servicelov § 50)",
    "sagsbehandler_godkendelsesproces": "Sagsbehandler-godkendelsesproces (Servicelov § 50)",
    "laesbarhedsindeks_test": "Læsbarhedsindeks-test (Sundhedsloven)",
}


def _make_generic_template(artifact_id: str) -> ArtifactTemplate:
    """Generisk fallback for ikke-curaterede artefakter."""
    label = _HUMAN_LABELS.get(artifact_id) or artifact_id.replace("_", " ").capitalize()
    return ArtifactTemplate(
        id=artifact_id,
        title=label,
        summary=(
            f"'{label}' er identificeret som påkrævet evidens-artefakt af en eller "
            f"flere regler i Bifrosts korpus. Detaljeret skabelon er endnu ikke "
            f"curateret — udfyld nedenstående felter med hvad I planlægger at gøre, "
            f"og opdater senere når en jurist har gennemgået artefaktet."
        ),
        category="generic",
        estimated_minutes=45,
        sections=[
            Section(
                key="hvad_er_dokumentet",
                heading="Hvad er dette dokument?",
                prompt="Kort beskrivelse af artefaktets formål.",
                required=True,
            ),
            Section(
                key="lovhjemmel",
                heading="Lovhjemmel",
                prompt="Hvilke retsregler kræver dette artefakt?",
                required=True,
            ),
            Section(
                key="ansvarlig",
                heading="Ansvarlig person/team",
                prompt="Hvem ejer artefaktet?",
                field_type="text",
                required=True,
            ),
            Section(
                key="indhold",
                heading="Indhold (fri tekst eller henvisning)",
                prompt=(
                    "Selve indholdet, eller henvisning til hvor artefaktet "
                    "ligger (sti, dokumentnavn, link)."
                ),
                required=True,
            ),
            Section(
                key="reviewers",
                heading="Reviewers / godkendere",
                prompt="Hvem har gennemgået og godkendt? Dato.",
                field_type="text",
                required=False,
            ),
        ],
    )


def get_template(artifact_id: str) -> ArtifactTemplate:
    """Returnér curated skabelon hvis vi har en, ellers generisk."""
    tmpl = ARTIFACT_TEMPLATES.get(artifact_id)
    if tmpl:
        return tmpl
    return _make_generic_template(artifact_id)


def list_templates() -> list[dict]:
    """Liste alle curated skabeloner — bruges af /drift og frontend katalog."""
    return [tmpl.to_dict() for tmpl in ARTIFACT_TEMPLATES.values()]


def all_known_ids() -> set[str]:
    """Inklusive både curated og kendte ikke-curaterede IDs (fra _HUMAN_LABELS)."""
    return set(ARTIFACT_TEMPLATES.keys()) | set(_HUMAN_LABELS.keys())


# ---- Status-beregning -----------------------------------------------------


def compute_status(template: ArtifactTemplate, content: dict[str, Any] | None) -> str:
    """Returnér 'mangler' | 'i_gang' | 'faerdig' baseret på hvilke required-
    sektioner der har indhold."""
    if not content:
        return "mangler"
    required = template.required_section_keys()
    if not required:
        # Skabelon uden krav-felter — betragt som færdig hvis nogen sektion er udfyldt
        any_filled = any(_is_filled(v) for v in content.values())
        return "faerdig" if any_filled else "mangler"

    filled_required = {k for k in required if _is_filled(content.get(k))}
    if not filled_required:
        # Måske er der noget i ikke-required felter
        any_filled = any(_is_filled(v) for v in content.values())
        return "i_gang" if any_filled else "mangler"
    if filled_required == required:
        return "faerdig"
    return "i_gang"


def _is_filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, bool):
        # boolean: betragtes som udfyldt hvis det er True (eller False og bevidst sat)
        return True
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return bool(value)
