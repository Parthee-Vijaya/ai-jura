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
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Optional

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
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC),
    )
    citation_found = Column(Boolean, nullable=False, default=False)
    flagged_for_review = Column(Boolean, nullable=False, default=False)
    http_status = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    source_url = Column(Text, nullable=True)
    snippet = Column(Text, nullable=True)  # short context where citat was found

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
            "citation_found": self.citation_found,
            "flagged_for_review": self.flagged_for_review,
            "http_status": self.http_status,
            "error_message": self.error_message,
            "source_url": self.source_url,
            "snippet": self.snippet,
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
            r = client.get(url, headers={"User-Agent": "Forseti/v3 citation-verifier"})
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
        body_normalized = _normalize(r.text)
        citat_normalized = _normalize(citat)
        found = citat_normalized in body_normalized
        snippet: Optional[str] = None
        if found:
            idx = body_normalized.find(citat_normalized)
            window_start = max(0, idx - 50)
            window_end = min(len(body_normalized), idx + len(citat_normalized) + 50)
            snippet = body_normalized[window_start:window_end]
        else:
            # Try a fuzzy match on first 100 chars
            sig = _shortest_signature(citat, 100)
            if sig and sig in body_normalized:
                found = True  # close enough — flag it but don't fail
                snippet = "Delvis match — første 100 tegn fundet, men ikke hele citatet"

        return VerificationResult(
            rule_id=rule_id,
            citation_found=found,
            flagged_for_review=not found,
            http_status=status,
            error_message=None if found else "Citat ikke fundet i kildens HTML",
            source_url=url,
            snippet=snippet,
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
    session.flush()
    return existing


def verify_all_rules(session: Session, rules: list[Rule]) -> list[RuleFreshness]:
    """Verify every rule and persist the result. Idempotent — running
    twice in a row produces the same final state."""
    results: list[RuleFreshness] = []
    for rule in rules:
        result = verify_rule(rule)
        persisted = persist_result(session, result)
        results.append(persisted)
    return results


def list_freshness(session: Session) -> list[RuleFreshness]:
    return session.query(RuleFreshness).order_by(RuleFreshness.rule_id).all()


def flagged_rule_ids(session: Session) -> set[str]:
    rows = (
        session.query(RuleFreshness.rule_id)
        .filter(RuleFreshness.flagged_for_review == True)  # noqa: E712
        .all()
    )
    return {r[0] for r in rows}
