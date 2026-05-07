"""Case workflow state-machine (Step 2 of the v3 evolution roadmap).

A *case* is the long-lived workflow object that aggregates N audit-log
entries (each a vurdering) under one external Kalundborg case-ID. The
case carries the decision-relevant state — kladde / vurderet /
remediation / godkendt / idriftsat / arkiveret — and lets sagsbehandlere
track what's actually happening over time.

The audit-log is still append-only and authoritative for the legal
record; this table is for workflow ergonomics on top of it.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import Column, DateTime, String, Text, ForeignKey, Index
from sqlalchemy.orm import Session, relationship

from src.database.connection import Base


# Allowed states. Order matters for kanban-rendering left-to-right.
CASE_STATUSES = (
    "kladde",       # Drafted, not yet vurderet
    "vurderet",     # Has at least one v3 assessment
    "remediation",  # Vurdering kræver kompenserende kontroller
    "godkendt",     # All requirements met, ready to deploy
    "idriftsat",    # In production
    "arkiveret",    # Closed (idriftsat + retention period passed, eller annulleret)
)
CASE_STATUS_LABELS = {
    "kladde": "Kladde",
    "vurderet": "Vurderet",
    "remediation": "Remediation",
    "godkendt": "Godkendt",
    "idriftsat": "Idriftsat",
    "arkiveret": "Arkiveret",
}


class Case(Base):
    """Long-lived workflow record aggregating one or more assessments."""

    __tablename__ = "cases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
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

    # External case identifier (the K-2026-0184 the sagsbehandler types in).
    # NOT unique — same external ID can have multiple workflow rows in
    # rare cases (split, reopen).
    case_id = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)

    status = Column(String(32), nullable=False, default="kladde", index=True)
    last_aggregate_status = Column(String(16), nullable=True)
    assigned_to = Column(String(64), nullable=True)
    next_review_at = Column(DateTime(timezone=True), nullable=True, index=True)
    notes = Column(Text, nullable=True)

    # If the case has been linked to a specific assessment, point at the
    # latest one. Use list_assessments_for_case() for the full history.
    last_assessment_log_id = Column(String(36), nullable=True)

    transitions = relationship(
        "CaseTransition",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="CaseTransition.changed_at",
    )

    __table_args__ = (
        Index("ix_cases_status_review", "status", "next_review_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "title": self.title,
            "status": self.status,
            "status_label": CASE_STATUS_LABELS.get(self.status, self.status),
            "last_aggregate_status": self.last_aggregate_status,
            "assigned_to": self.assigned_to,
            "next_review_at": self.next_review_at.isoformat() if self.next_review_at else None,
            "notes": self.notes,
            "last_assessment_log_id": self.last_assessment_log_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CaseTransition(Base):
    """Audit-trail of state changes on a case. Append-only."""

    __tablename__ = "case_transitions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_db_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    changed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    from_status = Column(String(32), nullable=True)  # null when first created
    to_status = Column(String(32), nullable=False)
    note = Column(Text, nullable=True)
    changed_by = Column(String(64), nullable=True)

    case = relationship("Case", back_populates="transitions")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "note": self.note,
            "changed_by": self.changed_by,
        }


# ---- Service helpers --------------------------------------------------------

def create_case(
    session: Session,
    *,
    case_id: str,
    title: str,
    notes: Optional[str] = None,
    status: str = "kladde",
    assigned_to: Optional[str] = None,
    last_assessment_log_id: Optional[str] = None,
    last_aggregate_status: Optional[str] = None,
) -> Case:
    """Create a new case + initial transition entry."""
    if status not in CASE_STATUSES:
        raise ValueError(f"invalid status: {status}")
    case = Case(
        case_id=case_id,
        title=title,
        notes=notes,
        status=status,
        assigned_to=assigned_to,
        last_assessment_log_id=last_assessment_log_id,
        last_aggregate_status=last_aggregate_status,
    )
    session.add(case)
    session.flush()
    transition = CaseTransition(
        case_db_id=case.id,
        from_status=None,
        to_status=status,
        note=f"Sag oprettet ({title})",
    )
    session.add(transition)
    session.flush()
    return case


def transition_case(
    session: Session,
    case_db_id: str,
    new_status: str,
    *,
    note: Optional[str] = None,
    changed_by: Optional[str] = None,
) -> Case:
    """Move a case to a new status with audit trail."""
    if new_status not in CASE_STATUSES:
        raise ValueError(f"invalid status: {new_status}")
    case = session.query(Case).filter(Case.id == case_db_id).one_or_none()
    if case is None:
        raise ValueError(f"case not found: {case_db_id}")
    if case.status == new_status:
        return case  # no-op
    transition = CaseTransition(
        case_db_id=case.id,
        from_status=case.status,
        to_status=new_status,
        note=note,
        changed_by=changed_by,
    )
    session.add(transition)
    case.status = new_status
    case.updated_at = datetime.now(UTC)
    session.flush()
    return case


def list_cases(
    session: Session,
    *,
    status: Optional[str] = None,
    case_id: Optional[str] = None,
    limit: int = 200,
) -> list[Case]:
    q = session.query(Case).order_by(Case.updated_at.desc())
    if status:
        q = q.filter(Case.status == status)
    if case_id:
        q = q.filter(Case.case_id == case_id)
    return q.limit(limit).all()


def get_case(session: Session, case_db_id: str) -> Optional[Case]:
    return session.query(Case).filter(Case.id == case_db_id).one_or_none()


def attach_assessment(
    session: Session,
    case_db_id: str,
    assessment_log_id: str,
    aggregate_status: str,
) -> Case:
    """Link a v3_assessment_log entry to a case + auto-transition."""
    case = get_case(session, case_db_id)
    if case is None:
        raise ValueError(f"case not found: {case_db_id}")
    case.last_assessment_log_id = assessment_log_id
    case.last_aggregate_status = aggregate_status
    case.updated_at = datetime.now(UTC)

    # Auto-transition kladde → vurderet on first assessment.
    if case.status == "kladde":
        transition_case(
            session,
            case_db_id,
            "vurderet",
            note=f"Auto-transition efter første vurdering ({aggregate_status})",
        )
    # Suggest remediation if BETINGET-GO/NO-GO and currently in vurderet.
    elif case.status == "vurderet" and aggregate_status in ("BETINGET-GO", "NO-GO"):
        transition_case(
            session,
            case_db_id,
            "remediation",
            note=f"Auto-transition: ny vurdering kræver remediation ({aggregate_status})",
        )
    session.flush()
    return case
