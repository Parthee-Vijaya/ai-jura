"""Notifications-tabel + helper-funktioner.

Auto-genererede events for sagsbehandlere — vises som badge i Bifrosts
sidebar header. Eksempler på events:

  - Evidens completed (alle eller specifik artefakt)
  - DPIA-tærskel udløst
  - Citat flagget for review
  - Case-transition (kladde → vurderet → godkendt)
  - AI-enhedens vurdering returneret

Read-state pr. (notification, user) er ikke implementeret i MVP — vi har
én global læs-state pr. notifikation. RBAC + per-user inboxes kommer
i pilot-readiness M9.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import Column, DateTime, String, Text, Index, desc, func
from sqlalchemy.orm import Session

from src.database.connection import Base


# Tilladte event-typer. Holdt simpelt — flere kan tilføjes uden migration.
NOTIFICATION_KINDS = (
    "evidens_completed",
    "evidens_started",
    "dpia_threshold",
    "citation_flagged",
    "case_transition",
    "ai_unit_returned",
    "info",
)

NOTIFICATION_SEVERITIES = ("info", "success", "warn", "danger")


class Notification(Base):
    """Én event-row vist i sagsbehandlerens notifikations-panel."""

    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )

    # Event identifikation
    kind = Column(String(32), nullable=False, index=True)
    severity = Column(String(16), nullable=False, default="info")

    # Indhold
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    case_id = Column(String(64), nullable=True, index=True)
    link_url = Column(String(255), nullable=True)
    actor = Column(String(64), nullable=True)

    # Read-state (global for nu — MVP)
    read_at = Column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        Index("ix_notifications_unread", "read_at", "created_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "kind": self.kind,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "case_id": self.case_id,
            "link_url": self.link_url,
            "actor": self.actor,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "is_read": self.read_at is not None,
        }


# ---- Service helpers ------------------------------------------------------


def emit(
    session: Session,
    *,
    kind: str,
    title: str,
    message: Optional[str] = None,
    case_id: Optional[str] = None,
    link_url: Optional[str] = None,
    severity: str = "info",
    actor: Optional[str] = None,
    dedupe_window_minutes: int = 30,
) -> Notification:
    """Skab en ny notifikation. Dedupliker mod identiske events i `dedupe_window`."""
    if kind not in NOTIFICATION_KINDS:
        kind = "info"
    if severity not in NOTIFICATION_SEVERITIES:
        severity = "info"

    # Dedup: samme kind + case_id + title inden for window → spring over
    if dedupe_window_minutes > 0:
        cutoff = datetime.now(UTC).timestamp() - dedupe_window_minutes * 60
        from datetime import datetime as _dt
        existing = (
            session.query(Notification)
            .filter(Notification.kind == kind)
            .filter(Notification.case_id == case_id)
            .filter(Notification.title == title)
            .order_by(desc(Notification.created_at))
            .first()
        )
        if existing and existing.created_at and existing.created_at.timestamp() > cutoff:
            return existing

    n = Notification(
        kind=kind,
        severity=severity,
        title=title,
        message=message,
        case_id=case_id,
        link_url=link_url,
        actor=actor,
    )
    session.add(n)
    session.flush()
    return n


def list_recent(
    session: Session,
    *,
    limit: int = 30,
    unread_only: bool = False,
) -> list[Notification]:
    q = session.query(Notification).order_by(desc(Notification.created_at))
    if unread_only:
        q = q.filter(Notification.read_at.is_(None))
    return q.limit(limit).all()


def count_unread(session: Session) -> int:
    return (
        session.query(func.count(Notification.id))
        .filter(Notification.read_at.is_(None))
        .scalar()
    ) or 0


def mark_read(session: Session, notification_id: str) -> Optional[Notification]:
    n = session.query(Notification).filter(Notification.id == notification_id).one_or_none()
    if n and n.read_at is None:
        n.read_at = datetime.now(UTC)
        session.flush()
    return n


def mark_all_read(session: Session) -> int:
    updated = (
        session.query(Notification)
        .filter(Notification.read_at.is_(None))
        .update({"read_at": datetime.now(UTC)}, synchronize_session=False)
    )
    return updated
