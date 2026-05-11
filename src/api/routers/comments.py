"""Evidens-comments router — per-felt diskussion på sager.

Endpoints:
  - GET    /api/v3/cases/{case_id}/comments
  - GET    /api/v3/cases/{case_id}/comments/counts
  - POST   /api/v3/cases/{case_id}/evidence/{artifact_id}/comments
  - POST   /api/v3/comments/{comment_id}/resolve
  - DELETE /api/v3/comments/{comment_id}

Bemærk to prefixes — case-scope og comment-scope. Implementeret som
to routers samlet under én Router for at have begge stier i ét modul.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from src.api.error_envelope import AppError
from src.api.rate_limiting import limiter, ADMIN_WRITE

logger = logging.getLogger("bifrost.comments")

router = APIRouter(tags=["comments"])


class CommentCreatePayload(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)
    section_key: Optional[str] = Field(default=None, max_length=96)
    author: Optional[str] = Field(default=None, max_length=64)


@router.get("/api/v3/cases/{case_id}/comments")
async def list_for_case(
    case_id: str,
    artifact_id: Optional[str] = None,
    section_key: Optional[str] = None,
    include_resolved: bool = True,
):
    """List kommentarer for en sag — optionelt filtreret på artifact + sektion."""
    from src.database.connection import SessionLocal
    from src.database.evidence_comments import list_comments

    db = SessionLocal()
    try:
        rows = list_comments(
            db,
            case_id=case_id,
            artifact_id=artifact_id,
            section_key=section_key,
            include_resolved=include_resolved,
        )
        return {
            "case_id": case_id,
            "count": len(rows),
            "items": [r.to_dict() for r in rows],
        }
    finally:
        db.close()


@router.get("/api/v3/cases/{case_id}/comments/counts")
async def counts_for_case(case_id: str):
    """Aggregat over kommentar-antal per artefakt og sektion.

    Format: {artifact_id: {section_key|"_doc": {open: N, resolved: N}}}
    """
    from src.database.connection import SessionLocal
    from src.database.evidence_comments import comment_counts_for_case

    db = SessionLocal()
    try:
        counts = comment_counts_for_case(db, case_id)
        return {"case_id": case_id, "counts": counts}
    finally:
        db.close()


@router.post("/api/v3/cases/{case_id}/evidence/{artifact_id}/comments")
@limiter.limit(ADMIN_WRITE)
async def create_comment_endpoint(
    request: Request,
    response: Response,
    case_id: str,
    artifact_id: str,
    body: CommentCreatePayload,
):
    """Opret en kommentar på et evidens-felt (eller hele dokumentet hvis section_key=null).

    Emitterer også en notifikation så andre brugere ser tråden i deres bell.
    """
    from src.database.connection import SessionLocal
    from src.database.evidence_comments import create_comment
    from src.database import notifications as notif_svc

    db = SessionLocal()
    try:
        try:
            comment = create_comment(
                db,
                case_id=case_id,
                artifact_id=artifact_id,
                section_key=body.section_key,
                body=body.body,
                author=body.author,
            )
        except ValueError as exc:
            raise AppError("invalid_comment", str(exc), status=400)

        # Emit notifikation — fejler stille hvis notifikations-systemet er nede
        try:
            preview = (body.body[:80] + "…") if len(body.body) > 80 else body.body
            section_label = body.section_key or "hele dokumentet"
            notif_svc.emit(
                db,
                kind="evidens_comment",
                title=f"Ny kommentar på {artifact_id.replace('_', ' ')}",
                message=f"{body.author or 'Bruger'} skrev på {section_label}: '{preview}'",
                case_id=case_id,
                link_url=f"/sag/{case_id}?tab=evidens",
                severity="info",
                actor=body.author,
            )
        except Exception as exc:
            logger.warning(f"comment notification emit failed: {exc}")

        db.commit()
        return comment.to_dict()
    finally:
        db.close()


@router.post("/api/v3/comments/{comment_id}/resolve")
@limiter.limit(ADMIN_WRITE)
async def resolve_comment_endpoint(
    request: Request,
    response: Response,
    comment_id: int,
    user: Optional[str] = None,
):
    from src.database.connection import SessionLocal
    from src.database.evidence_comments import resolve_comment

    db = SessionLocal()
    try:
        comment = resolve_comment(db, comment_id, user=user)
        if comment is None:
            raise AppError("comment_not_found", "Kommentar ikke fundet", status=404)
        db.commit()
        return comment.to_dict()
    finally:
        db.close()


@router.delete("/api/v3/comments/{comment_id}")
@limiter.limit(ADMIN_WRITE)
async def delete_comment_endpoint(
    request: Request,
    response: Response,
    comment_id: int,
):
    from src.database.connection import SessionLocal
    from src.database.evidence_comments import delete_comment

    db = SessionLocal()
    try:
        ok = delete_comment(db, comment_id)
        if not ok:
            raise AppError("comment_not_found", "Kommentar ikke fundet", status=404)
        db.commit()
        return {"deleted": True, "id": comment_id}
    finally:
        db.close()
