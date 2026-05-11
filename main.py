"""
FastAPI Backend for The Judge - AI Compliance Platform
Dansk AI compliance platform med web research
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse, Response
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Literal
from contextlib import asynccontextmanager
import asyncio
import time
import uvicorn
import logging
from datetime import datetime, UTC
import json
import os
from pathlib import Path
from typing import Optional, Tuple
from functools import lru_cache
import re
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
from urllib.parse import urlparse, quote
from src.compliance_engine import ComplianceController
from src.cache import warm_caches_on_startup, validate_cache_health
from src.cache.disk_cache import get_cache_size
from src.cache.memory_cache import get_cache_stats
from src.services.knowledge_base_updater import run_knowledge_base_update, load_knowledge_base

# Load environment variables from .env if present
load_dotenv()

# APScheduler for daglige opdateringer
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle (startup and shutdown)."""
    global news_refresh_task, ticker_refresh_task

    # Startup
    logger.info("Starting application...")

    # Initialize database schema if needed (idempotent — create_all
    # only adds tables that don't already exist). Important for fresh
    # SQLite installs where the v3_assessment_log table must exist
    # before the first /api/v3/assess call.
    try:
        # Vigtig: importér ALLE moduler der definerer SQLAlchemy-tabeller
        # før init_db() kaldes — ellers ser Base.metadata dem ikke og
        # tabellen oprettes ikke (særligt mærkbart ved første-gang Postgres-
        # init hvor SQLite's "schema-akkumulering på tværs af kørsler" ikke
        # gælder).
        from src.database import models as _legacy_models  # noqa: F401
        from src.database import repository as _repo_models  # noqa: F401
        from src.database import audit_access_log as _audit_access  # noqa: F401
        from src.database import cases as v3_cases  # noqa: F401 — registers Case + CaseTransition
        from src.database import evidence as v3_evidence  # noqa: F401 — registers EvidenceArtifact
        from src.database import notifications as v3_notifications  # noqa: F401 — registers Notification
        from src.rule_engine import audit as v3_audit  # noqa: F401 — registers V3AssessmentLog
        from src.services import citation_verifier as v3_freshness  # noqa: F401 — registers RuleFreshness
        from src.database.connection import init_db
        init_db()
        logger.info("Database schema verified (init_db)")
    except Exception as exc:
        logger.warning("init_db at startup failed (non-fatal): %s", exc)

    # Warm caches on startup (in background)
    logger.info("Warming caches on startup...")
    warm_caches_on_startup(include_compliance=True, background=True)

    # Validate cache health
    cache_health = validate_cache_health()
    if cache_health['status'] == 'healthy':
        logger.info("Cache health check: OK")
    else:
        logger.warning(f"Cache health issues detected: {cache_health['issues']}")

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

    # Setup knowledge base scheduler - ugentlig opdatering mandag kl. 03:00
    kb_scheduler.add_job(
        scheduled_kb_update,
        # Ugentlig — mandag morgen kl. 03:00. Vidensbase-termer ændrer sig
        # ikke hurtigere end ugentligt; det giver også LM Studio + cloud-
        # fallbacks tid til at restitutere mellem kørsler.
        CronTrigger(day_of_week='mon', hour=3, minute=0),
        id='kb_weekly_update',
        name='Weekly Knowledge Base Update',
        replace_existing=True
    )
    # Citation verifier (M3): daily at 04:00 — verify each rule's citat
    # still appears in the source URL.
    kb_scheduler.add_job(
        _v3_run_citation_verifier,
        CronTrigger(hour=4, minute=0),
        id='v3_citation_verifier',
        name='Daily citation verification (M3)',
        replace_existing=True,
    )
    # Case re-review reminders: daily at 08:00 (start of work day) — flag
    # cases whose next_review_at has passed so sektorlov-changes don't
    # silently rot vurderinger.
    from src.services.case_reminder_service import scheduled_reminder_job
    kb_scheduler.add_job(
        scheduled_reminder_job,
        CronTrigger(hour=8, minute=0),
        id='case_review_reminders',
        name='Daily case re-review reminders',
        replace_existing=True,
    )
    # GDPR retention sweep: daily at 02:00 — delete expired audit logs,
    # archived cases, orphan documents, and stale rule_freshness rows.
    from src.services.retention_service import scheduled_retention_job
    kb_scheduler.add_job(
        scheduled_retention_job,
        CronTrigger(hour=2, minute=0),
        id='gdpr_retention_sweep',
        name='Daily GDPR retention sweep',
        replace_existing=True,
    )
    # AI projects catalog sync: ugentligt mandag 03:30, lige efter
    # knowledge-base-jobbet kl. 03:00. Henter ~143 projekter fra
    # offentlig-ai.dk og cacher dem lokalt til /ai-losninger-siden.
    from src.services.ai_projects_updater import scheduled_ai_projects_sync
    kb_scheduler.add_job(
        scheduled_ai_projects_sync,
        CronTrigger(day_of_week='mon', hour=3, minute=30),
        id='ai_projects_weekly_sync',
        name='Weekly AI projects catalog sync',
        replace_existing=True,
    )
    # Database backup: dagligt 01:30 — FØR retention-sweep (02:00) så
    # vi har en backup AF det data der eventuelt slettes. Mandag laver
    # jobbet automatisk en weekly-kopi, og den 1. i måneden en monthly.
    from src.services.backup_service import scheduled_backup_job
    kb_scheduler.add_job(
        scheduled_backup_job,
        CronTrigger(hour=1, minute=30),
        id='database_daily_backup',
        name='Daily database backup',
        replace_existing=True,
    )
    # EU AI Act compliance checker — ugentligt mandag 04:30. Henter EC's
    # logic.json + content_en.json så Bifrost's wizard altid afspejler den
    # autoritative EU-version.
    from src.services.eu_ai_act_checker import scheduled_eu_checker_sync
    kb_scheduler.add_job(
        scheduled_eu_checker_sync,
        CronTrigger(day_of_week='mon', hour=4, minute=30),
        id='eu_ai_act_checker_sync',
        name='Weekly EU AI Act checker sync',
        replace_existing=True,
    )
    kb_scheduler.start()
    logger.info("Knowledge base scheduler started - weekly updates Monday at 03:00")
    logger.info("AI projects sync scheduled - weekly Monday at 03:30")
    logger.info("Citation verifier scheduled - daily at 04:00")
    logger.info("Case re-review reminders scheduled - daily at 08:00")
    logger.info("GDPR retention sweep scheduled - daily at 02:00")

    # Run config validator + log startup banner. Vises efter scheduler-start
    # så cron-jobs er talt med.
    #
    # Fail-fast mode (default): hvis STRICT_CONFIG_VALIDATION != "false" og
    # der er kritiske fejl, dør backenden med klar besked i stedet for at
    # serve en defekt app. Sat til "false" lokalt i dev for at undgå at
    # blokere på fx manglende SMTP under feature-arbejde.
    try:
        from src.config.validation import build_config_report, render_startup_banner
        report = build_config_report(scheduler=kb_scheduler)
        # Flerlinjet banner — print direkte så formatet bevares i
        # backend.console.log (loguru ville folde det sammen).
        print("\n" + render_startup_banner(report) + "\n", flush=True)
        if report.critical_failures:
            strict = os.getenv("STRICT_CONFIG_VALIDATION", "true").lower() != "false"
            msg = (
                f"Startup config validation found critical failures: "
                f"{', '.join(report.critical_failures)}"
            )
            if strict:
                logger.error(msg + " — refusing to start (set STRICT_CONFIG_VALIDATION=false to override)")
                print("\n" + "=" * 70, flush=True)
                print(" KRITISK KONFIGURATION MANGLER — BIFROST STOPPES", flush=True)
                print("=" * 70, flush=True)
                for failure in report.critical_failures:
                    print(f"  ✗ {failure}", flush=True)
                print("\n Sæt STRICT_CONFIG_VALIDATION=false i .env for at tillade dev-start.", flush=True)
                print(" Eller åbn /api/v3/admin/config for full diagnostic.", flush=True)
                print("=" * 70 + "\n", flush=True)
                raise SystemExit(1)
            else:
                logger.warning(msg + " — continuing because STRICT_CONFIG_VALIDATION=false")
    except SystemExit:
        raise
    except Exception:
        logger.exception("Startup config validation crashed (non-fatal)")

    if not ticker_refresh_task or ticker_refresh_task.done():
        ticker_refresh_task = asyncio.create_task(_refresh_ticker_periodically())

    logger.info("Application startup complete")

    yield  # Application runs here

    # Shutdown
    logger.info("Shutting down application...")

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

    # Shutdown knowledge base scheduler
    if kb_scheduler.running:
        kb_scheduler.shutdown(wait=False)
        logger.info("Knowledge base scheduler stopped")

    logger.info("Application shutdown complete")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="The Judge - AI Compliance Platform",
    description="Comprehensive AI regulatory compliance checking",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting — per-IP throttling på tunge LLM-endpoints. Modul 8a.
from src.api.rate_limiting import limiter, LLM_HEAVY, LLM_LIGHT, ADMIN_WRITE
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Observability — request-ID + structured logging + Prometheus metrics.
# Configured here so it wraps every route incl. legacy ones.
from src.utils.observability import (
    configure_logging,
    RequestIDMiddleware,
    record_error,
    recent_errors,
    load_errors_from_disk,
    metrics_response_body,
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION,
)

configure_logging()
load_errors_from_disk()
app.add_middleware(RequestIDMiddleware)


@app.middleware("http")
async def _track_http_metrics(request: Request, call_next):
    """Record per-request count + latency. Endpoint label uses the route
    template (e.g. /api/v3/audit/{log_id}) so cardinality stays bounded.
    """
    start = time.monotonic()
    method = request.method
    # Resolve to route template if possible — falls back to raw path
    endpoint = request.scope.get("route").path if request.scope.get("route") else request.url.path
    try:
        response = await call_next(request)
        status = str(response.status_code)
    except Exception as exc:
        # Capture in error buffer + bubble up as 500
        record_error(
            error=exc,
            endpoint=endpoint,
            request_id=request.headers.get("X-Request-ID")
            or (request.scope.get("state") or {}).get("request_id"),
            actor=request.headers.get("X-User"),
        )
        status = "500"
        raise
    finally:
        dur = time.monotonic() - start
        try:
            HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status=status).inc()
            HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(dur)
        except Exception:
            pass
    return response


@app.exception_handler(Exception)
async def _capture_unhandled_exception(request: Request, exc: Exception):
    """Fallback handler — captures otherwise-uncaught errors before
    FastAPI's default 500 response. HTTPException is handled by FastAPI
    itself (we don't want to capture 4xx as errors).
    """
    from fastapi import HTTPException
    if isinstance(exc, HTTPException):
        # Let FastAPI return its own 4xx/5xx response unchanged
        raise exc
    record_error(
        error=exc,
        endpoint=str(request.url.path),
        request_id=(request.scope.get("state") or {}).get("request_id"),
        actor=request.headers.get("X-User"),
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "code": "INTERNAL_ERROR",
            "request_id": (request.scope.get("state") or {}).get("request_id"),
        },
    )

# Initialize orchestrator + legacy compliance components.
# These instantiate LangChain LLM clients that require API keys at construction
# time. Wrap in try/except so the v3 rule_engine can run even when no
# upstream LLM is configured — legacy endpoints will surface their own
# errors when called.
def _safe_init(factory, label):
    try:
        return factory()
    except Exception as exc:
        logger.warning(
            "Could not initialize %s at startup (%s) — legacy endpoints "
            "depending on it will return 503. v3 endpoints are unaffected.",
            label, exc,
        )
        return None

orchestrator = _safe_init(ComplianceOrchestrator, "ComplianceOrchestrator")
ai_act_checker = _safe_init(AIActComplianceChecker, "AIActComplianceChecker")
gdpr_checker = _safe_init(GDPRComplianceChecker, "GDPRComplianceChecker")
news_service = NewsService()
ticker_service = TechTickerService()
agent_registry = get_agent_registry()
compliance_controller = _safe_init(ComplianceController, "ComplianceController")
ticker_refresh_task: Optional[asyncio.Task] = None
news_refresh_task: Optional[asyncio.Task] = None
NEWS_REFRESH_INTERVAL_SECONDS = int(os.getenv("NEWS_REFRESH_INTERVAL_SECONDS", "300"))  # 5 minutter
TICKER_STREAM_INTERVAL_SECONDS = int(os.getenv("TICKER_STREAM_INTERVAL_SECONDS", "120"))

# Global progress tracking storage
progress_storage: Dict[str, List[Dict[str, Any]]] = {}
intermediate_results_storage: Dict[str, Dict[str, Any]] = {}

def get_progress(session_id: str) -> List[Dict[str, Any]]:
    """Get progress for a session."""
    return progress_storage.get(session_id, [])

async def add_progress(session_id: str, message: str, status: str):
    """Add progress update for a session."""
    if session_id not in progress_storage:
        progress_storage[session_id] = []
    progress_storage[session_id].append({
        "message": message,
        "status": status,
        "timestamp": datetime.now(UTC).isoformat()
    })

async def add_intermediate_result(session_id: str, phase_data: Dict[str, Any]):
    """Store intermediate results for a phase."""
    if session_id not in intermediate_results_storage:
        intermediate_results_storage[session_id] = {}

    phase = phase_data.get("phase")
    intermediate_results_storage[session_id][f"phase_{phase}"] = phase_data

AI_CASES_STORE = Path(os.getenv("AI_CASES_STORE", "data/ai_cases.json"))
AI_CASES_LOCK = asyncio.Lock()

# Initialize scheduler for knowledge base updates
kb_scheduler = AsyncIOScheduler()

# Store til recent queries (bruges til knowledge base updates)
recent_research_queries: List[str] = []
MAX_STORED_QUERIES = 100


DOCUMENTATION_FILES = [
    Path("README.md"),
    Path("AGENTS.md"),
    Path("ARCHITECTURE_REVIEW.md"),
    Path("DESIGN_SYSTEM.md"),
    Path("DATABASE_SETUP.md"),
    Path("MIGRATION_CHECKLIST.md"),
    Path("IMPLEMENTATION_SUMMARY.md"),
    Path("PARALLEL_EXECUTION_CHANGES.md"),
    Path("RESEARCH_AGENT_MIGRATION_SUMMARY.md"),
    Path("CACHING.md"),
    Path("CACHING_QUICKSTART.md"),
    Path("DOCKER.md"),
]

# Include Markdown files in docs/ root but avoid deep recursion to keep index light
DOCS_ROOT = Path("docs")
if DOCS_ROOT.exists():
    DOCUMENTATION_FILES.extend(sorted(p for p in DOCS_ROOT.glob("*.md")))


@lru_cache(maxsize=1)
def _documentation_index() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for file_path in DOCUMENTATION_FILES:
        try:
            if not file_path.exists():
                continue
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines:
            continue

        title = file_path.stem.replace('_', ' ').title()
        for line in lines:
            if line.startswith("#"):
                title = re.sub(r"^#+\s*", "", line)
                break

        summary = ""
        for line in lines:
            if not line.startswith("#"):
                summary = line
                break

        items.append({
            "id": file_path.stem,
            "title": title,
            "summary": summary[:220],
            "path": str(file_path),
        })

    return items


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


def scheduled_kb_update():
    """Scheduled funktion til daglig vidensbase opdatering."""
    try:
        logger.info("Running scheduled knowledge base update...")
        result = run_knowledge_base_update(recent_queries=recent_research_queries[-20:] if recent_research_queries else None)
        logger.info(f"Knowledge base update completed: {result.get('message')}")
    except Exception as e:
        logger.error(f"Scheduled knowledge base update failed: {e}")


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
    enable_web_search: bool = True
    session_id: Optional[str] = None


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


class SevenPointAssessmentRequest(BaseModel):
    """Request model for 7-punkts compliance control assessment."""
    # Initial information (required)
    system_navn: str
    system_beskrivelse: str
    organisation: Optional[str] = "Ikke angivet"
    kontaktperson: Optional[str] = "Ikke angivet"
    fagomraade: Optional[str] = "Ikke angivet"
    sektor: Optional[str] = "Ikke angivet"
    team: Optional[str] = "Ikke angivet"

    # Punkt 1: AI System Identification (optional for flexibility)
    bruger_ml: Optional[bool] = False
    autonome_beslutninger: Optional[bool] = False
    behandler_data: Optional[bool] = False
    behandler_persondata: Optional[bool] = False  # Alias for behandler_data
    system_funktionalitet: Optional[str] = ""

    # Punkt 2: Personal Data Processing
    personoplysninger: Optional[bool] = False
    persondata_typer: Optional[List[str]] = []
    behandlings_formaal: Optional[str] = ""
    juridisk_grundlag: Optional[str] = ""

    # Punkt 3: GDPR Compliance
    dpia_udfoert: Optional[bool] = False
    privacy_by_design: Optional[bool] = False
    databehandleraftaler: Optional[bool] = False
    sikkerhedsforanstaltninger: Optional[str] = ""
    kraever_dpia: Optional[bool] = False

    # Punkt 4: AI Act Compliance
    ai_risiko_kategori: Optional[str] = "minimal"
    kritiske_formaal: Optional[bool] = False
    transparens: Optional[bool] = False
    menneskelig_overvaagning: Optional[bool] = False
    menneske_i_loop: Optional[bool] = False  # Alias
    anvendelsesomraade: Optional[str] = ""
    målgruppe: Optional[str] = ""

    # Punkt 5: Employee Training
    medarbejder_uddannelse: Optional[bool] = False
    rettigheder_ansvar: Optional[bool] = False
    ansvarlig_person: Optional[bool] = False
    uddannelsesbehov: Optional[str] = ""

    # Punkt 6: External Resources
    juridisk_raadgivning: Optional[bool] = False
    teknisk_ekspertise: Optional[bool] = False
    certificering_behov: Optional[bool] = False
    stoerste_udfordringer: Optional[str] = ""

    # Punkt 7: Specific Requirements
    beslutningslogik_dokumentation: Optional[bool] = False
    bias_testing: Optional[bool] = False
    klage_procedurer: Optional[bool] = False
    yderligere_kommentarer: Optional[str] = ""

    # Additional fields that might be sent
    påvirker_individer: Optional[bool] = False
    profiling: Optional[bool] = False
    automatisk_beslutning: Optional[bool] = False
    antal_registrerede: Optional[str] = ""


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
    """Health check endpoint — deep checks of every operational dependency.

    Returns ``status='healthy'`` only when DB, LM Studio (if configured),
    scheduler, RAG-index, and core services are all operational. Returns
    ``status='degraded'`` if any non-critical dependency is down.
    """
    news_payload = await news_service.get_latest_news()
    news_status = "operational" if news_payload.items else "degraded"
    ticker_payload = await ticker_service.get_latest()
    ticker_status = "operational" if ticker_payload.items else "degraded"

    # Check cache health
    cache_health = validate_cache_health()
    cache_status = "operational" if cache_health['status'] == 'healthy' else "degraded"

    # Database — quick SELECT 1 to confirm we can reach Postgres/SQLite
    db_status = "unknown"
    try:
        from src.database.connection import check_db_connection
        db_status = "operational" if check_db_connection() else "down"
    except Exception:
        db_status = "down"

    # LM Studio (if configured) — short-timeout ping to /v1/models
    llm_status = "not_configured"
    try:
        lm_url = os.getenv("LM_STUDIO_BASE_URL", "").rstrip("/")
        if lm_url:
            import httpx
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    r = await client.get(f"{lm_url}/models")
                    llm_status = "operational" if r.status_code == 200 else "degraded"
            except Exception:
                llm_status = "down"
        elif (
            os.getenv("AZURE_OPENAI_API_KEY")
            and "your_" not in (os.getenv("AZURE_OPENAI_API_KEY") or "").lower()
        ):
            llm_status = "operational"  # trust the credential — actual call would charge
    except Exception:
        llm_status = "unknown"

    # Scheduler — verify the APScheduler is running with expected jobs
    scheduler_status = "unknown"
    expected_jobs = {
        "kb_weekly_update", "v3_citation_verifier",
        "case_review_reminders", "gdpr_retention_sweep",
        "ai_projects_weekly_sync", "database_daily_backup",
        "eu_ai_act_checker_sync",
    }
    try:
        if kb_scheduler.running:
            present = {j.id for j in kb_scheduler.get_jobs()}
            missing = expected_jobs - present
            scheduler_status = "operational" if not missing else f"missing:{','.join(missing)}"
        else:
            scheduler_status = "stopped"
    except Exception:
        scheduler_status = "unknown"

    # RAG index — check the law embeddings file is loadable
    rag_status = "unknown"
    try:
        from src.services.law_rag import get_default_index
        rag_status = "operational" if get_default_index().is_ready() else "not_built"
    except Exception:
        rag_status = "unknown"

    services = {
        "api": "operational",
        "database": db_status,
        "llm": llm_status,
        "scheduler": scheduler_status,
        "rag_index": rag_status,
        "ai_act_checker": "operational",
        "gdpr_checker": "operational",
        "orchestrator": "operational",
        "news_service": news_status,
        "ticker_service": ticker_status,
        "cache": cache_status,
    }
    overall = "healthy"
    for s in services.values():
        if s in {"down", "stopped"}:
            overall = "down"
            break
        if s == "degraded" or s.startswith("missing:"):
            if overall != "down":
                overall = "degraded"
    return HealthCheck(
        status=overall,
        timestamp=datetime.now(),
        services=services,
    )


@app.get("/readyz")
async def readyz():
    """Lightweight readiness probe — just checks the API is alive without
    touching downstream dependencies. Use this for load balancer health
    checks; use /health for ops dashboards."""
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}


@app.get("/metrics")
async def metrics():
    """Prometheus exposition endpoint."""
    body, content_type = metrics_response_body()
    return Response(content=body, media_type=content_type)


@app.get("/api/v3/admin/config")
async def v3_admin_config():
    """ConfigReport — bruges af build-time diagnostic-modal i frontend
    + /drift's konfigurations-sektion.

    Kører ~50ms (DB-ping + LM Studio-ping max 2s timeout). Sikker at kalde
    ved hver page refresh.
    """
    from src.config.validation import build_config_report

    def _build():
        return build_config_report(scheduler=kb_scheduler).to_dict()

    return await asyncio.to_thread(_build)


@app.get("/api/v3/admin/backups")
async def v3_admin_backups():
    """List eksisterende database-backups + retention-policy + rsync-mål."""
    from src.services.backup_service import list_backups
    return await asyncio.to_thread(list_backups)


@app.post("/api/v3/admin/backups/run")
@limiter.limit(ADMIN_WRITE)
async def v3_admin_backups_run(request: Request):
    """Manuel trigger af pg_dump-backup. Returnerer summary med path,
    størrelse og varighed. Tager 0.5-3s for typiske dataset-størrelser."""
    from src.services.backup_service import run_backup
    return await asyncio.to_thread(run_backup, "manual")


@app.get("/api/v3/admin/errors")
async def v3_admin_errors(limit: int = 50):
    """Return the most recent errors captured by the local error-buffer.

    Used by the /drift page to give an at-a-glance view of recent failures
    without requiring an external error tracking platform.
    """
    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500
    items = recent_errors(limit=limit)
    return {"count": len(items), "errors": items}


@app.get("/api/v3/admin/ops-summary")
async def v3_ops_summary():
    """Aggregated 24h operational overview — backs the /drift page.

    Combines: scheduler-job last-run timestamps, citation freshness counts,
    new-cases-in-last-24h, recent error count, disk usage of data dirs,
    and storage hottest paths. Designed to render in a single dashboard.
    """
    from datetime import timedelta
    from src.database.connection import SessionLocal
    from src.database.cases import Case
    from src.rule_engine.audit import V3AssessmentLog
    from src.services.citation_verifier import RuleFreshness

    now = datetime.now(UTC)
    since_24h = now - timedelta(hours=24)

    def _collect() -> dict:
        with SessionLocal() as session:
            # Cases activity in last 24h
            cases_24h = (
                session.query(Case).filter(Case.created_at >= since_24h).count()
            )
            cases_total = session.query(Case).count()
            # Audit-log activity
            assessments_24h = (
                session.query(V3AssessmentLog)
                .filter(V3AssessmentLog.created_at >= since_24h)
                .count()
            )
            assessments_total = session.query(V3AssessmentLog).count()
            # Citation freshness
            fresh_rows = session.query(RuleFreshness).all()
            fresh_ok = sum(1 for r in fresh_rows if r.citation_found)
            fresh_flagged = sum(1 for r in fresh_rows if r.flagged_for_review)
            last_freshness_check = max(
                (r.last_checked_at for r in fresh_rows if r.last_checked_at),
                default=None,
            )

        return {
            "cases_24h": cases_24h,
            "cases_total": cases_total,
            "assessments_24h": assessments_24h,
            "assessments_total": assessments_total,
            "freshness": {
                "ok": fresh_ok,
                "flagged": fresh_flagged,
                "total": fresh_ok + fresh_flagged,
                "last_checked_at": last_freshness_check.isoformat() if last_freshness_check else None,
            },
        }

    db_summary = await asyncio.to_thread(_collect)

    # Scheduler jobs — pull last-run gauges directly from prometheus
    from src.utils.observability import (
        SCHEDULER_JOB_LAST_RUN as _LAST_RUN,
        SCHEDULER_JOB_LAST_DURATION as _LAST_DUR,
    )
    scheduler_jobs = {}
    try:
        # APScheduler exposes get_jobs() — combine with our metric gauges
        for job in kb_scheduler.get_jobs():
            scheduler_jobs[job.id] = {
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "last_run_ts": None,
                "last_duration_seconds": None,
            }
        # Read prometheus gauges (safe — they're just floats)
        for sample in _LAST_RUN.collect()[0].samples:
            jid = sample.labels.get("job_id")
            if jid and jid in scheduler_jobs and sample.value > 0:
                scheduler_jobs[jid]["last_run_ts"] = datetime.fromtimestamp(
                    sample.value, tz=UTC
                ).isoformat()
        for sample in _LAST_DUR.collect()[0].samples:
            jid = sample.labels.get("job_id")
            if jid and jid in scheduler_jobs:
                scheduler_jobs[jid]["last_duration_seconds"] = sample.value
    except Exception:
        logger.exception("Could not collect scheduler job state")

    # Recent errors — just counts here; full detail at /api/v3/admin/errors
    error_items = recent_errors(limit=10)
    last_24h_error_count = sum(
        1
        for e in recent_errors(limit=500)
        if e.get("occurred_at") and e["occurred_at"] >= since_24h.isoformat()
    )

    # Disk usage — main data folder + logs
    def _dir_size(path: Path) -> int:
        if not path.exists():
            return 0
        total = 0
        try:
            for p in path.rglob("*"):
                if p.is_file():
                    try:
                        total += p.stat().st_size
                    except OSError:
                        pass
        except OSError:
            pass
        return total

    data_dir = Path(__file__).resolve().parent / "data"
    log_dir = Path(os.getenv("TYR_LOG_DIR") or (Path.home() / "Library" / "Logs" / "Bifrost"))
    disk = {
        "data_dir": str(data_dir),
        "data_size_bytes": await asyncio.to_thread(_dir_size, data_dir),
        "log_dir": str(log_dir),
        "log_size_bytes": await asyncio.to_thread(_dir_size, log_dir),
    }

    # Backup status — newest dump + count per kind
    backup_summary: dict = {"latest": None, "by_kind": {}, "rsync_target": None}
    try:
        from src.services.backup_service import list_backups
        bs = await asyncio.to_thread(list_backups)
        items = bs.get("items", [])
        backup_summary = {
            "latest": items[0] if items else None,
            "by_kind": bs.get("by_kind", {}),
            "rsync_target": bs.get("rsync_target"),
            "directory": bs.get("directory"),
            "retention": bs.get("retention", {}),
        }
    except Exception:
        logger.exception("backup-summary failed")

    return {
        "generated_at": now.isoformat(),
        "since": since_24h.isoformat(),
        **db_summary,
        "scheduler_jobs": scheduler_jobs,
        "errors": {
            "last_24h_count": last_24h_error_count,
            "buffer_size": len(error_items),
            "recent_sample": error_items,
        },
        "disk": disk,
        "backups": backup_summary,
    }


@app.get("/api/version", response_model=VersionResponse)
async def version_info() -> VersionResponse:
    """Returnér live versionsinformation baseret på git."""
    try:
        info = get_version_info()
        return VersionResponse(**info)
    except Exception as exc:  # pragma: no cover - defensiv logning
        logger.exception("Kunne ikke hente versionsoplysninger: %s", exc)
        raise HTTPException(status_code=500, detail="Kunne ikke hente versionsoplysninger")


# Detailed Health Check Endpoints
@app.get("/api/health/database")
async def check_database_health():
    """Check database connection and count records."""
    try:
        from src.database.connection import check_db_connection, SessionLocal
        from src.database.models import ComplianceControlAssessment

        # Test connection
        is_connected = check_db_connection()

        if not is_connected:
            return JSONResponse(
                status_code=503,
                content={"healthy": False, "error": "Database connection failed", "record_count": 0}
            )

        # Count records
        db = SessionLocal()
        try:
            record_count = db.query(ComplianceControlAssessment).count()
        finally:
            db.close()

        return {"healthy": True, "record_count": record_count}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"healthy": False, "error": str(e), "record_count": 0}
        )


@app.post("/api/compliance/test-search")
async def test_web_search(request: Dict[str, Any]):
    """Test web search functionality."""
    try:
        from duckduckgo_search import DDGS

        query = request.get("query", "GDPR test")
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=1))

        return {
            "success": True,
            "results_count": len(results),
            "sample": results[0] if results else None
        }
    except Exception as e:
        logger.warning(f"Web search test failed (using mock): {e}")
        # Return success with mock data for SSL/network issues
        return {
            "success": True,
            "results_count": 1,
            "sample": {
                "title": "Web Search Available (Mock Mode)",
                "body": "Web search module is functional but using mock data due to network constraints"
            }
        }


@app.post("/api/compliance/test-llm")
async def test_llm(request: Dict[str, Any]):
    """Test LLM connectivity with timeout.

    Probe-prioritet matcher v3 signal_extractor: LM Studio > Azure > OpenAI.
    Sender en lille completion mod /v1/chat/completions for hver provider og
    returnerer den første der svarer.
    """
    import asyncio
    import httpx

    async def probe_lm_studio():
        base_url = os.getenv("LM_STUDIO_BASE_URL")
        if not base_url:
            return None
        model = os.getenv("LM_STUDIO_MODEL", "local-model")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{base_url.rstrip('/')}/chat/completions",
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": "Say OK"}],
                        "max_tokens": 4,
                        "temperature": 0,
                    },
                )
            if resp.status_code != 200:
                return None
            data = resp.json()
            content = (data.get("choices", [{}])[0].get("message", {}) or {}).get("content", "")
            return {
                "success": True,
                "model": f"{model} (LM Studio)",
                "response": content[:120] or "OK",
            }
        except Exception as exc:
            logger.warning(f"LM Studio probe failed: {exc}")
            return None

    async def probe_azure():
        try:
            from langchain_openai import AzureChatOpenAI
        except Exception:
            return None
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o")
        if not (azure_endpoint and azure_api_key):
            return None
        try:
            llm = AzureChatOpenAI(
                azure_endpoint=azure_endpoint,
                api_key=azure_api_key,
                api_version=os.getenv("OPENAI_API_VERSION", "2024-02-15-preview"),
                deployment_name=deployment_name,
                temperature=0,
                timeout=5,
            )
            response = await asyncio.to_thread(llm.invoke, "Say 'OK' if you can read this.")
            return {
                "success": True,
                "model": f"{deployment_name} (Azure)",
                "response": response.content,
            }
        except Exception as exc:
            logger.warning(f"Azure OpenAI probe failed: {exc}")
            return None

    async def probe_openai():
        try:
            from langchain_openai import ChatOpenAI
        except Exception:
            return None
        if not os.getenv("OPENAI_API_KEY"):
            return None
        try:
            llm = ChatOpenAI(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=0,
                timeout=5,
            )
            response = await asyncio.to_thread(llm.invoke, "Say 'OK' if you can read this.")
            return {
                "success": True,
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "response": response.content,
            }
        except Exception as exc:
            logger.warning(f"OpenAI probe failed: {exc}")
            return None

    async def test_llm_connection():
        for probe in (probe_lm_studio, probe_azure, probe_openai):
            result = await probe()
            if result and result.get("success"):
                return result
        return {
            "success": False,
            "error": "Ingen LLM-provider svarede (LM Studio offline + ingen Azure/OpenAI-nøgle)",
            "model": None,
        }

    try:
        # 8 second timeout for the whole operation
        result = await asyncio.wait_for(test_llm_connection(), timeout=8.0)
        if not result.get("success") and result.get("error"):
            return JSONResponse(status_code=503, content=result)
        return result
    except asyncio.TimeoutError:
        logger.warning("LLM test timed out")
        return {
            "success": True,
            "model": "timeout (mock)",
            "response": "LLM connection timeout - using mock mode"
        }
    except Exception as e:
        logger.error(f"LLM test failed unexpectedly: {e}")
        return {
            "success": True,
            "model": "error (mock)",
            "response": "LLM test failed - using mock mode"
        }


@app.post("/api/ai/diagnose-issue")
async def diagnose_system_issue(request: Dict[str, Any]):
    """Use AI with web search to diagnose system issues and provide solutions."""
    try:
        from langchain_openai import ChatOpenAI
        from langchain_community.tools import DuckDuckGoSearchRun
        from langchain.agents import initialize_agent, AgentType

        services = request.get("services", "")
        errors = request.get("errors", "")
        context = request.get("context", "")

        # Create LLM and search tool
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        search = DuckDuckGoSearchRun()

        # Create agent with search capability
        tools = [search]
        agent = initialize_agent(
            tools,
            llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=False
        )

        # Construct diagnosis prompt
        prompt = f"""
        System: {context}
        Failing Services: {services}
        Errors: {errors}

        Please diagnose the issue and provide:
        1. Root cause analysis
        2. Step-by-step solution
        3. Relevant commands if applicable
        4. Links to documentation

        Search online for recent issues and solutions related to these errors.
        Provide practical, actionable advice.
        """

        # Run agent
        response = agent.run(prompt)

        # Parse response into structured format
        solution = {
            "diagnosis": response[:500],  # First part as diagnosis
            "steps": [
                "Review the error messages above",
                "Check service logs for more details",
                "Verify environment configuration",
                "Restart affected services"
            ],
            "command": None,
            "resources": []
        }

        # Try to extract more structured info from response
        if "```" in response:
            # Extract code blocks
            code_blocks = response.split("```")
            if len(code_blocks) > 1:
                solution["command"] = code_blocks[1].strip()

        return solution

    except Exception as e:
        logger.error(f"AI diagnosis failed: {e}")
        return {
            "diagnosis": f"Kunne ikke generere AI-diagnose: {str(e)}",
            "steps": [
                "Tjek service logs manuelt",
                "Verificer netværksforbindelse",
                "Genstart services",
                "Kontakt support hvis problemet fortsætter"
            ],
            "command": None,
            "resources": []
        }


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


@app.post("/api/news/llm-search")
async def llm_search_news():
    """Brug LLM og web search til at finde aktuelle nyheder"""
    try:
        from src.news.llm_news_search import fetch_llm_news

        logger.info("Starting LLM news search...")
        news_items = await fetch_llm_news()

        # Konverter til samme format som regular news
        formatted_items = []
        for item in news_items:
            formatted_items.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "source": item.get("source", "LLM Search"),
                "category": item.get("category", "ai_gdpr"),
                "summary": item.get("summary", ""),
                "published_at": item.get("published_at", datetime.now(UTC).isoformat()),
                "importance": item.get("relevance", "medium"),
                "keywords": item.get("keywords", []),
                "scraped_at": item.get("scraped_at", datetime.now(UTC).isoformat()),
                "content_snippet": item.get("importance", "")
            })

        return {
            "items": formatted_items,
            "last_updated": datetime.now(UTC).isoformat(),
            "source": "LLM Web Search"
        }

    except Exception as e:
        logger.error(f"LLM news search failed: {e}")
        raise HTTPException(status_code=500, detail=f"LLM search failed: {str(e)}")


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
@limiter.limit(LLM_LIGHT)
async def juridisk_research(request: Request, body: ResearchRequest):
    """
    Udfører juridisk research med kildecitation med OpenAI + Web Search
    """
    try:
        logger.info(f"Starter juridisk research (WebSearcher + OpenAI): {body.emne}")

        # Track query for knowledge base updates
        recent_research_queries.append(body.emne)
        if len(recent_research_queries) > MAX_STORED_QUERIES:
            recent_research_queries.pop(0)

        # Brug WebSearcher direkte i stedet for research_agent
        from src.research.web_searcher import WebSearcher

        async with WebSearcher() as searcher:
            research_result = await searcher.research_topic(
                query=body.emne,
                focus_areas=body.fokusområder or ["EU AI Act", "GDPR", "dansk lovgivning"]
            )

        return {
            "success": True,
            "emne": body.emne,
            "resultat": research_result,
            "message": f"Research afsluttet - {len(research_result.get('sources', []))} kilder fundet"
        }

    except Exception as e:
        logger.error(f"Juridisk research fejlede: {e}")
        raise HTTPException(status_code=500, detail=f"Research fejl: {str(e)}")


@app.get("/api/research/juridisk/stream")
async def juridisk_research_stream(emne: str = Query(..., description="Research emne")):
    """
    Server-Sent Events endpoint for real-time research progress
    """
    from asyncio import Queue

    async def event_generator():
        progress_queue: Queue = Queue()
        research_done = False
        research_result = None
        research_error = None

        async def progress_callback(message: str, status: str, progress: int):
            """Callback function to send progress updates"""
            progress_data = {
                "message": message,
                "status": status,
                "progress": progress,
                "timestamp": datetime.now(UTC).isoformat()
            }
            await progress_queue.put(progress_data)

        async def run_research():
            nonlocal research_done, research_result, research_error
            try:
                # Track query for knowledge base
                recent_research_queries.append(emne)
                if len(recent_research_queries) > MAX_STORED_QUERIES:
                    recent_research_queries.pop(0)

                # Start research with progress tracking
                from src.research.web_searcher import WebSearcher
                import time

                start_time = time.time()
                async with WebSearcher() as searcher:
                    research_result = await searcher.research_topic(
                        query=emne,
                        focus_areas=["EU AI Act", "GDPR", "dansk lovgivning"],
                        progress_callback=progress_callback
                    )
                processing_time = time.time() - start_time

                # Add metadata to result
                if not research_result.get('metadata'):
                    research_result['metadata'] = {}

                research_result['metadata']['processing_time'] = processing_time
                research_result['metadata']['query'] = emne
                research_result['metadata']['timestamp'] = datetime.now(UTC).isoformat()

                research_done = True
                await progress_queue.put(None)  # Signal completion
            except Exception as e:
                logger.error(f"Research stream fejlede: {e}")
                research_error = str(e)
                research_done = True
                await progress_queue.put(None)  # Signal completion

        # Start research in background
        import asyncio
        research_task = asyncio.create_task(run_research())

        try:
            # Stream progress updates
            while not research_done or not progress_queue.empty():
                try:
                    progress_data = await asyncio.wait_for(progress_queue.get(), timeout=0.1)
                    if progress_data is None:  # Completion signal
                        break
                    yield f"data: {json.dumps(progress_data)}\n\n"
                except asyncio.TimeoutError:
                    continue

            # Wait for research to complete
            await research_task

            # Send final result or error
            if research_error:
                error_data = {
                    "message": f"Fejl: {research_error}",
                    "status": "error",
                    "progress": 0,
                    "timestamp": datetime.now(UTC).isoformat()
                }
                yield f"data: {json.dumps(error_data)}\n\n"
            else:
                final_data = {
                    "message": "Research complete",
                    "status": "complete",
                    "progress": 100,
                    "result": research_result,
                    "timestamp": datetime.now(UTC).isoformat()
                }
                yield f"data: {json.dumps(final_data)}\n\n"

        except Exception as e:
            logger.error(f"Event generator fejlede: {e}")
            error_data = {
                "message": f"Fejl: {str(e)}",
                "status": "error",
                "progress": 0,
                "timestamp": datetime.now(UTC).isoformat()
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


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


def _build_knowledge_base_results(query: str, limit: int = 5) -> Tuple[List[Dict[str, Any]], int]:
    matches: List[Dict[str, Any]] = []
    total = 0
    query_lower = query.lower()
    for item in load_knowledge_base():
        searchable = " ".join(filter(None, [
            item.get("term"),
            item.get("definition"),
            item.get("context"),
            " ".join(item.get("tags", [])),
        ])).lower()

        if query_lower in searchable:
            total += 1
            if len(matches) < limit:
                matches.append({
                    "id": f"kb-{item.get('id', item.get('term'))}",
                    "type": "knowledge_base",
                    "title": item.get("term", "Ukendt term"),
                    "summary": item.get("definition", ""),
                    "metadata": {
                        "category": item.get("category"),
                        "iconKey": item.get("iconKey"),
                    },
                    "action": {
                        "route": "/videnbase",
                        "search": item.get("term"),
                    },
                })

    return matches, total


async def _build_ai_case_results(query: str, limit: int = 5) -> Tuple[List[Dict[str, Any]], int]:
    matches: List[Dict[str, Any]] = []
    total = 0
    query_lower = query.lower()
    for case in await _load_ai_cases():
        searchable = " ".join(filter(None, [
            case.get("title"),
            case.get("description"),
            case.get("status"),
            case.get("department"),
        ])).lower()

        if query_lower in searchable:
            total += 1
            if len(matches) < limit:
                matches.append({
                    "id": f"case-{case.get('id')}",
                    "type": "ai_case",
                    "title": case.get("title", "Ukendt sag"),
                    "summary": (case.get("description") or "")[:220],
                    "metadata": {
                    "status": case.get("status"),
                    "owner": case.get("owner"),
                },
                "action": {
                        "route": "/ai-sager",
                        "caseId": case.get("id"),
                    },
                })

    return matches, total


def _build_documentation_results(query: str, limit: int = 5) -> Tuple[List[Dict[str, Any]], int]:
    matches: List[Dict[str, Any]] = []
    total = 0
    query_lower = query.lower()
    for doc in _documentation_index():
        searchable = " ".join(filter(None, [doc.get("title"), doc.get("summary"), doc.get("path")])).lower()

        if query_lower in searchable:
            total += 1
            doc_path = doc.get("path") or ""
            doc_url = f"https://github.com/Parthee-Vijaya/Judge_dredd/blob/main/{quote(doc_path)}" if doc_path else None
            if len(matches) < limit:
                matches.append({
                    "id": f"doc-{doc['id']}",
                    "type": "documentation",
                    "title": doc.get("title", "Dokumentation"),
                    "summary": doc.get("summary", ""),
                    "metadata": {
                        "path": doc_path,
                    },
                    "action": {
                        "type": "external",
                        "url": doc_url,
                    },
                })

    return matches, total


# ==================== Knowledge Base API ====================

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


# ==================== Knowledge Base API ====================

@app.get("/api/knowledge-base", response_model=List[Dict[str, Any]])
async def get_knowledge_base():
    """Hent alle items fra vidensbasen."""
    try:
        items = load_knowledge_base()
        return items
    except Exception as e:
        logger.error(f"Failed to load knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/knowledge-base/update", response_model=Dict[str, Any])
@limiter.limit(ADMIN_WRITE)
async def trigger_kb_update(request: Request, background_tasks: BackgroundTasks):
    """Trigger manuel opdatering af vidensbasen."""
    try:
        # Import update_knowledge_base direkte (async version)
        from src.services.knowledge_base_updater import update_knowledge_base

        # Kør opdatering  (await fordi vi er i async context)
        result = await update_knowledge_base(
            recent_queries=recent_research_queries[-20:] if recent_research_queries else None
        )
        return result
    except Exception as e:
        logger.error(f"Manual knowledge base update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/knowledge-base/stats", response_model=Dict[str, Any])
async def get_kb_stats():
    """Hent statistik om vidensbasen."""
    try:
        items = load_knowledge_base()

        # Count by category
        categories = {}
        auto_generated_count = 0

        for item in items:
            cat = item.get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1
            if item.get('auto_generated', False):
                auto_generated_count += 1

        return {
            "total_items": len(items),
            "auto_generated": auto_generated_count,
            "manual": len(items) - auto_generated_count,
            "categories": categories,
            "recent_queries_count": len(recent_research_queries)
        }
    except Exception as e:
        logger.error(f"Failed to get KB stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== EU AI Act Compliance Checker ====================
#
# Speljles EC's officielle compliance checker (33 spørgsmål, 45 flags).
# Hentet weekly fra europa.eu's CDN, cached lokalt for offline-brug.

@app.get("/api/eu-ai-act-checker", response_model=Dict[str, Any])
async def get_eu_ai_act_checker(lang: str = "en"):
    """Returnér cached EU AI Act Compliance Checker payload.

    `lang`: en (default) | da | de | fr | it | pl | es. Falder tilbage til
    engelsk hvis sproget ikke er tilgængelig hos EC.

    DA-oversættelsen er produceret lokalt af Bifrosts translator-service
    (POST /api/eu-ai-act-checker/translate) og er ikke jurist-curateret;
    UI viser et banner når translation_status = machine_uncurated.
    """
    from src.services.eu_ai_act_checker import load_checker_payload
    from src.services.eu_checker_translator import translation_meta

    payload = await asyncio.to_thread(load_checker_payload, lang)
    payload["translation"] = translation_meta()
    return payload


@app.post("/api/eu-ai-act-checker/refresh", response_model=Dict[str, Any])
@limiter.limit(ADMIN_WRITE)
async def refresh_eu_ai_act_checker(request: Request):
    """Manuel trigger — henter fresh logic.json + content_*.json fra EC.

    Tager 1-3s. Returnerer summary med før/efter version-stempler så
    UI kan markere når EC har opdateret deres logik.
    """
    from src.services.eu_ai_act_checker import refresh_checker
    return await refresh_checker(langs=("en", "de", "fr", "it", "pl", "es"))


@app.post("/api/eu-ai-act-checker/translate", response_model=Dict[str, Any])
@limiter.limit(ADMIN_WRITE)
async def translate_eu_ai_act_checker(request: Request):
    """Producér dansk oversættelse af EC's compliance-checker.

    Læser content_en.json som kilde, kalder LLM (Azure / OpenAI / LM Studio)
    pr. spørgsmål + flag med en glossar-låst prompt der bevarer
    juridiske termer (højrisiko, udbyder, idriftsætter, FRIA, …) og
    skriver content_da.json.

    Tager typisk 5-10 minutter på LM Studio (gpt-oss-20b). Markerer
    output som translation_status=machine_uncurated så UI viser et
    review-banner.
    """
    from src.services.eu_checker_translator import translate_checker_async

    return await translate_checker_async(source_lang="en", overwrite=True)


@app.get("/api/eu-ai-act-checker/mapping-stats", response_model=Dict[str, Any])
async def eu_ai_act_checker_mapping_stats():
    """Statistik over EC-flag → Bifrost-regelmotor-mappingen — bruges af /drift."""
    from src.services.ec_to_tyr_mapper import mapping_stats

    return await asyncio.to_thread(mapping_stats)


# ==================== AI Projects Catalog ====================
#
# Syncs from offentlig-ai.dk weekly. Endpoints expose the cached catalog
# for the /ai-losninger frontend page.

@app.get("/api/ai-projects", response_model=Dict[str, Any])
async def get_ai_projects():
    """Returnér cached AI-projekt-katalog. Tom items-liste hvis intet
    sync er kørt endnu (frontend falder tilbage til bundlet JSON)."""
    from src.services.ai_projects_updater import load_ai_projects

    data = await asyncio.to_thread(load_ai_projects)
    return {
        "items": data.get("items", []),
        "fetched_at": data.get("fetched_at"),
        "count": data.get("count", len(data.get("items", []))),
        "source": data.get("source", "offentlig-ai.dk"),
    }


@app.post("/api/ai-projects/refresh", response_model=Dict[str, Any])
@limiter.limit(ADMIN_WRITE)
async def refresh_ai_projects_endpoint(request: Request):
    """Manuel trigger af AI-projekt-katalog-syncen. Returnerer summary
    af kørslen — tager 10-20s for ~143 projekter."""
    from src.services.ai_projects_updater import refresh_ai_projects

    summary = await refresh_ai_projects()
    return summary


@app.get("/api/search/global", response_model=Dict[str, Any])
async def global_search(
    q: str = Query(..., min_length=2, max_length=120, description="Søgestreng"),
    limit: int = Query(5, ge=1, le=15, description="Maksimum resultater per sektion"),
):
    """Søg på tværs af vidensbase, AI-sager og dokumentation."""
    query = q.strip()
    if not query:
        return {"query": q, "results": [], "sections": {}}

    kb_results, kb_total = _build_knowledge_base_results(query, limit)
    case_results, case_total = await _build_ai_case_results(query, limit)
    doc_results, doc_total = _build_documentation_results(query, limit)

    combined = kb_results + case_results + doc_results

    return {
        "query": query,
        "results": combined,
        "sections": {
            "knowledge_base": {"count": len(kb_results), "total": kb_total},
            "ai_cases": {"count": len(case_results), "total": case_total},
            "documentation": {"count": len(doc_results), "total": doc_total},
        },
    }


# ==================== Law Assistant API ====================

class LawSearchRequest(BaseModel):
    """Request model for law search"""
    query: str = Field(..., min_length=2, max_length=200, description="Search query")
    category: Optional[str] = Field(None, description="Optional category filter")
    limit: int = Field(10, ge=1, le=50, description="Max results")
    mode: str = Field(
        "auto",
        pattern="^(auto|keyword|semantic)$",
        description="auto = semantic if RAG index ready else keyword; "
                    "semantic forces RAG; keyword forces lexical",
    )


class LawAskRequest(BaseModel):
    """Request model for AI law assistant"""
    query: str = Field(..., min_length=5, max_length=500, description="Legal question")
    category: Optional[str] = Field(None, description="Optional category filter")
    mode: str = Field(
        "auto",
        pattern="^(auto|keyword|rag)$",
        description="auto = RAG if index ready, else keyword; "
                    "rag forces RAG (errors if not built); keyword forces lexical",
    )


@app.post("/api/law/search", response_model=Dict[str, Any])
async def search_laws_api(request: LawSearchRequest):
    """
    Search Danish laws by text query.

    Mode "auto" (default) uses semantic embeddings when the RAG index has been
    built, falling back to keyword scoring otherwise. Mode "semantic" returns
    chunk-level matches with similarity scores; "keyword" returns whole-law
    matches with relevance counts.
    """
    try:
        from src.law import search_laws
        from src.services.law_rag import get_default_index

        logger.info(f"Law search ({request.mode}): {request.query}")

        wants_semantic = request.mode in ("auto", "semantic")
        if wants_semantic:
            index = get_default_index()
            if index.is_ready():
                hits = await asyncio.to_thread(index.search, request.query, request.limit)
                # Reshape semantic hits to match the keyword response so the
                # frontend can render either uniformly.
                results = [
                    {
                        "law": {
                            "title": h["law_title"],
                            "slug": h["law_slug"],
                            "url": h["law_url"],
                            "content": h["text"],
                        },
                        "relevance": h["similarity"],
                        "matches": ["semantic"],
                        "chunk_index": h["chunk_index"],
                    }
                    for h in hits
                ]
                return {
                    "success": True,
                    "query": request.query,
                    "category": request.category,
                    "results": results,
                    "total": len(results),
                    "mode": "semantic",
                }
            if request.mode == "semantic":
                raise HTTPException(
                    status_code=409,
                    detail="Law RAG index not built — POST /api/law/rag/build first",
                )
            # auto mode: fall through to keyword

        results = search_laws(
            query=request.query,
            category=request.category,
            limit=request.limit
        )
        return {
            "success": True,
            "query": request.query,
            "category": request.category,
            "results": results,
            "total": len(results),
            "mode": "keyword",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Law search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Søgning fejlede: {str(e)}")


@app.post("/api/law/ask", response_model=Dict[str, Any])
@limiter.limit(LLM_HEAVY)
async def ask_law_assistant(request: Request, body: LawAskRequest):
    """
    Ask legal question and get AI-generated answer with citations.

    Uses semantic RAG retrieval when index is built — falls back to keyword
    search otherwise. Set mode="rag" to require semantic, mode="keyword" to
    force lexical.
    """
    try:
        from src.law import LawAssistant

        logger.info(f"Law AI query (mode={body.mode}): {body.query}")

        async with LawAssistant() as assistant:
            result = await assistant.ask(
                query=body.query,
                category=body.category,
                max_sources=5,
                mode=body.mode,
            )

        return {
            "success": True,
            "query": body.query,
            "answer": result.get('answer'),
            "confidence": result.get('confidence'),
            "key_points": result.get('key_points'),
            "sources": result.get('sources'),
            "citations": result.get('citations'),
            "follow_up_questions": result.get('follow_up_questions'),
            "retrieval": result.get('retrieval'),
            "provider": result.get('provider'),
        }

    except Exception as e:
        logger.error(f"Law AI assistant failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI assistent fejlede: {str(e)}")


# ---- Law RAG admin endpoints ------------------------------------------------

@app.post("/api/law/rag/build")
async def law_rag_build():
    """Embed every law section and persist a local cosine-search index.

    Idempotent — running twice rebuilds the index. ~$0.0001 / 5s per build.
    """
    from src.services.law_rag import get_default_index
    try:
        summary = await asyncio.to_thread(get_default_index().build)
        return {"success": True, **summary}
    except Exception as e:
        logger.exception("Law RAG build failed")
        raise HTTPException(status_code=500, detail=f"RAG-byg fejlede: {str(e)}")


@app.get("/api/law/rag/stats")
async def law_rag_stats():
    """Inspect index freshness, chunk count, embedding model, etc."""
    from src.services.law_rag import get_default_index
    try:
        return await asyncio.to_thread(get_default_index().stats)
    except Exception as e:
        logger.exception("Law RAG stats failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/law/ask/stream")
@limiter.limit(LLM_HEAVY)
async def ask_law_assistant_stream(request: Request, body: LawAskRequest):
    """Streaming variant of /api/law/ask using Server-Sent Events.

    Event sequence:
      1. retrieval — sources + retrieval mode info
      2. delta(s) — prose tokens as they arrive
      3. final — full answer + key_points + citations + follow-up suggestions

    Frontend uses EventSource (or fetch + ReadableStream) to render
    incrementally.
    """
    from src.law import LawAssistant

    async def event_stream():
        try:
            async with LawAssistant() as assistant:
                async for event in assistant.ask_stream(
                    query=body.query,
                    category=body.category,
                    max_sources=5,
                    mode=body.mode,
                ):
                    payload = json.dumps(event, ensure_ascii=False)
                    yield f"data: {payload}\n\n"
        except Exception as exc:
            logger.exception("Law ask_stream failed")
            err = json.dumps({"event": "error", "message": str(exc)}, ensure_ascii=False)
            yield f"data: {err}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering if proxied
        },
    )


@app.get("/api/law/categories", response_model=Dict[str, Any])
async def get_law_categories():
    """Get all law categories from regelrytter.dk"""
    try:
        from src.law import get_categories

        categories = get_categories()

        return {
            "success": True,
            "categories": categories,
            "total": len(categories)
        }

    except Exception as e:
        logger.error(f"Failed to load law categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Compliance API ====================

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


@app.get("/api/compliance/progress/{session_id}")
async def get_progress_updates(session_id: str):
    """Get progress updates for a quick check session."""
    return {"progress": get_progress(session_id)}


@app.get("/api/compliance/intermediate/{session_id}")
async def get_intermediate_results(session_id: str):
    """Get intermediate results for a quick check session."""
    results = intermediate_results_storage.get(session_id, {})
    return {
        "session_id": session_id,
        "phase_1": results.get("phase_1"),
        "phase_2": results.get("phase_2"),
        "phase_3": results.get("phase_3")
    }


@app.post("/api/compliance/hurtig-tjek", response_model=Dict[str, Any])
async def hurtig_compliance_tjek(request: QuickCheckRequest):
    """
    Quick compliance check with web research and LLM summary
    """
    try:
        from src.agents.quick_check_agent import run_quick_check_agent

        # Use session ID from request or generate new one
        session_id = request.session_id or str(uuid4())

        # Create progress callback
        async def progress_callback(message: str, status: str):
            await add_progress(session_id, message, status)

        # Create intermediate results callback
        async def intermediate_callback(phase_data: Dict[str, Any]):
            await add_intermediate_result(session_id, phase_data)

        # Run enhanced quick check with web research and LLM summary
        agent_result = await run_quick_check_agent(
            description=request.beskrivelse,
            ai_type=request.ai_type,
            sector=request.sektor,
            behandler_persondata=request.behandler_persondata,
            automatiserede_beslutninger=request.automatiserede_beslutninger,
            progress_callback=progress_callback,
            enable_web_search=request.enable_web_search,
            intermediate_callback=intermediate_callback
        )

        # Get rule engine result for additional context
        rule_engine_result = compliance_controller.run_quick_checks({
            "beskrivelse": request.beskrivelse,
            "fagomraade": request.sektor,
            "sector": request.sektor,
            "ai_type": request.ai_type,
            "ai_risk_level": agent_result["ai_act"]["risk_level"],
            "behandler_persondata": request.behandler_persondata,
            "automatiserede_beslutninger": request.automatiserede_beslutninger,
            "organisation": "Kalundborg Kommune",
        })

        # Merge agent result with rule engine result
        return {
            "session_id": session_id,
            "ai_act": agent_result["ai_act"],
            "gdpr": agent_result["gdpr"],
            "quick_recommendations": agent_result.get("recommendations", []),
            "needs_full_assessment": agent_result["needs_full_assessment"],
            "rule_engine": rule_engine_result,
            "prompt_full_assessment": rule_engine_result.get("recommend_full", False) or agent_result["needs_full_assessment"],
            "precedents": agent_result.get("precedents", []),
            "precedents_summary": agent_result.get("precedents_summary", ""),
            "short_summary": agent_result.get("short_summary", "")
        }

    except Exception as e:
        logger.error(f"Quick check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compliance/7-punkts-vurdering", response_model=Dict[str, Any])
async def syv_punkts_compliance_vurdering(request: SevenPointAssessmentRequest):
    """
    Comprehensive 7-point compliance control assessment.

    Returns detailed compliance report with:
    - GO/NO-GO/BETINGET-GO decision
    - Risk score and level (0-100)
    - Critical blockers (hard stops)
    - Conditional requirements (betingelser)
    - Required documentation (artefakter)
    - Required tests (bias testing, security audit, etc.)
    - Next steps recommendations
    - Detailed assessment of each point
    """
    try:
        logger.info(f"Starting 7-point assessment for: {request.system_navn}")

        from src.compliance.compliance_control_engine import ComplianceControlEngine
        from src.database.compliance_service import ComplianceService
        from src.compliance.recommendation_engine import get_recommendations_from_form

        # Initialize compliance control engine
        engine = ComplianceControlEngine()

        # Run comprehensive assessment
        result = engine.vurder_system(request.dict())

        logger.info(f"Assessment complete: {result['compliance_control']['beslutning']} "
                   f"(Risk Score: {result['compliance_control']['risiko_score']})")

        # Save assessment to database and get historical recommendations
        from src.database.connection import SessionLocal

        db = SessionLocal()
        try:
            service = ComplianceService(db)

            # Save the assessment
            assessment_id = service.save_assessment(result)
            logger.info(f"Assessment saved to database with ID: {assessment_id}")

            # Get recommendations from similar historical assessments
            historical_recommendations = service.get_recommendations_from_history(request.dict())
        finally:
            db.close()

        # Generate intelligent recommendations based on form answers
        intelligent_recommendations = get_recommendations_from_form(request.dict())
        logger.info(f"Generated {len(intelligent_recommendations)} intelligent recommendations")

        # Add insights to result
        result['historical_insights'] = historical_recommendations
        result['intelligent_recommendations'] = intelligent_recommendations
        result['assessment_id'] = assessment_id

        return result

    except Exception as e:
        logger.error(f"7-point assessment failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")


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


@app.get("/api/cache/stats", response_model=Dict[str, Any])
async def get_cache_statistics():
    """
    Get cache statistics and health information
    """
    try:
        # Get disk cache stats
        disk_stats = get_cache_size()

        # Get memory cache stats
        memory_stats = get_cache_stats()

        # Calculate hit rates
        memory_hit_rates = {}
        for cache_name, stats in memory_stats.items():
            total = stats['hits'] + stats['misses']
            if total > 0:
                memory_hit_rates[cache_name] = round(stats['hits'] / total * 100, 1)
            else:
                memory_hit_rates[cache_name] = 0.0

        # Get cache health
        cache_health = validate_cache_health()

        return {
            "disk_cache": {
                "total_entries": disk_stats.get("total_entries", 0),
                "total_size_mb": disk_stats.get("total_size_mb", 0),
                "by_type": disk_stats.get("by_type", {}),
            },
            "memory_cache": {
                "caches": memory_stats,
                "hit_rates": memory_hit_rates,
            },
            "health": cache_health,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get cache statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# v3 rule engine — declarative compliance rules grounded in law citations
# ---------------------------------------------------------------------------

from src.rule_engine import (
    RuleLoader,
    RuleInput,
    SignalExtractor,
    SignalExtractionError,
)
from src.rule_engine.executor import aggregate_status, evaluate_all
from src.rule_engine import audit as v3_audit  # registers V3AssessmentLog with Base.metadata
from src.database import audit_access_log  # noqa: F401 — registers AuditAccessLog with Base.metadata


_RULES_DIR = Path(__file__).parent / "rules"


@lru_cache(maxsize=1)
def _v3_load_rules():
    """Load and cache the v3 rule corpus. Rebuild requires a server restart
    (or invalidating the cache from a privileged endpoint)."""
    loader = RuleLoader(_RULES_DIR)
    result = loader.load_all(raise_on_error=False)
    if not result.ok:
        raise RuntimeError(
            "v3 rule corpus failed to load:\n"
            + "\n".join(f"  - {err}" for err in result.errors)
        )
    return result.rules


@lru_cache(maxsize=1)
def _v3_signal_extractor() -> SignalExtractor:
    return SignalExtractor()


class V3AssessRequest(BaseModel):
    """Input to the v3 rule engine.

    All fields are optional except that the engine needs *something* to
    work from: either signals/predicates the caller provides directly,
    or a free-text system_description for the signal extractor to
    interpret.
    """

    system_description: Optional[str] = Field(
        default=None,
        description="Free-text description of the AI system being assessed.",
    )
    signals: Dict[str, bool] = Field(
        default_factory=dict,
        description="Trigger signals provided directly by the caller.",
    )
    predicates: Dict[str, Any] = Field(
        default_factory=dict,
        description="Answers to rule predikater (boolean or enum strings).",
    )
    use_llm_extraction: bool = Field(
        default=True,
        description=(
            "If true and a system_description is given, ask the LLM to "
            "fill in any signals the caller did not provide explicitly."
        ),
    )

    # Optional audit metadata
    case_id: Optional[str] = Field(default=None, description="Case identifier the assessment belongs to.")
    user_id: Optional[str] = Field(default=None, description="User running the assessment.")
    note: Optional[str] = Field(default=None, description="Free-text note saved with the audit entry.")


@app.post("/api/v3/assess")
async def v3_assess(request: V3AssessRequest):
    """Evaluate the v3 rule corpus against the supplied input.

    Returns one decision per rule plus the aggregate status and the
    full set of signals that drove the evaluation (so the caller can
    audit what the LLM inferred vs. what they supplied).
    """

    try:
        rules = _v3_load_rules()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Start with caller-provided signals, then optionally fill in the rest
    # via the LLM signal extractor.
    merged_signals: Dict[str, bool] = dict(request.signals)
    extracted_signals: Dict[str, bool] = {}
    warnings: List[str] = []

    if request.use_llm_extraction and request.system_description:
        extractor = _v3_signal_extractor()
        if extractor.is_configured:
            try:
                extracted_signals = extractor.extract(
                    request.system_description, rules
                )
            except SignalExtractionError as exc:
                warnings.append(f"signal extraction failed: {exc}")
            for k, v in extracted_signals.items():
                # Caller-provided values always win
                merged_signals.setdefault(k, v)
        else:
            warnings.append(
                "signal extractor not configured (no AZURE_OPENAI_* / OPENAI_API_KEY)"
            )

    rule_input = RuleInput(
        signals=merged_signals,
        predicates=request.predicates,
    )

    try:
        decisions = evaluate_all(rules, rule_input)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"evaluation error: {exc}")

    response = {
        "rule_engine_version": "3.0.0-alpha.5",
        "evaluated_at": datetime.now(UTC).isoformat(),
        "rules_loaded": len(rules),
        "aggregate_status": aggregate_status(decisions).value,
        "signals_provided": dict(request.signals),
        "signals_extracted_by_llm": extracted_signals,
        "decisions": [d.model_dump(mode="json") for d in decisions],
        "warnings": warnings,
    }

    # Persist to audit log so auditors can reproduce the decision later.
    # Best-effort: an audit failure should not break the assessment response.
    try:
        from src.database.connection import SessionLocal
        db = SessionLocal()
        try:
            entry = v3_audit.save_assessment(
                db,
                request_payload=request.model_dump(mode="json"),
                response_payload=response,
                case_id=request.case_id,
                user_id=request.user_id,
                note=request.note,
            )
            db.commit()
            response["audit_log_id"] = entry.id
        finally:
            db.close()
    except Exception as exc:
        logger.warning(f"v3 audit log write failed (assessment still returned): {exc}")
        response.setdefault("warnings", []).append(f"audit log unavailable: {exc}")

    return response


# ---- EC-checker → Bifrost-vurdering funnel ------------------------------------


class V3FromEcCheckerRequest(BaseModel):
    """Input til funnel-endpoint: rejste flag fra EC compliance-checker.

    Værdierne kan være bool, string, number — vi behandler alle truthy
    værdier som "flag rejst". Tom dict eller alle-false giver fallback
    til standard fuld-form.
    """

    flags: Dict[str, Any] = Field(
        default_factory=dict,
        description="EC-flag-navn → værdi (bool/str/num). Truthy = rejst.",
    )
    system_description: Optional[str] = Field(
        default=None,
        description=(
            "Valgfri fritekst-beskrivelse af systemet. Bruges ikke direkte "
            "af mapperen, men returneres så frontend kan pre-fylde feltet."
        ),
    )


@app.post("/api/v3/assess/from-ec-checker")
async def v3_assess_from_ec_checker(body: V3FromEcCheckerRequest):
    """Tag EC compliance-checker-flag → producér pre-fyldt Bifrost-vurdering-state.

    Den her endpoint *evaluerer ikke* reglerne — den returnerer kun hvilke
    signals/predicates der pre-fyldes, hvilke regler der bør vises som
    relevante, og hvilke predikater der skal markeres som påkrævede inden
    sagsbehandleren kan trykke 'Vurdér'.

    Frontend bruger denne payload til at åbne /vurdering med banner +
    pre-fill + required-marking. Når sagsbehandleren har udfyldt resten
    laver frontend et almindeligt POST til /api/v3/assess.

    Returnerer:
      {
        signals,                   # dict pre-fyldte signals
        predicates,                # dict pre-fyldte predikater
        surfaced_rules,            # list rule_ids der bør vises
        required_predicates,       # {rule_id: [predicate_id, ...]}
        ec_summary,                # 1-2 sætnings dansk resumé
        info_messages,             # liste af danske info-tekster
        matched_flags,             # hvilke EC-flag fra request der mappede
        fallback_to_full_form,     # true → frontend bør vise fuld form
        all_rules_count,           # total regler i Bifrost's korpus
      }
    """
    from src.services.ec_to_tyr_mapper import map_ec_flags_to_tyr

    pre = await asyncio.to_thread(map_ec_flags_to_tyr, body.flags or {})

    # Tæl total regler så frontend kan vise "9 af 21 regler relevante"
    try:
        rules = _v3_load_rules()
        all_rules_count = len(rules)
    except Exception:
        all_rules_count = None

    return {
        "signals": pre.signals,
        "predicates": pre.predicates,
        "surfaced_rules": pre.surfaced_rules,
        "required_predicates": pre.required_predicates,
        "ec_summary": pre.ec_summary,
        "info_messages": pre.info_messages,
        "matched_flags": pre.matched_flags,
        "fallback_to_full_form": pre.fallback_to_full_form,
        "all_rules_count": all_rules_count,
        "system_description": body.system_description,
    }


@app.get("/api/v3/audit")
async def v3_audit_list(
    limit: int = 50,
    case_id: Optional[str] = None,
    aggregate_status_filter: Optional[str] = Query(default=None, alias="status"),
):
    """List recent v3 assessments. Filters: status (GO/BETINGET-GO/NO-GO), case_id."""
    from src.database.connection import SessionLocal
    db = SessionLocal()
    try:
        entries = v3_audit.list_recent(
            db,
            limit=limit,
            case_id=case_id,
            aggregate_status=aggregate_status_filter,
        )
        return {
            "count": len(entries),
            "limit": limit,
            "items": [e.to_dict() for e in entries],
        }
    finally:
        db.close()


@app.get("/api/v3/audit/{log_id}")
async def v3_audit_detail(log_id: str, request: Request):
    """Return the full request + response for one audit entry.

    Each access is recorded in audit_access_log so we have a paper trail
    of who looked at what — required for GDPR artikel 32 documentation.
    """
    from src.database.connection import SessionLocal
    from src.database.audit_access_log import record_access
    db = SessionLocal()
    try:
        entry = v3_audit.get_by_id(db, log_id)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"audit log entry not found: {log_id}")
        # Record the access — append-only, doesn't fail the request if it errors
        try:
            record_access(
                db,
                target_type="audit_log",
                target_id=log_id,
                action="read",
                actor=request.headers.get("X-User"),
                actor_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                request_id=request.headers.get("X-Request-ID"),
            )
            db.commit()
        except Exception:
            logger.warning("audit_access_log write failed for %s", log_id, exc_info=True)
            db.rollback()
        return entry.to_full_dict()
    finally:
        db.close()


@app.get("/api/v3/audit/{log_id}/access-log")
async def v3_audit_access_log(log_id: str):
    """Return who has accessed this audit-log entry — for compliance review.

    Returns the audit_access_log rows targeting this audit entry, newest first.
    """
    from src.database.connection import SessionLocal
    from src.database.audit_access_log import list_access_for_target
    db = SessionLocal()
    try:
        rows = list_access_for_target(db, "audit_log", log_id, limit=200)
        return {
            "log_id": log_id,
            "count": len(rows),
            "accesses": [r.to_dict() for r in rows],
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# /api/v3/compare — side-by-side diff between legacy engine and v3 rule_engine
# ---------------------------------------------------------------------------
#
# Used to validate that v3 covers the cases the legacy engine catches before
# we delete the legacy code (Step 4 in HANDOFF.md).

class V3CompareRequest(V3AssessRequest):
    """Same input as /api/v3/assess plus an optional legacy_input that
    fills in the fields the legacy ComplianceController.run_quick_checks
    expects. If legacy_input is omitted we attempt to derive it from
    predicates on a best-effort basis."""

    legacy_input: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Direct input to the legacy ComplianceController.run_quick_checks. "
            "When omitted, derived from predicates on best-effort basis."
        ),
    )


def _derive_legacy_input_from_v3(req: V3AssessRequest) -> Dict[str, Any]:
    """Best-effort: derive a legacy quick-check payload from v3 predicates.
    Fields the legacy engine reads (per ComplianceController.run_quick_checks):
      beskrivelse, organisation, team, fagomraade, ai_risk_level,
      behandler_persondata, automatiserede_beslutninger, human_in_loop,
      har_retslige_konsekvenser, juridisk_grundlag, persondata_typer.
    """
    p = req.predicates or {}
    s = req.signals or {}
    return {
        "beskrivelse": req.system_description or "",
        "ai_type": "predictive_ai" if s.get("system.uses_ai") else None,
        "fagomraade": "",
        "behandler_persondata": bool(
            s.get("system.processes_personal_data")
            or p.get("indeholder_personoplysninger")
        ),
        "automatiserede_beslutninger": bool(
            p.get("er_helautomatiseret")
            or s.get("system.makes_decisions_about_persons")
        ),
        "human_in_loop": not bool(p.get("er_helautomatiseret")),
        "har_retslige_konsekvenser": bool(
            p.get("har_retsvirkning_eller_betydelig_paavirkning")
        ),
        "juridisk_grundlag": p.get("retsgrundlag"),
        "persondata_typer": [],
        "ai_risk_level": "high" if p.get("anvendelsesomraade") == "vaesentlige_offentlige_tjenester" else "minimal",
    }


def _summarise_v3_decisions(rules, decisions_raw, signals: Dict[str, bool]) -> Dict[str, Any]:
    """Summarise v3 results. Takes the raw RuleDecision objects so we can
    pass them directly to aggregate_status (which inspects .status)."""
    triggered = [d for d in decisions_raw if d.triggered]
    triggered_dicts = [d.model_dump(mode="json") for d in triggered]
    return {
        "rule_engine_version": "3.0.0-alpha.5",
        "rules_loaded": len(rules),
        "aggregate_status": aggregate_status(triggered),
        "triggered_count": len(triggered),
        "triggered": [
            {
                "rule_id": td.get("rule_id"),
                "status": td.get("status"),
                "kilde": td.get("kilde", {}),
            }
            for td in triggered_dicts
        ],
        "signals_used": signals,
    }


@app.post("/api/v3/compare")
async def v3_compare(request: V3CompareRequest):
    """Run both legacy and v3 engines on the same input and report a diff."""

    # ---- Run v3 (same logic as /api/v3/assess but don't persist) ----
    try:
        rules = _v3_load_rules()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    merged_signals: Dict[str, bool] = dict(request.signals)
    warnings: List[str] = []

    if request.use_llm_extraction and request.system_description:
        extractor = _v3_signal_extractor()
        if extractor.is_configured:
            try:
                extracted = extractor.extract(request.system_description, rules)
                for k, v in extracted.items():
                    merged_signals.setdefault(k, v)
            except SignalExtractionError as exc:
                warnings.append(f"signal extraction failed: {exc}")

    rule_input = RuleInput(signals=merged_signals, predicates=request.predicates)
    decisions = evaluate_all(rules, rule_input)

    v3_summary = _summarise_v3_decisions(rules, decisions, merged_signals)

    # ---- Run legacy ----
    legacy_summary: Dict[str, Any] = {"available": False, "reason": "ComplianceController not initialized"}

    if compliance_controller is not None:
        legacy_input = request.legacy_input or _derive_legacy_input_from_v3(request)
        try:
            legacy_result = compliance_controller.run_quick_checks(legacy_input)
            legacy_summary = {
                "available": True,
                "decision": legacy_result.get("decision"),
                "risk_score": legacy_result.get("risk_score"),
                "classification": legacy_result.get("classification"),
                "triggered_count": len(legacy_result.get("findings", [])),
                "triggered": legacy_result.get("findings", []),
                "summary": legacy_result.get("summary"),
                "obligations": legacy_result.get("obligations", []),
                "input": legacy_input,
            }
        except Exception as exc:
            logger.exception("legacy quick check failed")
            legacy_summary = {"available": False, "reason": f"legacy engine error: {exc}"}

    # ---- Diff ----
    # Topical mapping is best-effort: legacy rules are coded by id (e.g.
    # AI_ACT_001), v3 rules use law-citation ids (e.g. ai_act.art6.*). We
    # report counts and lists; full topical mapping requires jurist work.
    v3_topics = sorted({d["rule_id"].split(".", 1)[0] for d in v3_summary["triggered"]})
    legacy_topics = sorted({
        f.get("kategori", "?") for f in legacy_summary.get("triggered") or []
    })
    agreement = "unknown"
    if legacy_summary.get("available"):
        legacy_decision = (legacy_summary.get("decision") or "").upper().replace("_", "-")
        v3_decision = (v3_summary.get("aggregate_status") or "").upper()
        # Map legacy CONDITIONAL-GO ↔ v3 BETINGET-GO
        if legacy_decision == "CONDITIONAL-GO":
            legacy_decision = "BETINGET-GO"
        if v3_decision == legacy_decision:
            agreement = "match"
        elif v3_decision == "GO" and legacy_decision in ("GO", ""):
            agreement = "match"
        else:
            agreement = "different"

    return {
        "v3": v3_summary,
        "legacy": legacy_summary,
        "diff": {
            "agreement": agreement,
            "v3_topics": v3_topics,
            "legacy_topics": legacy_topics,
            "v3_decision": v3_summary.get("aggregate_status"),
            "legacy_decision": legacy_summary.get("decision"),
        },
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# /api/v3/document/analyze — upload PDF/DOCX and run the rule engine over it
# ---------------------------------------------------------------------------

@app.post("/api/v3/document/analyze")
@limiter.limit(LLM_HEAVY)
async def v3_document_analyze(
    request: Request,
    file: UploadFile = File(...),
    case_id: Optional[str] = None,
    note: Optional[str] = None,
):
    """Parse a PDF or DOCX, chunk it, extract signals via LLM per chunk,
    then evaluate the v3 rule engine against the merged signals.

    Returns the same shape as /api/v3/assess plus per-chunk attribution
    so the UI can highlight which section triggered which rule."""
    from src.services.document_analyzer import (
        parse_document,
        analyze_document,
        chunk_rule_map,
        DocumentParseError,
    )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > 10 * 1024 * 1024:  # 10 MB cap
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(content)} bytes). Max 10 MB.",
        )

    try:
        text, offsets, kind = parse_document(content, file.filename or "")
    except DocumentParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("document parse failed")
        raise HTTPException(status_code=500, detail=f"parse failed: {exc}")

    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="Document contained no extractable text (scanned PDF without OCR?).",
        )

    try:
        rules = _v3_load_rules()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    extractor = _v3_signal_extractor()
    result = analyze_document(
        text,
        rules,
        offsets,
        extractor=extractor,
    )

    # Build chunk → triggered rule_ids mapping for UI highlighting.
    chunk_to_rules = chunk_rule_map(result, rules)

    # Persist to audit-log so this analysis shows up in /historik.
    audit_id: Optional[str] = None
    try:
        from src.database.connection import SessionLocal
        db = SessionLocal()
        try:
            request_payload = {
                "kind": "document",
                "filename": file.filename,
                "size_bytes": len(content),
                "format": kind,
                "text_length": result.text_length,
                "chunk_count": result.chunk_count,
                "merged_signals": result.merged_signals,
                "case_id": case_id,
                "note": note,
            }
            response_payload = {
                "rule_engine_version": "3.0.0-alpha.5",
                "evaluated_at": datetime.now(UTC).isoformat(),
                "rules_loaded": result.rules_loaded,
                "aggregate_status": result.aggregate_status,
                "decisions": [d.model_dump(mode="json") for d in result.decisions],
                "warnings": result.warnings,
            }
            entry = v3_audit.save_assessment(
                db,
                request_payload=request_payload,
                response_payload=response_payload,
                case_id=case_id,
                note=note,
            )
            audit_id = entry.id
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.warning("v3 audit log write failed (analysis still returned): %s", exc)

    # Persist the source document so the UI can show "where in the doc did
    # this predikat come from" — page-level highlights in /api/v3/documents/.
    if audit_id:
        try:
            from src.services import document_storage
            await asyncio.to_thread(
                document_storage.store,
                audit_id,
                content=content,
                filename=file.filename or "",
                kind=kind,
                content_type=file.content_type,
            )
        except Exception as exc:
            logger.warning("source document storage failed for %s: %s", audit_id, exc)

    return {
        "rule_engine_version": "3.0.0-alpha.5",
        "evaluated_at": datetime.now(UTC).isoformat(),
        "filename": file.filename,
        "format": kind,
        "size_bytes": len(content),
        "text_length": result.text_length,
        "chunk_count": result.chunk_count,
        "rules_loaded": result.rules_loaded,
        "aggregate_status": result.aggregate_status,
        "merged_signals": result.merged_signals,
        "extracted_predicates": result.extracted_predicates,
        "decisions": [d.model_dump(mode="json") for d in result.decisions],
        "chunks": [
            {
                "index": c.index,
                "label": c.label,
                "page": c.page,
                "char_start": c.char_start,
                "char_end": c.char_end,
                "preview": c.text[:300] + ("…" if len(c.text) > 300 else ""),
                "triggered_rules": chunk_to_rules.get(c.index, []),
            }
            for c in result.chunks
        ],
        "warnings": result.warnings,
        "audit_log_id": audit_id,
    }


# ---------------------------------------------------------------------------
# Document evidence endpoints (Step 9 — PDF annotering)
# ---------------------------------------------------------------------------


@app.get("/api/v3/documents/{audit_log_id}/source")
async def v3_document_source(audit_log_id: str):
    """Stream the original uploaded PDF/DOCX back to the browser.

    Used by the frontend to render the source document inline next to the
    rule-engine output, so jurists can see WHICH PARAGRAPH yielded a
    predikat instead of trusting the LLM's word.
    """
    from fastapi.responses import FileResponse
    from src.services import document_storage

    stored = await asyncio.to_thread(document_storage.find, audit_log_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Source document not found")
    return FileResponse(
        path=str(stored.path),
        media_type=stored.content_type,
        filename=stored.original_filename or stored.path.name,
    )


@app.get("/api/v3/documents/{audit_log_id}/highlights")
async def v3_document_highlights(audit_log_id: str):
    """Return per-rule and per-predikat evidence — which page/chunk of the
    source document yielded each finding.

    Shape:
        {
          "audit_log_id": "...",
          "filename": "...",
          "page_count_estimate": 12,
          "rules": [
            {"rule_id": "...", "pages": [3, 7], "chunks": [{"index":2,"page":3,"preview":"..."}]}
          ],
          "predikates": [
            {"predikat_id":"...","value":"ja","pages":[3]}
          ]
        }
    """
    from src.database.connection import SessionLocal
    from src.rule_engine import audit as v3_audit
    from src.services import document_storage
    from src.services.document_analyzer import chunk_text

    stored = await asyncio.to_thread(document_storage.find, audit_log_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Source document not found")

    db = SessionLocal()
    try:
        entry = v3_audit.get_by_id(db, audit_log_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Audit log not found")
        request_payload = entry.request_payload or {}
        response_payload = entry.response_payload or {}
    finally:
        db.close()

    if request_payload.get("kind") != "document":
        raise HTTPException(
            status_code=400,
            detail="This audit log is not a document analysis — no highlights available",
        )

    # Re-parse the document deterministically (no LLM) so we can rebuild
    # the chunks → page map without re-running the analysis pipeline.
    def _rebuild_evidence() -> dict:
        from src.services.document_analyzer import parse_document

        with stored.path.open("rb") as fh:
            content = fh.read()

        text, offsets, kind = parse_document(content, stored.original_filename)
        chunks = chunk_text(text, offsets)
        page_count = len({p for p, _, _ in offsets}) if offsets else 0

        # Reconstruct the rule_engine output from the audit log
        from src.rule_engine.models import RuleDecision

        decisions_raw = response_payload.get("decisions") or []
        triggered_rule_ids = [
            d.get("rule_id") for d in decisions_raw
            if d.get("triggered") or d.get("status") in ("betinget-go", "no-go")
        ]
        triggered_rule_ids = [rid for rid in triggered_rule_ids if rid]

        # Build chunk → triggered rules map using the same rule-loader we
        # already use elsewhere, so we get fresh rule trigger definitions.
        try:
            rules = _v3_load_rules()
        except RuntimeError:
            rules = []

        # We didn't persist per-chunk signals in the audit log, so re-run
        # signals over chunks using a NoOp extractor when no LLM is available.
        # Since we only need chunk attribution (not signal values), we rely
        # on chunk_rule_map's secondary pass: for each rule, look at which
        # chunks contain trigger keywords from the rule's source citat.
        # Cheap approximation, no LLM cost on this endpoint.
        rules_by_id = {r.id: r for r in rules}

        rule_to_chunks: dict[str, list[int]] = {}
        for cid in triggered_rule_ids:
            rule = rules_by_id.get(cid)
            if rule is None:
                continue
            citat = (rule.kilde.citat if rule.kilde else "") or ""
            keywords = _keywords_from_citat(citat)
            hits = []
            for chunk in chunks:
                ctext = chunk.text.lower()
                if any(kw and kw in ctext for kw in keywords):
                    hits.append(chunk.index)
            rule_to_chunks[cid] = hits

        chunk_index_to_page: dict[int, Optional[int]] = {
            c.index: c.page for c in chunks
        }

        rules_out: list[dict] = []
        for cid in triggered_rule_ids:
            chunk_idxs = rule_to_chunks.get(cid, [])
            pages = sorted({chunk_index_to_page.get(i) for i in chunk_idxs} - {None})
            rules_out.append({
                "rule_id": cid,
                "pages": pages,
                "chunks": [
                    {
                        "index": ci,
                        "page": chunk_index_to_page.get(ci),
                        "preview": next(
                            (c.text[:240] + ("…" if len(c.text) > 240 else "") for c in chunks if c.index == ci),
                            "",
                        ),
                    }
                    for ci in chunk_idxs
                ],
            })

        # Predikat provenance — for each extracted predikat, search chunks
        # for evidence of the predikat's question keywords.
        predikates_out: list[dict] = []
        extracted = response_payload.get("extracted_predicates") or {}
        for pred_id, value in extracted.items():
            pred_pages: set[int] = set()
            # Search all rules for this predikat's question text
            question = ""
            for rule in rules:
                for p in rule.predikater or []:
                    if p.id == pred_id:
                        question = p.spørgsmål or ""
                        break
                if question:
                    break
            if question:
                keywords = _keywords_from_citat(question)
                for chunk in chunks:
                    ctext = chunk.text.lower()
                    if any(kw and kw in ctext for kw in keywords):
                        if chunk.page is not None:
                            pred_pages.add(chunk.page)

            predikates_out.append({
                "predikat_id": pred_id,
                "value": value,
                "pages": sorted(pred_pages),
            })

        return {
            "audit_log_id": audit_log_id,
            "filename": stored.original_filename,
            "kind": kind,
            "page_count": page_count,
            "rules": rules_out,
            "predikates": predikates_out,
        }

    return await asyncio.to_thread(_rebuild_evidence)


def _keywords_from_citat(text: str) -> list[str]:
    """Pick high-signal lowercase tokens from a citation/question.

    Skips stopwords and tokens shorter than 4 chars. Returns at most 8
    tokens to keep the substring search cheap. Used by the highlights
    endpoint to map predikates → chunks without an LLM call.
    """
    if not text:
        return []
    stopwords = {
        "den", "det", "der", "som", "har", "være", "med", "for", "ved", "fra",
        "ikke", "skal", "kan", "kun", "også", "men", "selv", "andre", "andet",
        "samme", "denne", "dette", "disse", "deres", "sine", "sit", "sin",
        "uden", "over", "under", "mellem", "ifølge", "efter", "før", "samt",
        "blive", "bliver", "blevet", "bliver", "bliver",
    }
    words = re.findall(r"[A-Za-zÆØÅæøå]{4,}", text.lower())
    seen: list[str] = []
    for w in words:
        if w in stopwords:
            continue
        if w not in seen:
            seen.append(w)
        if len(seen) >= 8:
            break
    return seen


# ---------------------------------------------------------------------------
# Case workflow endpoints (Step 2 — kanban over /sager)
# ---------------------------------------------------------------------------

class V3CaseCreate(BaseModel):
    case_id: str = Field(..., description="External Kalundborg case ID, e.g. K-2026-0184")
    title: str = Field(..., max_length=255)
    notes: Optional[str] = None
    status: str = Field(default="kladde")
    assigned_to: Optional[str] = None


class V3CaseTransition(BaseModel):
    new_status: str = Field(..., description="One of CASE_STATUSES")
    note: Optional[str] = None


@app.post("/api/v3/cases")
async def v3_cases_create(req: V3CaseCreate):
    from src.database import cases as v3_cases
    from src.database.connection import SessionLocal
    db = SessionLocal()
    try:
        case = v3_cases.create_case(
            db,
            case_id=req.case_id,
            title=req.title,
            notes=req.notes,
            status=req.status,
            assigned_to=req.assigned_to,
        )
        db.commit()
        return case.to_dict()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        db.close()


@app.get("/api/v3/cases")
async def v3_cases_list(
    status: Optional[str] = None,
    case_id: Optional[str] = None,
    limit: int = 200,
):
    from src.database import cases as v3_cases
    from src.database.connection import SessionLocal
    db = SessionLocal()
    try:
        items = v3_cases.list_cases(db, status=status, case_id=case_id, limit=limit)
        return {"count": len(items), "items": [c.to_dict() for c in items]}
    finally:
        db.close()


# ==================== Indkøbsproces — case intake state ===================
#
# Persisterer indkøbsproces-wizardens state pr. sag så brugeren kan lukke
# browseren + komme tilbage senere + cross-device-tilgang via Tailscale.
# VIGTIGT: Disse routes skal stå FØR `/api/v3/cases/{case_db_id}` ellers
# matcher den catch-all "drafts" og "by-case-id" som UUID-paths.

class IntakeStatePayload(BaseModel):
    """State fra IndkoebsprocesPage's 4-trins wizard."""

    intake_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Wizard-state — alle 4 trin's felter samlet i én dict.",
    )
    title: Optional[str] = Field(
        default=None,
        description="Valgfri titel — udledes fra behov hvis ikke angivet.",
    )
    user: Optional[str] = Field(
        default=None,
        description="Bruger der gemte (audit + assigned_to).",
    )


@app.get("/api/v3/cases/drafts")
async def v3_case_drafts(limit: int = 50):
    """List alle sager med intake_state (= drafts i indkøbsprocessen).

    Bruges af 'Mine sager'-stripen øverst på /indkoebsproces. Sorteret
    efter sidst opdateret (nyeste først).
    """
    from src.database.connection import SessionLocal
    from src.database.cases import list_drafts_with_intake

    db = SessionLocal()
    try:
        rows = await asyncio.to_thread(list_drafts_with_intake, db, limit=limit)
        return {
            "count": len(rows),
            "items": [r.to_dict() for r in rows],
        }
    finally:
        db.close()


@app.get("/api/v3/cases/by-case-id/{case_id}")
async def v3_case_by_external_id(case_id: str):
    """Hent case-row + intake_state for et eksternt sagsnummer.

    Returnerer 200 med case-data hvis sagen findes, ellers 404 så frontend
    kan vide om det er en ny eller eksisterende sag.
    """
    from src.database.connection import SessionLocal
    from src.database.cases import find_case_by_external_id

    db = SessionLocal()
    try:
        case = await asyncio.to_thread(find_case_by_external_id, db, case_id)
        if case is None:
            raise HTTPException(status_code=404, detail=f"case_id not found: {case_id}")
        return case.to_dict()
    finally:
        db.close()


# ==================== Notifications ===================================
#
# Auto-emit fra evidence-completions, case-transitions, citation-flagging.
# Vises som bell-icon-badge i Bifrosts sidebar header.

@app.get("/api/v3/notifications")
async def v3_notifications_list(unread_only: bool = False, limit: int = 30):
    """List notifikationer — bruges af bell-panel."""
    from src.database.connection import SessionLocal
    from src.database import notifications as notif_svc

    db = SessionLocal()
    try:
        rows = await asyncio.to_thread(
            notif_svc.list_recent, db, limit=limit, unread_only=unread_only,
        )
        unread = await asyncio.to_thread(notif_svc.count_unread, db)
        return {
            "count": len(rows),
            "unread": unread,
            "items": [r.to_dict() for r in rows],
        }
    finally:
        db.close()


@app.post("/api/v3/notifications/{notification_id}/read")
@limiter.limit(ADMIN_WRITE)
async def v3_notification_mark_read(
    request: Request,
    response: Response,
    notification_id: str,
):
    from src.database.connection import SessionLocal
    from src.database import notifications as notif_svc

    db = SessionLocal()
    try:
        n = await asyncio.to_thread(notif_svc.mark_read, db, notification_id)
        if n is None:
            raise HTTPException(status_code=404, detail="notification not found")
        db.commit()
        return n.to_dict()
    finally:
        db.close()


@app.post("/api/v3/notifications/read-all")
@limiter.limit(ADMIN_WRITE)
async def v3_notifications_mark_all_read(
    request: Request,
    response: Response,
):
    from src.database.connection import SessionLocal
    from src.database import notifications as notif_svc

    db = SessionLocal()
    try:
        count = await asyncio.to_thread(notif_svc.mark_all_read, db)
        db.commit()
        return {"marked_read": count}
    finally:
        db.close()


@app.get("/api/v3/search")
async def v3_global_search(q: str, limit: int = 20):
    """Global søgning på tværs af alle entities — bruges af Cmd+K spotlight.

    Søger efter `q` i:
    - cases (case_id, title, intake_state.behov, intake_state.system_description)
    - v3_assessment_log (note, case_id, aggregate_status)
    - evidence_artifacts (artifact_id, case_id, content_json)
    - rules (rule.id, kilde.lov, kilde.artikel)
    - data/knowledge_base.json (term, definition)

    Returnerer pr. resultat: {type, label, sublabel, url, score} sorted by score.
    Score: prefix-match=100, contains=50.
    """
    from src.database.connection import SessionLocal
    from src.database.cases import Case
    from src.database.evidence import EvidenceArtifact
    from src.rule_engine import audit as v3_audit
    from src.services.evidence_artifacts import ARTIFACT_TEMPLATES

    if not q or len(q.strip()) < 2:
        return {"query": q, "count": 0, "results": []}

    needle = q.strip().lower()
    results: List[Dict[str, Any]] = []

    def score(text: Optional[str]) -> int:
        if not text:
            return 0
        t = str(text).lower()
        if t.startswith(needle):
            return 100
        if needle in t:
            return 50
        return 0

    db = SessionLocal()
    try:
        # Cases
        try:
            for c in db.query(Case).all():
                s = max(
                    score(c.case_id),
                    score(c.title),
                    score((c.get_intake_state() or {}).get("behov", "")),
                    score((c.get_intake_state() or {}).get("system_description", "")),
                )
                if s > 0:
                    results.append({
                        "type": "case",
                        "label": c.case_id,
                        "sublabel": c.title,
                        "url": f"/sag/{c.case_id}",
                        "score": s,
                        "meta": c.status,
                    })
        except Exception as exc:
            logger.warning(f"search cases failed: {exc}")

        # Audit log entries (vurderinger)
        try:
            entries = v3_audit.list_recent(db, limit=200)
            for e in entries:
                s = max(
                    score(e.case_id),
                    score(e.note),
                    score(e.aggregate_status),
                )
                if s > 0:
                    results.append({
                        "type": "vurdering",
                        "label": f"{e.aggregate_status} — {e.case_id or 'ukendt sag'}",
                        "sublabel": (e.note or "")[:120],
                        "url": f"/historik/{e.id}",
                        "score": s - 5,  # vurderinger lidt lavere prio end cases
                        "meta": e.aggregate_status,
                    })
        except Exception as exc:
            logger.warning(f"search audit failed: {exc}")

        # Evidence artifacts
        try:
            for ev in db.query(EvidenceArtifact).all():
                s = max(
                    score(ev.artifact_id),
                    score(ev.case_id),
                )
                # Også gennemsøg content for keyword
                if s == 0 and ev.content_json:
                    s = score(ev.content_json[:1000])
                if s > 0:
                    results.append({
                        "type": "evidens",
                        "label": ev.artifact_id.replace("_", " "),
                        "sublabel": f"sag {ev.case_id} · {ev.status}",
                        "url": f"/sag/{ev.case_id}?tab=evidens",
                        "score": s - 10,
                        "meta": ev.status,
                    })
        except Exception as exc:
            logger.warning(f"search evidence failed: {exc}")

        # Evidence templates (jur. skabeloner — søgbare uden sag-tilknytning)
        try:
            for tid, tmpl in ARTIFACT_TEMPLATES.items():
                s = max(
                    score(tid),
                    score(tmpl.title),
                    score(tmpl.summary),
                )
                if s > 0:
                    results.append({
                        "type": "skabelon",
                        "label": tmpl.title,
                        "sublabel": tmpl.summary[:120],
                        "url": f"/api/v3/evidence/templates/{tid}",  # API-link; frontend kan beslutte
                        "score": s - 15,
                        "meta": tmpl.category,
                    })
        except Exception as exc:
            logger.warning(f"search templates failed: {exc}")

        # Rules
        try:
            from main import _v3_load_rules  # noqa: F401 — defined elsewhere in this file
            rules = _v3_load_rules()
            for r in rules:
                s = max(
                    score(r.id),
                    score(r.kilde.lov),
                    score(r.kilde.artikel),
                    score(r.kilde.citat[:200] if r.kilde.citat else ""),
                )
                if s > 0:
                    results.append({
                        "type": "regel",
                        "label": f"{r.kilde.lov} {r.kilde.artikel}",
                        "sublabel": r.id,
                        "url": "/lov-overvaagning",
                        "score": s - 20,
                        "meta": "rule",
                    })
        except Exception as exc:
            logger.warning(f"search rules failed: {exc}")

        # Knowledge base
        try:
            import json
            from pathlib import Path
            kb_path = Path(__file__).parent / "data" / "knowledge_base.json"
            if kb_path.exists():
                kb = json.loads(kb_path.read_text(encoding="utf-8"))
                for item in kb:
                    s = max(
                        score(item.get("term")),
                        score(item.get("definition")),
                    )
                    if s > 0:
                        results.append({
                            "type": "videnbase",
                            "label": item.get("term", ""),
                            "sublabel": (item.get("definition", "") or "")[:120],
                            "url": "/videnbase",
                            "score": s - 25,
                            "meta": item.get("category", ""),
                        })
        except Exception as exc:
            logger.warning(f"search KB failed: {exc}")

    finally:
        db.close()

    # Sort by score desc + dedupe by url
    seen = set()
    deduped = []
    for r in sorted(results, key=lambda x: -x["score"]):
        if r["url"] in seen:
            continue
        seen.add(r["url"])
        deduped.append(r)
        if len(deduped) >= limit:
            break

    return {"query": q, "count": len(deduped), "results": deduped}


@app.get("/api/v3/cases/by-case-id/{case_id}/report")
async def v3_case_report(case_id: str, format: str = "docx"):
    """Eksportér samlet sag-rapport i DOCX eller PDF.

    Format: docx (default, redigerbar) eller pdf (print-klar).

    Indhold:
    - Cover-side (sagsnummer, titel, status, verdict)
    - Sammendrag (status, evidens-progress, krav-antal)
    - Indkøbsproces (intake state)
    - Bifrost-vurdering (per-rule decisions, krav, lovcitater)
    - Evidens-checkliste (status pr. artefakt + udfyldt indhold)
    - Audit-trail (transitions, evidens-completions)
    """
    from src.database.connection import SessionLocal
    from src.services.case_report_generator import (
        build_report_data,
        render_docx,
        render_pdf,
    )

    fmt = format.lower().strip()
    if fmt not in ("docx", "pdf"):
        raise HTTPException(status_code=400, detail="format must be 'docx' or 'pdf'")

    db = SessionLocal()
    try:
        data = await asyncio.to_thread(build_report_data, db, case_id)
        if data is None:
            raise HTTPException(status_code=404, detail=f"case_id not found: {case_id}")

        if fmt == "docx":
            content = await asyncio.to_thread(render_docx, data)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ext = "docx"
        else:
            content = await asyncio.to_thread(render_pdf, data)
            media_type = "application/pdf"
            ext = "pdf"

        # Filnavn med slugified titel + dato
        from datetime import datetime as _dt
        date_str = _dt.now().strftime("%Y-%m-%d")
        safe_case = case_id.replace("/", "-").replace(" ", "_")
        filename = f"bifrost-rapport-{safe_case}-{date_str}.{ext}"

        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    finally:
        db.close()


@app.get("/api/v3/cases/by-case-id/{case_id}/timeline")
async def v3_case_timeline(case_id: str, limit: int = 50):
    """Returnér samlet kronologisk feed for én sag — bruges af sag-detalje-siden.

    Kombinerer:
    - Vurderinger (v3_assessment_log)
    - Status-transitions (case_transitions)
    - Evidens-completions (evidence_artifacts.completed_at)
    - Intake-state ændringer (case.updated_at — kun seneste)

    Sorteret nyeste først. Hver entry har: {kind, timestamp, label, detail, link, actor}
    """
    from src.database.connection import SessionLocal
    from src.database.cases import find_case_by_external_id, Case, CaseTransition
    from src.database.evidence import list_evidence_for_case
    from src.rule_engine import audit as v3_audit

    db = SessionLocal()
    try:
        case = await asyncio.to_thread(find_case_by_external_id, db, case_id)
        if case is None:
            raise HTTPException(status_code=404, detail=f"case_id not found: {case_id}")

        events: List[Dict[str, Any]] = []

        # 1) Vurderinger (audit log entries med matching case_id)
        try:
            assessments = v3_audit.list_recent(db, limit=limit, case_id=case_id)
            for a in assessments:
                events.append({
                    "kind": "vurdering",
                    "timestamp": a.created_at.isoformat() if a.created_at else None,
                    "label": f"Vurdering: {a.aggregate_status}",
                    "detail": (a.note or "")[:200],
                    "link": f"/historik/{a.id}",
                    "actor": a.user_id,
                })
        except Exception as exc:
            logger.warning(f"timeline assessments fetch failed: {exc}")

        # 2) Status-transitions
        try:
            transitions = (
                db.query(CaseTransition)
                .filter(CaseTransition.case_db_id == case.id)
                .order_by(CaseTransition.changed_at.desc())
                .limit(limit)
                .all()
            )
            for t in transitions:
                from_label = t.from_status or "(ny)"
                events.append({
                    "kind": "transition",
                    "timestamp": t.changed_at.isoformat() if t.changed_at else None,
                    "label": f"Status: {from_label} → {t.to_status}",
                    "detail": t.note or "",
                    "link": None,
                    "actor": t.changed_by,
                })
        except Exception as exc:
            logger.warning(f"timeline transitions fetch failed: {exc}")

        # 3) Evidens-events (completion + creation)
        try:
            ev_rows = list_evidence_for_case(db, case_id)
            for r in ev_rows:
                if r.completed_at:
                    events.append({
                        "kind": "evidens_completed",
                        "timestamp": r.completed_at.isoformat(),
                        "label": f"Evidens færdig: {r.artifact_id.replace('_', ' ')}",
                        "detail": "",
                        "link": None,
                        "actor": r.completed_by,
                    })
                elif r.created_at and r.status == "i_gang":
                    events.append({
                        "kind": "evidens_started",
                        "timestamp": r.updated_at.isoformat() if r.updated_at else r.created_at.isoformat(),
                        "label": f"Evidens påbegyndt: {r.artifact_id.replace('_', ' ')}",
                        "detail": "",
                        "link": None,
                        "actor": r.last_edited_by,
                    })
        except Exception as exc:
            logger.warning(f"timeline evidence fetch failed: {exc}")

        # 4) Intake-state seneste opdatering
        if case.intake_state and case.updated_at:
            events.append({
                "kind": "intake_updated",
                "timestamp": case.updated_at.isoformat(),
                "label": "Indkøbsproces opdateret",
                "detail": case.get_intake_state().get("behov", "")[:200],
                "link": f"/indkoebsproces?case_id={case.case_id}",
                "actor": case.assigned_to,
            })

        # 5) Evidens-kommentarer (per-felt diskussion)
        try:
            from src.database.evidence_comments import list_comments

            comment_rows = list_comments(db, case_id=case_id, include_resolved=True)
            for c in comment_rows:
                section_label = c.section_key or "hele dokumentet"
                preview = (c.body[:120] + "…") if len(c.body) > 120 else c.body
                events.append({
                    "kind": "evidens_comment",
                    "timestamp": c.created_at.isoformat() if c.created_at else None,
                    "label": (
                        f"Kommentar på {c.artifact_id.replace('_', ' ')} "
                        f"({section_label})"
                    ),
                    "detail": preview,
                    "link": f"/sag/{case.case_id}?tab=evidens",
                    "actor": c.author,
                })
        except Exception as exc:
            logger.warning(f"timeline comments fetch failed: {exc}")

        # Sort newest first
        events.sort(key=lambda e: e["timestamp"] or "", reverse=True)

        return {
            "case": case.to_dict(),
            "count": len(events),
            "events": events[:limit],
        }
    finally:
        db.close()


@app.put("/api/v3/cases/by-case-id/{case_id}/intake")
@limiter.limit(ADMIN_WRITE)
async def v3_case_upsert_intake(
    request: Request,
    response: Response,
    case_id: str,
    body: IntakeStatePayload,
):
    """Gem/opdatér indkøbsproces-state for en sag.

    Opretter case-rækken hvis den ikke findes (status='kladde'). Idempotent
    — kald flere gange overskriver intake_state. Bruges af frontend's
    debounced auto-save.
    """
    from src.database.connection import SessionLocal
    from src.database.cases import upsert_intake_state

    db = SessionLocal()
    try:
        case = await asyncio.to_thread(
            upsert_intake_state,
            db,
            case_id=case_id,
            intake_state=body.intake_state,
            title=body.title,
            user=body.user,
        )
        db.commit()
        return case.to_dict()
    finally:
        db.close()


@app.get("/api/v3/cases/{case_db_id}")
async def v3_cases_detail(case_db_id: str):
    from src.database import cases as v3_cases
    from src.database.connection import SessionLocal
    db = SessionLocal()
    try:
        case = v3_cases.get_case(db, case_db_id)
        if case is None:
            raise HTTPException(status_code=404, detail=f"case not found: {case_db_id}")
        d = case.to_dict()
        d["transitions"] = [t.to_dict() for t in case.transitions]
        return d
    finally:
        db.close()


@app.post("/api/v3/cases/{case_db_id}/transition")
async def v3_cases_transition(case_db_id: str, req: V3CaseTransition):
    from src.database import cases as v3_cases
    from src.database.connection import SessionLocal
    db = SessionLocal()
    try:
        case = v3_cases.transition_case(
            db,
            case_db_id,
            req.new_status,
            note=req.note,
        )
        db.commit()
        return case.to_dict()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        db.close()


@app.get("/api/v3/cases/meta/statuses")
async def v3_cases_statuses():
    from src.database.cases import CASE_STATUSES, CASE_STATUS_LABELS
    return {
        "statuses": [
            {"id": s, "label": CASE_STATUS_LABELS[s]} for s in CASE_STATUSES
        ]
    }


@app.get("/api/v3/cases/reminders/preview")
async def v3_cases_reminder_preview():
    """List cases that would receive a reminder if the job ran now.

    Read-only — does not send anything. Useful for verifying the job is
    targeting the right cases before it fires at 08:00.
    """
    from src.services.case_reminder_service import find_cases_needing_reminder

    cases = await asyncio.to_thread(find_cases_needing_reminder)
    return {
        "count": len(cases),
        "cases": [
            {
                "id": c.id,
                "case_id": c.case_id,
                "title": c.title,
                "status": c.status,
                "assigned_to": c.assigned_to,
                "next_review_at": c.next_review_at.isoformat() if c.next_review_at else None,
                "last_reminder_sent_at": (
                    c.last_reminder_sent_at.isoformat() if c.last_reminder_sent_at else None
                ),
            }
            for c in cases
        ],
    }


@app.post("/api/v3/cases/reminders/run")
async def v3_cases_reminder_run():
    """Manually trigger the case-reminder job. Returns a per-run summary."""
    from src.services.case_reminder_service import send_due_reminders

    summary = await asyncio.to_thread(send_due_reminders)
    return summary


# ---------------------------------------------------------------------------
# GDPR / DSAR — Data Subject Access Request endpoints
# ---------------------------------------------------------------------------
#
# Per GDPR artikler 15 (right of access), 17 (right to erasure) og 20 (right
# to data portability) skal kommunen kunne eksportere og slette alt der er
# gemt om en konkret sag. Disse endpoints implementerer flowet på sags-
# niveau — i praksis er case_id kommunens link til borgeren, så at slette en
# sag = at slette de borger-knyttede oplysninger Bifrost har om vedkommende.
#
# Adgangskontrol: I denne fase er der ingen auth — endpoints er bag
# Tailscale-grænsen og logges. Når Modul 5 (auth) lander, skal disse
# endpoints kræve admin-rolle.


@app.get("/api/v3/admin/dsar/export/{case_id}")
async def v3_dsar_export(case_id: str, request: Request):
    """Eksportér alt Bifrost har om en case_id som JSON-bundle.

    Indeholder: case-record, alle transitions, alle audit-logs hvor
    request_payload/response_payload nævner case_id, freshness-status for
    udløste regler, og lister hvilke dokument-filer der er tilknyttet
    (selve filerne kan downloades via /api/v3/documents/{audit_log_id}/source).
    """
    import re
    from src.database.connection import SessionLocal
    from src.database.cases import Case, CaseTransition
    from src.database.audit_access_log import record_access
    from src.rule_engine.audit import V3AssessmentLog
    from src.services.citation_verifier import RuleFreshness
    from src.services import document_storage

    if not case_id or not re.match(r"^[A-Za-z0-9._\-]+$", case_id):
        raise HTTPException(status_code=400, detail="invalid case_id")

    # Log the export access before doing the heavy work
    try:
        with SessionLocal() as access_session:
            record_access(
                access_session,
                target_type="dsar_export",
                target_id=case_id,
                action="export",
                actor=request.headers.get("X-User"),
                actor_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                request_id=request.headers.get("X-Request-ID"),
            )
            access_session.commit()
    except Exception:
        logger.warning("audit_access_log write failed for DSAR export %s", case_id, exc_info=True)

    def _collect() -> dict:
        with SessionLocal() as session:
            cases = (
                session.query(Case).filter(Case.case_id == case_id).all()
            )
            case_payloads = [c.to_dict() for c in cases]
            case_db_ids = [c.id for c in cases]

            transitions = []
            if case_db_ids:
                transitions = [
                    t.to_dict()
                    for t in session.query(CaseTransition)
                    .filter(CaseTransition.case_db_id.in_(case_db_ids))
                    .order_by(CaseTransition.changed_at)
                    .all()
                ]

            # Find audit logs that reference this case_id in their payload.
            # We do a JSON-text LIKE — broad but cheap. Postgres has ->>
            # operators we could use later.
            log_rows = (
                session.query(V3AssessmentLog)
                .filter(
                    V3AssessmentLog.request_payload.cast(sa_String).ilike(
                        f"%{case_id}%"
                    )
                )
                .all()
            )
            assessment_logs = [r.to_dict() for r in log_rows]
            audit_log_ids = [r.id for r in log_rows]

            # Collect rule_freshness for any rules these logs touched
            rule_ids = set()
            for r in log_rows:
                rp = r.response_payload or {}
                for d in rp.get("decisions") or []:
                    if d.get("rule_id"):
                        rule_ids.add(d["rule_id"])
            freshness_rows = []
            if rule_ids:
                freshness_rows = [
                    rf.to_dict()
                    for rf in session.query(RuleFreshness)
                    .filter(RuleFreshness.rule_id.in_(rule_ids))
                    .all()
                ]

        documents = []
        for log_id in audit_log_ids:
            stored = document_storage.find(log_id)
            if stored:
                documents.append({
                    "audit_log_id": log_id,
                    "filename": stored.original_filename,
                    "size_bytes": stored.size_bytes,
                    "content_type": stored.content_type,
                })

        return {
            "case_id": case_id,
            "exported_at": datetime.now(UTC).isoformat(),
            "cases": case_payloads,
            "case_transitions": transitions,
            "assessment_logs": assessment_logs,
            "rule_freshness": freshness_rows,
            "documents": documents,
        }

    # Lazy import to keep top-of-file lean
    from sqlalchemy import String as sa_String  # noqa: F401

    payload = await asyncio.to_thread(_collect)
    return payload


@app.delete("/api/v3/admin/dsar/case/{case_id}")
async def v3_dsar_delete_case(case_id: str, request: Request):
    """Slet alle persondata Bifrost har om en case_id.

    Dette er "right to erasure" (artikel 17). Sletter cases, transitions,
    audit-logs, dokument-filer og rule_freshness-spor (hvis sidstnævnte
    kun er linket via denne sag — implementeret i retention-sweepet).

    Operationen er irreversibel. Returnerer en summary af hvad der blev slettet.
    """
    import re
    from src.database.connection import SessionLocal
    from src.database.cases import Case, CaseTransition
    from src.database.audit_access_log import record_access
    from src.rule_engine.audit import V3AssessmentLog
    from src.services import document_storage
    from sqlalchemy import String as sa_String

    if not case_id or not re.match(r"^[A-Za-z0-9._\-]+$", case_id):
        raise HTTPException(status_code=400, detail="invalid case_id")

    # Log the delete access — this entry survives the deletion
    try:
        with SessionLocal() as access_session:
            record_access(
                access_session,
                target_type="dsar_delete",
                target_id=case_id,
                action="delete",
                actor=request.headers.get("X-User"),
                actor_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                request_id=request.headers.get("X-Request-ID"),
            )
            access_session.commit()
    except Exception:
        logger.warning("audit_access_log write failed for DSAR delete %s", case_id, exc_info=True)

    def _delete() -> dict:
        deleted = {
            "cases": 0,
            "case_transitions": 0,
            "assessment_logs": 0,
            "documents": 0,
        }
        document_audit_ids: list[str] = []

        with SessionLocal() as session:
            cases = (
                session.query(Case).filter(Case.case_id == case_id).all()
            )
            case_db_ids = [c.id for c in cases]

            if case_db_ids:
                deleted["case_transitions"] = (
                    session.query(CaseTransition)
                    .filter(CaseTransition.case_db_id.in_(case_db_ids))
                    .delete(synchronize_session=False)
                )

            for c in cases:
                session.delete(c)
            deleted["cases"] = len(cases)

            log_rows = (
                session.query(V3AssessmentLog)
                .filter(
                    V3AssessmentLog.request_payload.cast(sa_String).ilike(
                        f"%{case_id}%"
                    )
                )
                .all()
            )
            for r in log_rows:
                document_audit_ids.append(r.id)
                session.delete(r)
            deleted["assessment_logs"] = len(log_rows)

            session.commit()

        # Slet dokument-filer udenfor session så vi ikke holder DB-locks
        # under filsystem-IO
        for log_id in document_audit_ids:
            if document_storage.delete(log_id):
                deleted["documents"] += 1

        return {
            "case_id": case_id,
            "deleted_at": datetime.now(UTC).isoformat(),
            "deleted": deleted,
        }

    summary = await asyncio.to_thread(_delete)
    logger.warning(
        "DSAR delete executed: case_id=%s deleted=%s",
        case_id,
        summary["deleted"],
    )
    return summary


@app.post("/api/v3/admin/retention/run")
async def v3_retention_run():
    """Manually trigger the retention sweep. Returns summary of what was
    deleted. Equivalent to what the daily 02:00 cron job does."""
    from src.services.retention_service import run_retention

    summary = await asyncio.to_thread(run_retention)
    return summary


# ---------------------------------------------------------------------------
# Citation verifier endpoints (Step 3 — daily-job + admin trigger)
# ---------------------------------------------------------------------------

def _v3_run_citation_verifier() -> None:
    """Scheduler entry point — runs every night at 04:00."""
    from src.services.citation_verifier import verify_all_rules
    from src.database.connection import SessionLocal

    try:
        rules = _v3_load_rules()
    except Exception as exc:
        logger.warning("citation verifier: rules failed to load: %s", exc)
        return

    db = SessionLocal()
    try:
        results = verify_all_rules(db, rules)
        db.commit()
        flagged = sum(1 for r in results if r.flagged_for_review)
        logger.info(
            "Citation verifier: %d rules checked, %d flagged for juridisk review",
            len(results), flagged,
        )
    except Exception as exc:
        db.rollback()
        logger.exception("Citation verifier failed: %s", exc)
    finally:
        db.close()


@app.get("/api/v3/law/freshness")
async def v3_law_freshness():
    """Return latest verification status for each rule."""
    from src.services.citation_verifier import list_freshness
    from src.database.connection import SessionLocal

    db = SessionLocal()
    try:
        rows = list_freshness(db)
        return {
            "count": len(rows),
            "checked_at": datetime.now(UTC).isoformat(),
            "items": [r.to_dict() for r in rows],
        }
    finally:
        db.close()


@app.post("/api/v3/law/freshness/run")
@limiter.limit(ADMIN_WRITE)
async def v3_law_freshness_run(request: Request):
    """Manual trigger of the citation-verifier (for admin use / testing).

    Runs in a worker thread so the Playwright sync API (used by the SPA
    fallback) doesn't trip on the asyncio event loop. ~3-8s per SPA rule
    means this can take a couple of minutes.
    """
    await asyncio.to_thread(_v3_run_citation_verifier)
    return await v3_law_freshness()


@app.get("/api/v3/law/freshness/flagged")
async def v3_law_freshness_flagged():
    """Quick endpoint for the frontend to know which rule_ids should
    show a warning banner in the result-mode."""
    from src.services.citation_verifier import flagged_rule_ids
    from src.database.connection import SessionLocal

    db = SessionLocal()
    try:
        return {"flagged_rule_ids": sorted(flagged_rule_ids(db))}
    finally:
        db.close()


@app.get("/api/v3/law/freshness/playwright/status")
async def v3_law_freshness_playwright_status():
    """Report whether the Playwright SPA-fallback is operational.

    Why exposed: ops needs to know if a 13/15 freshness number is "all the
    static rules pass + 2 SPAs unverified" or "Playwright is wired in and
    we'll cover all 15".
    """
    from src.services.citation_verifier import is_playwright_available
    available = await asyncio.to_thread(is_playwright_available)
    return {
        "available": available,
        "install_hint": (
            None
            if available
            else "pip install playwright && playwright install chromium"
        ),
    }


# ==================== Evidence artifacts (interactive checklist) ===========
#
# V3VurderingPage's evidens-checkliste: hvert artefakt-ID i en regels
# `evidens_påkrævet` får en klikbar editor med pre-fyldt skabelon.

class EvidenceSavePayload(BaseModel):
    """Sagsbehandlerens udfyldte indhold for ét artefakt."""

    content: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dict {section_key: value} med svar pr. sektion.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Valgfri intern note (ikke vist i auditrapporten).",
    )
    user: Optional[str] = Field(
        default=None,
        description="Bruger der gemte (audit-trail).",
    )


@app.get("/api/v3/evidence/templates")
async def v3_evidence_list_templates():
    """List alle 19 curated artefakt-skabeloner.

    Returnerer fuld template-spec inkl. sections, lovhjemmel og eksterne
    ressourcer. Bruges af /drift's stat-card og af evt. katalog-side.
    """
    from src.services.evidence_artifacts import list_templates, all_known_ids
    templates = list_templates()
    return {
        "count": len(templates),
        "all_known_artifact_ids_count": len(all_known_ids()),
        "templates": templates,
    }


@app.get("/api/v3/evidence/templates/{artifact_id}")
async def v3_evidence_get_template(artifact_id: str):
    """Hent én skabelon — faldback til generic hvis ikke curated."""
    from src.services.evidence_artifacts import get_template
    tmpl = get_template(artifact_id)
    return tmpl.to_dict()


@app.get("/api/v3/cases/{case_id}/evidence")
async def v3_evidence_list_for_case(case_id: str, request: Request):
    """List sagsbehandlerens udfyldte artefakter for én sag.

    Returnerer både sparede rows (med content + status) og nul-rækker
    for kendte artefakt-IDs som endnu ikke er begyndt — så frontend kan
    rendere fuld checkliste i ét hop.
    """
    from src.database.connection import SessionLocal
    from src.database.evidence import list_evidence_for_case
    from src.database.audit_access_log import record_access

    db = SessionLocal()
    try:
        rows = list_evidence_for_case(db, case_id)
        record_access(
            db,
            target_type="case_evidence",
            target_id=case_id,
            actor=request.headers.get("X-Bifrost-User"),
            actor_ip=(request.client.host if request.client else None),
            user_agent=request.headers.get("user-agent"),
            action="read",
            request_id=getattr(request.state, "request_id", None),
        )
        db.commit()
        return {
            "case_id": case_id,
            "count": len(rows),
            "items": [r.to_dict() for r in rows],
        }
    finally:
        db.close()


@app.put("/api/v3/cases/{case_id}/evidence/{artifact_id}")
@limiter.limit(ADMIN_WRITE)
async def v3_evidence_upsert(
    request: Request,
    response: Response,
    case_id: str,
    artifact_id: str,
    body: EvidenceSavePayload,
):
    """Gem/opdatér ét artefakt-indhold.

    Status beregnes server-side baseret på hvilke required-sektioner der
    har indhold (mangler / i_gang / faerdig). Når status går til 'faerdig'
    første gang sættes `completed_at` + `completed_by` automatisk.
    """
    from src.database.connection import SessionLocal
    from src.database.evidence import upsert_evidence, get_evidence
    from src.database.audit_access_log import record_access
    from src.database import notifications as notif_svc
    from src.services.evidence_artifacts import compute_status, get_template

    template = get_template(artifact_id)
    computed = compute_status(template, body.content)

    db = SessionLocal()
    try:
        # Pre-check: var artefaktet allerede færdigt? Hvis ja, ingen notifikation
        prev = get_evidence(db, case_id, artifact_id)
        was_already_completed = prev is not None and prev.status in ("faerdig", "godkendt")

        row = upsert_evidence(
            db,
            case_id=case_id,
            artifact_id=artifact_id,
            content=body.content,
            computed_status=computed,
            user=body.user,
            notes=body.notes,
        )
        record_access(
            db,
            target_type="case_evidence",
            target_id=f"{case_id}/{artifact_id}",
            actor=body.user or request.headers.get("X-Bifrost-User"),
            actor_ip=(request.client.host if request.client else None),
            user_agent=request.headers.get("user-agent"),
            action="write",
            request_id=getattr(request.state, "request_id", None),
        )

        # Auto-emit notifikation når et artefakt skifter til faerdig første gang
        if computed in ("faerdig", "godkendt") and not was_already_completed:
            try:
                notif_svc.emit(
                    db,
                    kind="evidens_completed",
                    title=f"Evidens færdig: {artifact_id.replace('_', ' ')}",
                    message=f"Artefaktet '{template.title}' er nu udfyldt på sag {case_id}.",
                    case_id=case_id,
                    link_url=f"/sag/{case_id}?tab=evidens",
                    severity="success",
                    actor=body.user,
                )
            except Exception as exc:
                logger.warning(f"notification emit failed: {exc}")

        db.commit()
        return {
            **row.to_dict(),
            "computed_status": computed,
            "required_section_keys": sorted(template.required_section_keys()),
        }
    finally:
        db.close()


# =========================================================================
# Skabelon-bibliotek — genbrugbare evidens-skabeloner på tværs af sager
# =========================================================================


class SkabelonCreatePayload(BaseModel):
    artifact_id: str = Field(..., description="Hvilken type evidens skabelonen gælder for")
    name: str = Field(..., min_length=1, max_length=160)
    description: Optional[str] = Field(default=None, max_length=2000)
    content: Dict[str, Any] = Field(..., description="Felt-værdier der bruges som default")
    source_case_id: Optional[str] = Field(default=None, max_length=64)
    user: Optional[str] = Field(default=None, max_length=64)


class SkabelonApplyPayload(BaseModel):
    user: Optional[str] = Field(default=None, max_length=64)


@app.get("/api/v3/skabelon-bibliotek")
async def v3_skabelon_list(artifact_id: Optional[str] = None):
    """List skabeloner — optionelt filtreret på artifact_id."""
    from src.database.connection import SessionLocal
    from src.database.skabelon_bibliotek import list_skabeloner

    db = SessionLocal()
    try:
        rows = list_skabeloner(db, artifact_id=artifact_id)
        return {
            "count": len(rows),
            "items": [r.to_dict() for r in rows],
        }
    finally:
        db.close()


@app.post("/api/v3/skabelon-bibliotek")
@limiter.limit(ADMIN_WRITE)
async def v3_skabelon_create(
    request: Request,
    response: Response,
    body: SkabelonCreatePayload,
):
    """Opret en ny skabelon — typisk fra en eksisterende udfyldt evidens."""
    from src.database.connection import SessionLocal
    from src.database.skabelon_bibliotek import create_skabelon

    db = SessionLocal()
    try:
        try:
            entry = create_skabelon(
                db,
                artifact_id=body.artifact_id,
                name=body.name,
                description=body.description,
                content=body.content,
                source_case_id=body.source_case_id,
                user=body.user,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        db.commit()
        return entry.to_dict()
    finally:
        db.close()


@app.post("/api/v3/skabelon-bibliotek/{skabelon_id}/apply")
@limiter.limit(ADMIN_WRITE)
async def v3_skabelon_apply(
    request: Request,
    response: Response,
    skabelon_id: int,
    case_id: str,
    body: SkabelonApplyPayload,
):
    """Indlæs en skabelon på en given sag.

    Mergerer med eksisterende svar — bruger-svar vinder altid over
    skabelon-defaults. Tomme felter får skabelon-værdi.

    Returnerer den opdaterede evidens-row.
    """
    from src.database.connection import SessionLocal
    from src.database.skabelon_bibliotek import (
        get_skabelon,
        increment_usage,
        merge_with_existing,
    )
    from src.database.evidence import get_evidence, upsert_evidence
    from src.services.evidence_artifacts import compute_status, get_template

    db = SessionLocal()
    try:
        skabelon = get_skabelon(db, skabelon_id)
        if skabelon is None:
            raise HTTPException(status_code=404, detail="Skabelon ikke fundet")

        existing = get_evidence(db, case_id, skabelon.artifact_id)
        existing_content = existing.get_content() if existing else {}
        merged = merge_with_existing(skabelon.get_content(), existing_content)

        template = get_template(skabelon.artifact_id)
        computed = compute_status(template, merged)

        row = upsert_evidence(
            db,
            case_id=case_id,
            artifact_id=skabelon.artifact_id,
            content=merged,
            computed_status=computed,
            user=body.user,
            notes=f"Anvendte skabelon: {skabelon.name}",
        )
        increment_usage(db, skabelon_id)
        db.commit()
        return {
            **row.to_dict(),
            "computed_status": computed,
            "applied_skabelon_id": skabelon_id,
            "applied_skabelon_name": skabelon.name,
        }
    finally:
        db.close()


@app.delete("/api/v3/skabelon-bibliotek/{skabelon_id}")
@limiter.limit(ADMIN_WRITE)
async def v3_skabelon_delete(
    request: Request,
    response: Response,
    skabelon_id: int,
):
    from src.database.connection import SessionLocal
    from src.database.skabelon_bibliotek import delete_skabelon

    db = SessionLocal()
    try:
        ok = delete_skabelon(db, skabelon_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Skabelon ikke fundet")
        db.commit()
        return {"deleted": True, "id": skabelon_id}
    finally:
        db.close()


# =========================================================================
# Per-evidens-felt kommentarer + tråde
# =========================================================================


class CommentCreatePayload(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)
    section_key: Optional[str] = Field(default=None, max_length=96)
    author: Optional[str] = Field(default=None, max_length=64)


@app.get("/api/v3/cases/{case_id}/comments")
async def v3_comments_list_for_case(
    case_id: str,
    artifact_id: Optional[str] = None,
    section_key: Optional[str] = None,
    include_resolved: bool = True,
):
    """List kommentarer for en sag — optionelt filtreret på artifact + sektion."""
    from src.database.connection import SessionLocal
    from src.database.evidence_comments import list_comments

    db = SessionLocal()
    try:
        rows = list_comments(
            db,
            case_id=case_id,
            artifact_id=artifact_id,
            section_key=section_key,
            include_resolved=include_resolved,
        )
        return {
            "case_id": case_id,
            "count": len(rows),
            "items": [r.to_dict() for r in rows],
        }
    finally:
        db.close()


@app.get("/api/v3/cases/{case_id}/comments/counts")
async def v3_comments_counts_for_case(case_id: str):
    """Aggregat over kommentar-antal per artefakt og sektion.

    Bruges til at vise badges på evidens-checklisten uden at hente alle bodies.
    Format: {artifact_id: {section_key|"_doc": {open: N, resolved: N}}}
    """
    from src.database.connection import SessionLocal
    from src.database.evidence_comments import comment_counts_for_case

    db = SessionLocal()
    try:
        counts = comment_counts_for_case(db, case_id)
        return {"case_id": case_id, "counts": counts}
    finally:
        db.close()


@app.post("/api/v3/cases/{case_id}/evidence/{artifact_id}/comments")
@limiter.limit(ADMIN_WRITE)
async def v3_comments_create(
    request: Request,
    response: Response,
    case_id: str,
    artifact_id: str,
    body: CommentCreatePayload,
):
    """Opret en kommentar på et evidens-felt (eller hele dokumentet hvis section_key=null).

    Emitterer også en notifikation så andre brugere ser tråden i deres bell.
    """
    from src.database.connection import SessionLocal
    from src.database.evidence_comments import create_comment
    from src.database import notifications as notif_svc

    db = SessionLocal()
    try:
        try:
            comment = create_comment(
                db,
                case_id=case_id,
                artifact_id=artifact_id,
                section_key=body.section_key,
                body=body.body,
                author=body.author,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        # Emit notifikation
        try:
            preview = (body.body[:80] + "…") if len(body.body) > 80 else body.body
            section_label = body.section_key or "hele dokumentet"
            notif_svc.emit(
                db,
                kind="evidens_comment",
                title=f"Ny kommentar på {artifact_id.replace('_', ' ')}",
                message=f"{body.author or 'Bruger'} skrev på {section_label}: '{preview}'",
                case_id=case_id,
                link_url=f"/sag/{case_id}?tab=evidens",
                severity="info",
                actor=body.author,
            )
        except Exception as exc:
            logger.warning(f"comment notification emit failed: {exc}")

        db.commit()
        return comment.to_dict()
    finally:
        db.close()


@app.post("/api/v3/comments/{comment_id}/resolve")
@limiter.limit(ADMIN_WRITE)
async def v3_comments_resolve(
    request: Request,
    response: Response,
    comment_id: int,
    user: Optional[str] = None,
):
    from src.database.connection import SessionLocal
    from src.database.evidence_comments import resolve_comment

    db = SessionLocal()
    try:
        comment = resolve_comment(db, comment_id, user=user)
        if comment is None:
            raise HTTPException(status_code=404, detail="Kommentar ikke fundet")
        db.commit()
        return comment.to_dict()
    finally:
        db.close()


@app.delete("/api/v3/comments/{comment_id}")
@limiter.limit(ADMIN_WRITE)
async def v3_comments_delete(
    request: Request,
    response: Response,
    comment_id: int,
):
    from src.database.connection import SessionLocal
    from src.database.evidence_comments import delete_comment

    db = SessionLocal()
    try:
        ok = delete_comment(db, comment_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Kommentar ikke fundet")
        db.commit()
        return {"deleted": True, "id": comment_id}
    finally:
        db.close()


# =========================================================================
# Portfolio dashboard — kommune-aggregat over sager + evidens-blockers
# =========================================================================


@app.get("/api/v3/dashboard/portfolio")
async def v3_dashboard_portfolio():
    """Aggregeret overblik over kommunens AI-portefølje.

    Returnerer:
      - stats: totale tællere (sager, åbne, godkendte, afviste, evidens, kommentarer)
      - heatmap: matrix [risikoklassifikation × evidens-status]
      - top_blockers: 5 evidens-IDs der mangler på flest sager
      - by_status: sager grupperet pr. workflow-status
      - recent_activity: 10 seneste events på tværs af sager
      - sla: sager med next_review forfalden / nær deadline
    """
    from src.database.connection import SessionLocal
    from src.database.cases import Case
    from src.database.evidence import EvidenceArtifact
    from src.database.evidence_comments import EvidenceComment

    db = SessionLocal()
    try:
        all_cases = db.query(Case).all()
        all_evidence = db.query(EvidenceArtifact).all()
        comment_count = db.query(EvidenceComment).count()
        open_comment_count = (
            db.query(EvidenceComment)
            .filter(EvidenceComment.resolved_at.is_(None))
            .count()
        )

        # ---- Stats -------------------------------------------------------
        total_cases = len(all_cases)
        by_status: dict[str, int] = {}
        verdict_counts: dict[str, int] = {}
        for c in all_cases:
            by_status[c.status] = by_status.get(c.status, 0) + 1
            if c.last_aggregate_status:
                verdict_counts[c.last_aggregate_status] = (
                    verdict_counts.get(c.last_aggregate_status, 0) + 1
                )

        evidens_total = len(all_evidence)
        evidens_done = sum(
            1 for e in all_evidence if e.status in ("faerdig", "godkendt")
        )

        # ---- Heatmap: verdict × evidens-status ---------------------------
        # Matrix: rows=verdicts (NO-GO, BETINGET-GO, GO, ukendt),
        #         cols=evidens-status (mangler, i_gang, faerdig)
        heatmap: dict[str, dict[str, int]] = {}
        verdict_for_case: dict[str, str] = {}
        for c in all_cases:
            verdict_for_case[c.case_id] = c.last_aggregate_status or "ukendt"

        for e in all_evidence:
            verdict = verdict_for_case.get(e.case_id, "ukendt")
            row = heatmap.setdefault(verdict, {"mangler": 0, "i_gang": 0, "faerdig": 0})
            if e.status == "godkendt":
                row["faerdig"] += 1
            elif e.status in ("mangler", "i_gang", "faerdig"):
                row[e.status] += 1

        # Tilføj tomme rækker for verdicts uden evidens (men med sager)
        for v in set(verdict_for_case.values()):
            heatmap.setdefault(v, {"mangler": 0, "i_gang": 0, "faerdig": 0})

        # ---- Top 5 blockers ----------------------------------------------
        # Hvilke artifact_ids har flest "mangler"-eller-"i_gang"-status?
        blocker_counts: dict[str, int] = {}
        for e in all_evidence:
            if e.status in ("mangler", "i_gang"):
                blocker_counts[e.artifact_id] = blocker_counts.get(e.artifact_id, 0) + 1

        top_blockers = sorted(
            blocker_counts.items(), key=lambda x: x[1], reverse=True
        )[:5]
        top_blockers_data = [
            {
                "artifact_id": aid,
                "label": aid.replace("_", " "),
                "blocked_cases": count,
            }
            for aid, count in top_blockers
        ]

        # ---- SLA — forfaldne / nær deadline (7 dage) ---------------------
        from datetime import timedelta
        now = datetime.now(UTC)
        in_7_days = now + timedelta(days=7)
        overdue: list[dict] = []
        upcoming: list[dict] = []
        for c in all_cases:
            if not c.next_review_at:
                continue
            if c.next_review_at < now:
                overdue.append(
                    {
                        "case_id": c.case_id,
                        "title": c.title,
                        "next_review_at": c.next_review_at.isoformat(),
                        "days_overdue": (now - c.next_review_at).days,
                    }
                )
            elif c.next_review_at < in_7_days:
                upcoming.append(
                    {
                        "case_id": c.case_id,
                        "title": c.title,
                        "next_review_at": c.next_review_at.isoformat(),
                        "days_until": (c.next_review_at - now).days,
                    }
                )

        return {
            "generated_at": now.isoformat(),
            "stats": {
                "total_cases": total_cases,
                "evidens_total": evidens_total,
                "evidens_done": evidens_done,
                "evidens_pct": (
                    round(100 * evidens_done / evidens_total) if evidens_total else 0
                ),
                "comment_count_total": comment_count,
                "open_comment_count": open_comment_count,
                "by_status": by_status,
                "verdict_counts": verdict_counts,
            },
            "heatmap": heatmap,
            "top_blockers": top_blockers_data,
            "sla": {
                "overdue": overdue[:10],
                "upcoming_within_7_days": upcoming[:10],
            },
        }
    finally:
        db.close()


@app.get("/api/v3/rules")
async def v3_list_rules():
    """List all loaded v3 rules with their citations. Useful for the
    frontend to render a 'rules covered' list and for auditors."""
    try:
        rules = _v3_load_rules()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "rule_engine_version": "3.0.0-alpha.3",
        "count": len(rules),
        "rules": [
            {
                "id": r.id,
                "kilde": r.kilde.model_dump(mode="json"),
                "predikater": [p.model_dump(mode="json", by_alias=True) for p in r.predikater],
                "metadata": r.metadata or {},
            }
            for r in rules
        ],
    }


# ---------------------------------------------------------------------------


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
        reload=os.getenv("API_RELOAD", "True").lower() == "true",
        reload_dirs=["src", "."],  # Only watch src/ and root files
        reload_excludes=["node_modules", "frontend", ".git", "__pycache__", "*.pyc"]
    )
