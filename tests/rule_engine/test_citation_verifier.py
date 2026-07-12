"""Tests for citation-verifier (M3) — normalization + persistence logic.

Network calls (verify_rule) are not exercised here; they're integration-level.
We test the deterministic parts: text normalization, snippet extraction,
DB persistence and flagged_rule_ids querying.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.connection import Base
from src.rule_engine import audit  # noqa: F401
from src.services import citation_verifier as v3_freshness
from src.services.citation_verifier import (
    _canonical_source_url,
    _group_rules_by_source,
    _looks_like_spa,
    _normalize,
    _read_rendered_body,
    _result_from_source_text,
    _shortest_signature,
    flagged_rule_ids,
    list_freshness,
    persist_result,
    VerificationResult,
    verify_all_rules,
)


def _rule(rule_id: str, url: str, citat: str = "Et tilstrækkeligt langt lovcitat"):
    return SimpleNamespace(
        id=rule_id,
        kilde=SimpleNamespace(url=url, citat=citat),
    )


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    s = Session()
    try:
        yield s
    finally:
        s.close()


class TestNormalize:
    def test_strips_html_tags(self):
        assert _normalize("<p>hello <b>world</b></p>") == "hello world"

    def test_collapses_whitespace(self):
        assert _normalize("a   b\n\nc\td") == "a b c d"

    def test_handles_unicode_quotes(self):
        # Curly quotes → straight quotes
        assert '"hello"' in _normalize("“hello”")

    def test_handles_unicode_dashes(self):
        # em-dash → ascii-hyphen
        assert "-" in _normalize("a—b")

    def test_lowercases(self):
        assert _normalize("HELLO") == "hello"

    def test_empty_input(self):
        assert _normalize("") == ""
        assert _normalize(None) == ""


class TestShortestSignature:
    def test_returns_first_n_chars(self):
        text = "alle de gode regler "
        assert _shortest_signature(text, 10) == "alle de go"

    def test_normalizes_input(self):
        text = "<p>Hello World</p>"
        assert _shortest_signature(text, 10) == "hello worl"

    def test_short_text_returned_in_full(self):
        sig = _shortest_signature("kort", n=100)
        assert sig == "kort"


class TestSharedSourceMatching:
    def test_canonical_url_strips_article_fragment(self):
        assert _canonical_source_url("https://example.com/law#art_22") == (
            "https://example.com/law"
        )

    def test_dynamic_source_detection_checks_hostname_boundary(self):
        assert _looks_like_spa("https://eur-lex.europa.eu/eli/reg/2024/1689")
        assert not _looks_like_spa("https://eur-lex.europa.eu.evil.example/law")

    def test_groups_fragment_variants_under_one_source_page(self):
        rules = [
            _rule("gdpr.art5.test", "https://example.com/gdpr#art_5"),
            _rule("gdpr.art22.test", "https://example.com/gdpr#art_22"),
            _rule("ai_act.art5.test", "https://example.com/ai-act"),
        ]

        grouped = _group_rules_by_source(rules)

        assert set(grouped) == {
            "https://example.com/gdpr",
            "https://example.com/ai-act",
        }
        assert [rule.id for rule in grouped["https://example.com/gdpr"]] == [
            "gdpr.art5.test",
            "gdpr.art22.test",
        ]

    def test_matches_multiple_rules_against_reused_text(self):
        source = "Indledning. Et tilstrækkeligt langt lovcitat. Afslutning."
        result = _result_from_source_text(
            _rule("gdpr.art5.test", "https://example.com/gdpr"),
            source,
            http_status=200,
            method="playwright",
        )

        assert result.citation_found is True
        assert result.flagged_for_review is False
        assert result.method == "playwright"

    def test_waits_for_hydrated_document_before_reading_body(self):
        class HydratingPage:
            def __init__(self):
                self.text = "Henter lovtekst"
                self.calls = []

            def wait_for_function(self, expression, timeout):
                self.calls.append(("hydration", expression, timeout))
                self.text = "x" * 6_000

            def wait_for_load_state(self, state, timeout):
                self.calls.append(("load-state", state, timeout))

            def evaluate(self, _expression):
                self.calls.append(("evaluate",))
                return self.text

        page = HydratingPage()

        rendered = _read_rendered_body(page, timeout_ms=20_000)

        assert len(rendered) == 6_000
        assert page.calls[0][0] == "hydration"
        assert page.calls[-1][0] == "evaluate"

    def test_verify_all_batches_dynamic_rules_in_one_call(self, session, monkeypatch):
        rules = [
            _rule(
                "gdpr.art5.test",
                "https://eur-lex.europa.eu/eli/reg/2016/679/oj/dan#art_5",
            ),
            _rule(
                "gdpr.art22.test",
                "https://eur-lex.europa.eu/eli/reg/2016/679/oj/dan#art_22",
            ),
        ]
        batches = []

        monkeypatch.setattr(v3_freshness, "is_playwright_available", lambda: True)

        def fake_batch(batch):
            batches.append(batch)
            return {
                rule.id: VerificationResult(
                    rule.id,
                    True,
                    False,
                    200,
                    None,
                    str(rule.kilde.url),
                    "found",
                    method="playwright",
                )
                for rule in batch
            }

        monkeypatch.setattr(
            v3_freshness,
            "verify_rules_with_playwright",
            fake_batch,
        )
        monkeypatch.setattr(
            v3_freshness,
            "verify_rule",
            lambda _rule: pytest.fail("known dynamic sources must skip static fetch"),
        )

        rows = verify_all_rules(session, rules)

        assert len(batches) == 1
        assert [rule.id for rule in batches[0]] == [
            "gdpr.art5.test",
            "gdpr.art22.test",
        ]
        assert len(rows) == 2
        assert all(row.citation_found for row in rows)


class TestPersistence:
    def test_persist_creates_new_row(self, session):
        result = VerificationResult(
            rule_id="ai_act.art13.test",
            citation_found=True,
            flagged_for_review=False,
            http_status=200,
            error_message=None,
            source_url="https://example.com/",
            snippet="example snippet",
        )
        persist_result(session, result)
        session.commit()
        rows = list_freshness(session)
        assert len(rows) == 1
        assert rows[0].rule_id == "ai_act.art13.test"
        assert rows[0].citation_found is True

    def test_persist_updates_existing_row(self, session):
        # First run — flagged
        persist_result(
            session,
            VerificationResult(
                rule_id="r1",
                citation_found=False,
                flagged_for_review=True,
                http_status=404,
                error_message="not found",
                source_url="https://example.com/",
                snippet=None,
            ),
        )
        # Second run — found
        persist_result(
            session,
            VerificationResult(
                rule_id="r1",
                citation_found=True,
                flagged_for_review=False,
                http_status=200,
                error_message=None,
                source_url="https://example.com/",
                snippet="found",
            ),
        )
        session.commit()
        rows = list_freshness(session)
        assert len(rows) == 1
        assert rows[0].citation_found is True
        assert rows[0].flagged_for_review is False
        assert rows[0].http_status == 200

    def test_flagged_rule_ids_returns_only_flagged(self, session):
        for r in [
            VerificationResult("r1", True, False, 200, None, "u1", None),
            VerificationResult("r2", False, True, 404, "missing", "u2", None),
            VerificationResult("r3", False, True, 200, "no match", "u3", None),
            VerificationResult("r4", True, False, 200, None, "u4", None),
        ]:
            persist_result(session, r)
        session.commit()
        flagged = flagged_rule_ids(session)
        assert flagged == {"r2", "r3"}

    def test_snippet_is_truncated_to_500_chars(self, session):
        long_snippet = "x" * 1000
        persist_result(
            session,
            VerificationResult(
                rule_id="r1",
                citation_found=True,
                flagged_for_review=False,
                http_status=200,
                error_message=None,
                source_url="u",
                snippet=long_snippet,
            ),
        )
        session.commit()
        rows = list_freshness(session)
        assert len(rows[0].snippet) == 500
