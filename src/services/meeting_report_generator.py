"""Mødeoversigt — PDF til styregruppe-møder med 2+ sager samlet.

Genererer en print-venlig PDF med:
  - Cover-side: dato + sagsantal + verdict-fordeling
  - Pr. sag: 1-sides oversigt med verdict + status + top-blockers + næste-skridt
  - Slut-side: anbefalede beslutninger til styregruppen

Genbruger build_report_data fra case_report_generator så data-modellen er
identisk med per-sag-rapporten. Frontend kalder POST /api/v3/cases/meeting-report
med en liste af case_ids.
"""

from __future__ import annotations

import io
import logging
from collections import Counter
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy.orm import Session

from src.services.case_report_generator import (
    CaseReportData,
    build_report_data,
    _format_date,
)

logger = logging.getLogger(__name__)


VERDICT_COLORS = {
    "GO": "#2d6a31",
    "BETINGET-GO": "#b08a4a",
    "NO-GO": "#a02020",
}


def build_meeting_report_pdf(
    session: Session,
    *,
    case_ids: list[str],
    meeting_title: Optional[str] = None,
    meeting_date: Optional[str] = None,
    chair: Optional[str] = None,
) -> bytes:
    """Producér PDF med oversigt over flere sager til styregruppe-møde.

    Args:
        session: SQLAlchemy session
        case_ids: liste af eksterne case_ids (fx 'K-2026-0042')
        meeting_title: valgfri møde-titel (default: 'Styregruppe AI-compliance')
        meeting_date: valgfri ISO-dato (default: dags dato)
        chair: valgfri formand/leder navn

    Returns:
        PDF som bytes (kan returneres direkte fra FastAPI som application/pdf)

    Raises:
        ValueError: hvis case_ids er tom eller ingen sager fundet
    """
    if not case_ids:
        raise ValueError("Mindst én case_id kræves")

    # Build per-sag data
    reports: list[CaseReportData] = []
    missing: list[str] = []
    for cid in case_ids:
        data = build_report_data(session, cid)
        if data is None:
            missing.append(cid)
        else:
            reports.append(data)

    if not reports:
        raise ValueError(
            f"Ingen af de angivne sager findes: {', '.join(case_ids)}"
        )

    title = meeting_title or "Styregruppe — AI-compliance"
    date_str = meeting_date or datetime.now(UTC).strftime("%Y-%m-%d")

    # Render PDF
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, KeepTogether,
    )

    BRONZE = colors.HexColor("#6e5527")
    NAVY = colors.HexColor("#0d2e54")
    INK = colors.HexColor("#14181f")
    INK_SOFT = colors.HexColor("#555a64")
    SUCCESS = colors.HexColor("#2d6a31")
    DANGER = colors.HexColor("#a02020")
    WARN = colors.HexColor("#b08a4a")
    LINE = colors.HexColor("#d8d3c5")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=2.2 * cm, bottomMargin=2.2 * cm,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm,
        title=f"Mødeoversigt — {date_str}",
        author=chair or "Bifrost",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="MEyebrow", parent=styles["Normal"], fontSize=8, textColor=BRONZE, spaceAfter=4, leading=10))
    styles.add(ParagraphStyle(name="MTitle", parent=styles["Title"], fontSize=22, textColor=INK, spaceAfter=8, leading=26))
    styles.add(ParagraphStyle(name="MMeta", parent=styles["Normal"], fontSize=10, textColor=INK_SOFT, spaceAfter=10))
    styles.add(ParagraphStyle(name="MH2", parent=styles["Heading2"], fontSize=13, textColor=NAVY, spaceBefore=14, spaceAfter=8))
    styles.add(ParagraphStyle(name="MCaseTitle", parent=styles["Heading3"], fontSize=12, textColor=INK, spaceBefore=8, spaceAfter=4))
    styles.add(ParagraphStyle(name="MBody", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=3))
    styles.add(ParagraphStyle(name="MSmall", parent=styles["Normal"], fontSize=8.5, textColor=INK_SOFT, leading=11))
    styles.add(ParagraphStyle(name="MItalic", parent=styles["Italic"], fontSize=9, textColor=INK_SOFT, leading=12))
    styles.add(ParagraphStyle(name="MFooter", parent=styles["Italic"], fontSize=7.5, textColor=colors.grey, leading=9))

    story = []

    # ---- Cover ----
    story.append(Paragraph("BIFROST · MØDEOVERSIGT", styles["MEyebrow"]))
    story.append(Paragraph(title, styles["MTitle"]))
    meta_bits = [f"Dato: <b>{date_str}</b>"]
    if chair:
        meta_bits.append(f"Formand: {chair}")
    meta_bits.append(f"{len(reports)} sag{'er' if len(reports) != 1 else ''}")
    story.append(Paragraph(" · ".join(meta_bits), styles["MMeta"]))

    # Verdict-fordeling
    verdict_counts = Counter(r.last_aggregate_status or "Ikke vurderet" for r in reports)
    story.append(Paragraph("Verdict-fordeling", styles["MH2"]))
    vdata = [["Verdict", "Antal sager"]]
    for verdict in ("GO", "BETINGET-GO", "NO-GO", "Ikke vurderet"):
        if verdict in verdict_counts:
            vdata.append([verdict, str(verdict_counts[verdict])])
    vtable = Table(vdata, colWidths=[8 * cm, 4 * cm])
    vtable.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (-1, 0), INK_SOFT),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, BRONZE),
        ("LINEBELOW", (0, 1), (-1, -2), 0.2, LINE),
    ]))
    story.append(vtable)

    if missing:
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph(
            f"<i>Bemærk: følgende sager kunne ikke findes og er udeladt: "
            f"{', '.join(missing)}</i>",
            styles["MSmall"],
        ))

    story.append(Paragraph(
        f"Genereret {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        styles["MSmall"],
    ))

    story.append(PageBreak())

    # ---- Pr. sag: 1-side oversigt ----
    for idx, r in enumerate(reports, start=1):
        story.append(Paragraph(f"Sag {idx} af {len(reports)}", styles["MEyebrow"]))
        story.append(Paragraph(_xml_safe(r.title), styles["MCaseTitle"]))
        story.append(Paragraph(
            f"<b>{r.case_id}</b> · {r.status_label}"
            + (f" · {r.assigned_to}" if r.assigned_to else ""),
            styles["MSmall"],
        ))

        # Verdict-banner
        verdict = r.last_aggregate_status
        if verdict:
            vcolor = VERDICT_COLORS.get(verdict, "#14181f")
            story.append(Spacer(1, 0.2 * cm))
            story.append(Paragraph(
                f'<font color="{vcolor}" size="13"><b>Verdict: {verdict}</b></font>',
                styles["MBody"],
            ))
        else:
            story.append(Paragraph(
                "<i>Vurdering ikke kørt endnu.</i>",
                styles["MItalic"],
            ))

        story.append(Spacer(1, 0.3 * cm))

        # Nøgletal
        nrows = [
            ["Evidens-progress", f"{r.evidence_done} / {r.evidence_total}"],
            ["Antal krav", str(r.total_krav)],
            ["Sidste opdatering", _format_date(r.updated_at) or "—"],
        ]
        if r.next_review_at:
            nrows.append(["Næste review", _format_date(r.next_review_at)])
        ntable = Table(nrows, colWidths=[5 * cm, None])
        ntable.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("TEXTCOLOR", (0, 0), (0, -1), INK_SOFT),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -2), 0.2, LINE),
        ]))
        story.append(ntable)

        # Top 3 blockers (NO-GO eller BETINGET med begrundelse)
        blocking = [
            d for d in r.decisions
            if d.status in ("NO-GO", "BETINGET-GO")
        ][:3]
        if blocking:
            story.append(Spacer(1, 0.3 * cm))
            story.append(Paragraph("Top blockers", styles["MH2"]))
            for d in blocking:
                color = DANGER if d.status == "NO-GO" else WARN
                story.append(Paragraph(
                    f'<font color="{color.hexval()}"><b>{d.status}</b></font> · '
                    f'<b>{_xml_safe(d.lov)} {_xml_safe(d.artikel)}</b>',
                    styles["MBody"],
                ))
                if d.begrundelse:
                    story.append(Paragraph(
                        _xml_safe(d.begrundelse[:300]),
                        styles["MItalic"],
                    ))
                if d.krav:
                    krav_text = "; ".join(d.krav[:3])
                    story.append(Paragraph(
                        f"<i>Krav:</i> {_xml_safe(krav_text)}",
                        styles["MSmall"],
                    ))
                story.append(Spacer(1, 0.15 * cm))

        # Evidens-progress detail
        missing_evidens = [e for e in r.evidence if e.status in ("mangler", "i_gang")]
        if missing_evidens:
            story.append(Spacer(1, 0.2 * cm))
            story.append(Paragraph(
                f"Mangler evidens: {', '.join(_xml_safe(e.title) for e in missing_evidens[:5])}"
                + (f" og {len(missing_evidens) - 5} flere" if len(missing_evidens) > 5 else ""),
                styles["MSmall"],
            ))

        # Anbefaling
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("Anbefalet beslutning", styles["MH2"]))
        recommendation = _build_recommendation(r)
        story.append(Paragraph(recommendation, styles["MBody"]))

        if idx < len(reports):
            story.append(PageBreak())

    # ---- Final: samlede anbefalede beslutninger ----
    story.append(PageBreak())
    story.append(Paragraph("Samlede beslutninger til styregruppe", styles["MH2"]))
    story.append(Paragraph(
        "Foreslåede beslutninger pr. sag — kan udfyldes med beslutning + ansvarlig "
        "under mødet.",
        styles["MSmall"],
    ))
    story.append(Spacer(1, 0.4 * cm))

    decision_rows = [["Sag", "Verdict", "Anbefaling", "Beslutning"]]
    for r in reports:
        decision_rows.append([
            Paragraph(_xml_safe(r.case_id), styles["MBody"]),
            r.last_aggregate_status or "—",
            Paragraph(_xml_safe(_build_recommendation(r, short=True)), styles["MBody"]),
            Paragraph("__________________", styles["MSmall"]),
        ])
    dtable = Table(decision_rows, colWidths=[3 * cm, 2.6 * cm, 6 * cm, 5 * cm])
    dtable.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (-1, 0), INK_SOFT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, BRONZE),
        ("LINEBELOW", (0, 1), (-1, -1), 0.2, LINE),
    ]))
    story.append(dtable)

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica-Oblique", 7.5)
        canvas.setFillColor(colors.grey)
        canvas.drawString(
            2.2 * cm, 1.2 * cm,
            f"Bifrost mødeoversigt — {date_str} — side {doc.page}",
        )
        canvas.drawRightString(
            A4[0] - 2.2 * cm, 1.2 * cm,
            "Kalundborg Kommune · AI-compliance",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def _build_recommendation(r: CaseReportData, *, short: bool = False) -> str:
    """Generér én linje (eller 2-3 sætninger) anbefaling baseret på sagens tilstand."""
    verdict = r.last_aggregate_status
    blockers = [d for d in r.decisions if d.status == "NO-GO"]
    warnings = [d for d in r.decisions if d.status == "BETINGET-GO"]

    if verdict == "GO" and r.evidence_done == r.evidence_total and r.evidence_total > 0:
        msg = "Anbefal godkendelse — alle krav opfyldt og evidens komplet."
    elif verdict == "GO":
        msg = (
            f"Verdict GO, men evidens mangler ({r.evidence_done}/{r.evidence_total}). "
            f"Anbefal betinget godkendelse afhængig af evidens-deadline."
        )
    elif verdict == "BETINGET-GO":
        n_warnings = len(warnings)
        msg = (
            f"Betinget GO — {n_warnings} betingelse{'r' if n_warnings != 1 else ''} "
            f"skal afklares før endelig godkendelse."
        )
    elif verdict == "NO-GO":
        n_blockers = len(blockers)
        msg = (
            f"NO-GO — {n_blockers} blocker{'e' if n_blockers != 1 else ''} kræver "
            f"løsning. Anbefal at sagen returneres til sagsbehandler."
        )
    else:
        msg = "Vurdering ikke kørt — afvent kørsel af compliance-tjek før beslutning."

    if not short and r.next_review_at:
        msg += f" Næste review planlagt {_format_date(r.next_review_at)}."

    return msg


def _xml_safe(text) -> str:
    """Escape XML-special chars så reportlab Paragraph ikke crasher."""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
