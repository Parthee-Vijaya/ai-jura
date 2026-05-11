"""Admin-router — operational endpoints til /drift-siden + manuel intervention.

Endpoints:
  - GET  /api/v3/admin/config            → ConfigReport (DB + LLM + scheduler)
  - GET  /api/v3/admin/backups           → list backups
  - POST /api/v3/admin/backups/run       → trigger manuel backup
  - GET  /api/v3/admin/errors            → recent error-buffer
  - POST /api/v3/admin/rag/rebuild-index → embed alle love
  - POST /api/v3/admin/cache/invalidate  → ryd memory/disk cache
  - GET  /api/v3/admin/llm-health        → circuit-breaker status
  - POST /api/v3/admin/llm-health/{p}/reset → manuel breaker-reset

Disse var spredt i main.py — samlet her for nemmere drift-overblik og
isoleret test.
"""

import asyncio
import time
from datetime import datetime, UTC

from fastapi import APIRouter, Request, Response

from src.api.error_envelope import AppError
from src.api.rate_limiting import limiter, ADMIN_WRITE

router = APIRouter(prefix="/api/v3/admin", tags=["admin"])


# ---- Config ---------------------------------------------------------------


@router.get("/config")
async def admin_config():
    """ConfigReport — bruges af build-time diagnostic-modal og /drift.

    Kører ~50ms (DB-ping + LM Studio-ping max 2s timeout). Sikker at kalde
    ved hver page refresh.
    """
    from src.config.validation import build_config_report
    # Hent scheduler fra app-state hvis tilgængelig (kb_scheduler defineret i main)
    try:
        import main  # late-import for at undgå circular
        scheduler = getattr(main, "kb_scheduler", None)
    except Exception:
        scheduler = None

    def _build():
        return build_config_report(scheduler=scheduler).to_dict()

    return await asyncio.to_thread(_build)


# ---- Backups --------------------------------------------------------------


@router.get("/backups")
async def admin_backups():
    """List eksisterende database-backups + retention-policy + rsync-mål."""
    from src.services.backup_service import list_backups
    return await asyncio.to_thread(list_backups)


@router.post("/backups/run")
@limiter.limit(ADMIN_WRITE)
async def admin_backups_run(request: Request, response: Response):
    """Manuel trigger af pg_dump-backup. Returnerer summary med path,
    størrelse og varighed."""
    from src.services.backup_service import run_backup
    return await asyncio.to_thread(run_backup, "manual")


# ---- Errors ---------------------------------------------------------------


@router.get("/errors")
async def admin_errors(limit: int = 50):
    """Return the most recent errors captured by the local error-buffer.

    Used by the /drift page to give an at-a-glance view of recent failures
    without requiring an external error tracking platform.
    """
    from src.utils.observability import recent_errors
    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500
    items = recent_errors(limit=limit)
    return {"count": len(items), "errors": items}


# ---- RAG ------------------------------------------------------------------


@router.post("/rag/rebuild-index")
@limiter.limit(ADMIN_WRITE)
async def admin_rag_rebuild(request: Request, response: Response):
    """Genopbyg lov-RAG-embeddings-indekset.

    Kører `LawRAG.build()` der embedder hver lov-paragraf og persisterer
    til `data/law_embeddings.json`. Tager 1-5 min for ~7000 chunks.
    """
    from src.services.law_rag import LawRAG

    t0 = time.monotonic()
    try:
        rag = LawRAG()
        result = rag.build()
        elapsed = round(time.monotonic() - t0, 1)
        return {"status": "ok", "build_seconds": elapsed, **result}
    except Exception as exc:
        raise AppError(
            "rag_rebuild_failed",
            f"Embedding-rebuild fejlede: {exc}",
            status=500,
            hint="Tjek at OPENAI_API_KEY / LM_STUDIO_BASE_URL er sat",
        )


# ---- Cache ----------------------------------------------------------------


@router.post("/cache/invalidate")
@limiter.limit(ADMIN_WRITE)
async def admin_cache_invalidate(
    request: Request,
    response: Response,
    scope: str = "all",
):
    """Manuel cache-invalidering.

    scope:
      - "memory" — kun in-memory LRU (evidens-templates, KB-stats)
      - "disk" — disk-baseret cache (news, web research)
      - "all" — begge
    """
    from src.cache.memory_cache import clear_memory_cache
    from src.cache.disk_cache import clear_all_disk_cache

    cleared = {"memory": 0, "disk": 0}
    if scope in ("memory", "all"):
        clear_memory_cache()
        cleared["memory"] = 1
    if scope in ("disk", "all"):
        cleared["disk"] = clear_all_disk_cache()

    return {
        "scope": scope,
        "cleared": cleared,
        "timestamp": datetime.now(UTC).isoformat(),
    }


# ---- LLM health (circuit breakers) ---------------------------------------


@router.get("/llm-health")
async def admin_llm_health():
    """LLM-provider circuit-breaker status — backs /drift's "LLM"-card.

    Viser pr. provider (lm_studio, azure_openai, openai):
      - state: closed | half_open | open
      - failure_count, success_count, total_opens

    En åben breaker betyder at LLM-kald afvises lige nu — frontend bør
    vise "midlertidigt nede" i stedet for at vente.
    """
    from src.utils.llm_resilience import all_breaker_stats
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "providers": all_breaker_stats(),
    }


@router.post("/llm-health/{provider}/reset")
async def admin_llm_reset_breaker(provider: str):
    """Manuelt reset en breaker til closed. Bruges når man har fixet en
    LLM-problem og vil ikke vente på timeout."""
    from src.utils.llm_resilience import get_breaker
    try:
        breaker = get_breaker(provider)
    except ValueError as exc:
        raise AppError("unknown_provider", str(exc), status=404)
    breaker.reset()
    return {
        "provider": provider,
        "state": "closed",
        "reset_at": datetime.now(UTC).isoformat(),
    }
