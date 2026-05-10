"""Persistens af evidens-artefakter pr. sag.

Hvert artefakt (fx 'risikostyringsplan', 'dpia_dokument') gemmes som én række
med:

  * `case_id` — eksternt sags-ID (matchende `cases.case_id`)
  * `artifact_id` — skabelon-ID fra `evidence_artifacts.ARTIFACT_TEMPLATES`
  * `content_json` — dict {section_key: value} med sagsbehandlerens svar
  * `status` — beregnet automatisk: mangler | i_gang | faerdig
  * `last_edited_by` / `completed_by` — bruger-strenge

Vi bruger composite PK (case_id, artifact_id) så hver kombination er unik.

For `case_id` bruges *eksternt* ID (K-2026-0184) i stedet for FK til `cases.id`,
fordi en sagsbehandler kan begynde at udfylde artefakter INDEN sagen er
oprettet i workflow-tabellen — vi vil ikke kræve case-row eksisterer først.
"""

from __future__ import annotations

import json
from datetime import datetime, UTC
from typing import Any, Optional

from sqlalchemy import Column, DateTime, String, Text, Index
from sqlalchemy.orm import Session

from src.database.connection import Base


VALID_STATUSES = ("mangler", "i_gang", "faerdig", "godkendt")


class EvidenceArtifact(Base):
    """En sagsbehandler-udfyldt evidens-artefakt for én sag."""

    __tablename__ = "evidence_artifacts"

    case_id = Column(String(64), primary_key=True, nullable=False)
    artifact_id = Column(String(96), primary_key=True, nullable=False)

    status = Column(String(16), nullable=False, default="mangler")
    content_json = Column(Text, nullable=False, default="{}")

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    last_edited_by = Column(String(64), nullable=True)
    completed_by = Column(String(64), nullable=True)

    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_evidence_case_status", "case_id", "status"),
    )

    def get_content(self) -> dict[str, Any]:
        try:
            return json.loads(self.content_json or "{}")
        except (TypeError, ValueError):
            return {}

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "artifact_id": self.artifact_id,
            "status": self.status,
            "content": self.get_content(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "last_edited_by": self.last_edited_by,
            "completed_by": self.completed_by,
            "notes": self.notes,
        }


# ---- Service helpers ------------------------------------------------------


def list_evidence_for_case(session: Session, case_id: str) -> list[EvidenceArtifact]:
    """Alle artefakter for én sag."""
    return (
        session.query(EvidenceArtifact)
        .filter(EvidenceArtifact.case_id == case_id)
        .order_by(EvidenceArtifact.artifact_id)
        .all()
    )


def get_evidence(
    session: Session, case_id: str, artifact_id: str
) -> Optional[EvidenceArtifact]:
    return (
        session.query(EvidenceArtifact)
        .filter(
            EvidenceArtifact.case_id == case_id,
            EvidenceArtifact.artifact_id == artifact_id,
        )
        .one_or_none()
    )


def upsert_evidence(
    session: Session,
    *,
    case_id: str,
    artifact_id: str,
    content: dict[str, Any],
    computed_status: str,
    user: Optional[str] = None,
    notes: Optional[str] = None,
) -> EvidenceArtifact:
    """Opret eller opdatér et artefakt. Sætter completed_at automatisk når
    status går til 'faerdig' eller 'godkendt' første gang."""
    if computed_status not in VALID_STATUSES:
        raise ValueError(f"invalid status: {computed_status}")

    row = get_evidence(session, case_id, artifact_id)
    now = datetime.now(UTC)

    if row is None:
        row = EvidenceArtifact(
            case_id=case_id,
            artifact_id=artifact_id,
            status=computed_status,
            content_json=json.dumps(content, ensure_ascii=False),
            last_edited_by=user,
            notes=notes,
        )
        if computed_status in ("faerdig", "godkendt"):
            row.completed_at = now
            row.completed_by = user
        session.add(row)
    else:
        row.content_json = json.dumps(content, ensure_ascii=False)
        row.last_edited_by = user
        if notes is not None:
            row.notes = notes
        # Set completed_at the first time we hit faerdig/godkendt
        if computed_status in ("faerdig", "godkendt") and row.status not in ("faerdig", "godkendt"):
            row.completed_at = now
            row.completed_by = user
        # Reset completed_at if user backtracks
        if computed_status not in ("faerdig", "godkendt") and row.completed_at:
            row.completed_at = None
            row.completed_by = None
        row.status = computed_status
        row.updated_at = now

    session.flush()
    return row


def case_evidence_summary(session: Session, case_id: str) -> dict:
    """Aggregat for /drift eller case-detail-view."""
    rows = list_evidence_for_case(session, case_id)
    by_status: dict[str, int] = {}
    for row in rows:
        by_status[row.status] = by_status.get(row.status, 0) + 1
    return {
        "case_id": case_id,
        "total_started": len(rows),
        "by_status": by_status,
        "last_updated": max(
            (r.updated_at for r in rows if r.updated_at), default=None
        ),
    }
