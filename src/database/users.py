"""Bruger-tabel + helper-funktioner — første skridt mod multi-bruger RBAC.

I MVP'en bruges User-tabellen til:
  - @-mentions i evidens-kommentarer (autocomplete + email-notifikation)
  - Vise display_name i stedet for fri-tekst "author"
  - Senere udvidelse: roller (jurist / sagsbehandler / leder) + RBAC

Design-valg:
- email er primary identifier (case-insensitive lookup)
- display_name kan ændres uden at miste historik
- role er soft enum (string) så vi kan tilføje uden migration
- active=False bevarer bruger men skjuler i autocomplete
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Index, String, or_, func
from sqlalchemy.orm import Session

from src.database.connection import Base


ROLES = ("sagsbehandler", "jurist", "leder", "admin")
DEFAULT_ROLE = "sagsbehandler"

# Robust pr. RFC-5321 minimum — vi vil hellere være for liberale end blokerende
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")

# @-mention pattern: @-tegn efterfulgt af email-lignende streng. Tillader
# at @-mention står midt i en sætning. Indekserer kun det matchede e-mail-substring.
_MENTION_RE = re.compile(r"@([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), nullable=False, unique=True)
    display_name = Column(String(120), nullable=False)
    role = Column(String(32), nullable=False, default=DEFAULT_ROLE)
    active = Column(Boolean, nullable=False, default=True)

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

    __table_args__ = (
        Index("ix_users_email_lower", func.lower(email)),
        Index("ix_users_active_email", "active", "email"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name,
            "role": self.role,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---- Validation ----------------------------------------------------------


def is_valid_email(value: Optional[str]) -> bool:
    if not value or not isinstance(value, str):
        return False
    return bool(_EMAIL_RE.match(value.strip()))


def normalize_email(value: str) -> str:
    return value.strip().lower()


# ---- CRUD ---------------------------------------------------------------


def upsert_user(
    db: Session,
    *,
    email: str,
    display_name: str,
    role: str = DEFAULT_ROLE,
    active: bool = True,
) -> User:
    """Opret bruger hvis email ikke findes, opdatér ellers display_name/role.

    Email lookup er case-insensitive — vi gemmer normaliseret lowercase.
    """
    if not is_valid_email(email):
        raise ValueError(f"Ugyldig email: {email!r}")
    if not display_name or not display_name.strip():
        raise ValueError("display_name er påkrævet")
    if role not in ROLES:
        raise ValueError(f"Ugyldig rolle {role!r}, vælg fra {ROLES}")

    norm = normalize_email(email)
    user = db.query(User).filter(func.lower(User.email) == norm).one_or_none()
    if user is None:
        user = User(
            email=norm,
            display_name=display_name.strip(),
            role=role,
            active=active,
        )
        db.add(user)
    else:
        user.display_name = display_name.strip()
        user.role = role
        user.active = active
    db.commit()
    db.refresh(user)
    return user


def find_user_by_email(db: Session, email: str) -> Optional[User]:
    if not email:
        return None
    norm = normalize_email(email)
    return db.query(User).filter(func.lower(User.email) == norm).one_or_none()


def search_users(db: Session, query: str, *, limit: int = 10) -> list[User]:
    """Søg på email-prefix ELLER display_name-substring (case-insensitive).

    Bruges af @-mention autocomplete. Returnerer kun aktive brugere.
    """
    q = (query or "").strip().lower()
    if not q:
        return []
    pattern = f"%{q}%"
    return (
        db.query(User)
        .filter(User.active.is_(True))
        .filter(
            or_(
                func.lower(User.email).like(f"{q}%"),
                func.lower(User.display_name).like(pattern),
            )
        )
        .order_by(User.display_name.asc())
        .limit(limit)
        .all()
    )


def list_active_users(db: Session, *, limit: int = 100) -> list[User]:
    return (
        db.query(User)
        .filter(User.active.is_(True))
        .order_by(User.display_name.asc())
        .limit(limit)
        .all()
    )


def deactivate_user(db: Session, email: str) -> bool:
    user = find_user_by_email(db, email)
    if user is None:
        return False
    user.active = False
    db.commit()
    return True


# ---- @-mention parsing --------------------------------------------------


def extract_mentions(text: Optional[str]) -> list[str]:
    """Returnér unikke (lower-case) email-adresser nævnt med @ i teksten.

    Eksempel:
        "Hej @pavi@kalundborg.dk — og @anna@kalundborg.dk, kan I tjekke?"
        → ["pavi@kalundborg.dk", "anna@kalundborg.dk"]
    """
    if not text:
        return []
    matches = _MENTION_RE.findall(text)
    seen = set()
    out: list[str] = []
    for m in matches:
        norm = m.lower()
        if norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out


def resolve_mentions(db: Session, emails: list[str]) -> list[User]:
    """Returnér User-objekter for liste af email-adresser. Skipper ukendte."""
    if not emails:
        return []
    norm = [e.lower() for e in emails]
    return (
        db.query(User)
        .filter(func.lower(User.email).in_(norm))
        .filter(User.active.is_(True))
        .all()
    )
