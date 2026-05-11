"""Dashboard-router — portefølje-overblik + CSV-eksport.

Endpoints:
  - GET /api/v3/dashboard/portfolio       → aggregeret overblik
  - GET /api/v3/dashboard/portfolio.csv   → CSV-eksport af samme data

Bygger på top af de eksisterende database-laget (cases, evidence,
evidence_comments) — ingen state i routeren selv.
"""

from __future__ import annotations

from datetime import datetime, UTC, timedelta

from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter(prefix="/api/v3/dashboard", tags=["dashboard"])


@router.get("/portfolio")
async def portfolio():
    """Aggregeret overblik over kommunens AI-portefølje.

    Returnerer:
      - stats: totale tællere (sager, evidens, kommentarer, verdicts)
      - heatmap: matrix [verdict × evidens-status]
      - top_blockers: 5 evidens-IDs der mangler på flest sager
      - sla: sager med next_review forfalden / nær deadline (7 dage)
    """
    from src.database.connection import SessionLocal
    from src.database.cases import Case
    from src.database.evidence import EvidenceArtifact
    from src.database.evidence_comments import EvidenceComment

    db = SessionLocal()
    try:
        all_cases = db.query(Case).all()
        all_evidence = db.query(EvidenceArtifact).all()
        comment_count = db.query(EvidenceComment).count()
        open_comment_count = (
            db.query(EvidenceComment)
            .filter(EvidenceComment.resolved_at.is_(None))
            .count()
        )

        # Stats
        total_cases = len(all_cases)
        by_status: dict[str, int] = {}
        verdict_counts: dict[str, int] = {}
        for c in all_cases:
            by_status[c.status] = by_status.get(c.status, 0) + 1
            if c.last_aggregate_status:
                verdict_counts[c.last_aggregate_status] = (
                    verdict_counts.get(c.last_aggregate_status, 0) + 1
                )

        evidens_total = len(all_evidence)
        evidens_done = sum(
            1 for e in all_evidence if e.status in ("faerdig", "godkendt")
        )

        # Heatmap: verdict × evidens-status
        heatmap: dict[str, dict[str, int]] = {}
        verdict_for_case: dict[str, str] = {
            c.case_id: (c.last_aggregate_status or "ukendt") for c in all_cases
        }
        for e in all_evidence:
            verdict = verdict_for_case.get(e.case_id, "ukendt")
            row = heatmap.setdefault(verdict, {"mangler": 0, "i_gang": 0, "faerdig": 0})
            if e.status == "godkendt":
                row["faerdig"] += 1
            elif e.status in ("mangler", "i_gang", "faerdig"):
                row[e.status] += 1
        for v in set(verdict_for_case.values()):
            heatmap.setdefault(v, {"mangler": 0, "i_gang": 0, "faerdig": 0})

        # Top 5 blockers
        blocker_counts: dict[str, int] = {}
        for e in all_evidence:
            if e.status in ("mangler", "i_gang"):
                blocker_counts[e.artifact_id] = blocker_counts.get(e.artifact_id, 0) + 1
        top_blockers = sorted(blocker_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_blockers_data = [
            {"artifact_id": aid, "label": aid.replace("_", " "), "blocked_cases": count}
            for aid, count in top_blockers
        ]

        # SLA
        now = datetime.now(UTC)
        in_7_days = now + timedelta(days=7)
        overdue: list[dict] = []
        upcoming: list[dict] = []
        for c in all_cases:
            if not c.next_review_at:
                continue
            if c.next_review_at < now:
                overdue.append({
                    "case_id": c.case_id,
                    "title": c.title,
                    "next_review_at": c.next_review_at.isoformat(),
                    "days_overdue": (now - c.next_review_at).days,
                })
            elif c.next_review_at < in_7_days:
                upcoming.append({
                    "case_id": c.case_id,
                    "title": c.title,
                    "next_review_at": c.next_review_at.isoformat(),
                    "days_until": (c.next_review_at - now).days,
                })

        return {
            "generated_at": now.isoformat(),
            "stats": {
                "total_cases": total_cases,
                "evidens_total": evidens_total,
                "evidens_done": evidens_done,
                "evidens_pct": (
                    round(100 * evidens_done / evidens_total) if evidens_total else 0
                ),
                "comment_count_total": comment_count,
                "open_comment_count": open_comment_count,
                "by_status": by_status,
                "verdict_counts": verdict_counts,
            },
            "heatmap": heatmap,
            "top_blockers": top_blockers_data,
            "sla": {
                "overdue": overdue[:10],
                "upcoming_within_7_days": upcoming[:10],
            },
        }
    finally:
        db.close()


@router.get("/portfolio.csv")
async def portfolio_csv():
    """Eksportér portefølje-dashboard som flerafsnitlig CSV.

    Indeholder stats, heatmap, top blockers og SLA-lister i Excel-format.
    """
    from src.api.csv_exports import portfolio_to_csv
    snapshot = await portfolio()
    csv_text, filename = portfolio_to_csv(snapshot)
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
