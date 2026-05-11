"""CSV-eksport for revisor-, myndigheds- og leder-overblik.

Tilbyder tre primære eksport-funktioner:

1. cases_to_csv()   — alle sager med metadata + evidens-progress + verdict
2. audit_to_csv()   — v3 audit-log (vurderinger) i revisor-format
3. portfolio_to_csv() — portefølje-snapshot (stats + heatmap + blockers)

Designet til at være MAML-fri (kun standard csv + io.StringIO) så ingen
ekstra dependencies. Output er UTF-8 med BOM så Excel åbner det korrekt
med danske bogstaver.

Hver funktion returnerer (csv_text, suggested_filename).
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, UTC
from typing import Any, Optional


# ---- Helpers --------------------------------------------------------------


def _utf8_bom_writer() -> tuple[io.StringIO, csv.writer]:
    """Returnér (buffer, writer) hvor Excel kan læse danske tegn korrekt.

    BOM + UTF-8 + ; som separator (Excel-DK forventer det) + CRLF.
    """
    buf = io.StringIO()
    # BOM så Excel auto-detecter UTF-8
    buf.write("﻿")
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    return buf, writer


def _safe_str(val: Any) -> str:
    """Konvertér en værdi til CSV-safe streng."""
    if val is None:
        return ""
    if isinstance(val, (datetime,)):
        return val.isoformat()
    if isinstance(val, bool):
        return "ja" if val else "nej"
    s = str(val)
    # Newlines i celler bryder Excel — erstat med space
    return s.replace("\n", " ").replace("\r", " ").strip()


def _timestamp_slug() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


# ---- Sager liste ----------------------------------------------------------


def cases_to_csv(cases: list[dict], evidence_map: dict[str, list[dict]] | None = None) -> tuple[str, str]:
    """Eksportér en liste af sager til CSV.

    Hver række: case_id, title, status, verdict, assigned_to, created_at,
    updated_at, evidence_done, evidence_total, evidence_pct, behov_preview,
    indkoeb_eller_udvikling, sagsnummer, next_review_at.

    Args:
        cases: liste af case-dicts (typisk fra Case.to_dict())
        evidence_map: optional {case_id: [evidence rows]} for at beregne progress.
                      Hvis None, evidence_pct = "n/a"

    Returns:
        (csv_text, filename)
    """
    buf, writer = _utf8_bom_writer()

    writer.writerow([
        "case_id",
        "title",
        "status",
        "verdict",
        "assigned_to",
        "indkoeb_eller_udvikling",
        "sagsnummer_serviceportal",
        "behov_preview",
        "evidence_done",
        "evidence_total",
        "evidence_pct",
        "created_at",
        "updated_at",
        "next_review_at",
    ])

    for c in cases:
        intake = c.get("intake_state") or {}
        if isinstance(intake, str):
            # case.to_dict() kan returnere intake_state som JSON-string i nogle paths
            try:
                import json
                intake = json.loads(intake)
            except (TypeError, ValueError):
                intake = {}

        ev_rows = (evidence_map or {}).get(c.get("case_id"), [])
        ev_total = len(ev_rows)
        ev_done = sum(1 for e in ev_rows if e.get("status") in ("faerdig", "godkendt"))
        ev_pct = round(100 * ev_done / ev_total) if ev_total else 0

        behov_preview = (intake.get("behov") or "")[:200]

        writer.writerow([
            _safe_str(c.get("case_id")),
            _safe_str(c.get("title")),
            _safe_str(c.get("status")),
            _safe_str(c.get("last_aggregate_status")),
            _safe_str(c.get("assigned_to")),
            _safe_str(intake.get("indkoeb_eller_udvikling")),
            _safe_str(intake.get("sagsnummer")),
            _safe_str(behov_preview),
            ev_done,
            ev_total,
            f"{ev_pct}%" if ev_total else "n/a",
            _safe_str(c.get("created_at")),
            _safe_str(c.get("updated_at")),
            _safe_str(c.get("next_review_at")),
        ])

    return buf.getvalue(), f"bifrost-sager-{_timestamp_slug()}.csv"


# ---- Audit-log (v3 vurderinger) ------------------------------------------


def audit_to_csv(entries: list[dict]) -> tuple[str, str]:
    """Eksportér v3 audit-log til CSV — revisor-format.

    Hver række er én vurdering (run af regelmotoren) med dens metadata,
    aggregate verdict, antal triggered rules + executed time.

    Args:
        entries: liste af V3AuditEntry-dicts

    Returns:
        (csv_text, filename)
    """
    buf, writer = _utf8_bom_writer()

    writer.writerow([
        "audit_id",
        "timestamp",
        "case_id",
        "aggregate_status",
        "rule_count_triggered",
        "rule_count_total",
        "ruleset_version",
        "execution_ms",
        "actor",
        "system_description_preview",
    ])

    for e in entries:
        request_data = e.get("request") or {}
        response_data = e.get("response") or {}
        decisions = response_data.get("decisions") or []

        system_desc = (request_data.get("system_description") or "")[:300]
        rule_count_triggered = sum(1 for d in decisions if d.get("status") not in ("GO", "INFO"))

        writer.writerow([
            _safe_str(e.get("id")),
            _safe_str(e.get("created_at")),
            _safe_str(e.get("case_id")),
            _safe_str(e.get("aggregate_status")),
            rule_count_triggered,
            len(decisions),
            _safe_str(response_data.get("ruleset_version")),
            _safe_str(response_data.get("execution_ms") or response_data.get("duration_ms")),
            _safe_str(e.get("actor")),
            _safe_str(system_desc),
        ])

    return buf.getvalue(), f"bifrost-audit-{_timestamp_slug()}.csv"


# ---- Portfolio snapshot ---------------------------------------------------


def portfolio_to_csv(snapshot: dict) -> tuple[str, str]:
    """Eksportér portefølje-dashboard som flerafsnitlig CSV.

    Layout:
      Section: stats
        key;value
        total_cases;X
        ...
      <tom række>
      Section: heatmap
        verdict;mangler;i_gang;faerdig
        ...
      <tom række>
      Section: top_blockers
        rank;artifact_id;blocked_cases
        ...

    Args:
        snapshot: dict fra /api/v3/dashboard/portfolio

    Returns:
        (csv_text, filename)
    """
    buf, writer = _utf8_bom_writer()
    stats = snapshot.get("stats") or {}
    heatmap = snapshot.get("heatmap") or {}
    blockers = snapshot.get("top_blockers") or []
    sla = snapshot.get("sla") or {}

    # Section 1: stats
    writer.writerow(["section", "stats"])
    writer.writerow(["key", "value"])
    writer.writerow(["generated_at", _safe_str(snapshot.get("generated_at"))])
    writer.writerow(["total_cases", stats.get("total_cases", 0)])
    writer.writerow(["evidens_total", stats.get("evidens_total", 0)])
    writer.writerow(["evidens_done", stats.get("evidens_done", 0)])
    writer.writerow(["evidens_pct", f"{stats.get('evidens_pct', 0)}%"])
    writer.writerow(["open_comment_count", stats.get("open_comment_count", 0)])
    writer.writerow(["comment_count_total", stats.get("comment_count_total", 0)])
    for status, n in (stats.get("by_status") or {}).items():
        writer.writerow([f"by_status.{status}", n])
    for verdict, n in (stats.get("verdict_counts") or {}).items():
        writer.writerow([f"verdict.{verdict}", n])

    # Section 2: heatmap
    writer.writerow([])
    writer.writerow(["section", "heatmap"])
    writer.writerow(["verdict", "mangler", "i_gang", "faerdig", "total"])
    for verdict, row in heatmap.items():
        m = row.get("mangler", 0)
        i = row.get("i_gang", 0)
        f = row.get("faerdig", 0)
        writer.writerow([verdict, m, i, f, m + i + f])

    # Section 3: top blockers
    writer.writerow([])
    writer.writerow(["section", "top_blockers"])
    writer.writerow(["rank", "artifact_id", "label", "blocked_cases"])
    for i, b in enumerate(blockers, 1):
        writer.writerow([i, b.get("artifact_id"), b.get("label"), b.get("blocked_cases")])

    # Section 4: SLA overdue
    writer.writerow([])
    writer.writerow(["section", "sla_overdue"])
    writer.writerow(["case_id", "title", "next_review_at", "days_overdue"])
    for c in (sla.get("overdue") or []):
        writer.writerow([
            _safe_str(c.get("case_id")),
            _safe_str(c.get("title")),
            _safe_str(c.get("next_review_at")),
            c.get("days_overdue", 0),
        ])

    # Section 5: SLA upcoming
    writer.writerow([])
    writer.writerow(["section", "sla_upcoming_7_days"])
    writer.writerow(["case_id", "title", "next_review_at", "days_until"])
    for c in (sla.get("upcoming_within_7_days") or []):
        writer.writerow([
            _safe_str(c.get("case_id")),
            _safe_str(c.get("title")),
            _safe_str(c.get("next_review_at")),
            c.get("days_until", 0),
        ])

    return buf.getvalue(), f"bifrost-portefolje-{_timestamp_slug()}.csv"
