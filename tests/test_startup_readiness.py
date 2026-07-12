"""Regression tests for API startup readiness."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from starlette.requests import Request
from starlette.responses import Response

import main as app_main
from src.config import validation
from src.database import connection


class _SchedulerStub:
    def __init__(self):
        self.running = False

    def add_job(self, *_args, **_kwargs):
        return None

    def start(self):
        self.running = True

    def shutdown(self, wait=False):
        self.running = False


@pytest.mark.asyncio
async def test_external_feeds_do_not_block_lifespan_startup(monkeypatch):
    """The API must become ready even when every external feed is stalled."""
    stalled = asyncio.Event()
    refreshes_started: set[str] = set()

    async def stalled_news(*_args, **_kwargs):
        refreshes_started.add("news")
        await stalled.wait()

    async def stalled_ticker(*_args, **_kwargs):
        refreshes_started.add("ticker")
        await stalled.wait()

    monkeypatch.setattr(connection, "init_db", lambda: None)
    monkeypatch.setattr(app_main, "warm_caches_on_startup", lambda **_kwargs: None)
    monkeypatch.setattr(
        app_main,
        "validate_cache_health",
        lambda: {"status": "healthy", "issues": []},
    )
    monkeypatch.setattr(
        validation,
        "build_config_report",
        lambda **_kwargs: SimpleNamespace(critical_failures=[]),
    )
    monkeypatch.setattr(validation, "render_startup_banner", lambda _report: "")
    monkeypatch.setattr(app_main.news_service, "get_latest_news", stalled_news)
    monkeypatch.setattr(app_main.ticker_service, "get_latest", stalled_ticker)
    monkeypatch.setattr(app_main, "kb_scheduler", _SchedulerStub())
    monkeypatch.setattr(app_main, "news_refresh_task", None)
    monkeypatch.setattr(app_main, "ticker_refresh_task", None)

    async def enter_and_exit_lifespan():
        async with app_main.lifespan(app_main.app):
            # Let the newly scheduled refresh tasks begin. They remain stalled,
            # while the lifespan context itself is already serving-ready.
            await asyncio.sleep(0)
            assert refreshes_started == {"news", "ticker"}

    await asyncio.wait_for(enter_and_exit_lifespan(), timeout=1.0)


@pytest.mark.asyncio
async def test_freshness_trigger_supports_rate_limit_headers(monkeypatch):
    """SlowAPI needs a Response argument when the endpoint returns a dict."""
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v3/law/freshness/run",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "app": app_main.app,
        }
    )
    response = Response()

    monkeypatch.setattr(app_main, "_v3_run_citation_verifier", lambda: None)

    async def fake_freshness():
        return {"count": 0, "items": []}

    monkeypatch.setattr(app_main, "v3_law_freshness", fake_freshness)

    result = await app_main.v3_law_freshness_run(
        request=request,
        response=response,
    )

    assert result == {"count": 0, "items": []}
