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

import json

from sqlalchemy import Column, DateTime, String, Text, ForeignKey, Index, desc
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

    # Tracks when the case-reminder job last sent an email about this case.
    # Used to throttle reminders to once per CASE_REMINDER_COOLDOWN_DAYS.
    last_reminder_sent_at = Column(DateTime(timezone=True), nullable=True)

    # If the case has been linked to a specific assessment, point at the
    # latest one. Use list_assessments_for_case() for the full history.
    last_assessment_log_id = Column(String(36), nullable=True)

    # Indkøbsproces-wizardens state — gemmes som JSON så vi kan udvide
    # uden at lave nye migrations hver gang. Indeholder bl.a.:
    #   { "current_step": 1-4,
    #     "behov": str,
    #     "dobbeltsystem_tjekket": bool,
    #     "serviceportal_dato": "YYYY-MM-DD",
    #     "indkoeb_eller_udvikling": "indkoeb"|"udvikling"|null,
    #     "system_description": str,
    #     "ec_flags": dict|null,         # hvis EC-checker kørt
    #     "last_step_completed_at": iso }
    intake_state = Column(Text, nullable=True)

    transitions = relationship(
        "CaseTransition",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="CaseTransition.changed_at",
    )

    __table_args__ = (
        Index("ix_cases_status_review", "status", "next_review_at"),
    )

    def get_intake_state(self) -> dict:
        if not self.intake_state:
            return {}
        try:
            return json.loads(self.intake_state)
        except (TypeError, ValueError):
            return {}

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
            "last_reminder_sent_at": self.last_reminder_sent_at.isoformat() if self.last_reminder_sent_at else None,
            "last_assessment_log_id": self.last_assessment_log_id,
            "intake_state": self.get_intake_state(),
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


# ---- Intake-state helpers (indkøbsproces-wizard) --------------------------


def find_case_by_external_id(session: Session, case_id: str) -> Optional[Case]:
    """Finder seneste case-row med eksternt sagsnummer. Bruges af
    /indkoebsproces-wizardens load-from-URL flow."""
    return (
        session.query(Case)
        .filter(Case.case_id == case_id)
        .order_by(desc(Case.updated_at))
        .first()
    )


def upsert_intake_state(
    session: Session,
    *,
    case_id: str,
    intake_state: dict,
    title: Optional[str] = None,
    user: Optional[str] = None,
) -> Case:
    """Opret case-row hvis den ikke findes + gem/opdatér intake-state JSON.

    Bruges af `PUT /api/v3/cases/by-case-id/{case_id}/intake` til at persistere
    indkøbsproces-wizardens state. Status sættes til 'kladde' indtil en
    rigtig vurdering har kørt (transition håndteres af `attach_assessment`).
    """
    case = find_case_by_external_id(session, case_id)
    now = datetime.now(UTC)
    payload = json.dumps(intake_state, ensure_ascii=False)

    if case is None:
        # Auto-derive title from intake_state.behov hvis ikke givet
        derived_title = title or _derive_title_from_intake(intake_state) or case_id
        case = create_case(
            session,
            case_id=case_id,
            title=derived_title,
            assigned_to=user,
            status="kladde",
        )
        case.intake_state = payload
    else:
        case.intake_state = payload
        if title:
            case.title = title
        elif not case.title or case.title == case.case_id:
            # Re-derive title hvis det er placeholder
            t = _derive_title_from_intake(intake_state)
            if t:
                case.title = t
        if user and not case.assigned_to:
            case.assigned_to = user
        case.updated_at = now
    session.flush()
    return case


def _derive_title_from_intake(intake_state: dict) -> Optional[str]:
    """Udlede en vist titel fra behov eller system_description."""
    for key in ("behov", "system_description"):
        v = (intake_state or {}).get(key)
        if isinstance(v, str) and v.strip():
            first = v.strip().split("\n")[0].split(".")[0].strip()
            if 5 <= len(first) <= 120:
                return first[:1].upper() + first[1:]
    return None


def list_drafts_with_intake(session: Session, *, limit: int = 50) -> list[Case]:
    """List sager med ikke-tom intake_state, sorteret efter sidst opdateret.
    Bruges af 'Mine sager'-stripen i indkøbsproces-wizarden."""
    return (
        session.query(Case)
        .filter(Case.intake_state.isnot(None))
        .filter(Case.intake_state != "{}")
        .order_by(desc(Case.updated_at))
        .limit(limit)
        .all()
    )
