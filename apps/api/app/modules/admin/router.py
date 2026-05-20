"""Admin endpoints that are not tied to a single SoT entity.

Holds the audit log readers and the GlitchTip self-test trigger. The
SoT model/file/tag/category write endpoints live in
`app.modules.sot.admin_router`.
"""

import datetime
import json
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, func, select

from app.core.auth.dependencies import current_admin
from app.core.db.models import AuditLog, User
from app.core.db.session import get_session
from app.modules.admin.users_schemas import AdminUserListItem, AdminUserListResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post(
    "/sentry-test",
    summary="Deliberately raise to verify GlitchTip plumbing (admin only)",
    description=(
        "Raises a test exception to prove the GlitchTip → portal symbolication pipeline "
        "is working end-to-end. Admin-only. The decorator declares 204, but in practice "
        "the unhandled `RuntimeError` propagates through FastAPI's default exception "
        "handler and the client sees **HTTP 500** while Sentry captures the event. "
        "**Do NOT 'fix' the raise — it is the contract.** Used by "
        "`infra/scripts/verify-symbolication.sh` and the operator's manual verify ritual."
    ),
    status_code=204,
    responses={
        500: {"description": "Deliberate raise propagates to FastAPI's default 500 handler"}
    },
)
def sentry_test(_user_id: uuid.UUID = current_admin) -> None:
    """Deliberately raise to verify GlitchTip plumbing. Admin-only."""
    raise RuntimeError("sentry-test: deliberate test event")


@router.get(
    "/audit",
    summary="List raw audit-log events (admin only)",
    description=(
        "Returns paged audit events with `before` / `after` JSON snapshots inline. "
        "`limit` 1-500 (default 50), `offset` ≥0. Admin-only — agent role gets 403. "
        "Use `/audit-log` for the typed/structured response shape; this endpoint returns "
        "an untyped dict for backwards compatibility with operator scripts."
    ),
)
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


@router.get(
    "/audit-log",
    summary="List audit-log events as typed AuditLogResponse (admin only)",
    description=(
        "Same data as `/audit` but with a typed Pydantic response shape (`AuditLogResponse`). "
        "Filters: `entity_type` (e.g. `model`, `tag`), `entity_id`. `limit` 1-200 "
        "(default 50). Admin-only — agent role gets 403."
    ),
    response_model=AuditLogResponse,
)
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


@router.get(
    "/users",
    response_model=AdminUserListResponse,
    summary="List portal users with search, sort, and pagination (admin only)",
    description=(
        "Returns the 8 panel-visible columns from epics §1770 verbatim "
        "(id, email, display_name, role, created_at, last_active_at, "
        "totp_enabled, is_active). `password_hash` and `totp_secret` are "
        "filtered at the Pydantic projection layer and NEVER appear in the "
        "response (Decision I hygiene rule). Ordering defaults to "
        "`created_at DESC`; `sort_by=last_active_at` puts NULLs LAST "
        "regardless of `sort_order`. Pagination is 1-indexed; `page_size` "
        "is capped at 200 to match the Init 5 admin-list contract."
    ),
)
def list_admin_users(
    session: Annotated[Session, Depends(get_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    search: str | None = Query(default=None, max_length=255),
    sort_by: Literal["email", "role", "created_at", "last_active_at"] | None = Query(default=None),
    sort_order: Literal["asc", "desc"] | None = Query(default=None),
    _user_id: uuid.UUID = current_admin,
) -> AdminUserListResponse:
    base_stmt = select(User)
    count_stmt = select(func.count()).select_from(User)
    if search:
        pattern = f"%{search}%"
        base_stmt = base_stmt.where(User.email.ilike(pattern))
        count_stmt = count_stmt.where(User.email.ilike(pattern))

    if sort_by is None:
        base_stmt = base_stmt.order_by(User.created_at.desc())
    else:
        column = {
            "email": User.email,
            "role": User.role,
            "created_at": User.created_at,
            "last_active_at": User.last_active_at,
        }[sort_by]
        order_default_desc = sort_by in {"created_at", "last_active_at"}
        order = sort_order or ("desc" if order_default_desc else "asc")
        direction = column.desc() if order == "desc" else column.asc()
        if sort_by == "last_active_at":
            base_stmt = base_stmt.order_by(User.last_active_at.is_(None).asc(), direction)
        else:
            base_stmt = base_stmt.order_by(direction)

    total = session.exec(count_stmt).one()
    offset = (page - 1) * page_size
    rows = session.exec(base_stmt.offset(offset).limit(page_size)).all()

    items = [
        AdminUserListItem(
            id=row.id,
            email=row.email,
            display_name=row.display_name,
            role=row.role,
            created_at=row.created_at,
            last_active_at=row.last_active_at,
            totp_enabled=row.totp_enabled_at is not None,
            is_active=row.is_active,
        )
        for row in rows
    ]
    return AdminUserListResponse(total=total, items=items, page=page, page_size=page_size)
