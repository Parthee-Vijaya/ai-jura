"""Skabelon-bibliotek-router — genbrugbare evidens-skabeloner.

Endpoints:
  - GET    /api/v3/skabelon-bibliotek
  - POST   /api/v3/skabelon-bibliotek
  - POST   /api/v3/skabelon-bibliotek/{id}/apply
  - DELETE /api/v3/skabelon-bibliotek/{id}
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from src.api.error_envelope import AppError
from src.api.rate_limiting import limiter, ADMIN_WRITE

router = APIRouter(prefix="/api/v3/skabelon-bibliotek", tags=["skabeloner"])


class SkabelonCreatePayload(BaseModel):
    artifact_id: str = Field(..., description="Hvilken type evidens skabelonen gælder for")
    name: str = Field(..., min_length=1, max_length=160)
    description: Optional[str] = Field(default=None, max_length=2000)
    content: Dict[str, Any] = Field(..., description="Felt-værdier der bruges som default")
    source_case_id: Optional[str] = Field(default=None, max_length=64)
    user: Optional[str] = Field(default=None, max_length=64)


class SkabelonApplyPayload(BaseModel):
    user: Optional[str] = Field(default=None, max_length=64)


@router.get("")
async def list_skabeloner_endpoint(artifact_id: Optional[str] = None):
    """List skabeloner — optionelt filtreret på artifact_id."""
    from src.database.connection import SessionLocal
    from src.database.skabelon_bibliotek import list_skabeloner

    db = SessionLocal()
    try:
        rows = list_skabeloner(db, artifact_id=artifact_id)
        return {"count": len(rows), "items": [r.to_dict() for r in rows]}
    finally:
        db.close()


@router.post("")
@limiter.limit(ADMIN_WRITE)
async def create_skabelon_endpoint(
    request: Request,
    response: Response,
    body: SkabelonCreatePayload,
):
    """Opret en ny skabelon — typisk fra en eksisterende udfyldt evidens."""
    from src.database.connection import SessionLocal
    from src.database.skabelon_bibliotek import create_skabelon

    db = SessionLocal()
    try:
        try:
            entry = create_skabelon(
                db,
                artifact_id=body.artifact_id,
                name=body.name,
                description=body.description,
                content=body.content,
                source_case_id=body.source_case_id,
                user=body.user,
            )
        except ValueError as exc:
            raise AppError("invalid_skabelon", str(exc), status=400)
        db.commit()
        return entry.to_dict()
    finally:
        db.close()


@router.post("/{skabelon_id}/apply")
@limiter.limit(ADMIN_WRITE)
async def apply_skabelon_endpoint(
    request: Request,
    response: Response,
    skabelon_id: int,
    case_id: str,
    body: SkabelonApplyPayload,
):
    """Indlæs en skabelon på en given sag.

    Merger med eksisterende svar — bruger-svar vinder altid over skabelon-defaults.
    """
    from src.database.connection import SessionLocal
    from src.database.skabelon_bibliotek import (
        get_skabelon, increment_usage, merge_with_existing,
    )
    from src.database.evidence import get_evidence, upsert_evidence
    from src.services.evidence_artifacts import compute_status, get_template

    db = SessionLocal()
    try:
        skabelon = get_skabelon(db, skabelon_id)
        if skabelon is None:
            raise AppError("skabelon_not_found", "Skabelon ikke fundet", status=404)

        existing = get_evidence(db, case_id, skabelon.artifact_id)
        existing_content = existing.get_content() if existing else {}
        merged = merge_with_existing(skabelon.get_content(), existing_content)

        template = get_template(skabelon.artifact_id)
        computed = compute_status(template, merged)

        row = upsert_evidence(
            db,
            case_id=case_id,
            artifact_id=skabelon.artifact_id,
            content=merged,
            computed_status=computed,
            user=body.user,
            notes=f"Anvendte skabelon: {skabelon.name}",
        )
        increment_usage(db, skabelon_id)
        db.commit()
        return {
            **row.to_dict(),
            "computed_status": computed,
            "applied_skabelon_id": skabelon_id,
            "applied_skabelon_name": skabelon.name,
        }
    finally:
        db.close()


@router.delete("/{skabelon_id}")
@limiter.limit(ADMIN_WRITE)
async def delete_skabelon_endpoint(
    request: Request,
    response: Response,
    skabelon_id: int,
):
    from src.database.connection import SessionLocal
    from src.database.skabelon_bibliotek import delete_skabelon

    db = SessionLocal()
    try:
        ok = delete_skabelon(db, skabelon_id)
        if not ok:
            raise AppError("skabelon_not_found", "Skabelon ikke fundet", status=404)
        db.commit()
        return {"deleted": True, "id": skabelon_id}
    finally:
        db.close()
