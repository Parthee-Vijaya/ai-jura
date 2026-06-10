"""Persistens af genererede risikovurderinger — journalisering + historik.

Hvorfor: AI-tjeklisten kræver at indkøb journaliseres på en særskilt sag, og
GDPR-god praksis kræver spor af hvad AI-værktøjet har produceret. Før denne
tabel levede en genereret vurdering KUN i browserens state — lukket tab =
tabt arbejde + intet revisionsspor.

Hver generate-kørsel gemmes (best-effort, blokerer aldrig svaret) med hele
Risikovurdering-objektet som JSON, så Word-dokumentet kan re-renderes
deterministisk senere uden nye LLM-kald.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String
from sqlalchemy.orm import Session

from src.database.connection import Base


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    systemnavn = Column(String(200), nullable=False, index=True)
    case_id = Column(String(64), nullable=True, index=True)
    created_by = Column(String(128), nullable=True)
    rv_json = Column(JSON, nullable=False)
    n_risici = Column(Integer, nullable=False, default=0)
    verify_valid = Column(Boolean, nullable=True)

    def to_summary(self) -> dict:
        """Liste-visning — uden den tunge rv_json."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "systemnavn": self.systemnavn,
            "case_id": self.case_id,
            "created_by": self.created_by,
            "n_risici": self.n_risici,
            "verify_valid": self.verify_valid,
        }

    def to_full(self) -> dict:
        d = self.to_summary()
        d["risikovurdering"] = self.rv_json
        return d


def save_assessment(
    db: Session,
    *,
    systemnavn: str,
    rv_json: dict,
    n_risici: int,
    case_id: Optional[str] = None,
    created_by: Optional[str] = None,
    verify_valid: Optional[bool] = None,
) -> RiskAssessment:
    """Gem en genereret risikovurdering. Caller committer."""
    row = RiskAssessment(
        systemnavn=(systemnavn or "system")[:200],
        case_id=(case_id or None),
        created_by=(created_by or None),
        rv_json=rv_json,
        n_risici=n_risici,
        verify_valid=verify_valid,
    )
    db.add(row)
    db.flush()
    return row


def list_assessments(
    db: Session,
    *,
    case_id: Optional[str] = None,
    limit: int = 50,
) -> list[RiskAssessment]:
    q = db.query(RiskAssessment).order_by(RiskAssessment.created_at.desc())
    if case_id:
        q = q.filter(RiskAssessment.case_id == case_id)
    return q.limit(min(limit, 200)).all()


def get_assessment(db: Session, assessment_id: str) -> Optional[RiskAssessment]:
    return (
        db.query(RiskAssessment)
        .filter(RiskAssessment.id == assessment_id)
        .one_or_none()
    )
