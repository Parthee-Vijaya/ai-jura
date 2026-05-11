"""Tests for src.api.csv_exports — sager/audit/portefølje CSV-eksport."""

import csv
import io

import pytest

from src.api.csv_exports import (
    cases_to_csv,
    audit_to_csv,
    portfolio_to_csv,
)


# ---- Helpers --------------------------------------------------------------


def parse_csv(text: str) -> list[list[str]]:
    """Parse CSV-tekst (med BOM + ; separator) tilbage til rækker."""
    text = text.lstrip("﻿")
    reader = csv.reader(io.StringIO(text), delimiter=";")
    return list(reader)


# ---- cases_to_csv --------------------------------------------------------


def test_cases_to_csv_returns_text_and_filename():
    text, filename = cases_to_csv([])
    assert isinstance(text, str)
    assert filename.startswith("bifrost-sager-")
    assert filename.endswith(".csv")


def test_cases_to_csv_has_utf8_bom():
    text, _ = cases_to_csv([])
    # BOM = U+FEFF skal være første tegn så Excel auto-detecter UTF-8
    assert text.startswith("﻿")


def test_cases_to_csv_header_row():
    text, _ = cases_to_csv([])
    rows = parse_csv(text)
    assert rows[0] == [
        "case_id", "title", "status", "verdict", "assigned_to",
        "indkoeb_eller_udvikling", "sagsnummer_serviceportal",
        "behov_preview", "evidence_done", "evidence_total",
        "evidence_pct", "created_at", "updated_at", "next_review_at",
    ]


def test_cases_to_csv_single_case():
    cases = [{
        "case_id": "K-2026-0184",
        "title": "Borgerassistent — pension",
        "status": "kladde",
        "last_aggregate_status": "BETINGET-GO",
        "assigned_to": "pavi@kalundborg.dk",
        "intake_state": {
            "behov": "AI-assistent til pensionsansøgninger",
            "indkoeb_eller_udvikling": "indkoeb",
            "sagsnummer": "SP-12345",
        },
        "created_at": "2026-05-01T10:00:00Z",
        "updated_at": "2026-05-11T14:30:00Z",
        "next_review_at": None,
    }]
    text, _ = cases_to_csv(cases)
    rows = parse_csv(text)
    assert len(rows) == 2  # header + 1 data
    row = rows[1]
    assert row[0] == "K-2026-0184"
    assert "Borgerassistent" in row[1]
    assert row[2] == "kladde"
    assert row[3] == "BETINGET-GO"
    assert row[5] == "indkoeb"
    assert row[6] == "SP-12345"
    assert "AI-assistent" in row[7]
    assert row[10] == "n/a"  # ingen evidens-map


def test_cases_to_csv_with_evidence_progress():
    cases = [{
        "case_id": "K-1",
        "title": "Test",
        "status": "vurderet",
        "last_aggregate_status": "GO",
        "intake_state": {},
        "created_at": "2026-05-01",
        "updated_at": "2026-05-11",
    }]
    evidence_map = {
        "K-1": [
            {"artifact_id": "dpia", "status": "faerdig"},
            {"artifact_id": "ropa", "status": "godkendt"},
            {"artifact_id": "log_plan", "status": "i_gang"},
            {"artifact_id": "risk", "status": "mangler"},
        ],
    }
    text, _ = cases_to_csv(cases, evidence_map=evidence_map)
    rows = parse_csv(text)
    row = rows[1]
    assert row[8] == "2"   # done
    assert row[9] == "4"   # total
    assert row[10] == "50%"  # pct


def test_cases_to_csv_handles_string_intake_state():
    """intake_state kan komme som JSON-string fra nogle paths."""
    cases = [{
        "case_id": "K-X",
        "title": "Test",
        "status": "kladde",
        "intake_state": '{"behov": "noget", "sagsnummer": "SP-99"}',
    }]
    text, _ = cases_to_csv(cases)
    rows = parse_csv(text)
    assert "noget" in rows[1][7]
    assert rows[1][6] == "SP-99"


def test_cases_to_csv_escapes_newlines_in_behov():
    """Behov med newlines må ikke bryde CSV-strukturen."""
    cases = [{
        "case_id": "K-1",
        "title": "T",
        "status": "kladde",
        "intake_state": {"behov": "linje1\nlinje2\nlinje3"},
    }]
    text, _ = cases_to_csv(cases)
    rows = parse_csv(text)
    assert len(rows) == 2  # header + 1 data — IKKE 4 (én pr. linje)


# ---- audit_to_csv --------------------------------------------------------


def test_audit_to_csv_header_row():
    text, _ = audit_to_csv([])
    rows = parse_csv(text)
    assert rows[0] == [
        "audit_id", "timestamp", "case_id", "aggregate_status",
        "rule_count_triggered", "rule_count_total",
        "ruleset_version", "execution_ms", "actor",
        "system_description_preview",
    ]


def test_audit_to_csv_with_entry():
    entries = [{
        "id": "abc-123",
        "created_at": "2026-05-11T10:00:00Z",
        "case_id": "K-1",
        "aggregate_status": "BETINGET-GO",
        "actor": "pavi",
        "request": {"system_description": "Test AI-system til pensionsansøgninger"},
        "response": {
            "decisions": [
                {"rule_id": "ai_act_6", "status": "BETINGET-GO"},
                {"rule_id": "gdpr_35", "status": "GO"},
                {"rule_id": "fvl_22", "status": "BETINGET-GO"},
            ],
            "ruleset_version": "3.0.0",
            "execution_ms": 245,
        },
    }]
    text, _ = audit_to_csv(entries)
    rows = parse_csv(text)
    row = rows[1]
    assert row[0] == "abc-123"
    assert row[3] == "BETINGET-GO"
    assert row[4] == "2"   # 2 ikke-GO triggered
    assert row[5] == "3"   # 3 total decisions
    assert row[6] == "3.0.0"
    assert row[7] == "245"
    assert "Test AI-system" in row[9]


# ---- portfolio_to_csv ---------------------------------------------------


def test_portfolio_to_csv_has_sections():
    snapshot = {
        "generated_at": "2026-05-11T14:00:00Z",
        "stats": {
            "total_cases": 5,
            "evidens_total": 20,
            "evidens_done": 15,
            "evidens_pct": 75,
            "open_comment_count": 3,
            "comment_count_total": 8,
            "by_status": {"kladde": 2, "vurderet": 3},
            "verdict_counts": {"GO": 1, "BETINGET-GO": 2},
        },
        "heatmap": {
            "GO": {"mangler": 0, "i_gang": 1, "faerdig": 5},
            "BETINGET-GO": {"mangler": 2, "i_gang": 3, "faerdig": 4},
        },
        "top_blockers": [
            {"artifact_id": "dpia_dokument", "label": "DPIA-dokument", "blocked_cases": 3},
            {"artifact_id": "risk", "label": "Risikostyring", "blocked_cases": 2},
        ],
        "sla": {
            "overdue": [
                {"case_id": "K-1", "title": "Forsinket sag", "next_review_at": "2026-04-01", "days_overdue": 40},
            ],
            "upcoming_within_7_days": [
                {"case_id": "K-2", "title": "Kommer", "next_review_at": "2026-05-15", "days_until": 4},
            ],
        },
    }
    text, filename = portfolio_to_csv(snapshot)
    assert filename.startswith("bifrost-portefolje-")
    assert "section;stats" in text
    assert "section;heatmap" in text
    assert "section;top_blockers" in text
    assert "section;sla_overdue" in text
    assert "section;sla_upcoming_7_days" in text


def test_portfolio_to_csv_stats_values():
    snapshot = {
        "generated_at": "2026-05-11T14:00:00Z",
        "stats": {"total_cases": 5, "evidens_pct": 75},
    }
    text, _ = portfolio_to_csv(snapshot)
    rows = parse_csv(text)
    # Find stats-rækker
    flat = [";".join(r) for r in rows]
    assert any("total_cases;5" in r for r in flat)
    assert any("evidens_pct;75%" in r for r in flat)


def test_portfolio_to_csv_top_blockers_ranked():
    snapshot = {
        "stats": {},
        "heatmap": {},
        "top_blockers": [
            {"artifact_id": "a", "label": "A", "blocked_cases": 10},
            {"artifact_id": "b", "label": "B", "blocked_cases": 5},
        ],
        "sla": {},
    }
    text, _ = portfolio_to_csv(snapshot)
    rows = parse_csv(text)
    # Find top_blockers-rækker
    in_section = False
    blocker_rows = []
    for r in rows:
        if r and r[0] == "section" and len(r) > 1 and r[1] == "top_blockers":
            in_section = True
            continue
        if in_section and r and r[0] == "section":
            break
        if in_section and r and r[0] not in ("rank", ""):
            blocker_rows.append(r)
    # 2 entries med rank 1 og 2
    assert len(blocker_rows) == 2
    assert blocker_rows[0][0] == "1"
    assert blocker_rows[0][3] == "10"
    assert blocker_rows[1][0] == "2"
