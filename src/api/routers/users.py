"""Bruger-router — første step mod multi-bruger RBAC.

Endpoints:
  - GET    /api/v3/users               — list aktive brugere
  - GET    /api/v3/users/search?q=…    — autocomplete for @-mentions
  - POST   /api/v3/users               — upsert (admin: tilføj eller opdatér)
  - DELETE /api/v3/users/{email}       — deaktivér (soft delete)

Bemærk: ingen autentificering i MVP — det kommer i RBAC-modulet senere.
For nu er det op til admin at seed'e via /api/v3/users.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from src.api.error_envelope import AppError
from src.api.rate_limiting import limiter, ADMIN_WRITE, READ_GENEROUS
from src.database.users import (
    DEFAULT_ROLE,
    ROLES,
    deactivate_user,
    find_user_by_email,
    is_valid_email,
    list_active_users,
    search_users,
    upsert_user,
)


logger = logging.getLogger("bifrost.users")
router = APIRouter(tags=["users"])


class UserUpsertPayload(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=120)
    role: str = Field(default=DEFAULT_ROLE, max_length=32)
    active: bool = Field(default=True)


@router.get("/api/v3/users")
@limiter.limit(READ_GENEROUS)
async def list_users(request: Request, response: Response, limit: int = 100):
    from src.database.connection import SessionLocal

    db = SessionLocal()
    try:
        users = list_active_users(db, limit=min(limit, 500))
        return {"users": [u.to_dict() for u in users], "count": len(users)}
    finally:
        db.close()


@router.get("/api/v3/users/search")
@limiter.limit(READ_GENEROUS)
async def search_users_endpoint(
    request: Request, response: Response, q: str = "", limit: int = 10
):
    """Autocomplete for @-mentions: matchér email-prefix ELLER display_name substring."""
    from src.database.connection import SessionLocal

    if not q or len(q.strip()) < 1:
        return {"users": [], "query": q}

    db = SessionLocal()
    try:
        users = search_users(db, q, limit=min(limit, 25))
        return {
            "users": [
                {
                    "email": u.email,
                    "display_name": u.display_name,
                    "role": u.role,
                }
                for u in users
            ],
            "query": q,
        }
    finally:
        db.close()


@router.post("/api/v3/users")
@limiter.limit(ADMIN_WRITE)
async def upsert_user_endpoint(
    request: Request, response: Response, body: UserUpsertPayload
):
    from src.database.connection import SessionLocal

    if not is_valid_email(body.email):
        raise AppError("invalid_email", f"Ugyldig email: {body.email!r}", status=400)
    if body.role not in ROLES:
        raise AppError(
            "invalid_role",
            f"Rolle {body.role!r} ikke tilladt — vælg fra {ROLES}",
            status=400,
        )

    db = SessionLocal()
    try:
        try:
            user = upsert_user(
                db,
                email=body.email,
                display_name=body.display_name,
                role=body.role,
                active=body.active,
            )
        except ValueError as exc:
            raise AppError("invalid_input", str(exc), status=400)
        return user.to_dict()
    finally:
        db.close()


@router.delete("/api/v3/users/{email}")
@limiter.limit(ADMIN_WRITE)
async def deactivate_user_endpoint(
    request: Request, response: Response, email: str
):
    from src.database.connection import SessionLocal

    db = SessionLocal()
    try:
        ok = deactivate_user(db, email)
        if not ok:
            raise AppError("user_not_found", f"Bruger {email} findes ikke", status=404)
        return {"deactivated": email}
    finally:
        db.close()
