"""Notifications-router — in-app bell-system.

Endpoints:
  - GET  /api/v3/notifications              → list (filter via unread_only)
  - POST /api/v3/notifications/{id}/read    → mark én som læst
  - POST /api/v3/notifications/read-all     → mark alle som læst
"""

import asyncio
from typing import Optional

from fastapi import APIRouter, Request, Response

from src.api.error_envelope import AppError
from src.api.rate_limiting import limiter, ADMIN_WRITE

router = APIRouter(prefix="/api/v3/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(unread_only: bool = False, limit: int = 30):
    """List notifikationer — bruges af bell-panel."""
    from src.database.connection import SessionLocal
    from src.database import notifications as notif_svc

    db = SessionLocal()
    try:
        rows = await asyncio.to_thread(
            notif_svc.list_recent, db, limit=limit, unread_only=unread_only,
        )
        unread = await asyncio.to_thread(notif_svc.count_unread, db)
        return {
            "count": len(rows),
            "unread": unread,
            "items": [r.to_dict() for r in rows],
        }
    finally:
        db.close()


@router.post("/{notification_id}/read")
@limiter.limit(ADMIN_WRITE)
async def mark_read(
    request: Request,
    response: Response,
    notification_id: str,
):
    from src.database.connection import SessionLocal
    from src.database import notifications as notif_svc

    db = SessionLocal()
    try:
        n = await asyncio.to_thread(notif_svc.mark_read, db, notification_id)
        if n is None:
            raise AppError("notification_not_found", "Notifikation findes ikke", status=404)
        db.commit()
        return n.to_dict()
    finally:
        db.close()


@router.post("/read-all")
@limiter.limit(ADMIN_WRITE)
async def mark_all_read(
    request: Request,
    response: Response,
):
    from src.database.connection import SessionLocal
    from src.database import notifications as notif_svc

    db = SessionLocal()
    try:
        count = await asyncio.to_thread(notif_svc.mark_all_read, db)
        db.commit()
        return {"marked_read": count}
    finally:
        db.close()
