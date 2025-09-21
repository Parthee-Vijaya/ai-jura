"""
FastAPI Backend for The Judge - AI Compliance Platform
Dansk AI compliance platform med web research
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Literal
import asyncio
import uvicorn
import logging
from datetime import datetime, UTC
import json
import os
from pathlib import Path
from typing import Optional
from uuid import uuid4
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

from src.core.models import (
    ProjectInput,
    ComplianceAssessment,
    ComplianceReport,
    RiskLevel,
    ComplianceStatus,
)
from src.core.news_models import NewsFeedPayload, TickerArticle, TickerPayload
from src.agents import AgentConfig, get_agent_registry
from src.agents.compliance_orchestrator import ComplianceOrchestrator
from src.compliance.ai_act_checker import AIActComplianceChecker
from src.compliance.gdpr_checker import GDPRComplianceChecker
from src.services import NewsService, TechTickerService
from src.utils import get_version_info
from src.agents import run_research_agent
from urllib.parse import urlparse
from src.compliance_engine import ComplianceController

# Load environment variables from .env if present
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="The Judge - AI Compliance Platform",
    description="Comprehensive AI regulatory compliance checking",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator
orchestrator = ComplianceOrchestrator()
ai_act_checker = AIActComplianceChecker()
gdpr_checker = GDPRComplianceChecker()
news_service = NewsService()
ticker_service = TechTickerService()
agent_registry = get_agent_registry()
compliance_controller = ComplianceController()
ticker_refresh_task: Optional[asyncio.Task] = None
news_refresh_task: Optional[asyncio.Task] = None
NEWS_REFRESH_INTERVAL_SECONDS = int(os.getenv("NEWS_REFRESH_INTERVAL_SECONDS", "900"))  # 15 minutter
TICKER_STREAM_INTERVAL_SECONDS = int(os.getenv("TICKER_STREAM_INTERVAL_SECONDS", "120"))

AI_CASES_STORE = Path(os.getenv("AI_CASES_STORE", "data/ai_cases.json"))
AI_CASES_LOCK = asyncio.Lock()


async def _refresh_news_periodically() -> None:
    """Baggrundsopgave der opdaterer nyheder hvert kvarter"""
    logger.info("Starter periodisk nyhedsopdatering hver %s sekunder", NEWS_REFRESH_INTERVAL_SECONDS)
    try:
        while True:
            await asyncio.sleep(NEWS_REFRESH_INTERVAL_SECONDS)
            try:
                await news_service.get_latest_news(force_refresh=True)
                logger.debug("Nyheds-cache opdateret via baggrundsopgave")
            except Exception as exc:  # pragma: no cover - defensiv logning
                logger.warning("Kunne ikke opdatere nyheder automatisk: %s", exc)
    except asyncio.CancelledError:  # pragma: no cover - normal shutdown sti
        logger.info("Periodisk nyhedsopgave stoppet")
        raise


async def _refresh_ticker_periodically() -> None:
    """Baggrundsopgave for internationale tech-nyheder"""
    logger.info("Starter periodisk ticker-opdatering hver %s sekunder", NEWS_REFRESH_INTERVAL_SECONDS)
    try:
        while True:
            await asyncio.sleep(NEWS_REFRESH_INTERVAL_SECONDS)
            try:
                await ticker_service.get_latest(force_refresh=True)
                logger.debug("Ticker-cache opdateret via baggrundsopgave")
            except Exception as exc:  # pragma: no cover
                logger.warning("Kunne ikke opdatere ticker automatisk: %s", exc)
    except asyncio.CancelledError:  # pragma: no cover
        logger.info("Periodisk ticker-opgave stoppet")
        raise


@app.on_event("startup")
async def startup_event() -> None:
    """Initialiser services ved opstart"""
    global news_refresh_task, ticker_refresh_task
    # Fetch nyheder med det samme så forsiden har data
    try:
        await news_service.get_latest_news(force_refresh=True)
    except Exception as exc:
        logger.warning("Første nyhedsopdatering fejlede: %s", exc)

    try:
        await ticker_service.get_latest(force_refresh=True)
    except Exception as exc:
        logger.warning("Første ticker-opdatering fejlede: %s", exc)

    # Start baggrundsopgaven hvis ikke allerede aktiv
    if not news_refresh_task or news_refresh_task.done():
        news_refresh_task = asyncio.create_task(_refresh_news_periodically())

    if not ticker_refresh_task or ticker_refresh_task.done():
        ticker_refresh_task = asyncio.create_task(_refresh_ticker_periodically())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Ryd op ved nedlukning"""
    global news_refresh_task, ticker_refresh_task
    if news_refresh_task and not news_refresh_task.done():
        news_refresh_task.cancel()
        try:
            await news_refresh_task
        except asyncio.CancelledError:
            pass

    if ticker_refresh_task and not ticker_refresh_task.done():
        ticker_refresh_task.cancel()
        try:
            await ticker_refresh_task
        except asyncio.CancelledError:
            pass

# In-memory storage for assessments (use database in production)
assessments_db: Dict[str, ComplianceAssessment] = {}


def _ensure_case_store() -> None:
    AI_CASES_STORE.parent.mkdir(parents=True, exist_ok=True)
    if not AI_CASES_STORE.exists():
        AI_CASES_STORE.write_text('[]', encoding='utf-8')


async def _load_ai_cases() -> List[Dict[str, Any]]:
    def _load() -> List[Dict[str, Any]]:
        _ensure_case_store()
        with AI_CASES_STORE.open('r', encoding='utf-8') as handle:
            try:
                data = json.load(handle)
            except json.JSONDecodeError:
                logger.warning("Kunde ikke parse AI sager filen - initialiserer ny liste")
                data = []
        return data

    return await asyncio.to_thread(_load)


async def _save_ai_cases(cases: List[Dict[str, Any]]) -> None:
    def _save() -> None:
        _ensure_case_store()
        with AI_CASES_STORE.open('w', encoding='utf-8') as handle:
            json.dump(cases, handle, ensure_ascii=False, indent=2)

    await asyncio.to_thread(_save)


def _send_case_email_sync(case: "AICase") -> str:
    recipient = os.getenv('AI_CASES_RECIPIENT', 'ServicePortalen@kalundborg.dk')
    cc_raw = os.getenv('AI_CASES_CC', 'pavi@kalundborg.dk')
    cc_recipients = [addr.strip() for addr in cc_raw.split(',') if addr.strip()]

    smtp_host = os.getenv('SMTP_HOST', 'localhost')
    smtp_port = int(os.getenv('SMTP_PORT', '25'))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    use_tls = os.getenv('SMTP_USE_TLS', 'false').lower() not in {'0', 'false', 'no'}
    sender = os.getenv('SMTP_FROM') or smtp_user or 'no-reply@judgedredd.local'

    message = EmailMessage()
    message['Subject'] = f"Ny AI sag: {case.title}"
    message['From'] = sender
    message['To'] = recipient
    if cc_recipients:
        message['Cc'] = ', '.join(cc_recipients)
    reply_to = os.getenv('SMTP_REPLY_TO')
    if reply_to:
        message['Reply-To'] = reply_to

    created_at_local = case.created_at.astimezone(UTC)
    created_at_text = created_at_local.strftime('%Y-%m-%d %H:%M:%S UTC')
    body = (
        f"Ny AI sag er indsendt via AI Compliance Platformen.\n\n"
        f"Titel: {case.title}\n"
        f"Indsendt: {created_at_text}\n"
        f"Sags-ID: {case.id}\n\n"
        f"Beskrivelse:\n{case.description}\n"
    )
    message.set_content(body)

    recipients = [recipient, *cc_recipients]

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            if use_tls:
                server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.send_message(message, from_addr=sender, to_addrs=recipients)
        logger.info(
            "Sendte AI sag email for %s til %s (cc=%s) via %s:%s",
            case.id,
            recipient,
            ','.join(cc_recipients) if cc_recipients else 'ingen',
            smtp_host,
            smtp_port,
        )
        return 'sent'
    except Exception as exc:  # pragma: no cover - robusthed
        logger.exception("Kunne ikke sende email for AI sag %s: %s", case.id, exc)
        return 'failed'


async def _dispatch_case_email(case: "AICase") -> str:
    """Kør e-mailafsendelse i baggrunden så API-tråden ikke blokeres."""
    return await asyncio.to_thread(_send_case_email_sync, case)


class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    services: Dict[str, str]


class QuickCheckRequest(BaseModel):
    beskrivelse: str
    ai_type: str
    sektor: str
    behandler_persondata: bool = False
    automatiserede_beslutninger: bool = False


class CommitMetadata(BaseModel):
    hash: Optional[str]
    shortHash: Optional[str]
    message: Optional[str]
    author: Optional[str]
    timestamp: Optional[datetime]


class VersionResponse(BaseModel):
    version: str
    lastChangeType: Literal['major', 'minor', 'patch']
    lastCommit: Optional[CommitMetadata]
    generatedAt: datetime


class AICaseCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    description: str = Field(..., min_length=10, max_length=5000)


class AICase(BaseModel):
    id: str
    title: str
    description: str
    created_at: datetime
    email_status: Literal['sent', 'skipped', 'failed']


class ResearchRequest(BaseModel):
    emne: str
    fokusområder: List[str] = None


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "message": "The Judge - AI Compliance Platform API",
        "beskrivelse": "Dansk AI compliance platform med web research",
        "dokumentation": "/docs",
        "sundhedstjek": "/health"
    }


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    news_payload = await news_service.get_latest_news()
    news_status = "operational" if news_payload.items else "degraded"
    ticker_payload = await ticker_service.get_latest()
    ticker_status = "operational" if ticker_payload.items else "degraded"

    return HealthCheck(
        status="healthy",
        timestamp=datetime.now(),
        services={
            "api": "operational",
            "ai_act_checker": "operational",
            "gdpr_checker": "operational",
            "orchestrator": "operational",
            "news_service": news_status,
            "ticker_service": ticker_status
        }
    )


@app.get("/api/version", response_model=VersionResponse)
async def version_info() -> VersionResponse:
    """Returnér live versionsinformation baseret på git."""
    try:
        info = get_version_info()
        return VersionResponse(**info)
    except Exception as exc:  # pragma: no cover - defensiv logning
        logger.exception("Kunne ikke hente versionsoplysninger: %s", exc)
        raise HTTPException(status_code=500, detail="Kunne ikke hente versionsoplysninger")


@app.get("/api/ai-cases", response_model=List[AICase])
async def list_ai_cases() -> List[AICase]:
    """Returnér alle indsendte AI sager."""
    raw_cases = await _load_ai_cases()
    normalized: List[AICase] = []
    for item in raw_cases:
        if 'email_status' not in item:
            item['email_status'] = 'skipped'
        try:
            normalized.append(AICase(**item))
        except Exception as exc:  # pragma: no cover - robusthed
            logger.warning("Springer ugyldig AI sag over: %s", exc)
    return normalized


@app.post("/api/ai-cases", response_model=AICase, status_code=201)
async def create_ai_case(case_input: AICaseCreate) -> AICase:
    """Opret en ny AI sag og send email-notifikation."""
    trimmed_title = case_input.title.strip()
    trimmed_description = case_input.description.strip()
    if not trimmed_title or not trimmed_description:
        raise HTTPException(status_code=400, detail="Titel og beskrivelse må ikke være tomme")

    base_case = AICase(
        id=str(uuid4()),
        title=trimmed_title,
        description=trimmed_description,
        created_at=datetime.now(UTC),
        email_status='pending',
    )

    email_status = await _dispatch_case_email(base_case)
    new_case = base_case.model_copy(update={'email_status': email_status})

    async with AI_CASES_LOCK:
        cases = await _load_ai_cases()
        cases.append(new_case.model_dump(mode='json'))
        await _save_ai_cases(cases)

    logger.info("Oprettede AI sag %s med status %s", new_case.id, new_case.email_status)
    return new_case


@app.get("/api/news/latest", response_model=NewsFeedPayload)
async def get_latest_news(
    force_refresh: bool = False,
    category: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 20,
):
    """Returnér seneste nyheder om AI og jura"""
    limit = max(1, min(limit, news_service.max_items))
    payload = await news_service.get_latest_news(
        force_refresh=force_refresh,
        category=category,
        source=source,
        limit=limit,
    )
    return payload


@app.post("/api/news/refresh", response_model=NewsFeedPayload)
async def refresh_news():
    """Tving opdatering af nyhedsfeed"""
    payload = await news_service.get_latest_news(force_refresh=True)
    return payload


@app.get("/api/news/ticker", response_model=TickerPayload)
async def get_ticker_news(force_refresh: bool = False):
    """Returnér AI-ticker fra internationale medier"""
    return await _build_ticker_payload(force_refresh=force_refresh)


@app.get("/api/news/ticker/stream")
async def stream_ticker(request: Request):
    """Server-Sent Events stream med løbende ticker data"""

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break

            payload = await _build_ticker_payload()
            data = json.dumps([
                article.model_dump(mode="json") for article in payload.items
            ])
            yield f"data: {data}\n\n"
            await asyncio.sleep(TICKER_STREAM_INTERVAL_SECONDS)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def _build_ticker_payload(force_refresh: bool = False) -> TickerPayload:
    ticker_payload = await ticker_service.get_latest(force_refresh=force_refresh)
    news_payload = await news_service.get_latest_news()

    legal_highlights: List[TickerArticle] = []
    for item in news_payload.items[:5]:
        legal_highlights.append(
            TickerArticle(
                title=item.title,
                url=item.url,
                source=item.source,
                published_at=item.published_at,
                scraped_at=item.scraped_at,
            )
        )

    combined: List[TickerArticle] = []
    seen_urls = set()
    for article in legal_highlights + ticker_payload.items:
        if article.url in seen_urls:
            continue
        seen_urls.add(article.url)
        combined.append(article)

    return TickerPayload(
        items=combined[: ticker_service.max_items],
        last_updated=datetime.now(UTC),
        cache_ttl_seconds=int(ticker_service.cache_ttl.total_seconds()),
    )


@app.get("/api/agents/registry", response_model=List[AgentConfig])
async def list_agent_configs():
    """Returnér registrerede agentroller"""
    return agent_registry.list_agents()


@app.get("/api/agents/registry/{agent_id}", response_model=AgentConfig)
async def get_agent_config(agent_id: str):
    """Returnér detaljer for en specifik agentrolle"""
    try:
        return agent_registry.ensure(agent_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/research/juridisk", response_model=Dict[str, Any])
async def juridisk_research(request: ResearchRequest):
    """
    Udfører juridisk research med kildecitation
    """
    try:
        logger.info(f"Starter juridisk research (agent): {request.emne}")

        agent_result = await asyncio.to_thread(
            run_research_agent,
            query=request.emne,
            focus_areas=request.fokusområder or ["EU AI Act", "GDPR", "dansk lovgivning"],
        )

        formatted = _format_research_result(agent_result, request.emne, request.fokusområder)

        return {
            "success": True,
            "emne": request.emne,
            "resultat": formatted,
            "message": f"Research afsluttet - {len(formatted['sources'])} kilder fundet"
        }

    except Exception as e:
        logger.error(f"Juridisk research fejlede: {e}")
        raise HTTPException(status_code=500, detail=f"Research fejl: {str(e)}")


def _format_research_result(
    raw: Dict[str, Any] | str,
    query: str,
    focus_areas: Optional[List[str]],
) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {
            "query": query,
            "focus_areas": focus_areas or [],
            "summary": str(raw),
            "key_findings": [],
            "recommendations": [],
            "sources": [],
            "cross_references": [],
        }

    def _normalise_sources(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalised: List[Dict[str, Any]] = []
        for source in sources or []:
            if not isinstance(source, dict):
                continue
            url = source.get("url") or ""
            domain = source.get("domain")
            if not domain and url:
                domain = urlparse(url).netloc
            normalised.append({
                "title": source.get("title") or domain or "Ukendt kilde",
                "url": url,
                "authority": source.get("authority"),
                "domain": domain,
                "date_accessed": source.get("date_accessed"),
                "relevance_score": source.get("relevance_score"),
            })
        return normalised

    def _normalise_cross_refs(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalised: List[Dict[str, Any]] = []
        for item in items or []:
            statement = item.get("statement") if isinstance(item, dict) else None
            if not statement:
                continue
            citations = []
            for citation in item.get("citations", []):
                if not isinstance(citation, dict):
                    continue
                citations.append({
                    "title": citation.get("title"),
                    "authority": citation.get("authority"),
                    "url": citation.get("url"),
                })
            normalised.append({
                "statement": statement,
                "citations": citations,
            })
        return normalised

    summary = raw.get("summary") or raw.get("answer") or raw.get("llm_answer")
    key_findings = raw.get("key_findings") or []
    recommendations = raw.get("recommended_actions") or raw.get("recommendations") or []
    sources = _normalise_sources(raw.get("sources") or [])
    cross_refs = _normalise_cross_refs(raw.get("cross_references") or raw.get("crossReferences") or [])
    llm_answer = raw.get("answer") or raw.get("llm_answer")
    llm_citations = raw.get("llm_answer_citations") or raw.get("citations", [])

    return {
        "query": query,
        "focus_areas": focus_areas or [],
        "summary": summary or "Ingen sammenfatning tilgængelig.",
        "key_findings": key_findings,
        "recommendations": recommendations,
        "sources": sources,
        "cross_references": cross_refs,
        "llm_answer": llm_answer,
        "llm_answer_citations": llm_citations,
    }


@app.post("/api/compliance/analyser", response_model=Dict[str, Any])
async def analyser_compliance(project: ProjectInput, background_tasks: BackgroundTasks):
    """
    Analyze a project for AI compliance
    """
    try:
        logger.info(f"Starting compliance analysis for: {project.name}")

        # Run analysis (in production, this would be async with job queue)
        assessment = await orchestrator.analyze_project(project)

        # Store assessment
        assessment_id = assessment.project_id
        assessments_db[assessment_id] = assessment

        # Return summary
        return {
            "assessment_id": assessment_id,
            "project_name": assessment.project_name,
            "risk_level": assessment.risk_level.value,
            "overall_status": assessment.overall_status.value,
            "compliance_score": assessment.compliance_score,
            "summary": {
                "ai_act_risk": assessment.risk_level.value,
                "gdpr_compliant": assessment.compliance_score >= 70,
                "gaps_count": len(assessment.compliance_gaps),
                "recommendations_count": len(assessment.recommendations)
            },
            "message": "Analysis complete. Use assessment_id to retrieve full report."
        }

    except Exception as e:
        logger.error(f"Compliance analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compliance/hurtig-tjek", response_model=Dict[str, Any])
async def hurtig_compliance_tjek(request: QuickCheckRequest):
    """
    Quick compliance check without full analysis
    """
    try:
        # Create simplified project input
        project = ProjectInput(
            name="Hurtig Tjek",
            description=request.beskrivelse,
            ai_type=request.ai_type,
            sector=request.sektor,
            personal_data=request.behandler_persondata,
            automated_decision_making=request.automatiserede_beslutninger,
            data_types=["generel"]
        )

        # Run quick checks
        risk_level, risk_reasons = ai_act_checker.assess_risk_level(project)

        gdpr_relevant = request.behandler_persondata
        gdpr_high_risk = gdpr_checker._requires_dpia(project) if gdpr_relevant else False

        rule_engine_result = compliance_controller.run_quick_checks({
            "beskrivelse": request.beskrivelse,
            "fagomraade": request.sektor,
            "sector": request.sektor,
            "ai_type": request.ai_type,
            "ai_risk_level": risk_level.value,
            "behandler_persondata": request.behandler_persondata,
            "automatiserede_beslutninger": request.automatiserede_beslutninger,
            "organisation": "Kalundborg Kommune",
        })

        return {
            "ai_act": {
                "risk_level": risk_level.value,
                "reasons": risk_reasons
            },
            "gdpr": {
                "relevant": gdpr_relevant,
                "high_risk": gdpr_high_risk,
                "requires_dpia": gdpr_high_risk
            },
            "quick_recommendations": _generate_quick_recommendations(risk_level, gdpr_relevant, gdpr_high_risk),
            "needs_full_assessment": risk_level in [RiskLevel.HIGH, RiskLevel.UNACCEPTABLE] or gdpr_high_risk,
            "rule_engine": rule_engine_result,
            "prompt_full_assessment": rule_engine_result.get("recommend_full", False) or risk_level in [RiskLevel.HIGH, RiskLevel.UNACCEPTABLE] or gdpr_high_risk
        }

    except Exception as e:
        logger.error(f"Quick check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/compliance/assessment/{assessment_id}", response_model=Dict[str, Any])
async def get_assessment(assessment_id: str):
    """
    Retrieve a specific compliance assessment
    """
    if assessment_id not in assessments_db:
        raise HTTPException(status_code=404, detail="Assessment not found")

    assessment = assessments_db[assessment_id]

    return {
        "assessment_id": assessment_id,
        "project_name": assessment.project_name,
        "assessment_date": assessment.assessment_date.isoformat(),
        "risk_level": assessment.risk_level.value,
        "overall_status": assessment.overall_status.value,
        "compliance_score": assessment.compliance_score,
        "ai_act_compliance": assessment.ai_act_compliance,
        "gdpr_compliance": assessment.gdpr_compliance,
        "sector_compliance": assessment.sector_compliance,
        "requirements": [
            {
                "id": req.id,
                "framework": req.framework.value,
                "description": req.description,
                "status": req.compliance_status.value,
                "mandatory": req.mandatory,
                "recommendations": req.recommendations
            }
            for req in assessment.requirements
        ],
        "identified_risks": assessment.identified_risks,
        "recommendations": assessment.recommendations,
        "action_items": assessment.action_items
    }


@app.get("/api/compliance/assessments", response_model=List[Dict[str, Any]])
async def list_assessments():
    """
    List all compliance assessments
    """
    return [
        {
            "assessment_id": aid,
            "project_name": assessment.project_name,
            "assessment_date": assessment.assessment_date.isoformat(),
            "risk_level": assessment.risk_level.value,
            "overall_status": assessment.overall_status.value,
            "compliance_score": assessment.compliance_score
        }
        for aid, assessment in assessments_db.items()
    ]


@app.post("/api/compliance/report/{assessment_id}/generate")
async def generate_report(assessment_id: str, format: str = "json"):
    """
    Generate compliance report in specified format
    """
    if assessment_id not in assessments_db:
        raise HTTPException(status_code=404, detail="Assessment not found")

    assessment = assessments_db[assessment_id]

    if format == "json":
        return JSONResponse(content=assessment.model_dump(mode="json"))
    else:
        # In production, generate PDF/Word documents here
        raise HTTPException(status_code=400, detail=f"Format {format} not yet implemented")


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload project documentation for analysis
    """
    try:
        # Save file temporarily
        file_location = f"/tmp/{file.filename}"
        with open(file_location, "wb") as f:
            f.write(await file.read())

        # In production, process the document and extract project information
        return {
            "filename": file.filename,
            "status": "uploaded",
            "message": "Document uploaded successfully. Processing will begin shortly."
        }

    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
                "description": "Regulation on Artificial Intelligence",
                "version": "2024"
            },
            {
                "id": "gdpr",
                "name": "GDPR",
                "description": "General Data Protection Regulation",
                "version": "2016/679"
            },
            {
                "id": "danish_data_act",
                "name": "Danish Data Act",
                "description": "Danish implementation of data protection",
                "version": "Current"
            }
        ],
        "sectors": [
            "Healthcare",
            "Finance",
            "Education",
            "Employment",
            "Government",
            "Technology",
            "Retail",
            "Manufacturing",
            "Other"
        ],
        "ai_types": [
            "generative_ai",
            "predictive_ai",
            "classification",
            "recommendation",
            "computer_vision",
            "nlp",
            "robotics",
            "other"
        ]
    }


@app.get("/api/requirements/ai-act/{risk_level}")
async def get_ai_act_requirements(risk_level: str):
    """
    Get AI Act requirements for a specific risk level
    """
    try:
        level = RiskLevel(risk_level)
        # Generate sample requirements
        dummy_project = ProjectInput(
            name="Sample",
            description="Sample project",
            ai_type="generative_ai",
            sector="Technology"
        )
        requirements = ai_act_checker.generate_requirements(dummy_project, level)

        return {
            "risk_level": risk_level,
            "requirements": [
                {
                    "id": req.id,
                    "category": req.category,
                    "description": req.description,
                    "article_reference": req.article_reference,
                    "mandatory": req.mandatory
                }
                for req in requirements
            ]
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid risk level")


def _generate_quick_recommendations(risk_level: RiskLevel, gdpr_relevant: bool, gdpr_high_risk: bool) -> List[str]:
    """Generate quick recommendations based on initial assessment"""
    recommendations = []

    if risk_level == RiskLevel.UNACCEPTABLE:
        recommendations.append("CRITICAL: System appears to involve prohibited AI practices")
    elif risk_level == RiskLevel.HIGH:
        recommendations.append("Prepare for high-risk AI system compliance requirements")
        recommendations.append("Plan for conformity assessment")

    if gdpr_relevant:
        recommendations.append("Establish lawful basis for personal data processing")
        if gdpr_high_risk:
            recommendations.append("Conduct Data Protection Impact Assessment (DPIA)")

    recommendations.append("Document AI system capabilities and limitations")
    recommendations.append("Implement transparency measures")

    return recommendations[:5]  # Return top 5


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("API_RELOAD", "True").lower() == "true"
    )
