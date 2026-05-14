"""Tests for src.services.eu_database_export — EU AI Act Art. 49.

Test-fokus:
  - _extract_from_evidence: prioritering på tværs af artefakter
  - _find_completion_date: kun returnerer hvis status faerdig/godkendt
  - _identify_missing: detekterer fallback-strings
  - render_pdf: producerer valid PDF-bytes
  - FAGOMRAADE_TO_ANNEX_III mapping
"""

import pytest
from unittest.mock import MagicMock

from src.services.eu_database_export import (
    EU_DB_FIELDS,
    FAGOMRAADE_TO_ANNEX_III,
    _extract_from_evidence,
    _find_completion_date,
    _identify_missing,
    _safe,
    render_pdf,
)


# ---- Constants ---------------------------------------------------------


class TestConstants:
    def test_eu_db_fields_count(self):
        # Annex VIII A (8) + Annex VIII C deployer additions (4) = 12
        assert len(EU_DB_FIELDS) == 12

    def test_fagomraade_mapping_covers_common(self):
        # Mindst de mest brugte fagområder skal være mappet
        for k in ("beskaeftigelse", "uddannelse", "sundhed", "borgerservice"):
            assert k in FAGOMRAADE_TO_ANNEX_III
            assert "Annex III" in FAGOMRAADE_TO_ANNEX_III[k]


# ---- _extract_from_evidence -------------------------------------------


class TestExtractFromEvidence:
    def _mk_evidens(self, artifact_id, content, status="faerdig"):
        e = MagicMock()
        e.artifact_id = artifact_id
        e.status = status
        e.content = content
        e.get_content = lambda: content
        return e

    def test_picks_matching_artifact(self):
        ev = [
            self._mk_evidens("other", {"foo": "bar"}),
            self._mk_evidens("human_oversight_plan", {"scope": "Always-on review"}),
        ]
        out = _extract_from_evidence(
            ev,
            artifact_ids=["human_oversight_plan"],
            sections=["scope"],
            fallback="default",
        )
        assert "Always-on review" in out

    def test_combines_multiple_sections(self):
        ev = [
            self._mk_evidens("risikostyringsplan", {
                "risici": "data drift",
                "mitigation": "weekly retraining",
            }),
        ]
        out = _extract_from_evidence(
            ev,
            artifact_ids=["risikostyringsplan"],
            sections=["risici", "mitigation"],
            fallback="default",
        )
        assert "data drift" in out
        assert "weekly retraining" in out

    def test_returns_fallback_when_no_match(self):
        ev = [self._mk_evidens("other", {"foo": "bar"})]
        out = _extract_from_evidence(
            ev,
            artifact_ids=["human_oversight_plan"],
            sections=["scope"],
            fallback="DEFAULT",
        )
        assert out == "DEFAULT"

    def test_returns_fallback_when_sections_empty(self):
        ev = [self._mk_evidens("human_oversight_plan", {"scope": ""})]
        out = _extract_from_evidence(
            ev,
            artifact_ids=["human_oversight_plan"],
            sections=["scope"],
            fallback="DEFAULT",
        )
        assert out == "DEFAULT"


# ---- _find_completion_date --------------------------------------------


class TestFindCompletionDate:
    def _mk(self, artifact_id, status, completed_at):
        e = MagicMock()
        e.artifact_id = artifact_id
        e.status = status
        e.completed_at = completed_at
        return e

    def test_returns_completed_date_for_faerdig(self):
        from datetime import datetime
        ev = [self._mk("conformity_assessment", "faerdig", datetime(2026, 1, 15))]
        out = _find_completion_date(ev, artifact_ids=["conformity_assessment"])
        assert out == "2026-01-15"

    def test_skips_unfinished_status(self):
        from datetime import datetime
        ev = [
            self._mk("conformity_assessment", "i_gang", datetime(2026, 1, 15)),
            self._mk("conformity_assessment", "mangler", None),
        ]
        out = _find_completion_date(ev, artifact_ids=["conformity_assessment"])
        assert out is None

    def test_returns_none_for_no_match(self):
        ev = []
        out = _find_completion_date(ev, artifact_ids=["foo"])
        assert out is None


# ---- _identify_missing ------------------------------------------------


class TestIdentifyMissing:
    def test_detects_fallback_strings(self):
        check = {
            "field_a": "real data",
            "field_b": "Udfyldes manuelt fra evidens",
            "field_c": None,
            "field_d": "",
        }
        missing = _identify_missing(check)
        assert "field_a" not in missing
        assert "field_b" in missing
        assert "field_c" in missing
        assert "field_d" in missing


# ---- _safe ------------------------------------------------------------


class TestSafe:
    def test_escapes_xml(self):
        assert _safe("a & b") == "a &amp; b"
        assert _safe("<a>") == "&lt;a&gt;"

    def test_handles_none(self):
        assert _safe(None) == ""

    def test_handles_int(self):
        assert _safe(42) == "42"


# ---- render_pdf -------------------------------------------------------


class TestRenderPdf:
    def test_renders_valid_pdf(self):
        payload = {
            "deployer_name": "Kalundborg Kommune",
            "deployer_address": "Holbækvej 141",
            "deployer_contact": "kontakt@k.dk",
            "system_trade_name": "Test AI",
            "system_purpose": "Beskriver formålet",
            "system_high_risk_category": "Annex III §5",
            "system_status": "planlagt",
            "data_categories": ["CPR", "navn"],
            "human_oversight_measures": "Manuel godkendelse",
            "fria_mitigations": "Bias-monitoring",
            "conformity_assessment_date": "2026-04-01",
            "registration_date": "2026-05-14",
            "_meta": {
                "case_id": "K-2026-0042",
                "case_title": "Test sag",
                "case_status": "vurderet",
                "exported_at": "2026-05-14T12:00:00Z",
                "source": "Bifrost EU-database export v1",
                "disclaimer": "Test disclaimer med <html>",
                "missing_fields": [],
            },
        }
        pdf = render_pdf(payload)
        assert isinstance(pdf, bytes)
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 1500  # cover + 4 sektioner + signature

    def test_handles_missing_fields_banner(self):
        payload = {
            "deployer_name": "K",
            "deployer_address": "A",
            "deployer_contact": "c@k.dk",
            "system_trade_name": "X",
            "system_purpose": "p",
            "system_high_risk_category": "cat",
            "system_status": "planlagt",
            "data_categories": [],
            "human_oversight_measures": "",
            "fria_mitigations": "",
            "conformity_assessment_date": None,
            "registration_date": "2026-05-14",
            "_meta": {
                "case_id": "K-1",
                "case_title": "X",
                "case_status": "kladde",
                "exported_at": "2026-05-14T12:00:00Z",
                "source": "test",
                "disclaimer": "Test",
                "missing_fields": ["human_oversight_measures", "fria_mitigations"],
            },
        }
        pdf = render_pdf(payload)
        assert pdf[:4] == b"%PDF"
