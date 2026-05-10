"""Per-evidens-felt kommentarer / diskussion.

Brug-case: jurist + sagsbehandler diskuterer en konkret formulering i en
evidens-skabelon. Kommentarerne er knyttet til (case_id, artifact_id,
section_key) — så de bliver synlige NÆSTE GANG nogen åbner samme felt.

Når en kommentar oprettes emitteres et timeline-event så det vises i
sagens audit-trail. Det er det eneste sted det "lever" ud over selve
felt-popoveren.

Designvalg:
- section_key = NULL betyder kommentaren er på hele dokumentet.
- "resolved" markering bruges til at skjule besvarede tråde uden at slette.
- Ingen threading (én flad liste pr. felt) — keep it simple.
- Author er fri-tekst (kommunal brugerdatabase findes ikke endnu).
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, Index
from sqlalchemy.orm import Session

from src.database.connection import Base


class EvidenceComment(Base):
    __tablename__ = "evidence_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), nullable=False)
    artifact_id = Column(String(96), nullable=False)
    section_key = Column(String(96), nullable=True)  # null = på hele dokumentet

    body = Column(Text, nullable=False)
    author = Column(String(64), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_evidence_comments_case_artifact", "case_id", "artifact_id"),
        Index("ix_evidence_comments_section", "case_id", "artifact_id", "section_key"),
        Index("ix_evidence_comments_created_at", "created_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "artifact_id": self.artifact_id,
            "section_key": self.section_key,
            "body": self.body,
            "author": self.author,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "is_resolved": self.resolved_at is not None,
        }


# ---- Service helpers ------------------------------------------------------


def list_comments(
    session: Session,
    *,
    case_id: str,
    artifact_id: Optional[str] = None,
    section_key: Optional[str] = None,
    include_resolved: bool = True,
) -> list[EvidenceComment]:
    query = session.query(EvidenceComment).filter(
        EvidenceComment.case_id == case_id,
    )
    if artifact_id is not None:
        query = query.filter(EvidenceComment.artifact_id == artifact_id)
    if section_key is not None:
        query = query.filter(EvidenceComment.section_key == section_key)
    if not include_resolved:
        query = query.filter(EvidenceComment.resolved_at.is_(None))
    return query.order_by(EvidenceComment.created_at.asc()).all()


def create_comment(
    session: Session,
    *,
    case_id: str,
    artifact_id: str,
    section_key: Optional[str],
    body: str,
    author: Optional[str] = None,
) -> EvidenceComment:
    if not body or not body.strip():
        raise ValueError("body is required")
    if len(body) > 4000:
        raise ValueError("body too long (max 4000 chars)")

    comment = EvidenceComment(
        case_id=case_id,
        artifact_id=artifact_id,
        section_key=section_key,
        body=body.strip(),
        author=author,
    )
    session.add(comment)
    session.flush()
    return comment


def resolve_comment(
    session: Session, comment_id: int, *, user: Optional[str] = None
) -> Optional[EvidenceComment]:
    comment = (
        session.query(EvidenceComment)
        .filter(EvidenceComment.id == comment_id)
        .one_or_none()
    )
    if comment is None:
        return None
    comment.resolved_at = datetime.now(UTC)
    comment.resolved_by = user
    session.flush()
    return comment


def delete_comment(session: Session, comment_id: int) -> bool:
    comment = (
        session.query(EvidenceComment)
        .filter(EvidenceComment.id == comment_id)
        .one_or_none()
    )
    if comment is None:
        return False
    session.delete(comment)
    session.flush()
    return True


def comment_counts_for_case(
    session: Session, case_id: str
) -> dict[str, dict[str, int]]:
    """Returner {artifact_id: {section_key|"_doc": {open: N, resolved: N}}}.

    Bruges til at vise comment-badges i UI uden at hente alle bodies.
    """
    rows = (
        session.query(EvidenceComment)
        .filter(EvidenceComment.case_id == case_id)
        .all()
    )
    out: dict[str, dict[str, dict[str, int]]] = {}
    for c in rows:
        artifact_bucket = out.setdefault(c.artifact_id, {})
        key = c.section_key or "_doc"
        section_bucket = artifact_bucket.setdefault(key, {"open": 0, "resolved": 0})
        if c.resolved_at:
            section_bucket["resolved"] += 1
        else:
            section_bucket["open"] += 1
    return out
