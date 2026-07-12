"""Citation-verifier — verificerer at hver YAML-regels lov-citat stadig findes
ordret i kilden (EUR-Lex, Retsinformation osv.).

Dette giver kommunale jurister noget ailex.dk ikke kan: bevisbart at vores
citater er friske ift. den faktiske lovtekst — fitness-funktion der matcher
kommunal grundighed.

Køres dagligt via APScheduler. Per regel:
  1. Hent kilde.url (cached 24h via httpx)
  2. Normalisér whitespace (citater fra YAML kan være formatteret anderledes
     end siden de stammer fra)
  3. Søg efter kilde.citat som substring
  4. Hvis fundet: opdater sidst_verificeret = i dag
  5. Hvis ikke fundet: marker regel som flagget_juridisk_review = true
     og log advarsel i RuleFreshness-tabellen.

Resultaterne persisteres så frontend kan vise grøn/rød/grå status.
"""

from __future__ import annotations

import logging
import os
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Optional
from urllib.parse import urldefrag, urlparse

import httpx
from sqlalchemy import Column, DateTime, String, Text, Boolean, Integer
from sqlalchemy.orm import Session

from src.database.connection import Base
from src.rule_engine.models import Rule

logger = logging.getLogger(__name__)


# ---- Database model for verification results --------------------------------


class RuleFreshness(Base):
    """Latest verification status per rule_id. Updated daily."""

    __tablename__ = "rule_freshness"

    rule_id = Column(String(128), primary_key=True)
    last_checked_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    citation_found = Column(Boolean, nullable=False, default=False)
    flagged_for_review = Column(Boolean, nullable=False, default=False)
    http_status = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    source_url = Column(Text, nullable=True)
    snippet = Column(Text, nullable=True)  # short context where citat was found
    # Which verification method produced the latest result — "requests" for
    # static HTML, "playwright" for SPA-rendered pages. Helps operators see
    # which rules need the slower path.
    verification_method = Column(String(16), nullable=True)

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "last_checked_at": (
                self.last_checked_at.isoformat() if self.last_checked_at else None
            ),
            "citation_found": self.citation_found,
            "flagged_for_review": self.flagged_for_review,
            "http_status": self.http_status,
            "error_message": self.error_message,
            "source_url": self.source_url,
            "snippet": self.snippet,
            "verification_method": self.verification_method,
        }


# ---- Verification logic -----------------------------------------------------


@dataclass
class VerificationResult:
    rule_id: str
    citation_found: bool
    flagged_for_review: bool
    http_status: Optional[int]
    error_message: Optional[str]
    source_url: Optional[str]
    snippet: Optional[str]
    method: str = "requests"  # "requests" or "playwright"


_HTML_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """Strip HTML, normalize Unicode forms (NFKD), collapse whitespace,
    lowercase. Compares text robustly across HTML formatting and unicode
    quote/dash variants."""
    if not text:
        return ""
    text = _HTML_TAG.sub(" ", text)
    text = unicodedata.normalize("NFKD", text)
    # Replace common unicode variants with ASCII equivalents
    text = text.replace(" ", " ")  # non-breaking space
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    text = text.replace("»", '"').replace("«", '"')
    text = _WHITESPACE.sub(" ", text)
    return text.strip().lower()


def _shortest_signature(citat: str, n: int = 100) -> str:
    """Return first N significant chars of citat — used for fuzzy fallback
    when full substring match fails (e.g. site reformatted listing)."""
    sig = _normalize(citat)
    return sig[:n] if len(sig) >= n else sig


def _canonical_source_url(url: str) -> str:
    """Return the fetchable page URL shared by citation fragment variants."""
    page_url, _fragment = urldefrag(url)
    return page_url


def _result_from_source_text(
    rule: Rule,
    source_text: str,
    *,
    http_status: Optional[int],
    method: str,
) -> VerificationResult:
    """Match one rule against already-fetched source text.

    Keeping matching separate from fetching lets a rendered law page serve all
    rules that cite it, instead of launching a browser once per citation.
    """
    raw_url = getattr(rule.kilde, "url", None) if rule.kilde else None
    url = str(raw_url) if raw_url else None
    citat = getattr(rule.kilde, "citat", "") if rule.kilde else ""

    if not url or not citat:
        return VerificationResult(
            rule_id=rule.id,
            citation_found=False,
            flagged_for_review=True,
            http_status=http_status,
            error_message="No source URL or citat",
            source_url=url,
            snippet=None,
            method=method,
        )

    body_normalized = _normalize(source_text or "")
    citat_normalized = _normalize(citat)
    found = citat_normalized in body_normalized
    snippet: Optional[str] = None

    if found:
        idx = body_normalized.find(citat_normalized)
        window_start = max(0, idx - 50)
        window_end = min(len(body_normalized), idx + len(citat_normalized) + 50)
        snippet = body_normalized[window_start:window_end]
    else:
        sig = _shortest_signature(citat, 100)
        if sig and sig in body_normalized:
            found = True
            suffix = " (Playwright-render)" if method == "playwright" else ""
            snippet = f"Delvis match — første 100 tegn fundet{suffix}"

    source_kind = (
        "Playwright-rendered HTML" if method == "playwright" else "kildens HTML"
    )
    return VerificationResult(
        rule_id=rule.id,
        citation_found=found,
        flagged_for_review=not found,
        http_status=http_status,
        error_message=None if found else f"Citat ikke fundet i {source_kind}",
        source_url=url,
        snippet=snippet,
        method=method,
    )


def verify_rule(rule: Rule, *, timeout: float = 15.0) -> VerificationResult:
    """Fetch the rule's source URL and verify the citat appears in it."""
    raw_url = getattr(rule.kilde, "url", None) if rule.kilde else None
    # rule.kilde.url is a Pydantic AnyUrl — coerce to plain string for
    # httpx and SQLAlchemy storage.
    url = str(raw_url) if raw_url else None
    citat = getattr(rule.kilde, "citat", "") if rule.kilde else ""
    rule_id = rule.id

    if not url:
        return VerificationResult(
            rule_id=rule_id,
            citation_found=False,
            flagged_for_review=True,
            http_status=None,
            error_message="No source URL on this rule",
            source_url=None,
            snippet=None,
        )
    if not citat:
        return VerificationResult(
            rule_id=rule_id,
            citation_found=False,
            flagged_for_review=True,
            http_status=None,
            error_message="No citat on this rule",
            source_url=url,
            snippet=None,
        )

    try:
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            r = client.get(url, headers={"User-Agent": "Bifrost/v3 citation-verifier"})
        status = r.status_code
        if status >= 400:
            return VerificationResult(
                rule_id=rule_id,
                citation_found=False,
                flagged_for_review=True,
                http_status=status,
                error_message=f"HTTP {status} from source",
                source_url=url,
                snippet=None,
            )
        return _result_from_source_text(
            rule,
            r.text,
            http_status=status,
            method="requests",
        )
    except httpx.RequestError as exc:
        logger.warning("citation-verify network error for %s: %s", rule_id, exc)
        return VerificationResult(
            rule_id=rule_id,
            citation_found=False,
            flagged_for_review=True,
            http_status=None,
            error_message=f"Network error: {exc}",
            source_url=url,
            snippet=None,
        )
    except Exception as exc:
        logger.exception("citation-verify failed for %s", rule_id)
        return VerificationResult(
            rule_id=rule_id,
            citation_found=False,
            flagged_for_review=True,
            http_status=None,
            error_message=f"Unexpected error: {exc}",
            source_url=url,
            snippet=None,
        )


def persist_result(session: Session, result: VerificationResult) -> RuleFreshness:
    existing = (
        session.query(RuleFreshness)
        .filter(RuleFreshness.rule_id == result.rule_id)
        .one_or_none()
    )
    if existing is None:
        existing = RuleFreshness(rule_id=result.rule_id)
        session.add(existing)
    existing.last_checked_at = datetime.now(UTC)
    existing.citation_found = result.citation_found
    existing.flagged_for_review = result.flagged_for_review
    existing.http_status = result.http_status
    existing.error_message = result.error_message
    existing.source_url = result.source_url
    existing.snippet = result.snippet[:500] if result.snippet else None
    existing.verification_method = result.method
    session.flush()
    return existing


# ---- Playwright fallback ---------------------------------------------------

# Trusted law portals that render content client-side, so requests cannot find
# the citation text. These rules skip directly to Playwright when available.
_KNOWN_SPA_HOSTS = (
    "eur-lex.europa.eu",
    "data.europa.eu",
    "retsinformation.dk",
)


def _looks_like_spa(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").lower()
    return any(
        hostname == host or hostname.endswith(f".{host}") for host in _KNOWN_SPA_HOSTS
    )


def is_playwright_available() -> bool:
    """Check if Playwright + a Chromium browser binary are installed.

    Cheap — does not actually launch a browser. Returns False if either the
    Python package or the browser binary is missing.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False

    try:
        # Trying to find the executable is the cheapest way to confirm the
        # browser is installed without launching it.
        with sync_playwright() as p:
            path = p.chromium.executable_path
            return bool(path) and os.path.exists(path)
    except Exception:
        return False


def _playwright_error_result(rule: Rule, message: str) -> VerificationResult:
    raw_url = getattr(rule.kilde, "url", None) if rule.kilde else None
    return VerificationResult(
        rule_id=rule.id,
        citation_found=False,
        flagged_for_review=True,
        http_status=None,
        error_message=message,
        source_url=str(raw_url) if raw_url else None,
        snippet=None,
        method="playwright",
    )


def _group_rules_by_source(rules: list[Rule]) -> dict[str, list[Rule]]:
    """Group citation rules by the page that must be rendered."""
    grouped: dict[str, list[Rule]] = defaultdict(list)
    for rule in rules:
        raw_url = getattr(rule.kilde, "url", None) if rule.kilde else None
        citat = getattr(rule.kilde, "citat", "") if rule.kilde else ""
        if raw_url and citat:
            grouped[_canonical_source_url(str(raw_url))].append(rule)
    return dict(grouped)


def verify_rules_with_playwright(
    rules: list[Rule], *, timeout_ms: int = 20_000
) -> dict[str, VerificationResult]:
    """Render each unique source page once and verify all citations on it.

    A single Chromium browser and context are reused for the whole run. URL
    fragments are ignored for fetching, so GDPR article links share one render.
    """
    results: dict[str, VerificationResult] = {}
    grouped = _group_rules_by_source(rules)

    for rule in rules:
        raw_url = getattr(rule.kilde, "url", None) if rule.kilde else None
        citat = getattr(rule.kilde, "citat", "") if rule.kilde else ""
        if not raw_url or not citat:
            results[rule.id] = _playwright_error_result(rule, "No source URL or citat")

    if not grouped:
        return results

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        for source_rules in grouped.values():
            for rule in source_rules:
                results[rule.id] = _playwright_error_result(
                    rule, "Playwright not installed"
                )
        return results

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                context = browser.new_context(
                    user_agent="Bifrost/v3 citation-verifier (Playwright)",
                )
                for url, source_rules in grouped.items():
                    page = None
                    try:
                        page = context.new_page()
                        response = page.goto(
                            url,
                            wait_until="domcontentloaded",
                            timeout=timeout_ms,
                        )
                        http_status = response.status if response else None
                        if http_status is not None and http_status >= 400:
                            for rule in source_rules:
                                results[rule.id] = _playwright_error_result(
                                    rule, f"HTTP {http_status} from source"
                                )
                                results[rule.id].http_status = http_status
                            continue

                        # Client-rendered law portals continue hydrating after
                        # DOMContentLoaded. Network-idle is best effort only.
                        try:
                            page.wait_for_load_state("networkidle", timeout=3_000)
                        except Exception:
                            pass
                        rendered_text = page.evaluate(
                            "() => document.body ? document.body.innerText : ''"
                        )
                        for rule in source_rules:
                            results[rule.id] = _result_from_source_text(
                                rule,
                                rendered_text or "",
                                http_status=http_status,
                                method="playwright",
                            )
                    except Exception as exc:
                        logger.exception(
                            "Playwright verification failed for source %s", url
                        )
                        for rule in source_rules:
                            results[rule.id] = _playwright_error_result(
                                rule, f"Playwright error: {exc}"
                            )
                    finally:
                        if page is not None:
                            page.close()
            finally:
                browser.close()
    except Exception as exc:
        logger.exception("Could not start Playwright citation verification")
        for source_rules in grouped.values():
            for rule in source_rules:
                if rule.id not in results:
                    results[rule.id] = _playwright_error_result(
                        rule, f"Playwright error: {exc}"
                    )

    return results


def verify_rule_with_playwright(
    rule: Rule, *, timeout_ms: int = 30_000
) -> VerificationResult:
    """Compatibility wrapper for verifying one rendered source."""
    return verify_rules_with_playwright([rule], timeout_ms=timeout_ms)[rule.id]


def verify_all_rules(
    session: Session,
    rules: list[Rule],
    *,
    enable_playwright_fallback: bool = True,
) -> list[RuleFreshness]:
    """Verify every rule and persist the result. Idempotent — running
    twice in a row produces the same final state.

    Two-pass strategy:
      1. Fast `requests` for static pages. Known client-rendered law portals
         are deferred when Playwright is available.
      2. Render every unique missed source page once and reuse its text for all
         citations on that page.
    """
    results_by_id: dict[str, VerificationResult] = {}
    playwright_available = enable_playwright_fallback and is_playwright_available()
    playwright_rules: list[Rule] = []

    for rule in rules:
        url = str(rule.kilde.url) if rule.kilde and rule.kilde.url else ""
        if playwright_available and _looks_like_spa(url):
            playwright_rules.append(rule)
            continue

        static_result = verify_rule(rule)
        results_by_id[rule.id] = static_result
        if playwright_available and not static_result.citation_found:
            playwright_rules.append(rule)

    if playwright_rules:
        logger.info(
            "Retrying %d rules across %d source pages with Playwright",
            len(playwright_rules),
            len(_group_rules_by_source(playwright_rules)),
        )
        rendered_results = verify_rules_with_playwright(playwright_rules)
        for rule in playwright_rules:
            rendered = rendered_results.get(rule.id)
            current = results_by_id.get(rule.id)
            if rendered is None:
                continue
            # A completed render is the strongest result. If Chromium itself
            # failed, retain a valid static response when one exists.
            if rendered.http_status is not None or current is None:
                results_by_id[rule.id] = rendered

    persisted: list[RuleFreshness] = []
    for rule in rules:
        final_result = results_by_id.get(rule.id)
        if final_result is None:
            continue
        persisted.append(persist_result(session, final_result))
    return persisted


def list_freshness(session: Session) -> list[RuleFreshness]:
    return session.query(RuleFreshness).order_by(RuleFreshness.rule_id).all()


def flagged_rule_ids(session: Session) -> set[str]:
    rows = (
        session.query(RuleFreshness.rule_id)
        .filter(RuleFreshness.flagged_for_review == True)  # noqa: E712
        .all()
    )
    return {r[0] for r in rows}
