"""Pydantic-datamodeller for risikovurderingsmotoren.

Bevidst IKKE `from __future__ import annotations` — det bryder Pydantic v2
forward-ref-resolution når modellerne bruges i FastAPI-signaturer.

Defaults er liberale så en delvis LLM-ekstraktion ikke crasher; manglende
felter udløser i stedet et afklarende spørgsmål (se clarifying.py).
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class DataKategori(str, Enum):
    """GDPR-datakategorier."""
    ALMINDELIGE = "almindelige"   # art. 6
    FOELSOMME = "følsomme"        # art. 9
    CPR = "cpr"                   # databeskyttelsesloven § 11
    STRAFBARE = "strafbare"       # art. 10
    INGEN = "ingen"               # systemet behandler ikke persondata


class Niveau(str, Enum):
    """Risikoniveauer — tekstuelle trin brugt i skabelonen."""
    LAV = "Lav"
    LAV_MIDDEL = "Lav-middel"
    MIDDEL = "Middel"
    MIDDEL_HOEJ = "Middel-høj"
    HOEJ = "Høj"


class Anskaffelsesvej(str, Enum):
    """Indkøbsvej jf. Kalundborg Kommunes Retningslinjer for IT-anskaffelser."""
    SKI_DIREKTE = "ski_direkte"            # direkte tildeling på SKI-aftale
    SKI_MINIUDBUD = "ski_miniudbud"        # mini-udbud mellem leverandører på SKI
    UNDER_TAERSKEL = "under_taerskel"       # < kr. 1.601.944 (2022), ingen udbudspligt
    EU_UDBUD = "eu_udbud"                   # > tærskel, EU-udbudspligt
    BYGGE_ANLAEG = "bygge_anlaeg"           # netværk/installationer i kommunale bygninger
    UKENDT = "ukendt"                       # endnu ikke afklaret


# Udbudsterskel (2022) jf. Retningslinjer for IT-anskaffelser — beregnet over 4 år
UDBUDSTERSKEL_KR_4AAR = 1_601_944

# De 9 kommunale procespunkter — SINGLE SOURCE OF TRUTH.
# (attribut-navn på SystemFacts, option-label vist i UI).
# clarifying.build_questions genererer multiselect-options herfra, og
# apply_answers matcher svar mod labels — så label-tekst og parsing aldrig
# kan divergere. Ændr label her, og begge sider følger med.
PROCES_PUNKTER: list[tuple[str, str]] = [
    ("dit_involveret_tidligt", "Digitalisering og IT adviseret tidligt"),
    ("cio_har_underskrevet", "CIO har underskrevet kontrakt + DBA"),
    ("databehandleraftale_indgaaet", "Databehandleraftale indgået"),
    ("styregruppe_etableret", "Styregruppe etableret (EU-udbud)"),
    ("fortegnelse_art30_opdateret", "Tilmeldt fortegnelse art. 30 (via IT-sikkerhedsambassadør)"),
    ("oplysningspligt_opfyldt", "Oplysningspligt opfyldt (art. 13-14)"),
    ("dpia_sendt_til_dpo", "DPIA-udkast sendt til DPO"),
    ("ai_faerdigheder_dokumenteret", "AI-færdigheder dokumenteret (AI-forord. art. 4)"),
    ("contract_management_plan", "Contract Management-plan klar"),
]


# Tilladte fritekst-varianter LLM'en kan finde på at returnere → normalisér
_NIVEAU_ALIASES = {
    "lav": Niveau.LAV,
    "lav-middel": Niveau.LAV_MIDDEL,
    "lav-mellem": Niveau.LAV_MIDDEL,
    "middel": Niveau.MIDDEL,
    "mellem": Niveau.MIDDEL,
    "middel-høj": Niveau.MIDDEL_HOEJ,
    "middel-hoj": Niveau.MIDDEL_HOEJ,
    "mellem-høj": Niveau.MIDDEL_HOEJ,
    "høj": Niveau.HOEJ,
    "hoj": Niveau.HOEJ,
    "high": Niveau.HOEJ,
    "low": Niveau.LAV,
    "medium": Niveau.MIDDEL,
}


def normalize_niveau(value) -> Niveau:
    """Konvertér fritekst/enum til et gyldigt Niveau. Default = MIDDEL."""
    if isinstance(value, Niveau):
        return value
    if not value:
        return Niveau.MIDDEL
    key = str(value).strip().lower()
    if key in _NIVEAU_ALIASES:
        return _NIVEAU_ALIASES[key]
    # Prøv eksakt enum-value match (fx "Lav-middel")
    for n in Niveau:
        if n.value.lower() == key:
            return n
    return Niveau.MIDDEL


class Underdatabehandler(BaseModel):
    navn: str
    cvr_eller_id: Optional[str] = None
    land: str = "Ukendt"
    rolle: str = ""  # fx "Hosting", "AI-inference", "E-mail"


class SystemFacts(BaseModel):
    """Strukturerede fakta udtrukket fra uploadede dokumenter + bruger-svar."""

    systemnavn: str = ""
    leverandoer_navn: str = ""
    leverandoer_cvr: Optional[str] = None
    leverandoer_land: str = "Ukendt"
    leverandoer_stiftet_aar: Optional[int] = None

    formaal_kort: str = ""        # 1-2 sætninger om hvad systemet gør
    funktionalitet: str = ""      # teknisk beskrivelse, 3-5 sætninger

    hosting_lokation: str = ""    # fx "Microsoft Azure EU-region"
    underdatabehandlere: List[Underdatabehandler] = Field(default_factory=list)

    persondata_kategorier: List[DataKategori] = Field(default_factory=list)
    persondata_typer: List[str] = Field(default_factory=list)
    registrerede: List[str] = Field(default_factory=list)
    authentication: str = ""      # fx "Entra ID SSO + MFA"

    # Røde flag identificeret i MSA/DBA
    msa_risiko_klausuler: List[str] = Field(default_factory=list)
    ansvarsloft: Optional[str] = None
    ip_indemnification_cap: Optional[str] = None
    retention_efter_ophoer: Optional[str] = None

    # Bruger-svar fra afklarende spørgsmål
    scope: str = "begge"          # "poc" | "bred_udrulning" | "begge"
    tilgang: str = "idealiseret"  # "idealiseret" | "realistisk"
    medarbejder_overvaagning: bool = False
    ekstra_interessenter: List[str] = Field(default_factory=list)

    # Intern/ekstern: påvirker hvilke risici der er relevante
    internt_udviklet: bool = False

    # ---- Kalundborg-specifikke procesforhold (Retningslinjer + AI-tjekliste) ----
    # Kontraktværdi over 4 år (kr.). Bestemmer udbudspligt vs UDBUDSTERSKEL_KR_4AAR.
    kontraktvaerdi_4aar_kr: Optional[int] = None
    # Når værdien stammer fra et bucket-svar (ikke et faktisk beløb) sættes
    # er_estimat=True + bucket_label, så prompts viser intervallet i stedet for
    # det repræsentative tal — ellers risikerer LLM at citere et opdigtet beløb
    # som faktum i et officielt dokument.
    kontraktvaerdi_er_estimat: bool = False
    kontraktvaerdi_bucket_label: str = ""
    anskaffelsesvej: Anskaffelsesvej = Anskaffelsesvej.UKENDT
    # Fagområde + relevant særlovgivning (fri tekst — fx "Beskæftigelse — LAB §17a")
    fagomraade: str = ""
    saerlovgivning: List[str] = Field(default_factory=list)
    # Hjemmelsgrundlag (national hjemmel UDOVER GDPR-grundlaget)
    national_lovhjemmel: str = ""
    # Svar på de dynamiske Datatilsyn-skabelon-spørgsmål (key uden dt_-præfiks → svar).
    # Bruges som ekstra kontekst til risiko- og indholdsgenerering.
    datatilsyn_svar: dict = Field(default_factory=dict)
    # Procesforhold — booleans der afgør compliance med kommunal proces
    dit_involveret_tidligt: bool = False     # Digitalisering og IT adviseret i idéfasen
    cio_har_underskrevet: bool = False        # Digitaliserings- og IT-chefens underskrift
    styregruppe_etableret: bool = False       # ledelsesmæssig forankring (EU-udbud kræver)
    fortegnelse_art30_opdateret: bool = False # tilmeldt fortegnelse via IT-sikkerhedsambassadør
    dpia_sendt_til_dpo: bool = False          # konsekvensanalyse-udkast fremsendt
    oplysningspligt_opfyldt: bool = False     # art. 13-14
    ai_faerdigheder_dokumenteret: bool = False  # AI-forordningens art. 4
    databehandleraftale_indgaaet: bool = False  # DBA underskrevet
    contract_management_plan: bool = False    # plan for driftsperioden

    def er_ekstern_leverandoer(self) -> bool:
        return not self.internt_udviklet and bool(self.leverandoer_navn)

    def har_foelsomme_data(self) -> bool:
        return any(
            k in (DataKategori.FOELSOMME, DataKategori.CPR, DataKategori.STRAFBARE)
            for k in self.persondata_kategorier
        )

    def er_over_udbudsterskel(self) -> Optional[bool]:
        """True hvis kontraktværdi > tærskel, False hvis under, None hvis ukendt."""
        if self.kontraktvaerdi_4aar_kr is None:
            return None
        return self.kontraktvaerdi_4aar_kr > UDBUDSTERSKEL_KR_4AAR

    def kontraktvaerdi_label(self) -> str:
        """Tekst til LLM-prompts. Bruger bucket-intervallet når værdien er et
        estimat, så et opdigtet repræsentativt tal aldrig citeres som faktum."""
        if self.kontraktvaerdi_4aar_kr is None:
            return "ukendt"
        if self.kontraktvaerdi_er_estimat:
            return (
                f"{self.kontraktvaerdi_bucket_label} (bruger-estimat — "
                f"citér IKKE et konkret beløb i teksten)"
            )
        return f"{self.kontraktvaerdi_4aar_kr:,} kr.".replace(",", ".")

    def udbudspligt_mismatch(self) -> bool:
        """True hvis værdi over tærskel men anskaffelsesvej ikke er EU-udbud →
        compliance-risiko (potentielt ulovligt indkøb)."""
        if self.er_over_udbudsterskel() is True:
            return self.anskaffelsesvej not in (
                Anskaffelsesvej.EU_UDBUD, Anskaffelsesvej.UKENDT,
            )
        return False

    def proces_status_count(self) -> tuple[int, int]:
        """Returnér (opfyldt, total) for de 9 procesforhold — bruges til status-badge."""
        flags = [
            self.dit_involveret_tidligt, self.cio_har_underskrevet,
            self.styregruppe_etableret, self.fortegnelse_art30_opdateret,
            self.dpia_sendt_til_dpo, self.oplysningspligt_opfyldt,
            self.ai_faerdigheder_dokumenteret, self.databehandleraftale_indgaaet,
            self.contract_management_plan,
        ]
        return sum(flags), len(flags)


class Risiko(BaseModel):
    risiko: str = Field(..., description="Kort identifikation af risikoen")
    konsekvens_beskrivelse: str = Field(
        ..., description="Hel sætning — konkrete konsekvenser for de registrerede"
    )
    sandsynlighed: Niveau = Niveau.MIDDEL
    score: Niveau = Niveau.MIDDEL
    hvorfor: str = Field(default="", description="2-4 sætninger der begrunder scoren")


class Risikovurdering(BaseModel):
    """Komplet vurdering — facts + risici + alle skabelon-felttekster.

    Dette er det fulde objekt der sendes til DOCX-assembleren. Frontend
    holder det mellem /generate og /render så render-trinet er deterministisk
    uden flere LLM-kald.
    """

    facts: SystemFacts
    risici: List[Risiko] = Field(default_factory=list)

    # Table 0
    formaal_tekst: str = ""
    omfang_tekst: str = ""
    ansvarlige_tekst: str = ""
    # Table 1
    baggrund_tekst: str = ""
    funktionalitet_tekst: str = ""
    interessenter_tekst: str = ""
    # Table 2
    personoplysninger_tekst: str = ""
    lokationer_tekst: str = ""
    adgangsrettigheder_tekst: str = ""
    saarbarheder_tekst: str = ""
    # Table 6
    tiltag_tekst: str = ""
    ansvarlige_tiltag_tekst: str = ""
    # Table 7
    kontrolmekanismer_tekst: str = ""
    opdatering_tekst: str = ""

    def alle_felttekster(self) -> dict:
        """Til verifikation — map af feltnavn → tekst (ekskl. risici)."""
        return {
            "formaal": self.formaal_tekst,
            "omfang": self.omfang_tekst,
            "ansvarlige": self.ansvarlige_tekst,
            "baggrund": self.baggrund_tekst,
            "funktionalitet": self.funktionalitet_tekst,
            "interessenter": self.interessenter_tekst,
            "personoplysninger": self.personoplysninger_tekst,
            "lokationer": self.lokationer_tekst,
            "adgangsrettigheder": self.adgangsrettigheder_tekst,
            "saarbarheder": self.saarbarheder_tekst,
            "tiltag": self.tiltag_tekst,
            "ansvarlige_tiltag": self.ansvarlige_tiltag_tekst,
            "kontrolmekanismer": self.kontrolmekanismer_tekst,
            "opdatering": self.opdatering_tekst,
        }


class ClarifyingQuestion(BaseModel):
    """Et afklarende spørgsmål der vises til brugeren."""
    key: str
    question: str
    type: str = "radio"  # radio | multiselect | text
    options: List[str] = Field(default_factory=list)
    default: Optional[str] = None
    reason: str = ""  # hvorfor vi spørger (vises som hjælpetekst)
