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

    def er_ekstern_leverandoer(self) -> bool:
        return not self.internt_udviklet and bool(self.leverandoer_navn)

    def har_foelsomme_data(self) -> bool:
        return any(
            k in (DataKategori.FOELSOMME, DataKategori.CPR, DataKategori.STRAFBARE)
            for k in self.persondata_kategorier
        )


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
