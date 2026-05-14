"""EU AI Act Art. 49 database-registrerings wizard.

Mapper Bifrost-sagsdata (intake_state + evidens) → de felter som EU's
AI-database kræver for høj-risiko AI-systemer brugt af offentlige myndigheder.

Referencer (EU AI Act):
  Art. 47   — EU declaration of conformity
  Art. 49   — Registration in EU database
  Annex VIII section A — Provider-information (8 felter)
  Annex VIII section C — Public authority deployer-information (4 ekstra felter)

Output:
  - JSON: struktureret payload (forventet input til fremtidig EU-database-API)
  - PDF: print-venlig formular der kan udfyldes manuelt eller arkiveres

Designvalg:
  - Felter der ikke kan udledes fra intake markeres explicit som "udfyldes manuelt"
  - Bifrost gemmer IKKE i EU-databasen direkte — det er en eksport-funktion
  - Vi mapper KUN sager med verdict=NO-GO eller BETINGET-GO der har høj-risiko-klassifikation
"""

from __future__ import annotations

import io
import json
import logging
from datetime import datetime, UTC
from typing import Any, Optional

from sqlalchemy.orm import Session

from src.database.cases import find_case_by_external_id
from src.database.evidence import list_evidence_for_case

logger = logging.getLogger(__name__)


# 12 felter samlet fra Annex VIII A + C
# Disse er det minimum EU-databasen forventer for offentlig høj-risiko-anvendelse
EU_DB_FIELDS = [
    # ---- Provider/deployer info ----
    "deployer_name",              # Kommunen
    "deployer_address",           # Kommunens adresse
    "deployer_contact",           # Kontaktperson + email
    # ---- AI system identification ----
    "system_trade_name",          # System-navn
    "system_purpose",             # Tilsigtet formål (beskrivelse)
    "system_high_risk_category",  # Hvilken Annex III-kategori
    "system_status",              # planlagt | i_drift | tilbagetrukket
    # ---- Data + oversight ----
    "data_categories",            # Typer af data systemet bruger
    "human_oversight_measures",   # Hvilken menneskelig kontrol
    "fria_mitigations",           # Identificerede risici + mitigations
    # ---- Compliance status ----
    "conformity_assessment_date", # Hvornår conformity-assessment blev udført
    "registration_date",          # Hvornår vi registrerer dette
]


# Mapping fra intake_state.fagomraade → Annex III høj-risiko-kategori
# (forsimplet — i praksis kræver det jurist-vurdering)
FAGOMRAADE_TO_ANNEX_III = {
    "beskaeftigelse": "Annex III §4 (employment, workers management)",
    "uddannelse": "Annex III §3 (education, vocational training)",
    "sundhed": "Annex III §5 (essential public services — healthcare)",
    "borgerservice": "Annex III §5 (essential public services)",
    "retshjaelp": "Annex III §6 (law enforcement) eller §8 (justice)",
    "kritisk_infrastruktur": "Annex III §2 (critical infrastructure)",
    "biometri": "Annex III §1 (biometric identification)",
    "migration": "Annex III §7 (migration, asylum, border control)",
    "infrastruktur": "Annex III §2 (critical infrastructure)",
}


class EUDatabaseExportError(Exception):
    pass


def build_export(
    session: Session,
    case_id: str,
    *,
    deployer_overrides: Optional[dict] = None,
) -> dict[str, Any]:
    """Generér EU-database-payload for en sag.

    Args:
        session: SQLAlchemy session
        case_id: eksternt case_id (fx 'K-2026-0042')
        deployer_overrides: valgfrit dict til at overskrive deployer-info
            (default = Kalundborg Kommune)

    Returns:
        Dict med 12 EU-database-felter + meta (export_id, generated_at, source)

    Raises:
        EUDatabaseExportError: hvis sag ikke findes eller mangler kritiske data
    """
    case = find_case_by_external_id(session, case_id)
    if case is None:
        raise EUDatabaseExportError(f"Sag {case_id} findes ikke")

    intake = case.get_intake_state() or {}
    evidens = list_evidence_for_case(session, case.id)

    # Default deployer = Kalundborg Kommune
    deployer = {
        "deployer_name": "Kalundborg Kommune",
        "deployer_address": "Holbækvej 141 B, 4400 Kalundborg, Danmark",
        "deployer_contact": "ServicePortalen@kalundborg.dk",
    }
    if deployer_overrides:
        deployer.update(deployer_overrides)

    # System-identifikation
    system_name = case.title or intake.get("system_navn") or "(uden navn)"
    system_purpose = (
        intake.get("system_description")
        or intake.get("behov")
        or "Ikke specificeret i intake"
    )

    # Annex III mapping via fagomraade
    fagomraade = (intake.get("fagomraade") or "").lower()
    high_risk_cat = FAGOMRAADE_TO_ANNEX_III.get(
        fagomraade,
        f"Ikke automatisk mappet — fagområde='{intake.get('fagomraade') or 'ukendt'}'",
    )

    # System-status fra case-status
    status_map = {
        "kladde": "planlagt",
        "vurderet": "planlagt",
        "remediation": "under_review",
        "godkendt": "i_drift",
        "afvist": "tilbagetrukket",
    }
    system_status = status_map.get(case.status, case.status)

    # Persondata-kategorier
    data_categories = []
    if intake.get("behandler_persondata"):
        types = intake.get("persondata_typer") or []
        if isinstance(types, list):
            data_categories = types
        elif isinstance(types, str):
            data_categories = [types]
    if not data_categories:
        data_categories = ["Ingen persondata"]

    # Human oversight + FRIA — udled fra evidens hvis udfyldt
    human_oversight = _extract_from_evidence(
        evidens,
        artifact_ids=["human_oversight_plan", "menneskelig_kontrol"],
        sections=["overordnet_design", "fallback", "alarmer", "scope"],
        fallback="Udfyldes manuelt fra menneskelig-kontrol-evidens",
    )
    fria_mitigations = _extract_from_evidence(
        evidens,
        artifact_ids=[
            "fundamental_rights_impact_assessment",
            "fria",
            "risikostyringsplan",
        ],
        sections=["mitigation", "tiltag", "risici", "risikomatrix"],
        fallback="Udfyldes manuelt fra FRIA-evidens",
    )

    # Conformity assessment dato — fra evidens hvis godkendt
    conformity_date = _find_completion_date(
        evidens,
        artifact_ids=["ai_act_conformity_assessment", "conformity_assessment"],
    )

    payload = {
        **deployer,
        "system_trade_name": system_name,
        "system_purpose": (system_purpose or "")[:2000],  # trunkér til EU-grænse
        "system_high_risk_category": high_risk_cat,
        "system_status": system_status,
        "data_categories": data_categories,
        "human_oversight_measures": (human_oversight or "")[:1500],
        "fria_mitigations": (fria_mitigations or "")[:1500],
        "conformity_assessment_date": conformity_date,
        "registration_date": datetime.now(UTC).strftime("%Y-%m-%d"),
        # Meta
        "_meta": {
            "case_id": case_id,
            "case_title": case.title,
            "case_status": case.status,
            "exported_at": datetime.now(UTC).isoformat(),
            "source": "Bifrost EU-database export v1",
            "disclaimer": (
                "Genereret automatisk fra Bifrost-data. SKAL reviewes af jurist "
                "før indsendelse til EU-databasen. Felter markeret 'Udfyldes manuelt' "
                "kræver oplysninger der ikke findes i intake/evidens."
            ),
            "missing_fields": _identify_missing(payload_check := {
                "human_oversight_measures": human_oversight,
                "fria_mitigations": fria_mitigations,
                "conformity_assessment_date": conformity_date,
            }),
        },
    }

    return payload


def _extract_from_evidence(
    evidens: list,
    *,
    artifact_ids: list[str],
    sections: list[str],
    fallback: str,
) -> str:
    """Find udfyldt indhold fra én af de relevante evidens-artefakter."""
    for e in evidens:
        if e.artifact_id not in artifact_ids:
            continue
        content = e.get_content() if hasattr(e, "get_content") else (e.content or {})
        if not isinstance(content, dict):
            continue
        # Saml relevant indhold fra de matchende sections
        bits = []
        for sk in sections:
            v = content.get(sk)
            if v and isinstance(v, str) and v.strip():
                bits.append(f"{sk}: {v.strip()}")
        if bits:
            return " | ".join(bits)
    return fallback


def _find_completion_date(
    evidens: list, *, artifact_ids: list[str]
) -> Optional[str]:
    """Returnér completed_at-dato for første matching evidens i status faerdig/godkendt."""
    for e in evidens:
        if e.artifact_id in artifact_ids and e.status in ("faerdig", "godkendt"):
            if e.completed_at:
                return e.completed_at.strftime("%Y-%m-%d")
    return None


def _identify_missing(check: dict) -> list[str]:
    """Returnér liste af felter der mangler reel data (kun fallback-tekst)."""
    missing = []
    for key, val in check.items():
        if val is None or not val or (isinstance(val, str) and "Udfyldes manuelt" in val):
            missing.append(key)
    return missing


# ---- PDF rendering -----------------------------------------------------


def render_pdf(payload: dict[str, Any]) -> bytes:
    """Render EU-database-payload som print-venlig PDF."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    )

    NAVY = colors.HexColor("#0d2e54")
    BRONZE = colors.HexColor("#6e5527")
    INK = colors.HexColor("#14181f")
    INK_SOFT = colors.HexColor("#555a64")
    WARN = colors.HexColor("#b08a4a")
    LINE = colors.HexColor("#d8d3c5")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=2.2 * cm, bottomMargin=2.2 * cm,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm,
        title=f"EU-database-registrering — {payload['_meta'].get('case_id', '?')}",
        author=payload.get("deployer_name", "Bifrost"),
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="EUEyebrow", parent=styles["Normal"], fontSize=8, textColor=BRONZE, spaceAfter=4, leading=10))
    styles.add(ParagraphStyle(name="EUTitle", parent=styles["Title"], fontSize=20, textColor=INK, spaceAfter=8, leading=24))
    styles.add(ParagraphStyle(name="EUSubtitle", parent=styles["Normal"], fontSize=10, textColor=INK_SOFT, spaceAfter=10))
    styles.add(ParagraphStyle(name="EUH2", parent=styles["Heading2"], fontSize=12, textColor=NAVY, spaceBefore=14, spaceAfter=6))
    styles.add(ParagraphStyle(name="EULabel", parent=styles["Normal"], fontSize=9, textColor=INK_SOFT, spaceBefore=4, spaceAfter=2))
    styles.add(ParagraphStyle(name="EUBody", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=4))
    styles.add(ParagraphStyle(name="EUSmall", parent=styles["Normal"], fontSize=8.5, textColor=INK_SOFT, leading=11))
    styles.add(ParagraphStyle(name="EUWarning", parent=styles["Normal"], fontSize=9, textColor=WARN, leading=12, spaceAfter=6))

    story = []

    # ---- Header ----
    story.append(Paragraph("EU AI Act · Art. 49 · Database-registrering", styles["EUEyebrow"]))
    story.append(Paragraph(_safe(payload.get("system_trade_name", "AI-system")), styles["EUTitle"]))
    story.append(Paragraph(
        f"Sag <b>{_safe(payload['_meta'].get('case_id', '?'))}</b> · "
        f"Genereret {payload['_meta'].get('exported_at', '')[:10]} · "
        f"{payload.get('deployer_name', '')}",
        styles["EUSubtitle"],
    ))

    # Disclaimer
    story.append(Paragraph(
        f"<b>Vigtigt:</b> {_safe(payload['_meta'].get('disclaimer', ''))}",
        styles["EUWarning"],
    ))

    # Missing fields banner
    missing = payload["_meta"].get("missing_fields", [])
    if missing:
        story.append(Paragraph(
            f"<b>{len(missing)} felter mangler reel data:</b> {', '.join(missing)}",
            styles["EUWarning"],
        ))

    # ---- Felter pr. sektion ----
    sections = [
        ("1. Deployer (offentlig myndighed)", [
            ("Deployer", payload.get("deployer_name")),
            ("Adresse", payload.get("deployer_address")),
            ("Kontakt", payload.get("deployer_contact")),
        ]),
        ("2. AI-system identifikation", [
            ("Handelsnavn", payload.get("system_trade_name")),
            ("Tilsigtet formål", payload.get("system_purpose")),
            ("Høj-risiko kategori", payload.get("system_high_risk_category")),
            ("Status", payload.get("system_status")),
        ]),
        ("3. Data + menneskelig kontrol", [
            ("Datakategorier", ", ".join(payload.get("data_categories", []))),
            ("Menneskelig kontrol", payload.get("human_oversight_measures")),
            ("FRIA + mitigations", payload.get("fria_mitigations")),
        ]),
        ("4. Compliance status", [
            ("Conformity assessment dato", payload.get("conformity_assessment_date") or "(udfyldes manuelt)"),
            ("Registreringsdato", payload.get("registration_date")),
        ]),
    ]

    for title, fields in sections:
        story.append(Paragraph(title, styles["EUH2"]))
        rows = []
        for label, value in fields:
            v = _safe(str(value or "(tom)"))
            rows.append([
                Paragraph(label, styles["EULabel"]),
                Paragraph(v, styles["EUBody"]),
            ])
        t = Table(rows, colWidths=[5.5 * cm, None])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -2), 0.2, LINE),
        ]))
        story.append(t)

    # ---- Underskrift ----
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("Underskrift af ansvarlig", styles["EUH2"]))
    sig_rows = [
        ["Navn:", "____________________________________"],
        ["Titel:", "____________________________________"],
        ["Dato:", "____________________________________"],
        ["Underskrift:", "____________________________________"],
    ]
    sig_table = Table(sig_rows, colWidths=[4 * cm, None])
    sig_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), INK_SOFT),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(sig_table)

    # Footer
    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica-Oblique", 7.5)
        canvas.setFillColor(colors.grey)
        canvas.drawString(
            2.2 * cm, 1.2 * cm,
            f"Bifrost EU-database-export · sag {payload['_meta'].get('case_id', '?')} · side {doc.page}",
        )
        canvas.drawRightString(
            A4[0] - 2.2 * cm, 1.2 * cm,
            "Kalundborg Kommune · AI-compliance",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def _safe(text) -> str:
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
