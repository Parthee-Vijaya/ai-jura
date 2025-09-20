"""
Simplified FastAPI Backend for The Judge - AI Compliance Platform
Dansk AI compliance platform med web research (simplified version)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime, timedelta
import json
import asyncio

# Import our modules
from src.news.live_scraper import LiveNewsScraper
from src.knowledge.legal_database import legal_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Project Judge Dredd - AI Compliance Control",
    description="Professional AI Compliance Control Platform med juridisk regelmotor, evidenskatalog og beslutningslogik",
    version="2.0.0"
)

# Initialize news scraper
news_scraper = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global news_scraper
    news_scraper = LiveNewsScraper()
    async with news_scraper:
        await news_scraper.fetch_latest_news()

    # Start background news updating
    asyncio.create_task(start_news_updater())

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    services: Dict[str, str]

# 7-punkts AI-vurdering modeller
class SevenStepAssessmentRequest(BaseModel):
    """Struktureret 7-punkts AI-vurdering anmodning"""
    # Grundlæggende information
    system_navn: str
    system_beskrivelse: str
    organisation: str
    kontaktperson: str

    # Trin 1: AI-system identifikation
    system_type: str  # software, hardware, hybrid
    automatisering_grad: str  # manuel, semi-automatisk, fuldt_automatisk
    beslutningstagning: str  # ingen, støttende, automatisk

    # Trin 2: Data behandling
    behandler_data: bool = True
    data_typer: List[str] = []
    personoplysninger: bool = False
    særlige_kategorier: bool = False  # følsomme personoplysninger

    # Kontekst information
    sektor: str
    målgruppe: List[str] = []
    geografisk_område: List[str] = ["Danmark", "EU"]

    # Ekstra information
    nuværende_status: str = "planlægning"  # planlægning, udvikling, test, produktion
    tidslinje: Optional[str] = None

class AssessmentStep(BaseModel):
    """Enkelt vurderingstrin"""
    step_nummer: int
    step_navn: str
    step_beskrivelse: str
    status: str  # ikke_startet, igangværende, afsluttet, ikke_relevant
    resultat: Optional[Dict[str, Any]] = None
    anbefalinger: List[str] = []
    næste_trin: List[str] = []

class SevenStepAssessmentResult(BaseModel):
    """Resultat af 7-punkts vurdering"""
    vurdering_id: str
    oprettet: datetime
    system_info: Dict[str, Any]

    # De 7 trin
    trin_1_ai_system: AssessmentStep
    trin_2_persondata: AssessmentStep
    trin_3_databeskyttelse: AssessmentStep
    trin_4_ai_forordning: AssessmentStep
    trin_5_medarbejder_uddannelse: AssessmentStep
    trin_6_ressourcer: AssessmentStep
    trin_7_systemkrav: AssessmentStep

    # Samlet vurdering
    samlet_risikoniveau: str  # lav, medium, høj, kritisk
    compliance_score: float
    prioriterede_handlinger: List[Dict[str, Any]]

    # Specialvurderinger
    kræver_dpia: bool = False
    kræver_fria: bool = False
    kræver_lovlig_grund: bool = False

    # Ressourcer og vejledning
    relevante_ressourcer: List[Dict[str, Any]] = []
    næste_skridt: List[str] = []

# Bevar den gamle model for bagudkompatibilitet
class QuickCheckRequest(BaseModel):
    beskrivelse: str
    ai_type: str
    sektor: str
    behandler_persondata: bool = False
    automatiserede_beslutninger: bool = False

class ResearchRequest(BaseModel):
    emne: str
    fokusområder: List[str] = None

# 7-punkts AI-vurdering logik
class SevenStepAssessmentEngine:
    """Motor til at udføre struktureret 7-punkts AI-vurdering"""

    def __init__(self):
        self.assessment_results = {}

    def perform_full_assessment(self, request: SevenStepAssessmentRequest) -> SevenStepAssessmentResult:
        """Udfører komplet 7-punkts vurdering"""
        vurdering_id = f"assessment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Grundlæggende system information
        system_info = {
            "navn": request.system_navn,
            "beskrivelse": request.system_beskrivelse,
            "organisation": request.organisation,
            "sektor": request.sektor,
            "status": request.nuværende_status
        }

        # Udfør alle 7 trin
        trin_1 = self._assess_step_1_ai_system(request)
        trin_2 = self._assess_step_2_personal_data(request)
        trin_3 = self._assess_step_3_data_protection(request, trin_2)
        trin_4 = self._assess_step_4_ai_regulation(request, trin_1)
        trin_5 = self._assess_step_5_employee_training(request)
        trin_6 = self._assess_step_6_resources(request)
        trin_7 = self._assess_step_7_system_requirements(request, trin_1, trin_4)

        # Beregn samlet risikoniveau og compliance score
        risk_level, compliance_score = self._calculate_overall_assessment(
            trin_1, trin_2, trin_3, trin_4, trin_5, trin_6, trin_7
        )

        # Bestem specialvurderinger
        kræver_dpia = self._requires_dpia(request, trin_2)
        kræver_fria = self._requires_fria(request, trin_1, trin_4)
        kræver_lovlig_grund = request.personoplysninger

        # Generer prioriterede handlinger
        prioriterede_handlinger = self._generate_priority_actions(
            trin_1, trin_2, trin_3, trin_4, trin_5, trin_6, trin_7,
            kræver_dpia, kræver_fria
        )

        # Samle relevante ressourcer
        relevante_ressourcer = self._gather_relevant_resources(request, trin_1, trin_4)

        # Generer næste skridt
        næste_skridt = self._generate_next_steps(
            risk_level, kræver_dpia, kræver_fria, prioriterede_handlinger
        )

        return SevenStepAssessmentResult(
            vurdering_id=vurdering_id,
            oprettet=datetime.now(),
            system_info=system_info,
            trin_1_ai_system=trin_1,
            trin_2_persondata=trin_2,
            trin_3_databeskyttelse=trin_3,
            trin_4_ai_forordning=trin_4,
            trin_5_medarbejder_uddannelse=trin_5,
            trin_6_ressourcer=trin_6,
            trin_7_systemkrav=trin_7,
            samlet_risikoniveau=risk_level,
            compliance_score=compliance_score,
            prioriterede_handlinger=prioriterede_handlinger,
            kræver_dpia=kræver_dpia,
            kræver_fria=kræver_fria,
            kræver_lovlig_grund=kræver_lovlig_grund,
            relevante_ressourcer=relevante_ressourcer,
            næste_skridt=næste_skridt
        )

    def _assess_step_1_ai_system(self, request: SevenStepAssessmentRequest) -> AssessmentStep:
        """Trin 1: Undersøg om systemet er et AI-system"""
        # Analysér om systemet kvalificerer som AI ifølge EU AI Act definition
        ai_indicators = []
        is_ai_system = False

        # Check for AI karakteristika
        if request.automatisering_grad in ["semi-automatisk", "fuldt_automatisk"]:
            ai_indicators.append("Automatiseret funktionalitet")

        if request.beslutningstagning in ["støttende", "automatisk"]:
            ai_indicators.append("Beslutningsstøtte eller automatisk beslutningstagning")

        # Analysér systembeskrivelse for AI-nøgleord
        ai_keywords = [
            "machine learning", "kunstig intelligens", "ai", "algoritme",
            "neural network", "deep learning", "predict", "classification",
            "recommendation", "computer vision", "natural language",
            "generativ", "prædiktiv"
        ]

        beskrivelse_lower = request.system_beskrivelse.lower()
        found_keywords = [kw for kw in ai_keywords if kw in beskrivelse_lower]
        if found_keywords:
            ai_indicators.extend([f"AI-relateret teknologi: {kw}" for kw in found_keywords])

        # Bestam om det er et AI-system
        is_ai_system = len(ai_indicators) >= 2 or any(
            kw in beskrivelse_lower for kw in ["ai", "kunstig intelligens", "machine learning"]
        )

        if is_ai_system:
            status = "afsluttet"
            resultat = {
                "er_ai_system": True,
                "ai_type": self._determine_ai_type(request),
                "indikatorer": ai_indicators,
                "definition_match": "Systemet opfylder EU AI Act definition af AI-system"
            }
            anbefalinger = [
                "Systemet klassificeres som AI-system - AI Act krav gælder",
                "Gennemfør risikovurdering jf. AI Act Annex III",
                "Dokumentér AI-systemets kapaciteter og begrænsninger"
            ]
            næste_trin = ["Trin 2: Vurder personoplysningsbehandling"]
        else:
            status = "afsluttet"
            resultat = {
                "er_ai_system": False,
                "begrundelse": "Systemet opfylder ikke EU AI Act definition",
                "manglende_elementer": ["Utilstrækkelige AI-karakteristika identificeret"]
            }
            anbefalinger = [
                "Systemet klassificeres ikke som AI-system",
                "AI Act krav gælder ikke direkte",
                "Overvej almindelige databeskyttelseskrav hvis relevant"
            ]
            næste_trin = ["Eventuelt: Trin 2 for databeskyttelse"]

        return AssessmentStep(
            step_nummer=1,
            step_navn="AI-system identifikation",
            step_beskrivelse="Undersøger om systemet opfylder EU AI Act definition af AI-system",
            status=status,
            resultat=resultat,
            anbefalinger=anbefalinger,
            næste_trin=næste_trin
        )

    def _assess_step_2_personal_data(self, request: SevenStepAssessmentRequest) -> AssessmentStep:
        """Trin 2: Undersøg om AI-systemet behandler personoplysninger"""
        if not request.behandler_data:
            return AssessmentStep(
                step_nummer=2,
                step_navn="Personoplysningsbehandling",
                step_beskrivelse="Vurdering af personoplysningsbehandling",
                status="ikke_relevant",
                resultat={"behandler_persondata": False},
                anbefalinger=["Ingen personoplysninger behandles - GDPR ikke relevant"],
                næste_trin=["Spring til Trin 4: AI-forordning"]
            )

        # Analysér datatyper for personoplysninger
        personal_data_indicators = []
        risk_level = "lav"

        if request.personoplysninger:
            personal_data_indicators.append("Direkte personoplysninger identificeret")

        if request.særlige_kategorier:
            personal_data_indicators.append("Særlige kategorier af personoplysninger")
            risk_level = "høj"

        # Check datatyper for potentielle personoplysninger
        sensitive_data_types = [
            "biometrisk", "sundhed", "genetisk", "race", "religion",
            "politisk", "fagforening", "seksuel", "straffeattest"
        ]

        for data_type in request.data_typer:
            if any(sensitive in data_type.lower() for sensitive in sensitive_data_types):
                personal_data_indicators.append(f"Potentielt følsom datatype: {data_type}")
                risk_level = "høj"

        # Almindelige persondata indikatorer
        personal_identifiers = ["navn", "email", "telefon", "adresse", "cpr", "ip-adresse"]
        for data_type in request.data_typer:
            if any(identifier in data_type.lower() for identifier in personal_identifiers):
                personal_data_indicators.append(f"Personidentifikator: {data_type}")
                if risk_level == "lav":
                    risk_level = "medium"

        # Sektorspecifik analyse
        if request.sektor.lower() in ["sundhed", "finans", "uddannelse"]:
            personal_data_indicators.append(f"Sektor '{request.sektor}' typisk personoplysningsintensiv")
            if risk_level == "lav":
                risk_level = "medium"

        has_personal_data = len(personal_data_indicators) > 0 or request.personoplysninger

        resultat = {
            "behandler_personoplysninger": has_personal_data,
            "risikoniveau": risk_level,
            "identificerede_indikatorer": personal_data_indicators,
            "særlige_kategorier": request.særlige_kategorier,
            "datatyper": request.data_typer
        }

        if has_personal_data:
            anbefalinger = [
                "GDPR compliance nødvendig",
                "Etabler lovligt grundlag for behandling",
                "Implementer databeskyttelse by design",
                "Overvej DPIA hvis højrisiko behandling"
            ]
            if risk_level == "høj":
                anbefalinger.insert(0, "HØJE RISIKO: Særlige kategorier kræver eksplicit samtykke")

            næste_trin = ["Trin 3: Databeskyttelsesregler"]
        else:
            anbefalinger = ["Ingen personoplysninger identificeret", "GDPR ikke direkte relevant"]
            næste_trin = ["Spring til Trin 4: AI-forordning"]

        return AssessmentStep(
            step_nummer=2,
            step_navn="Personoplysningsbehandling",
            step_beskrivelse="Vurdering af om systemet behandler personoplysninger",
            status="afsluttet",
            resultat=resultat,
            anbefalinger=anbefalinger,
            næste_trin=næste_trin
        )

    def _assess_step_3_data_protection(self, request: SevenStepAssessmentRequest,
                                      trin_2: AssessmentStep) -> AssessmentStep:
        """Trin 3: Vurdering i forhold til databeskyttelsesreglerne"""
        if not trin_2.resultat or not trin_2.resultat.get("behandler_personoplysninger"):
            return AssessmentStep(
                step_nummer=3,
                step_navn="Databeskyttelsesregler",
                step_beskrivelse="GDPR compliance vurdering",
                status="ikke_relevant",
                resultat={"gdpr_relevant": False},
                anbefalinger=["GDPR ikke relevant - ingen personoplysninger"],
                næste_trin=["Trin 4: AI-forordning"]
            )

        # GDPR compliance check baseret på eksisterende gdpr_checker logik
        gdpr_issues = []
        gdpr_score = 70  # Baseline score

        # Lovligt grundlag
        legal_basis_options = []
        if request.sektor.lower() in ["sundhed", "medical"]:
            legal_basis_options.append("Eksplicit samtykke (sundhedsdata)")
            gdpr_score -= 10
        elif "offentlig" in request.sektor.lower():
            legal_basis_options.append("Opgave i samfundets interesse")
        else:
            legal_basis_options.append("Berettiget interesse (med balancetest)")

        # Automatiserede beslutninger
        automated_decision_issues = []
        if request.beslutningstagning == "automatisk":
            automated_decision_issues = [
                "Implementer menneskelig indgriben",
                "Sørg for mulighed for at anfægte beslutninger",
                "Giv information om logikken i beslutningstagning"
            ]
            gdpr_score -= 20

        # Sikkerhedsforanstaltninger
        security_requirements = [
            "Kryptering af data i transit og hvile",
            "Adgangskontrol og autentificering",
            "Logning og overvågning",
            "Regelmæssige sikkerhedstests"
        ]

        # Datasubjekt rettigheder
        data_rights = [
            "Ret til information (artikel 13-14)",
            "Ret til indsigt (artikel 15)",
            "Ret til berigtigelse (artikel 16)",
            "Ret til sletning (artikel 17)",
            "Ret til dataportabilitet (artikel 20)",
            "Ret til indsigelse (artikel 21)"
        ]

        if automated_decision_issues:
            data_rights.append("Særlige rettigheder ved automatiseret beslutningstagning (artikel 22)")

        resultat = {
            "gdpr_score": gdpr_score,
            "lovligt_grundlag_anbefalinger": legal_basis_options,
            "automatiserede_beslutninger": automated_decision_issues,
            "sikkerhedskrav": security_requirements,
            "datasubjekt_rettigheder": data_rights,
            "identificerede_problemer": gdpr_issues
        }

        anbefalinger = [
            f"Etabler lovligt grundlag: {legal_basis_options[0]}",
            "Udarbejd privacy notice/databeskyttelsespolitik",
            "Implementer databeskyttelse by design og by default",
            "Etabler procedurer for datasubjekt rettigheder"
        ]

        if automated_decision_issues:
            anbefalinger.extend(automated_decision_issues)

        if gdpr_score < 60:
            anbefalinger.insert(0, "KRITISK: Flere GDPR compliance problemer identificeret")

        return AssessmentStep(
            step_nummer=3,
            step_navn="Databeskyttelsesregler",
            step_beskrivelse="GDPR compliance vurdering og krav",
            status="afsluttet",
            resultat=resultat,
            anbefalinger=anbefalinger,
            næste_trin=["Trin 4: AI-forordning vurdering"]
        )

    def _assess_step_4_ai_regulation(self, request: SevenStepAssessmentRequest,
                                   trin_1: AssessmentStep) -> AssessmentStep:
        """Trin 4: Vurdering i forhold til AI-forordningen"""
        if not trin_1.resultat or not trin_1.resultat.get("er_ai_system"):
            return AssessmentStep(
                step_nummer=4,
                step_navn="AI-forordning (EU AI Act)",
                step_beskrivelse="Vurdering af AI Act compliance krav",
                status="ikke_relevant",
                resultat={"ai_act_relevant": False},
                anbefalinger=["AI Act ikke relevant - systemet er ikke et AI-system"],
                næste_trin=["Trin 5: Medarbejderuddannelse"]
            )

        # AI Act risikovurdering baseret på eksisterende ai_act_checker logik
        risk_level = "minimal"
        risk_reasons = []
        requirements = []

        # Check for forbudte praksisser
        prohibited_keywords = ["social scoring", "subliminal", "manipulation", "udnyttelse"]
        if any(keyword in request.system_beskrivelse.lower() for keyword in prohibited_keywords):
            risk_level = "unacceptable"
            risk_reasons.append("Potentielle forbudte AI-praksisser identificeret")

        # Check for højrisiko sektorer og anvendelser
        high_risk_factors = []
        if request.sektor.lower() in ["sundhed", "finans", "beskæftigelse", "uddannelse", "retsvæsen"]:
            high_risk_factors.append(f"Højrisiko sektor: {request.sektor}")

        if request.beslutningstagning == "automatisk":
            high_risk_factors.append("Automatisk beslutningstagning")

        # Biometrisk identifikation
        if any("biometrisk" in dt.lower() for dt in request.data_typer):
            high_risk_factors.append("Biometrisk identifikationssystem")

        # Kritisk infrastruktur
        if "kritisk" in request.system_beskrivelse.lower() or "infrastruktur" in request.system_beskrivelse.lower():
            high_risk_factors.append("Kritisk infrastruktur anvendelse")

        # Bestemmelse af risikoniveau
        if high_risk_factors and risk_level != "unacceptable":
            if len(high_risk_factors) >= 2 or request.beslutningstagning == "automatisk":
                risk_level = "high"
                risk_reasons.extend(high_risk_factors)
            else:
                risk_level = "limited"
                risk_reasons.extend(high_risk_factors)

        # Generér AI Act krav baseret på risikoniveau
        if risk_level == "unacceptable":
            requirements = [
                "STOP: Systemet kan ikke deployes i EU",
                "Redesign systemet for at undgå forbudte praksisser",
                "Søg juridisk rådgivning"
            ]
        elif risk_level == "high":
            requirements = [
                "Implementer risikostyringssystem (Artikel 9)",
                "Sikre datastyring og -kvalitet (Artikel 10)",
                "Oprethold teknisk dokumentation (Artikel 11)",
                "Implementer automatisk logning (Artikel 12)",
                "Sikre gennemsigtighed for brugere (Artikel 13)",
                "Etabler menneskelig overvågning (Artikel 14)",
                "Sikre nøjagtighed og robusthed (Artikel 15)",
                "Gennemfør overensstemmelsesvurdering",
                "Registrer system i EU-database (når operationel)"
            ]
        elif risk_level == "limited":
            requirements = [
                "Informer brugere om AI-interaktion (Artikel 52)",
                "Implementer gennemsigtighedsforanstaltninger"
            ]
            # Generativ AI krav
            if "generativ" in request.system_beskrivelse.lower():
                requirements.append("Mærk AI-genereret indhold (Artikel 52(3))")
        else:
            requirements = [
                "Overvej frivillig implementering af bedste praksis",
                "Dokumenter AI-systemets formål og begrænsninger"
            ]

        resultat = {
            "ai_act_risikoniveau": risk_level,
            "risiko_faktorer": risk_reasons,
            "påkrævede_krav": requirements,
            "conformity_assessment_required": risk_level == "high",
            "registration_required": risk_level == "high"
        }

        if risk_level == "unacceptable":
            anbefalinger = [
                "KRITISK: Systemet overtrader AI Act og kan ikke bruges",
                "Ophør med udvikling/deployment straks",
                "Konsulter juridiske eksperter for redesign"
            ]
        elif risk_level == "high":
            anbefalinger = [
                "Højrisiko AI-system kræver fuld AI Act compliance",
                "Start med risikostyringssystem implementering",
                "Forbered konformitetsvurdering",
                "Planlæg regulatorisk godkendelse"
            ]
        else:
            anbefalinger = [
                f"AI-system klassificeret som {risk_level} risiko",
                "Implementer påkrævede gennemsigtighedsforanstaltninger",
                "Følg best practices for ansvarlig AI"
            ]

        return AssessmentStep(
            step_nummer=4,
            step_navn="AI-forordning (EU AI Act)",
            step_beskrivelse="Vurdering af AI Act compliance krav og risikoniveau",
            status="afsluttet",
            resultat=resultat,
            anbefalinger=anbefalinger,
            næste_trin=["Trin 5: Medarbejderuddannelse"]
        )

    def _assess_step_5_employee_training(self, request: SevenStepAssessmentRequest) -> AssessmentStep:
        """Trin 5: Uddannelse af medarbejderne i AI-færdigheder"""
        # Vurder organisations behov for AI-kompetencer
        training_needs = []
        specific_areas = []

        # Baseret på sektor
        if request.sektor.lower() in ["sundhed", "finans", "uddannelse"]:
            training_needs.append("Sektorspecifik AI etik og compliance")
            specific_areas.append(f"AI regulering i {request.sektor} sektoren")

        # Baseret på AI-type og kompleksitet
        if "machine learning" in request.system_beskrivelse.lower():
            training_needs.extend([
                "Machine Learning grundprincipper",
                "Data kvalitet og bias håndtering",
                "Model validering og testing"
            ])

        if request.beslutningstagning in ["støttende", "automatisk"]:
            training_needs.extend([
                "AI beslutningssystemer og ansvar",
                "Menneske-AI samarbejde",
                "Transparent AI forklaring"
            ])

        # Generelle AI-kompetencer
        core_training = [
            "AI etik og ansvarlig AI udvikling",
            "Databeskyttelse og AI (GDPR compliance)",
            "AI Act grundprincipper og krav",
            "Risk management for AI-systemer",
            "AI sikkerhed og robusthed"
        ]

        # Målgruppe-specifik træning
        role_specific = {
            "ledelse": [
                "AI governance og strategi",
                "Forretningsmæssige AI-risici",
                "AI compliance ledelse"
            ],
            "udviklere": [
                "Privacy by design implementation",
                "AI testing og validering",
                "Sikkerhedsforanstaltninger i AI"
            ],
            "brugere": [
                "AI systemforståelse",
                "Datasubjekt rettigheder",
                "AI interaktion og begrænsninger"
            ]
        }

        resultat = {
            "vurderede_træningsbehov": training_needs,
            "kernekompetencer": core_training,
            "rollespecifik_træning": role_specific,
            "sektorspecifikke_områder": specific_areas,
            "prioritering": "Høj - nødvendig for compliance"
        }

        anbefalinger = [
            "Implementer omfattende AI-træningsprogram",
            "Start med AI etik og compliance grundkurser",
            "Tilpas træning til specifikke roller og ansvar",
            "Etabler løbende kompetenceudvikling",
            "Dokumenter træningsdeltagelse for compliance"
        ]

        return AssessmentStep(
            step_nummer=5,
            step_navn="Medarbejderuddannelse i AI",
            step_beskrivelse="Vurdering af nødvendige AI-kompetencer og træningsbehov",
            status="afsluttet",
            resultat=resultat,
            anbefalinger=anbefalinger,
            næste_trin=["Trin 6: Ressourcer og hjælp"]
        )

    def _assess_step_6_resources(self, request: SevenStepAssessmentRequest) -> AssessmentStep:
        """Trin 6: Få mere hjælp (ressourcer)"""
        # Samle relevante ressourcer baseret på vurdering
        regulatory_resources = [
            {
                "navn": "EU AI Act - Fuld tekst",
                "url": "https://eur-lex.europa.eu/legal-content/DA/TXT/?uri=CELEX:32024R1689",
                "type": "lovgivning",
                "beskrivelse": "Den officielle AI-forordning på dansk"
            },
            {
                "navn": "Databeskyttelsesforordningen (GDPR)",
                "url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
                "type": "lovgivning",
                "beskrivelse": "GDPR forordningen"
            },
            {
                "navn": "Datatilsynets vejledning om AI",
                "url": "https://www.datatilsynet.dk/hvad-siger-reglerne/vejledning/ai-og-gdpr/",
                "type": "vejledning",
                "beskrivelse": "Dansk vejledning om AI og databeskyttelse"
            }
        ]

        practical_tools = [
            {
                "navn": "AI Act Compliance Checker",
                "type": "værktøj",
                "beskrivelse": "Automatiseret compliance vurdering"
            },
            {
                "navn": "DPIA Skabelon for AI",
                "type": "skabelon",
                "beskrivelse": "Struktureret DPIA tilgang for AI-systemer"
            },
            {
                "navn": "Risk Assessment Framework",
                "type": "framework",
                "beskrivelse": "Systematisk risikovurdering for AI"
            }
        ]

        # Sektorspecifikke ressourcer
        sector_resources = []
        if request.sektor.lower() == "sundhed":
            sector_resources.extend([
                {
                    "navn": "EU Health AI Guidelines",
                    "type": "vejledning",
                    "beskrivelse": "Specifikke retningslinjer for AI i sundhedssektoren"
                },
                {
                    "navn": "Medicinudstyr forordningen (MDR) og AI",
                    "type": "lovgivning",
                    "beskrivelse": "AI som medicinudstyr"
                }
            ])
        elif request.sektor.lower() == "finans":
            sector_resources.append({
                "navn": "EBA Guidelines on AI/ML",
                "type": "vejledning",
                "beskrivelse": "Europæiske banktilsyns AI retningslinjer"
            })

        support_contacts = [
            {
                "organisation": "Datatilsynet",
                "kontakt": "https://www.datatilsynet.dk/kontakt/",
                "områder": ["GDPR spørgsmål", "Databeskyttelse", "DPIA vejledning"]
            },
            {
                "organisation": "Erhvervsstyrelsen",
                "kontakt": "https://erhvervsstyrelsen.dk/",
                "områder": ["EU regulering", "Erhvervsret"]
            },
            {
                "organisation": "AI Watch (EU)",
                "kontakt": "https://ai-watch.ec.europa.eu/",
                "områder": ["AI Act implementering", "Best practices"]
            }
        ]

        resultat = {
            "regulatoriske_ressourcer": regulatory_resources,
            "praktiske_værktøjer": practical_tools,
            "sektorspecifikke_ressourcer": sector_resources,
            "support_kontakter": support_contacts,
            "anbefalet_rækkefølge": [
                "Start med AI Act tekst review",
                "Gennemgå Datatilsynets vejledninger",
                "Implementer praktiske værktøjer",
                "Søg sektorspecifik guidance"
            ]
        }

        anbefalinger = [
            "Læs AI Act grundigt - særligt relevante artikler",
            "Følg Datatilsynets opdateringer og vejledninger",
            "Etabler kontakt til relevante myndigheder tidligt",
            "Brug EU AI Watch for opdateringer",
            "Overvej juridisk rådgivning til komplekse spørgsmål"
        ]

        return AssessmentStep(
            step_nummer=6,
            step_navn="Ressourcer og hjælp",
            step_beskrivelse="Samling af relevante ressourcer, værktøjer og kontakter",
            status="afsluttet",
            resultat=resultat,
            anbefalinger=anbefalinger,
            næste_trin=["Trin 7: Systemkrav"]
        )

    def _assess_step_7_system_requirements(self, request: SevenStepAssessmentRequest,
                                         trin_1: AssessmentStep, trin_4: AssessmentStep) -> AssessmentStep:
        """Trin 7: Vejledende krav til AI-systemet"""
        system_requirements = []
        implementation_priorities = []

        # Baseret på AI-systemets klassifikation
        if trin_1.resultat and trin_1.resultat.get("er_ai_system"):
            ai_act_risk = trin_4.resultat.get("ai_act_risikoniveau", "minimal") if trin_4.resultat else "minimal"

            # Grundlæggende krav for alle AI-systemer
            basic_requirements = [
                {
                    "kategori": "Dokumentation",
                    "krav": "Dokumenter AI-systemets formål, kapaciteter og begrænsninger",
                    "prioritet": "høj",
                    "compliance_framework": "AI Act"
                },
                {
                    "kategori": "Gennemsigtighed",
                    "krav": "Gør brugere opmærksomme på AI-interaktion",
                    "prioritet": "høj",
                    "compliance_framework": "AI Act"
                }
            ]

            # Højrisiko AI-system krav
            if ai_act_risk == "high":
                high_risk_requirements = [
                    {
                        "kategori": "Risikostyring",
                        "krav": "Etabler og vedligehold risikostyringssystem",
                        "prioritet": "kritisk",
                        "compliance_framework": "AI Act Art. 9"
                    },
                    {
                        "kategori": "Datakvalitet",
                        "krav": "Sikre trænings-, validerings- og testdata kvalitet",
                        "prioritet": "kritisk",
                        "compliance_framework": "AI Act Art. 10"
                    },
                    {
                        "kategori": "Teknisk dokumentation",
                        "krav": "Oprethold omfattende teknisk dokumentation",
                        "prioritet": "kritisk",
                        "compliance_framework": "AI Act Art. 11"
                    },
                    {
                        "kategori": "Logning",
                        "krav": "Implementer automatisk hændelseslogning",
                        "prioritet": "høj",
                        "compliance_framework": "AI Act Art. 12"
                    },
                    {
                        "kategori": "Menneskelig overvågning",
                        "krav": "Sikre passende menneskelig kontrol",
                        "prioritet": "kritisk",
                        "compliance_framework": "AI Act Art. 14"
                    }
                ]
                system_requirements.extend(high_risk_requirements)

            system_requirements.extend(basic_requirements)

        # GDPR krav hvis personoplysninger behandles
        if request.personoplysninger:
            gdpr_requirements = [
                {
                    "kategori": "Lovligt grundlag",
                    "krav": "Etabler og dokumenter lovligt grundlag for behandling",
                    "prioritet": "kritisk",
                    "compliance_framework": "GDPR Art. 6"
                },
                {
                    "kategori": "Databeskyttelse by design",
                    "krav": "Implementer privacy by design principper",
                    "prioritet": "høj",
                    "compliance_framework": "GDPR Art. 25"
                },
                {
                    "kategori": "Datasubjekt rettigheder",
                    "krav": "Implementer mekanismer for datasubjekt rettigheder",
                    "prioritet": "høj",
                    "compliance_framework": "GDPR Art. 15-22"
                },
                {
                    "kategori": "Sikkerhed",
                    "krav": "Implementer passende tekniske og organisatoriske sikkerhedsforanstaltninger",
                    "prioritet": "høj",
                    "compliance_framework": "GDPR Art. 32"
                }
            ]
            system_requirements.extend(gdpr_requirements)

        # Sektorspecifikke krav
        if request.sektor.lower() == "sundhed":
            health_requirements = [
                {
                    "kategori": "Medicinudstyr",
                    "krav": "Vurder om systemet klassificeres som medicinudstyr",
                    "prioritet": "høj",
                    "compliance_framework": "MDR"
                },
                {
                    "kategori": "Klinisk validering",
                    "krav": "Gennemfør klinisk validering hvis relevant",
                    "prioritet": "høj",
                    "compliance_framework": "MDR/AI Act"
                }
            ]
            system_requirements.extend(health_requirements)

        # Prioriter krav
        critical_requirements = [req for req in system_requirements if req["prioritet"] == "kritisk"]
        high_requirements = [req for req in system_requirements if req["prioritet"] == "høj"]

        implementation_priorities = [
            {
                "fase": "Umiddelbar prioritet (0-3 måneder)",
                "krav": critical_requirements
            },
            {
                "fase": "Høj prioritet (3-6 måneder)",
                "krav": high_requirements
            },
            {
                "fase": "Medium prioritet (6-12 måneder)",
                "krav": [req for req in system_requirements if req["prioritet"] not in ["kritisk", "høj"]]
            }
        ]

        resultat = {
            "samlede_systemkrav": system_requirements,
            "implementerings_prioritering": implementation_priorities,
            "compliance_frameworks": list(set([req["compliance_framework"] for req in system_requirements])),
            "kritiske_krav_antal": len(critical_requirements),
            "estimeret_implementeringstid": f"{len(system_requirements) * 2-4} uger"
        }

        anbefalinger = [
            "Start med kritiske krav straks",
            "Udvikl implementeringsplan baseret på prioritering",
            "Allokér tilstrækkelige ressourcer til compliance",
            "Etabler løbende compliance monitoring",
            "Planlæg regelmæssige compliance reviews"
        ]

        return AssessmentStep(
            step_nummer=7,
            step_navn="Vejledende systemkrav",
            step_beskrivelse="Specificerede krav til AI-systemet baseret på compliance analyse",
            status="afsluttet",
            resultat=resultat,
            anbefalinger=anbefalinger,
            næste_trin=["Implementering og løbende overvågning"]
        )

    # Hjælpemetoder
    def _determine_ai_type(self, request: SevenStepAssessmentRequest) -> str:
        """Bestem AI-type baseret på systembeskrivelse"""
        beskrivelse = request.system_beskrivelse.lower()
        if any(kw in beskrivelse for kw in ["generativ", "generative", "gpt", "llm"]):
            return "generativ_ai"
        elif any(kw in beskrivelse for kw in ["prædiktiv", "prediction", "forecasting"]):
            return "prædiktiv_ai"
        elif any(kw in beskrivelse for kw in ["klassificering", "classification"]):
            return "klassifikation"
        elif any(kw in beskrivelse for kw in ["recommendation", "anbefalings"]):
            return "anbefaling"
        elif any(kw in beskrivelse for kw in ["computer vision", "billedgenkendelse", "image"]):
            return "computer_vision"
        elif any(kw in beskrivelse for kw in ["natural language", "nlp", "tekstanalyse"]):
            return "nlp"
        else:
            return "andet"

    def _calculate_overall_assessment(self, *steps) -> tuple[str, float]:
        """Beregn samlet risikoniveau og compliance score"""
        risk_scores = {"minimal": 1, "limited": 2, "medium": 3, "high": 4, "unacceptable": 5}
        max_risk = 1
        total_score = 0
        score_count = 0

        for step in steps:
            if step.resultat:
                # AI Act risiko
                if "ai_act_risikoniveau" in step.resultat:
                    ai_risk = step.resultat["ai_act_risikoniveau"]
                    max_risk = max(max_risk, risk_scores.get(ai_risk, 1))

                # GDPR score
                if "gdpr_score" in step.resultat:
                    total_score += step.resultat["gdpr_score"]
                    score_count += 1

                # Persondata risiko
                if "risikoniveau" in step.resultat:
                    data_risk = step.resultat["risikoniveau"]
                    if data_risk == "høj":
                        max_risk = max(max_risk, 4)
                    elif data_risk == "medium":
                        max_risk = max(max_risk, 3)

        # Beregn samlet compliance score
        if score_count > 0:
            avg_score = total_score / score_count
        else:
            avg_score = 70  # Default score

        # Justér score baseret på risiko
        if max_risk >= 5:
            avg_score = min(avg_score, 30)
        elif max_risk >= 4:
            avg_score = min(avg_score, 60)

        # Konverter risikoniveau
        risk_mapping = {1: "lav", 2: "lav", 3: "medium", 4: "høj", 5: "kritisk"}
        overall_risk = risk_mapping[max_risk]

        return overall_risk, avg_score

    def _requires_dpia(self, request: SevenStepAssessmentRequest, trin_2: AssessmentStep) -> bool:
        """Bestem om DPIA er påkrævet"""
        if not trin_2.resultat or not trin_2.resultat.get("behandler_personoplysninger"):
            return False

        # DPIA triggers
        if request.beslutningstagning == "automatisk":
            return True

        if request.særlige_kategorier:
            return True

        if any("biometrisk" in dt.lower() for dt in request.data_typer):
            return True

        if "storstilet" in request.system_beskrivelse.lower() or "large scale" in request.system_beskrivelse.lower():
            return True

        # Højrisiko sektorer med persondata
        if request.sektor.lower() in ["sundhed", "finans"] and request.personoplysninger:
            return True

        return False

    def _requires_fria(self, request: SevenStepAssessmentRequest, trin_1: AssessmentStep, trin_4: AssessmentStep) -> bool:
        """Bestem om Fundamental Rights Impact Assessment (FRIA) er påkrævet"""
        if not trin_1.resultat or not trin_1.resultat.get("er_ai_system"):
            return False

        if not trin_4.resultat:
            return False

        ai_risk = trin_4.resultat.get("ai_act_risikoniveau", "minimal")
        return ai_risk == "high"

    def _generate_priority_actions(self, *steps, kræver_dpia: bool, kræver_fria: bool) -> List[Dict[str, Any]]:
        """Generer prioriterede handlinger baseret på vurdering"""
        actions = []

        # Kritiske handlinger først
        for step in steps:
            if step.resultat:
                if step.resultat.get("ai_act_risikoniveau") == "unacceptable":
                    actions.append({
                        "prioritet": "kritisk",
                        "handling": "Stop alle AI-aktiviteter - systemet overtræder AI Act",
                        "tidsfrist": "Straks",
                        "ansvarlig": "Ledelse + Juridisk",
                        "framework": "AI Act"
                    })

                if step.resultat.get("ai_act_risikoniveau") == "high":
                    actions.append({
                        "prioritet": "høj",
                        "handling": "Implementer højrisiko AI compliance program",
                        "tidsfrist": "3-6 måneder",
                        "ansvarlig": "Compliance team",
                        "framework": "AI Act"
                    })

                if step.resultat.get("gdpr_score", 100) < 50:
                    actions.append({
                        "prioritet": "høj",
                        "handling": "Ret kritiske GDPR compliance problemer",
                        "tidsfrist": "1-3 måneder",
                        "ansvarlig": "DPO + IT",
                        "framework": "GDPR"
                    })

        # Specialvurderinger
        if kræver_dpia:
            actions.append({
                "prioritet": "høj",
                "handling": "Gennemfør Data Protection Impact Assessment (DPIA)",
                "tidsfrist": "1-2 måneder",
                "ansvarlig": "DPO",
                "framework": "GDPR"
            })

        if kræver_fria:
            actions.append({
                "prioritet": "høj",
                "handling": "Gennemfør Fundamental Rights Impact Assessment (FRIA)",
                "tidsfrist": "2-3 måneder",
                "ansvarlig": "Compliance + Juridisk",
                "framework": "AI Act"
            })

        # Grundlæggende handlinger
        actions.extend([
            {
                "prioritet": "medium",
                "handling": "Etabler AI governance struktur",
                "tidsfrist": "3-6 måneder",
                "ansvarlig": "Ledelse",
                "framework": "Best practice"
            },
            {
                "prioritet": "medium",
                "handling": "Implementer medarbejder AI-træning",
                "tidsfrist": "6-12 måneder",
                "ansvarlig": "HR + Compliance",
                "framework": "AI Act"
            }
        ])

        # Sorter efter prioritet
        priority_order = {"kritisk": 1, "høj": 2, "medium": 3, "lav": 4}
        actions.sort(key=lambda x: priority_order.get(x["prioritet"], 4))

        return actions[:8]  # Top 8 handlinger

    def _gather_relevant_resources(self, request: SevenStepAssessmentRequest, trin_1: AssessmentStep, trin_4: AssessmentStep) -> List[Dict[str, Any]]:
        """Samle relevante ressourcer baseret på vurdering"""
        resources = []

        # Grundlæggende AI Act ressourcer
        if trin_1.resultat and trin_1.resultat.get("er_ai_system"):
            resources.append({
                "titel": "EU AI Act - Komplet tekst",
                "url": "https://eur-lex.europa.eu/legal-content/DA/TXT/?uri=CELEX:32024R1689",
                "type": "lovgivning",
                "relevans": "høj"
            })

        # Højrisiko specifikke ressourcer
        if trin_4.resultat and trin_4.resultat.get("ai_act_risikoniveau") == "high":
            resources.extend([
                {
                    "titel": "AI Act Implementation Guide - High Risk Systems",
                    "url": "https://ai-watch.ec.europa.eu/ai-act-compliance",
                    "type": "guide",
                    "relevans": "kritisk"
                },
                {
                    "titel": "Conformity Assessment Procedures",
                    "url": "https://ec.europa.eu/ai-act-conformity",
                    "type": "procedure",
                    "relevans": "høj"
                }
            ])

        # GDPR ressourcer ved persondata
        if request.personoplysninger:
            resources.extend([
                {
                    "titel": "GDPR Artikel 22 - Automatiseret beslutningstagning",
                    "url": "https://www.datatilsynet.dk/emner/internet-og-apps/algoritmer/automatiserede-beslutninger",
                    "type": "vejledning",
                    "relevans": "høj"
                },
                {
                    "titel": "DPIA Skabelon",
                    "url": "https://www.datatilsynet.dk/emner/databeskyttelse/dpia",
                    "type": "skabelon",
                    "relevans": "høj"
                }
            ])

        # Sektorspecifikke ressourcer
        if request.sektor.lower() == "sundhed":
            resources.append({
                "titel": "AI i Sundhedssektoren - Danske retningslinjer",
                "url": "https://sundhedsstyrelsen.dk/da/nyheder/2024/ai-retningslinjer",
                "type": "guideline",
                "relevans": "høj"
            })

        return resources[:6]  # Top 6 ressourcer

    def _generate_next_steps(self, risk_level: str, kræver_dpia: bool, kræver_fria: bool, actions: List[Dict[str, Any]]) -> List[str]:
        """Generer konkrete næste skridt"""
        steps = []

        if risk_level == "kritisk":
            steps = [
                "STOP al udvikling og deployment af AI-systemet",
                "Indkald til krisemøde med ledelse og juridisk afdeling",
                "Vurder redesign muligheder med juridiske eksperter",
                "Dokumentér alle beslutninger og handlinger"
            ]
        elif risk_level == "høj":
            steps = [
                "Etabler AI compliance projekt med dedikerede ressourcer",
                "Start risikostyringssystem implementering",
                "Planlæg konformitetsvurdering med certificeringsorganer",
                "Forbered dokumentation til regulatorisk godkendelse"
            ]
        else:
            steps = [
                "Gennemgå alle vurderingsresultater med relevante teams",
                "Prioritér handlinger baseret på compliance gaps",
                "Allokér ressourcer til de vigtigste compliance aktiviteter",
                "Etabler regelmæssig compliance monitoring"
            ]

        # Tilføj specialvurderinger
        if kræver_dpia:
            steps.insert(-1, "Start DPIA proces med DPO og relevante stakeholders")

        if kræver_fria:
            steps.insert(-1, "Forbered Fundamental Rights Impact Assessment")

        # Tilføj generelle skridt
        steps.extend([
            "Planlæg medarbejder AI-træning baseret på anbefalinger",
            "Etabler kontakt til relevante myndigheder og eksperter",
            "Opsæt løbende overvågning af regulatoriske ændringer"
        ])

        return steps[:8]  # Max 8 skridt

# Initialize assessment engine
assessment_engine = SevenStepAssessmentEngine()

# Initialize compliance control engine
from src.compliance_engine import ComplianceController
compliance_controller = ComplianceController()

# Mock compliance checker
def mock_ai_act_assessment(project_data):
    """Mock AI Act risk assessment"""
    description = project_data.beskrivelse.lower()

    # Check for prohibited practices
    prohibited_keywords = ["social scoring", "subliminal", "manipulation"]
    if any(keyword in description for keyword in prohibited_keywords):
        return "unacceptable", ["Potentiel forbudt AI-praksis identificeret"]

    # Check for high risk
    high_risk_sectors = ["sundhed", "finans", "beskæftigelse", "uddannelse"]
    if (project_data.sektor.lower() in high_risk_sectors and
        project_data.automatiserede_beslutninger):
        return "high", ["Højrisiko sektor med automatiserede beslutninger"]

    if "biometric" in description or "ansigtsgenkendelses" in description:
        return "high", ["Biometrisk identifikationssystem"]

    # Check for limited risk
    if "chatbot" in description or "generativ" in project_data.ai_type.lower():
        return "limited", ["AI system der interagerer med brugere"]

    return "minimal", ["Ingen højrisiko indikatorer identificeret"]

def mock_gdpr_assessment(project_data):
    """Mock GDPR assessment"""
    if not project_data.behandler_persondata:
        return {
            "relevant": False,
            "score": 90,
            "issues": ["Ingen personoplysninger behandles"],
            "dpia_required": False
        }

    score = 70
    issues = []

    if project_data.automatiserede_beslutninger:
        score -= 20
        issues.append("Automatiserede beslutninger kræver særlige sikkerhedsforanstaltninger")

    if "sundhed" in project_data.sektor.lower():
        score -= 10
        issues.append("Sundhedsdata kræver udtrykkelig samtykke")

    dpia_required = score < 60 or project_data.automatiserede_beslutninger

    return {
        "relevant": True,
        "score": score,
        "issues": issues,
        "dpia_required": dpia_required
    }

def mock_research_results(emne, fokusområder):
    """Mock research results with citations"""
    sources = [
        {
            "title": "Forordning (EU) 2024/1689 om kunstig intelligens (AI-loven)",
            "url": "https://eur-lex.europa.eu/legal-content/DA/TXT/?uri=CELEX:32024R1689",
            "domain": "eur-lex.europa.eu",
            "authority": "EU-Kommissionen",
            "source_type": "regulation",
            "date_accessed": datetime.now().isoformat(),
            "date_published": "2024-07-12",
            "relevance_score": 0.95
        },
        {
            "title": "Databeskyttelsesforordningen (GDPR)",
            "url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
            "domain": "eur-lex.europa.eu",
            "authority": "EU",
            "source_type": "regulation",
            "date_accessed": datetime.now().isoformat(),
            "date_published": "2016-05-04",
            "relevance_score": 0.90
        },
        {
            "title": "Datatilsynets vejledning om AI og databeskyttelse",
            "url": "https://www.datatilsynet.dk/hvad-siger-reglerne/vejledning/ai-og-gdpr/",
            "domain": "datatilsynet.dk",
            "authority": "Datatilsynet",
            "source_type": "guideline",
            "date_accessed": datetime.now().isoformat(),
            "relevance_score": 0.85
        }
    ]

    citations = [
        {
            "text": "AI-systemer, der er forbudt omfatter anvendelse af subliminale teknikker ud over en persons bevidsthed med det formål at påvirke personens adfærd væsentligt på en måde, der kan forårsage eller sandsynligvis vil forårsage denne person eller en anden person fysisk eller psykisk skade.",
            "source": sources[0],
            "confidence": 0.95
        },
        {
            "text": "Den registrerede har ret til ikke at være underlagt en afgørelse, der udelukkende er baseret på automatiseret behandling, herunder profilering, som har retsvirkning for den pågældende eller på lignende vis påvirker den pågældende i væsentlig grad.",
            "source": sources[1],
            "confidence": 0.92
        },
        {
            "text": "Når AI-systemer træffer automatiserede beslutninger om personer, skal der være passende sikkerhedsforanstaltninger, herunder ret til at opnå menneskelig indgriben.",
            "source": sources[2],
            "confidence": 0.88
        }
    ]

    return {
        "query": emne,
        "focus_areas": fokusområder,
        "sources": sources,
        "citations": citations,
        "summary": f"Research om '{emne}' har identificeret {len(sources)} relevante kilder fra autoritative databaser.",
        "key_findings": [
            "AI Act klassificerer AI-systemer efter risikoniveau",
            "GDPR artikel 22 regulerer automatiserede beslutninger",
            "Datatilsynet giver specifik guidance for danske implementeringer"
        ],
        "recommendations": [
            "Sikr compliance med AI Act risikovurdering",
            "Implementer GDPR artikel 22 safeguards",
            "Følg Datatilsynets specifikke vejledninger"
        ],
        "last_updated": datetime.now().isoformat()
    }

# Routes
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "message": "Project Judge Dredd - AI Compliance Control API",
        "beskrivelse": "Professional AI Compliance Control Platform",
        "dokumentation": "/docs",
        "sundhedstjek": "/health"
    }

async def start_news_updater():
    """Background task to update news every 15 minutes"""
    while True:
        try:
            if news_scraper:
                async with news_scraper:
                    await news_scraper.fetch_latest_news()
                logger.info("News updated successfully")
            await asyncio.sleep(900)  # 15 minutes
        except Exception as e:
            logger.error(f"News update failed: {e}")
            await asyncio.sleep(300)  # Try again in 5 minutes

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now(),
        services={
            "api": "operational",
            "ai_act_checker": "operational",
            "gdpr_checker": "operational",
            "web_research": "operational"
        }
    )

@app.post("/api/research/juridisk", response_model=Dict[str, Any])
async def juridisk_research(request: ResearchRequest):
    """
    Udfører juridisk research med kildecitation
    """
    try:
        logger.info(f"Starter juridisk research: {request.emne}")

        resultat = mock_research_results(
            request.emne,
            request.fokusområder or ["EU AI Act", "GDPR", "dansk lovgivning"]
        )

        return {
            "success": True,
            "emne": request.emne,
            "resultat": resultat,
            "message": f"Research afsluttet - {len(resultat['sources'])} kilder fundet"
        }

    except Exception as e:
        logger.error(f"Juridisk research fejlede: {e}")
        raise HTTPException(status_code=500, detail=f"Research fejl: {str(e)}")

@app.post("/api/compliance/hurtig-tjek", response_model=Dict[str, Any])
async def hurtig_compliance_tjek(request: QuickCheckRequest):
    """
    Hurtig compliance check uden fuld analyse
    """
    try:
        logger.info(f"Starter hurtig tjek for: {request.beskrivelse[:50]}...")

        # AI Act assessment
        ai_act_risk, ai_act_reasons = mock_ai_act_assessment(request)

        # GDPR assessment
        gdpr_result = mock_gdpr_assessment(request)

        # Generate recommendations
        recommendations = []
        if ai_act_risk == "unacceptable":
            recommendations.append("KRITISK: System kan ikke deployes - involverer forbudte praksisser")
        elif ai_act_risk == "high":
            recommendations.append("HØJ: Implementer alle højrisiko AI system krav")

        if gdpr_result["dpia_required"]:
            recommendations.append("Gennemfør konsekvensanalyse for databeskyttelse (DPIA)")

        if gdpr_result["relevant"]:
            recommendations.append("Etabler retsgrundlag for behandling af personoplysninger")

        recommendations.append("Dokumenter AI systemets kapaciteter og begrænsninger")

        return {
            "ai_act": {
                "risk_level": ai_act_risk,
                "reasons": ai_act_reasons
            },
            "gdpr": gdpr_result,
            "quick_recommendations": recommendations,
            "needs_full_assessment": ai_act_risk in ["high", "unacceptable"] or gdpr_result["dpia_required"]
        }

    except Exception as e:
        logger.error(f"Hurtig tjek fejlede: {e}")
        raise HTTPException(status_code=500, detail=f"Tjek fejl: {str(e)}")

@app.post("/api/compliance/7-punkts-vurdering", response_model=Dict[str, Any])
async def syv_punkts_ai_vurdering(request: SevenStepAssessmentRequest):
    """
    Struktureret 7-punkts AI-vurdering proces

    Denne endpoint udfører en komplet struktureret vurdering af AI-systemer
    gennem 7 definerede trin som vejleder organisationen gennem hele
    compliance processen.
    """
    try:
        logger.info(f"Starter 7-punkts vurdering for: {request.system_navn}")

        # Udfør komplet 7-punkts vurdering
        resultat = assessment_engine.perform_full_assessment(request)

        # Udfør compliance control med regelmotor
        compliance_result = compliance_controller.process_compliance_control(request.dict())

        return {
            "success": True,
            "vurdering_type": "7-punkts struktureret AI-vurdering",
            "system_navn": request.system_navn,
            "vurdering_id": resultat.vurdering_id,
            "oprettet": resultat.oprettet.isoformat(),

            # Samlet vurdering
            "samlet_vurdering": {
                "risikoniveau": resultat.samlet_risikoniveau,
                "compliance_score": resultat.compliance_score,
                "kræver_dpia": resultat.kræver_dpia,
                "kræver_fria": resultat.kræver_fria,
                "kræver_lovlig_grund": resultat.kræver_lovlig_grund
            },

            # De 7 trin i detaljer
            "detaljeret_vurdering": {
                "trin_1_ai_system": {
                    "navn": resultat.trin_1_ai_system.step_navn,
                    "status": resultat.trin_1_ai_system.status,
                    "resultat": resultat.trin_1_ai_system.resultat,
                    "anbefalinger": resultat.trin_1_ai_system.anbefalinger,
                    "næste_trin": resultat.trin_1_ai_system.næste_trin
                },
                "trin_2_persondata": {
                    "navn": resultat.trin_2_persondata.step_navn,
                    "status": resultat.trin_2_persondata.status,
                    "resultat": resultat.trin_2_persondata.resultat,
                    "anbefalinger": resultat.trin_2_persondata.anbefalinger,
                    "næste_trin": resultat.trin_2_persondata.næste_trin
                },
                "trin_3_databeskyttelse": {
                    "navn": resultat.trin_3_databeskyttelse.step_navn,
                    "status": resultat.trin_3_databeskyttelse.status,
                    "resultat": resultat.trin_3_databeskyttelse.resultat,
                    "anbefalinger": resultat.trin_3_databeskyttelse.anbefalinger,
                    "næste_trin": resultat.trin_3_databeskyttelse.næste_trin
                },
                "trin_4_ai_forordning": {
                    "navn": resultat.trin_4_ai_forordning.step_navn,
                    "status": resultat.trin_4_ai_forordning.status,
                    "resultat": resultat.trin_4_ai_forordning.resultat,
                    "anbefalinger": resultat.trin_4_ai_forordning.anbefalinger,
                    "næste_trin": resultat.trin_4_ai_forordning.næste_trin
                },
                "trin_5_medarbejder_uddannelse": {
                    "navn": resultat.trin_5_medarbejder_uddannelse.step_navn,
                    "status": resultat.trin_5_medarbejder_uddannelse.status,
                    "resultat": resultat.trin_5_medarbejder_uddannelse.resultat,
                    "anbefalinger": resultat.trin_5_medarbejder_uddannelse.anbefalinger,
                    "næste_trin": resultat.trin_5_medarbejder_uddannelse.næste_trin
                },
                "trin_6_ressourcer": {
                    "navn": resultat.trin_6_ressourcer.step_navn,
                    "status": resultat.trin_6_ressourcer.status,
                    "resultat": resultat.trin_6_ressourcer.resultat,
                    "anbefalinger": resultat.trin_6_ressourcer.anbefalinger,
                    "næste_trin": resultat.trin_6_ressourcer.næste_trin
                },
                "trin_7_systemkrav": {
                    "navn": resultat.trin_7_systemkrav.step_navn,
                    "status": resultat.trin_7_systemkrav.status,
                    "resultat": resultat.trin_7_systemkrav.resultat,
                    "anbefalinger": resultat.trin_7_systemkrav.anbefalinger,
                    "næste_trin": resultat.trin_7_systemkrav.næste_trin
                }
            },

            # Handlingsplan
            "handlingsplan": {
                "prioriterede_handlinger": resultat.prioriterede_handlinger,
                "næste_skridt": resultat.næste_skridt,
                "relevante_ressourcer": resultat.relevante_ressourcer
            },

            # Specialvurderinger
            "specialvurderinger": {
                "dpia_påkrævet": resultat.kræver_dpia,
                "fria_påkrævet": resultat.kræver_fria,
                "lovligt_grundlag_påkrævet": resultat.kræver_lovlig_grund,
                "compliance_status": {
                    "ai_act": resultat.trin_4_ai_forordning.resultat.get("ai_act_risikoniveau") if resultat.trin_4_ai_forordning.resultat else "ikke_vurderet",
                    "gdpr": "relevant" if request.personoplysninger else "ikke_relevant",
                    "samlet_score": resultat.compliance_score
                }
            },

            # Metadata
            "metadata": {
                "vurdering_version": "1.0",
                "system_info": resultat.system_info,
                "vurderingstidspunkt": resultat.oprettet.isoformat(),
                "næste_review": (resultat.oprettet.replace(month=resultat.oprettet.month + 6)).isoformat() if resultat.oprettet.month <= 6 else (resultat.oprettet.replace(year=resultat.oprettet.year + 1, month=resultat.oprettet.month - 6)).isoformat()
            },

            # Compliance Control med regelmotor
            "compliance_control": {
                "beslutning": compliance_result["beslutning"],
                "beslutning_beskrivelse": compliance_result["beslutning_beskrivelse"],
                "risiko_score": compliance_result["risiko_score"],
                "risiko_niveau": compliance_result["risiko_niveau"],

                "hard_stops": compliance_result["hard_stops"],
                "betingelser": compliance_result["betingelser"],

                "nødvendige_artefakter": compliance_result["nødvendige_artefakter"],
                "nødvendige_tests": compliance_result["nødvendige_tests"],

                "anvendte_regler": compliance_result["anvendte_regler"],

                "sammenfatning": compliance_result["sammenfatning"],
                "næste_skridt": compliance_result["næste_skridt"]
            }
        }

    except Exception as e:
        logger.error(f"7-punkts vurdering fejlede: {e}")
        raise HTTPException(status_code=500, detail=f"Vurdering fejl: {str(e)}")

@app.get("/api/compliance/7-punkts-guide", response_model=Dict[str, Any])
async def get_syv_punkts_guide():
    """
    Hent guide til 7-punkts AI-vurdering

    Returnerer en struktureret guide der forklarer hvert trin i
    vurderingsprocessen og hvad der forventes.
    """
    return {
        "title": "Guide til 7-punkts AI-vurdering",
        "beskrivelse": "Struktureret proces til vurdering af AI-systemers compliance med EU AI Act og GDPR",

        "proces_oversigt": {
            "formål": "Sikre systematisk og fuldstændig vurdering af AI-systemer",
            "målgruppe": "Organisationer der udvikler eller implementerer AI-systemer",
            "estimeret_tid": "2-4 timer for grundlæggende vurdering",
            "output": "Detaljeret compliance rapport med handlingsplan"
        },

        "trin_guide": [
            {
                "trin": 1,
                "navn": "AI-system identifikation",
                "formål": "Afgør om systemet kvalificerer som AI-system under EU AI Act",
                "input_påkrævet": [
                    "Detaljeret systembeskrivelse",
                    "Automatiseringsgrad",
                    "Beslutningstagnings-kapaciteter"
                ],
                "output": "Klassifikation som AI-system eller ej",
                "vigtigt": "Hvis systemet ikke er et AI-system, gælder AI Act ikke"
            },
            {
                "trin": 2,
                "navn": "Personoplysningsbehandling",
                "formål": "Identificer om og hvilke personoplysninger systemet behandler",
                "input_påkrævet": [
                    "Datatyper systemet behandler",
                    "Særlige kategorier af personoplysninger",
                    "Datakilder og dataflow"
                ],
                "output": "Vurdering af GDPR-relevans og risikoniveau",
                "vigtigt": "Særlige kategorier udløser skærpede krav"
            },
            {
                "trin": 3,
                "navn": "Databeskyttelsesregler (GDPR)",
                "formål": "Vurdér compliance med GDPR krav",
                "input_påkrævet": [
                    "Lovligt grundlag for behandling",
                    "Sikkerhedsforanstaltninger",
                    "Datasubjekt rettigheder implementering"
                ],
                "output": "GDPR compliance score og specifikke krav",
                "vigtigt": "Automatiserede beslutninger har særlige krav"
            },
            {
                "trin": 4,
                "navn": "AI-forordningen (EU AI Act)",
                "formål": "Klassificér AI-systemets risikoniveau og bestem krav",
                "input_påkrævet": [
                    "Anvendelsesområde og sektor",
                    "AI-systemets kapaciteter",
                    "Potentielle risici for grundlæggende rettigheder"
                ],
                "output": "AI Act risikoklassifikation og specifikke compliance krav",
                "vigtigt": "Højrisiko systemer kræver omfattende compliance"
            },
            {
                "trin": 5,
                "navn": "Medarbejderuddannelse",
                "formål": "Vurdér nødvendige AI-kompetencer i organisationen",
                "input_påkrævet": [
                    "Nuværende kompetenceniveau",
                    "Roller og ansvar",
                    "Træningsbehov"
                ],
                "output": "Struktureret træningsplan for AI-kompetencer",
                "vigtigt": "Kompetent personale er kritisk for compliance"
            },
            {
                "trin": 6,
                "navn": "Ressourcer og hjælp",
                "formål": "Identificer relevante ressourcer og support muligheder",
                "input_påkrævet": [
                    "Specifikke compliance udfordringer",
                    "Sektorspecifikke behov",
                    "Implementeringskapacitet"
                ],
                "output": "Kureret liste af ressourcer og kontakter",
                "vigtigt": "Tidlig kontakt til myndigheder kan spare tid senere"
            },
            {
                "trin": 7,
                "navn": "Vejledende systemkrav",
                "formål": "Specificer konkrete krav til AI-systemet",
                "input_påkrævet": [
                    "Resultater fra alle foregående trin",
                    "Implementeringskapacitet",
                    "Tidslinje for deployment"
                ],
                "output": "Prioriteret liste af systemkrav med implementeringsplan",
                "vigtigt": "Kritiske krav skal implementeres før deployment"
            }
        ],

        "special_vurderinger": {
            "dpia": {
                "navn": "Data Protection Impact Assessment",
                "påkrævet_når": [
                    "Automatiserede beslutninger med retsvirkning",
                    "Storstilet behandling af særlige kategorier",
                    "Systematisk overvågning af offentligt tilgængelige områder"
                ],
                "proces": "Struktureret risikovurdering for databeskyttelse"
            },
            "fria": {
                "navn": "Fundamental Rights Impact Assessment",
                "påkrævet_når": [
                    "Højrisiko AI-systemer under AI Act",
                    "Systemer der påvirker grundlæggende rettigheder"
                ],
                "proces": "Vurdering af påvirkning på grundlæggende rettigheder"
            }
        },

        "best_practices": [
            "Start vurderingen tidligt i udviklingsfasen",
            "Involvér juridiske eksperter ved komplekse systemer",
            "Dokumentér alle beslutninger og vurderinger",
            "Planlæg regelmæssige compliance reviews",
            "Hold dig opdateret om regulatoriske ændringer"
        ],

        "common_mistakes": [
            "Undervurdere betydningen af AI-systemklassifikation",
            "Ignorere GDPR krav ved 'anonyme' datasæt",
            "Udsætte compliance aktiviteter til efter development",
            "Mangle dokumentation af compliance beslutninger",
            "Glemme medarbejderuddannelse i compliance planer"
        ]
    }

@app.get("/api/frameworks", response_model=Dict[str, Any])
async def get_supported_frameworks():
    """
    Get list of supported compliance frameworks
    """
    return {
        "frameworks": [
            {
                "id": "eu_ai_act",
                "name": "EU AI Act",
                "description": "Forordning om kunstig intelligens",
                "version": "2024"
            },
            {
                "id": "gdpr",
                "name": "GDPR",
                "description": "Databeskyttelsesforordningen",
                "version": "2016/679"
            },
            {
                "id": "danish_data_act",
                "name": "Dansk databeskyttelseslov",
                "description": "Dansk implementering af databeskyttelse",
                "version": "Aktuel"
            }
        ],
        "sectors": [
            "Sundhed",
            "Finans",
            "Uddannelse",
            "Beskæftigelse",
            "Offentlig sektor",
            "Teknologi",
            "Detail",
            "Produktion",
            "Andet"
        ],
        "ai_types": [
            "generativ_ai",
            "prædiktiv_ai",
            "klassifikation",
            "anbefaling",
            "computer_vision",
            "nlp",
            "robotik",
            "andet"
        ]
    }

@app.get("/api/news/seneste", response_model=Dict[str, Any])
async def get_seneste_nyheder(kategori: Optional[str] = None, limit: int = 20):
    """
    Hent seneste nyheder om AI og data protection
    """
    try:
        if not news_scraper:
            # Return mock data if scraper not initialized
            mock_news = [
                {
                    "title": "Datatilsynet udgiver nye AI retningslinjer",
                    "url": "https://www.datatilsynet.dk/nyheder/ai-retningslinjer-2024",
                    "source": "Datatilsynet",
                    "published_date": (datetime.now() - timedelta(hours=2)).isoformat(),
                    "category": "datatilsynet",
                    "summary": "Nye retningslinjer for AI i offentlig sektor er udgivet.",
                    "importance": "high",
                    "keywords": ["ai retningslinjer", "offentlig sektor"]
                },
                {
                    "title": "EU Commission AI Act implementation update",
                    "url": "https://ec.europa.eu/news/ai-act-update-2024",
                    "source": "EU Commission",
                    "published_date": (datetime.now() - timedelta(hours=6)).isoformat(),
                    "category": "eu_news",
                    "summary": "Commission provides implementation timeline for AI Act.",
                    "importance": "high",
                    "keywords": ["ai act", "implementation", "timeline"]
                }
            ]

            if kategori:
                mock_news = [item for item in mock_news if item["category"] == kategori]

            return {
                "success": True,
                "nyheder": mock_news[:limit],
                "total": len(mock_news),
                "last_updated": datetime.now().isoformat()
            }

        # Use real scraper if available
        news_items = news_scraper.get_cached_news(category=kategori, limit=limit)

        return {
            "success": True,
            "nyheder": news_items,
            "total": len(news_items),
            "last_updated": news_scraper.last_update.isoformat()
        }

    except Exception as e:
        logger.error(f"Hent nyheder fejlede: {e}")
        raise HTTPException(status_code=500, detail=f"Nyheder fejl: {str(e)}")

@app.get("/api/news/vigtige", response_model=Dict[str, Any])
async def get_vigtige_nyheder():
    """
    Hent vigtige nyheder (high importance)
    """
    try:
        if not news_scraper:
            # Return mock high importance news
            mock_important = [
                {
                    "title": "BREAKING: Ny EU domstolsafgørelse om AI bias",
                    "url": "https://curia.europa.eu/ai-bias-ruling-2024",
                    "source": "EU Domstol",
                    "published_date": (datetime.now() - timedelta(hours=1)).isoformat(),
                    "category": "court_cases",
                    "summary": "Banebrydende afgørelse om AI diskrimination i ansættelsesprocesser.",
                    "importance": "high",
                    "keywords": ["ai bias", "diskrimination", "domstol"]
                }
            ]
            return {
                "success": True,
                "vigtige_nyheder": mock_important,
                "total": len(mock_important)
            }

        important_news = news_scraper.get_news_by_importance("high")

        return {
            "success": True,
            "vigtige_nyheder": important_news,
            "total": len(important_news)
        }

    except Exception as e:
        logger.error(f"Hent vigtige nyheder fejlede: {e}")
        raise HTTPException(status_code=500, detail=f"Vigtige nyheder fejl: {str(e)}")

@app.get("/api/news/relevant", response_model=Dict[str, Any])
async def get_relevant_news(
    system: Optional[str] = None,
    risk: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 10
):
    """
    Hent kontekstuelle nyheder baseret på AI-system vurdering

    Returnerer relevante nyheder baseret på:
    - AI system type og anvendelse
    - Risikoniveau identificeret
    - Compliance områder der kræver opmærksomhed
    """
    try:
        # Define keywords based on assessment context
        keywords = []

        if risk:
            risk_keywords = {
                "high": ["højrisiko", "high risk", "biometrisk", "automatiserede beslutninger", "FRIA"],
                "limited": ["begrænset risiko", "limited risk", "chatbot", "generativ AI", "transparens"],
                "minimal": ["minimal risiko", "minimal risk", "compliance", "dokumentation"],
                "unacceptable": ["forbudt", "prohibited", "subliminal", "social scoring"]
            }
            if risk.lower() in risk_keywords:
                keywords.extend(risk_keywords[risk.lower()])

        if system:
            # Extract keywords from system description
            system_lower = system.lower()
            if "recrui" in system_lower or "ansættel" in system_lower:
                keywords.extend(["recruitment", "ansættelse", "bias", "diskrimination"])
            if "health" in system_lower or "sundhed" in system_lower:
                keywords.extend(["sundhed", "health", "medicinsk", "patient"])
            if "finans" in system_lower or "kredit" in system_lower:
                keywords.extend(["finans", "kredit", "bank", "financial"])
            if "chatbot" in system_lower or "chat" in system_lower:
                keywords.extend(["chatbot", "conversational AI", "transparens"])

        # Always include general AI compliance keywords
        keywords.extend(["AI Act", "GDPR", "datatilsynet", "compliance", "artificial intelligence"])

        if not news_scraper:
            # Return contextual mock news
            mock_contextual = []

            if risk == "high":
                mock_contextual.append({
                    "title": "Ny vejledning til højrisiko AI-systemer fra Datatilsynet",
                    "url": "https://datatilsynet.dk/high-risk-ai-guidance",
                    "source": "Datatilsynet",
                    "published_date": (datetime.now() - timedelta(days=2)).isoformat(),
                    "category": "datatilsynet",
                    "summary": "Datatilsynet udgiver ny vejledning til organisationer med højrisiko AI-systemer om DPIA og sikkerhedsforanstaltninger.",
                    "importance": "high",
                    "keywords": ["højrisiko", "DPIA", "sikkerhed", "vejledning"],
                    "relevance_score": 0.95
                })

            if "ansættel" in (system or "").lower() or "recrui" in (system or "").lower():
                mock_contextual.append({
                    "title": "EU domstol afgør sag om AI bias i rekruttering",
                    "url": "https://curia.europa.eu/ai-recruitment-bias",
                    "source": "EU Domstol",
                    "published_date": (datetime.now() - timedelta(days=1)).isoformat(),
                    "category": "court_cases",
                    "summary": "Landmark afgørelse fastslår virksomheders ansvar for at forhindre diskrimination i AI-baserede rekrutteringssystemer.",
                    "importance": "high",
                    "keywords": ["recruitment", "bias", "diskrimination", "domstol"],
                    "relevance_score": 0.92
                })

            # Add general compliance news
            mock_contextual.append({
                "title": "EDPB udgiver nye retningslinjer for AI og GDPR",
                "url": "https://edpb.europa.eu/ai-gdpr-guidelines-2024",
                "source": "EDPB",
                "published_date": (datetime.now() - timedelta(days=3)).isoformat(),
                "category": "edpb",
                "summary": "European Data Protection Board præciserer hvordan GDPR artikel 22 skal fortolkes for AI-systemer.",
                "importance": "medium",
                "keywords": ["EDPB", "GDPR", "artikel 22", "retningslinjer"],
                "relevance_score": 0.85
            })

            # Sort by relevance and limit
            mock_contextual.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

            return {
                "success": True,
                "nyheder": mock_contextual[:limit],
                "total": len(mock_contextual),
                "context": {
                    "system": system,
                    "risk_level": risk,
                    "keywords_used": keywords[:5]  # First 5 keywords
                }
            }

        # Get news from scraper and filter by relevance
        all_news = []
        if category:
            all_news = news_scraper.get_news_by_category(category)
        else:
            all_news = news_scraper.get_latest_news(limit * 3)  # Get more to filter

        # Filter news by keywords relevance
        relevant_news = []
        for news_item in all_news:
            relevance_score = calculate_relevance_score(news_item, keywords)
            if relevance_score > 0.3:  # Threshold for relevance
                news_item['relevance_score'] = relevance_score
                relevant_news.append(news_item)

        # Sort by relevance score
        relevant_news.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

        return {
            "success": True,
            "nyheder": relevant_news[:limit],
            "total": len(relevant_news),
            "context": {
                "system": system,
                "risk_level": risk,
                "keywords_used": keywords[:5]
            }
        }

    except Exception as e:
        logger.error(f"Hent relevante nyheder fejlede: {e}")
        # Return empty but valid response on error
        return {
            "success": False,
            "nyheder": [],
            "total": 0,
            "error": str(e)
        }

def calculate_relevance_score(news_item, keywords):
    """Calculate relevance score for news item based on keywords"""
    score = 0.0
    text_to_search = f"{news_item.get('title', '')} {news_item.get('summary', '')} {' '.join(news_item.get('keywords', []))}".lower()

    for keyword in keywords:
        if keyword.lower() in text_to_search:
            # Base score for keyword match
            score += 0.1

            # Bonus for title match
            if keyword.lower() in news_item.get('title', '').lower():
                score += 0.1

            # Bonus for importance
            importance = news_item.get('importance', 'low')
            if importance == 'high':
                score += 0.1
            elif importance == 'medium':
                score += 0.05

    # Bonus for recent news
    try:
        pub_date = datetime.fromisoformat(news_item.get('published_date', ''))
        days_old = (datetime.now() - pub_date).days
        if days_old <= 7:
            score += 0.2
        elif days_old <= 30:
            score += 0.1
    except:
        pass

    return min(score, 1.0)  # Cap at 1.0

@app.get("/api/knowledge/kilder", response_model=Dict[str, Any])
async def get_juridiske_kilder(type: Optional[str] = None, myndighed: Optional[str] = None):
    """
    Hent juridiske kilder fra videnbase
    """
    try:
        if type:
            sources = legal_db.get_sources_by_type(type)
        elif myndighed:
            sources = legal_db.get_sources_by_authority(myndighed)
        else:
            sources = legal_db.get_all_sources()

        return {
            "success": True,
            "kilder": sources,
            "total": len(sources),
            "available_types": ["regulation", "directive", "law", "guideline", "standard", "policy"],
            "available_authorities": ["EU", "Danmark", "Datatilsynet", "EU Commission", "EDPB", "ISO/IEC", "IEEE"]
        }

    except Exception as e:
        logger.error(f"Hent juridiske kilder fejlede: {e}")
        raise HTTPException(status_code=500, detail=f"Kilder fejl: {str(e)}")

@app.get("/api/knowledge/søg", response_model=Dict[str, Any])
async def søg_juridiske_kilder(q: str):
    """
    Søg i juridiske kilder
    """
    try:
        if not q:
            raise HTTPException(status_code=400, detail="Søgeforespørgsel påkrævet")

        results = legal_db.search_sources(q)

        return {
            "success": True,
            "query": q,
            "resultater": results,
            "total": len(results)
        }

    except Exception as e:
        logger.error(f"Søgning i kilder fejlede: {e}")
        raise HTTPException(status_code=500, detail=f"Søgefejl: {str(e)}")

@app.get("/api/knowledge/eu-kilder", response_model=Dict[str, Any])
async def get_eu_kilder():
    """
    Hent alle EU-relaterede juridiske kilder
    """
    try:
        sources = legal_db.get_eu_sources()

        return {
            "success": True,
            "eu_kilder": sources,
            "total": len(sources)
        }

    except Exception as e:
        logger.error(f"Hent EU kilder fejlede: {e}")
        raise HTTPException(status_code=500, detail=f"EU kilder fejl: {str(e)}")

@app.get("/api/knowledge/danske-kilder", response_model=Dict[str, Any])
async def get_danske_kilder():
    """
    Hent alle danske juridiske kilder
    """
    try:
        sources = legal_db.get_danish_sources()

        return {
            "success": True,
            "danske_kilder": sources,
            "total": len(sources)
        }

    except Exception as e:
        logger.error(f"Hent danske kilder fejlede: {e}")
        raise HTTPException(status_code=500, detail=f"Danske kilder fejl: {str(e)}")

@app.get("/api/knowledge/aktive-regler", response_model=Dict[str, Any])
async def get_aktive_regler():
    """
    Hent alle aktive forordninger og love
    """
    try:
        regulations = legal_db.get_active_regulations()

        return {
            "success": True,
            "aktive_regler": regulations,
            "total": len(regulations)
        }

    except Exception as e:
        logger.error(f"Hent aktive regler fejlede: {e}")
        raise HTTPException(status_code=500, detail=f"Aktive regler fejl: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "simple_main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )