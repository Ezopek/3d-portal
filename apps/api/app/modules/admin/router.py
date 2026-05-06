"""Admin endpoints that are not tied to a single SoT entity.

Holds the audit log readers and the GlitchTip self-test trigger. The
SoT model/file/tag/category write endpoints live in
`app.modules.sot.admin_router`.
"""

import datetime
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, func, select

from app.core.auth.dependencies import current_admin
from app.core.db.models import AuditLog
from app.core.db.session import get_session

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/sentry-test", status_code=204)
def sentry_test(_user_id: uuid.UUID = current_admin) -> None:
    """Deliberately raise to verify GlitchTip plumbing. Admin-only."""
    raise RuntimeError("sentry-test: deliberate test event")


@router.get("/audit")
def list_audit(
    session: Annotated[Session, Depends(get_session)],
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _user_id: uuid.UUID = current_admin,
) -> dict:
    total = session.exec(select(func.count()).select_from(AuditLog)).one()
    rows = session.exec(
        select(AuditLog).order_by(AuditLog.at.desc()).offset(offset).limit(limit),
    ).all()
    return {
        "total": total,
        "events": [
            {
                "id": str(e.id),
                "at": e.at.isoformat(),
                "actor_user_id": str(e.actor_user_id) if e.actor_user_id else None,
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": str(e.entity_id) if e.entity_id else None,
                "before": json.loads(e.before_json) if e.before_json else None,
                "after": json.loads(e.after_json) if e.after_json else None,
                "request_id": e.request_id,
            }
            for e in rows
        ],
    }


class AuditLogEntry(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    before_json: dict | None
    after_json: dict | None
    at: datetime.datetime

    @classmethod
    def from_row(cls, row: AuditLog) -> "AuditLogEntry":
        return cls(
            id=row.id,
            actor_user_id=row.actor_user_id,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            before_json=json.loads(row.before_json) if row.before_json else None,
            after_json=json.loads(row.after_json) if row.after_json else None,
            at=row.at,
        )


class AuditLogResponse(BaseModel):
    items: list[AuditLogEntry]


@router.get("/audit-log", response_model=AuditLogResponse)
def admin_get_audit_log(
    session: Annotated[Session, Depends(get_session)],
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    _user_id: uuid.UUID = current_admin,
) -> AuditLogResponse:
    stmt = select(AuditLog)
    if entity_type is not None:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    stmt = stmt.order_by(AuditLog.at.desc()).limit(limit)
    rows = session.exec(stmt).all()
    return AuditLogResponse(items=[AuditLogEntry.from_row(r) for r in rows])
