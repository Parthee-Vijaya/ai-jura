from datetime import datetime, timezone

import pytest

from src.core.news_models import NewsImportance
from src.news.live_scraper import NewsItem
from src.services.news_service import NewsService


class _DummyScraper:
    def __init__(self, items):
        self._items = items

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def fetch_latest_news(self):
        return self._items


class _FailingScraper(_DummyScraper):
    async def fetch_latest_news(self):
        raise RuntimeError("network unavailable")


@pytest.mark.asyncio
async def test_news_service_returns_articles_and_persists_fallback(tmp_path):
    published = datetime(2024, 9, 15, 12, 0, tzinfo=timezone.utc)
    scraped = datetime(2024, 9, 15, 12, 5, tzinfo=timezone.utc)
    items = [
        NewsItem(
            title="AI Act guidance released",
            url="https://example.com/ai-act",
            source="EU Commission",
            published_date=published,
            category="eu_news",
            summary="Latest guidance on AI Act implementation.",
            keywords=["AI Act", "implementation"],
            importance="high",
            scraped_at=scraped,
            content_snippet="Key obligations summarised",
        )
    ]

    fallback_path = tmp_path / "news_cache.json"
    service = NewsService(
        cache_ttl_seconds=60,
        scraper_factory=lambda: _DummyScraper(items),
        fallback_path=fallback_path,
        max_items=10,
    )

    payload = await service.get_latest_news(force_refresh=True)

    assert payload.items, "service should return news from scraper"
    assert payload.items[0].title == "AI Act guidance released"
    assert payload.items[0].importance == NewsImportance.HIGH
    assert fallback_path.exists(), "fallback cache should be written"

    # Ensure fallback is used when scraper fails
    failing_service = NewsService(
        cache_ttl_seconds=60,
        scraper_factory=lambda: _FailingScraper(items),
        fallback_path=fallback_path,
        max_items=10,
    )

    fallback_payload = await failing_service.get_latest_news(force_refresh=True)
    assert fallback_payload.items, "fallback cache should be returned when scraper fails"
    assert fallback_payload.items[0].title == "AI Act guidance released"
    assert any(status.status.value in {"available", "no_recent_items", "error"} for status in fallback_payload.source_status)
