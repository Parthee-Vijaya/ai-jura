"""Tests for src.services.meeting_report_generator.

Test-fokus:
  - _build_recommendation: korrekt anbefaling baseret på verdict + evidens-state
  - _xml_safe: escape af XML-special chars
  - build_meeting_report_pdf: validering af input (tom liste, ingen sager fundet)
  - Smoke: PDF-bytes returneres med valid PDF-signatur
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.services.meeting_report_generator import (
    _build_recommendation,
    _xml_safe,
    build_meeting_report_pdf,
)
from src.services.case_report_generator import CaseReportData, ReportRuleDecision


# ---- _xml_safe -----------------------------------------------------------


class TestXmlSafe:
    def test_basic_escape(self):
        assert _xml_safe("a & b") == "a &amp; b"
        assert _xml_safe("<tag>") == "&lt;tag&gt;"
        assert _xml_safe("normal text") == "normal text"

    def test_handles_none(self):
        assert _xml_safe(None) == ""

    def test_handles_non_string(self):
        assert _xml_safe(42) == "42"

    def test_combined_chars(self):
        assert _xml_safe("a<b>&c") == "a&lt;b&gt;&amp;c"


# ---- _build_recommendation ----------------------------------------------


def _mk_report(
    verdict=None,
    decisions=None,
    evidence_done=0,
    evidence_total=0,
    next_review_at=None,
):
    return CaseReportData(
        case_id="K-2026-0001",
        title="Test sag",
        status="kladde",
        status_label="Kladde",
        last_aggregate_status=verdict,
        assigned_to=None,
        created_at=None,
        updated_at=None,
        next_review_at=next_review_at,
        generated_at="2026-05-14T00:00:00Z",
        intake_state={},
        latest_assessment_log_id=None,
        latest_assessment_at=None,
        rule_engine_version=None,
        decisions=decisions or [],
        total_krav=0,
        total_artefakter=0,
        evidence=[],
        evidence_done=evidence_done,
        evidence_total=evidence_total,
        events=[],
    )


class TestBuildRecommendation:
    def test_go_complete_evidence_recommends_godkendelse(self):
        r = _mk_report(verdict="GO", evidence_done=8, evidence_total=8)
        msg = _build_recommendation(r)
        assert "godkendelse" in msg.lower()
        assert "alle krav opfyldt" in msg.lower()

    def test_go_incomplete_evidence_warns_about_evidens(self):
        r = _mk_report(verdict="GO", evidence_done=3, evidence_total=8)
        msg = _build_recommendation(r)
        assert "betinget godkendelse" in msg.lower()
        assert "3/8" in msg

    def test_betinget_recommends_clarification(self):
        decisions = [
            ReportRuleDecision(
                rule_id=f"r{i}", status="BETINGET-GO",
                lov="X", artikel="Y", citat="", url="", begrundelse="",
            )
            for i in range(2)
        ]
        r = _mk_report(verdict="BETINGET-GO", decisions=decisions)
        msg = _build_recommendation(r)
        assert "betinget go" in msg.lower()
        assert "2 betingelser" in msg.lower()

    def test_no_go_recommends_returnering(self):
        decisions = [
            ReportRuleDecision(
                rule_id=f"r{i}", status="NO-GO",
                lov="X", artikel="Y", citat="", url="", begrundelse="",
            )
            for i in range(3)
        ]
        r = _mk_report(verdict="NO-GO", decisions=decisions)
        msg = _build_recommendation(r)
        assert "no-go" in msg.lower()
        assert "3 blockere" in msg
        assert "returneres til sagsbehandler" in msg

    def test_no_verdict_recommends_kør_vurdering(self):
        r = _mk_report(verdict=None)
        msg = _build_recommendation(r)
        assert "ikke kørt" in msg.lower()

    def test_short_mode_omits_next_review(self):
        r = _mk_report(verdict="GO", evidence_done=8, evidence_total=8, next_review_at="2027-01-01")
        short = _build_recommendation(r, short=True)
        long = _build_recommendation(r, short=False)
        assert "Næste review" not in short
        assert "Næste review" in long


# ---- build_meeting_report_pdf ------------------------------------------


class TestBuildMeetingReportPdf:
    def test_empty_case_ids_raises(self):
        with pytest.raises(ValueError):
            build_meeting_report_pdf(MagicMock(), case_ids=[])

    def test_all_missing_raises(self, monkeypatch):
        # Patch build_report_data to return None for all → ingen sager fundet
        from src.services import meeting_report_generator as mod
        monkeypatch.setattr(mod, "build_report_data", lambda *a, **kw: None)
        with pytest.raises(ValueError, match="Ingen af de angivne"):
            build_meeting_report_pdf(MagicMock(), case_ids=["K-1", "K-2"])

    def test_happy_path_produces_pdf_bytes(self, monkeypatch):
        from src.services import meeting_report_generator as mod

        sample = _mk_report(
            verdict="GO",
            evidence_done=5,
            evidence_total=5,
            decisions=[],
        )

        monkeypatch.setattr(mod, "build_report_data", lambda *a, **kw: sample)

        pdf = build_meeting_report_pdf(
            MagicMock(),
            case_ids=["K-2026-0001"],
            meeting_title="Test møde",
            meeting_date="2026-05-14",
            chair="Test Chair",
        )
        # PDF magic bytes
        assert isinstance(pdf, bytes)
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 1000  # rimelig størrelse for cover + 1-sag + decisions-side
