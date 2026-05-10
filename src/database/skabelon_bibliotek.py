"""Skabelon-bibliotek — gemte evidens-skabeloner til genbrug på tværs af sager.

Baggrund: Pavi udfylder fx `ai_faerdigheder_program` for sag 1, og det
program er ofte 95% identisk på sag 2, 3, 4, ... Vi vil have at en sagsbehandler
kan markere en udfyldt evidens som "skabelon", give den et navn ("Standard
literacy-program for Borgerservice"), og så kunne hente den ind i en anden
sag som startpunkt.

Designvalg:
- En skabelon er bundet til ét artifact_id (literacy-skabelon kan kun
  appliceres på et `ai_faerdigheder_program`-evidens, ikke på et DPIA).
- En skabelon ejes af kommunen (ikke pr-bruger), men vi tracker `created_by`
  for audit. Andre brugere kan se og bruge skabelonerne.
- "Apply" overskriver IKKE eksisterende svar — den merger så bruger-svar
  altid vinder over skabelon-default. Tomme felter får skabelon-værdi.
- Skabelon kan slettes af enhver bruger (intet RBAC for nu — kommunal trust).
"""

from __future__ import annotations

import json
from datetime import datetime, UTC
from typing import Any, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, Index
from sqlalchemy.orm import Session

from src.database.connection import Base


class SkabelonBibliotekEntry(Base):
    """En genbrugbar evidens-skabelon i kommunens bibliotek."""

    __tablename__ = "skabelon_bibliotek"

    id = Column(Integer, primary_key=True, autoincrement=True)
    artifact_id = Column(String(96), nullable=False)  # fx 'ai_faerdigheder_program'
    name = Column(String(160), nullable=False)  # bruger-givet navn
    description = Column(Text, nullable=True)
    content_json = Column(Text, nullable=False, default="{}")

    # Provenance — hvilken sag stammer skabelonen fra (kan være null hvis manuelt oprettet)
    source_case_id = Column(String(64), nullable=True)

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
    created_by = Column(String(64), nullable=True)

    # Stats — bumpes når en bruger bruger skabelonen
    times_used = Column(Integer, nullable=False, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_skabelon_bibliotek_artifact", "artifact_id"),
    )

    def get_content(self) -> dict[str, Any]:
        try:
            return json.loads(self.content_json or "{}")
        except (TypeError, ValueError):
            return {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "artifact_id": self.artifact_id,
            "name": self.name,
            "description": self.description,
            "content": self.get_content(),
            "source_case_id": self.source_case_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "times_used": self.times_used,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }


# ---- Service helpers ------------------------------------------------------


def list_skabeloner(
    session: Session, artifact_id: Optional[str] = None
) -> list[SkabelonBibliotekEntry]:
    """Liste alle skabeloner — optionelt filtreret på artifact_id."""
    query = session.query(SkabelonBibliotekEntry)
    if artifact_id:
        query = query.filter(SkabelonBibliotekEntry.artifact_id == artifact_id)
    return query.order_by(
        SkabelonBibliotekEntry.times_used.desc(),
        SkabelonBibliotekEntry.updated_at.desc(),
    ).all()


def get_skabelon(session: Session, skabelon_id: int) -> Optional[SkabelonBibliotekEntry]:
    return (
        session.query(SkabelonBibliotekEntry)
        .filter(SkabelonBibliotekEntry.id == skabelon_id)
        .one_or_none()
    )


def create_skabelon(
    session: Session,
    *,
    artifact_id: str,
    name: str,
    content: dict[str, Any],
    description: Optional[str] = None,
    source_case_id: Optional[str] = None,
    user: Optional[str] = None,
) -> SkabelonBibliotekEntry:
    if not name or not name.strip():
        raise ValueError("name is required")
    if len(name) > 160:
        raise ValueError("name too long (max 160 chars)")

    entry = SkabelonBibliotekEntry(
        artifact_id=artifact_id,
        name=name.strip(),
        description=description,
        content_json=json.dumps(content, ensure_ascii=False),
        source_case_id=source_case_id,
        created_by=user,
    )
    session.add(entry)
    session.flush()
    return entry


def increment_usage(session: Session, skabelon_id: int) -> None:
    """Bump times_used + last_used_at — kaldes når brugeren applier en skabelon."""
    entry = get_skabelon(session, skabelon_id)
    if entry is None:
        return
    entry.times_used = (entry.times_used or 0) + 1
    entry.last_used_at = datetime.now(UTC)
    session.flush()


def delete_skabelon(session: Session, skabelon_id: int) -> bool:
    entry = get_skabelon(session, skabelon_id)
    if entry is None:
        return False
    session.delete(entry)
    session.flush()
    return True


def merge_with_existing(
    skabelon_content: dict[str, Any],
    existing_content: dict[str, Any],
) -> dict[str, Any]:
    """Merger så eksisterende svar ALTID vinder over skabelon-default.

    Tomme/manglende felter i existing_content udfyldes fra skabelonen.
    """
    merged = dict(skabelon_content)
    for key, val in (existing_content or {}).items():
        # Behold kun eksisterende værdi hvis den er ikke-tom
        if val is None:
            continue
        if isinstance(val, str) and val.strip() == "":
            continue
        if isinstance(val, (list, dict)) and len(val) == 0:
            continue
        merged[key] = val
    return merged
