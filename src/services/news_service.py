"""Service-lag der forbinder LiveNewsScraper med API'et"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import AsyncContextManager, Callable, List, Optional, Sequence

from pydantic import ValidationError

from src.core.news_models import (
    NewsArticle,
    NewsFeedPayload,
    NewsImportance,
    NewsSourceStatus,
    SourceFetchStatus,
)
from src.news.live_scraper import LiveNewsScraper, NewsItem

logger = logging.getLogger(__name__)


ScraperFactory = Callable[[], AsyncContextManager[LiveNewsScraper]]


class NewsService:
    """Håndterer caching, fallback og normalisering af nyheder"""

    def __init__(
        self,
        *,
        cache_ttl_seconds: int = 15 * 60,
        max_items: int = 50,
        scraper_factory: Optional[ScraperFactory] = None,
        fallback_path: Optional[Path] = None,
    ) -> None:
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self.max_items = max_items
        self._scraper_factory = scraper_factory or (lambda: LiveNewsScraper())
        self._fallback_path = fallback_path or Path("data/news_fallback.json")

        self._cache: List[NewsArticle] = []
        self._cache_ts: Optional[datetime] = None
        default_sources = self._discover_sources()
        self._source_status: dict[str, NewsSourceStatus] = {
            source: NewsSourceStatus(source=source, status=SourceFetchStatus.NO_RECENT_ITEMS)
            for source in default_sources
        }
        self._lock = asyncio.Lock()

    async def get_latest_news(
        self,
        *,
        force_refresh: bool = False,
        category: Optional[str] = None,
        source: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> NewsFeedPayload:
        """Returnér seneste nyheder, opdater cache hvis nødvendigt"""

        async with self._lock:
            if force_refresh or self._cache_expired:
                await self._refresh_cache()

            items = self._cache

            if category:
                items = [item for item in items if item.category == category]

            if source:
                items = [item for item in items if item.source.lower() == source.lower()]

            if limit:
                items = items[: limit or self.max_items]

            payload = NewsFeedPayload(
                items=items,
                last_updated=self._cache_ts,
                cache_ttl_seconds=int(self.cache_ttl.total_seconds()),
                source_status=list(self._source_status.values()),
            )
            return payload

    @property
    def _cache_expired(self) -> bool:
        if not self._cache_ts:
            return True
        return datetime.now(UTC) - self._cache_ts > self.cache_ttl

    async def _refresh_cache(self) -> None:
        """Forsøg at hente nye nyheder og opdater cache"""

        logger.info("Refreshing news cache")
        items: Sequence[NewsItem] = []

        try:
            async with self._scraper_factory() as scraper:
                items = await scraper.fetch_latest_news()
        except Exception as exc:  # pragma: no cover - logging path
            logger.warning("Live news scraping failed: %s", exc)
            self._mark_sources_error(str(exc))

        articles: List[NewsArticle] = []
        if items:
            articles = self._convert_items(items)
            articles = self._sort_articles(articles)
            self._update_source_status(articles)
            await self._write_fallback_cache(articles)
        else:
            logger.info("Falling back to cached news file")
            articles = await self._load_fallback_articles()
            articles = self._sort_articles(articles)
            self._update_source_status(articles, fallback=True)

        self._cache = articles[: self.max_items]
        self._cache_ts = datetime.now(UTC)

    def _convert_items(self, items: Sequence[NewsItem]) -> List[NewsArticle]:
        converted: List[NewsArticle] = []
        for item in items[: self.max_items]:
            try:
                url = item.url
                # ensure URL validation handles http/https
                # HttpUrl requires scheme and host; fallback to AnyHttpUrl already handles
                importance_value = (item.importance or NewsImportance.MEDIUM.value).lower()
                try:
                    importance = NewsImportance(importance_value)
                except ValueError:
                    importance = NewsImportance.MEDIUM

                article = NewsArticle(
                    title=item.title,
                    url=url,
                    source=item.source,
                    category=item.category,
                    summary=item.summary,
                    published_at=item.published_date,
                    importance=importance,
                    keywords=item.keywords or [],
                    scraped_at=item.scraped_at,
                    content_snippet=item.content_snippet or None,
                )
            except ValidationError as exc:
                logger.debug("Skipping news item due to validation error: %s", exc)
                continue
            except ValueError:
                # Guard mod ukendte importance levels
                article = NewsArticle(
                    title=item.title,
                    url=item.url,
                    source=item.source,
                    category=item.category,
                    summary=item.summary,
                    published_at=item.published_date,
                    importance=NewsImportance.MEDIUM,
                    keywords=item.keywords or [],
                    scraped_at=item.scraped_at,
                    content_snippet=item.content_snippet or None,
                )
            converted.append(article)
        return converted

    def _update_source_status(self, articles: Sequence[NewsArticle], *, fallback: bool = False) -> None:
        now = datetime.now(UTC)
        counts: dict[str, int] = {}
        for article in articles:
            counts[article.source] = counts.get(article.source, 0) + 1

        for source_name, count in counts.items():
            current = self._source_status.get(source_name)
            if fallback and count == 0:
                status = SourceFetchStatus.NO_RECENT_ITEMS
            else:
                status = SourceFetchStatus.AVAILABLE
            self._source_status[source_name] = NewsSourceStatus(
                source=source_name,
                status=status,
                last_attempt=now,
                last_success=now if not fallback else current.last_success if current else None,
                last_error=current.last_error if current else None,
                items_collected=count,
            )

        if fallback:
            # Mark kilder uden artikler som manglende
            for source_name, status in self._source_status.items():
                if counts.get(source_name, 0) == 0:
                    self._source_status[source_name] = status.model_copy(update={
                        "status": SourceFetchStatus.NO_RECENT_ITEMS,
                        "last_attempt": now,
                        "items_collected": 0,
                    })

    def _mark_sources_error(self, error_message: str) -> None:
        now = datetime.now(UTC)
        for source, status in list(self._source_status.items()):
            self._source_status[source] = status.model_copy(
                update={
                    "status": SourceFetchStatus.ERROR,
                    "last_attempt": now,
                    "last_error": error_message,
                }
            )

    async def _write_fallback_cache(self, articles: Sequence[NewsArticle]) -> None:
        try:
            data = [article.model_dump(mode="json") for article in articles]

            def _write() -> None:
                self._fallback_path.parent.mkdir(parents=True, exist_ok=True)
                self._fallback_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

            await asyncio.to_thread(_write)
        except Exception as exc:  # pragma: no cover - IO failure scenario
            logger.warning("Could not persist news fallback cache: %s", exc)

    async def _load_fallback_articles(self) -> List[NewsArticle]:
        if not self._fallback_path.exists():
            logger.info("No fallback cache found, returning empty list")
            return []

        try:

            def _read() -> List[NewsArticle]:
                raw = json.loads(self._fallback_path.read_text())
                return [NewsArticle.model_validate(item) for item in raw]

            return await asyncio.to_thread(_read)
        except Exception as exc:  # pragma: no cover - fallback parse failure
            logger.warning("Failed to load fallback news cache: %s", exc)
            return []

    def _discover_sources(self) -> List[str]:
        try:
            scraper = LiveNewsScraper()
            return list(scraper.sources.keys())
        except Exception:  # pragma: no cover - should never happen
            return []

    def _sort_articles(self, articles: Sequence[NewsArticle]) -> List[NewsArticle]:
        """Returner artikler sorteret efter nyeste udgivelses- eller scrape-tidspunkt."""
        epoch = datetime.fromtimestamp(0, tz=UTC)

        def authored_at(article: NewsArticle) -> datetime:
            if article.published_at:
                return article.published_at
            if article.scraped_at:
                return article.scraped_at
            return epoch

        return sorted(articles, key=authored_at, reverse=True)


__all__ = ["NewsService"]
