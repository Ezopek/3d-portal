"""Admin endpoints that are not tied to a single SoT entity.

Holds the audit log readers and the GlitchTip self-test trigger. The
SoT model/file/tag/category write endpoints live in
`app.modules.sot.admin_router`.
"""

import datetime
import json
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import update
from sqlmodel import Session, func, select

from app.core.audit import record_event
from app.core.auth.dependencies import current_admin
from app.core.db.models import AuditLog, RecoveryCode, RefreshToken, User
from app.core.db.models._enums import UserRole
from app.core.db.session import get_engine, get_session
from app.modules.admin.users_schemas import (
    AdminUserListItem,
    AdminUserListResponse,
    UserMutationRequest,
)

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

    # Codex P2 fix-up: every sort branch MUST end with a stable
    # tie-breaker (User.email ASC + User.id ASC) so OFFSET/LIMIT
    # pagination doesn't shuffle rows across pages when the primary
    # sort key has duplicates (e.g. many role=member or many NULL
    # last_active_at rows). Without it, SQLite/Postgres are free to
    # reorder ties → page-skip + page-repeat under user navigation.
    if sort_by is None:
        base_stmt = base_stmt.order_by(User.created_at.desc(), User.email.asc(), User.id.asc())
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
            base_stmt = base_stmt.order_by(
                User.last_active_at.is_(None).asc(),
                direction,
                User.email.asc(),
                User.id.asc(),
            )
        else:
            base_stmt = base_stmt.order_by(direction, User.email.asc(), User.id.asc())

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
            force_2fa_enrollment=row.force_2fa_enrollment,
        )
        for row in rows
    ]
    return AdminUserListResponse(total=total, items=items, page=page, page_size=page_size)


@router.patch(
    "/users/{user_id}",
    status_code=204,
    summary="Update admin-visible user fields (role + is_active)",
    description=(
        "Accepts a partial mutation body `{role?, is_active?}` and applies it to the "
        'target user. Unknown body fields return 422 via `extra="forbid"`. Four '
        "foot-gun guardrails (FR5-ADMIN-2 + NFR5-INT-1): "
        "**cannot_target_self** blocks the operator from demoting or deactivating "
        "their own row (single-admin lockout prevention); "
        "**cannot_target_agent** blocks any mutation on the agent service account "
        "(NFR5-INT-1 nginx-bypass invariant); "
        "**cannot_promote_to_agent** blocks promotion to the system-managed role "
        "(architecture.md:1049 — agent is created by the bootstrap script); "
        "**no_mutation_provided** rejects empty bodies (400). Emits "
        "`user.role_changed` / `user.deactivated` / `user.reactivated` audit events "
        "per FR5-AUDIT-1; no-op mutations are not audited. On deactivation also "
        "burns every active refresh-token family for the target so the access-token "
        "window is bounded to ≤10 minutes."
    ),
)
def update_admin_user(
    user_id: uuid.UUID,
    body: UserMutationRequest,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    admin_id: uuid.UUID = current_admin,
) -> None:
    if not body.model_fields_set:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no_mutation_provided")

    target = session.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")

    if target.id == admin_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot_target_self")
    if target.role == UserRole.agent:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot_target_agent")
    if (
        "role" in body.model_fields_set
        and body.role == UserRole.agent
        and target.role != UserRole.agent
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot_promote_to_agent")

    request_id = request.headers.get("x-request-id")
    before_role = target.role
    before_is_active = target.is_active

    role_changed = (
        "role" in body.model_fields_set and body.role is not None and body.role != target.role
    )
    active_changed = (
        "is_active" in body.model_fields_set
        and body.is_active is not None
        and body.is_active != target.is_active
    )

    if role_changed:
        assert body.role is not None
        target.role = body.role
    if active_changed:
        assert body.is_active is not None
        target.is_active = body.is_active
        if body.is_active is False:
            # Decision I §1622: invalidate the entire refresh-token surface for
            # the deactivated user so the access-token-only window is bounded
            # to ≤10 minutes (JWT TTL). The AC-3 /refresh gate catches anything
            # that still gets through, but this immediate burn closes the
            # in-flight replay window deterministically.
            now = datetime.datetime.now(datetime.UTC)
            rows = session.exec(
                select(RefreshToken)
                .where(RefreshToken.user_id == target.id)
                .where(RefreshToken.revoked_at.is_(None))
            ).all()
            for r in rows:
                r.revoked_at = now
                r.revoke_reason = "force_deactivation"
                session.add(r)

    if role_changed or active_changed:
        session.add(target)
        session.commit()

    if role_changed:
        record_event(
            get_engine(),
            action="user.role_changed",
            entity_type="user",
            entity_id=target.id,
            actor_user_id=admin_id,
            before={"role": before_role.value},
            after={"role": target.role.value},
            request_id=request_id,
        )
    if active_changed:
        assert body.is_active is not None
        record_event(
            get_engine(),
            action="user.deactivated" if body.is_active is False else "user.reactivated",
            entity_type="user",
            entity_id=target.id,
            actor_user_id=admin_id,
            before={"is_active": before_is_active},
            after={"is_active": target.is_active},
            request_id=request_id,
        )


@router.post(
    "/users/{user_id}/force-logout",
    status_code=204,
    summary="Force-logout all sessions of the target user (admin only)",
    description=(
        "Invalidates every active refresh-token family for the target user. "
        "Idempotent: returns 204 with `revoked_count: 0` if the target has no "
        "active families. Guards: **cannot_target_self** (the operator uses "
        "`POST /api/auth/logout-all` for their own sessions — preserves the "
        "audit invariant `actor != target` for `user.force_logout`); "
        "**cannot_target_agent** (NFR5-INT-1). The access-token (JWT) is NOT "
        "proactively invalidated — it expires naturally within 10 minutes."
    ),
)
def force_logout_admin_user(
    user_id: uuid.UUID,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    admin_id: uuid.UUID = current_admin,
) -> None:
    target = session.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
    if target.id == admin_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot_target_self")
    if target.role == UserRole.agent:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot_target_agent")

    now = datetime.datetime.now(datetime.UTC)
    rows = session.exec(
        select(RefreshToken)
        .where(RefreshToken.user_id == target.id)
        .where(RefreshToken.revoked_at.is_(None))
    ).all()
    for r in rows:
        r.revoked_at = now
        r.revoke_reason = "admin_force_logout"
        session.add(r)
    session.commit()

    record_event(
        get_engine(),
        action="user.force_logout",
        entity_type="user",
        entity_id=target.id,
        actor_user_id=admin_id,
        after={"revoked_count": len(rows)},
        request_id=request.headers.get("x-request-id"),
    )


@router.post(
    "/users/{user_id}/force-2fa-enrollment",
    status_code=204,
    summary="Force a user to enroll 2FA on next login (admin only)",
    description=(
        "Sets ``users.force_2fa_enrollment = TRUE`` on the target user so that the "
        "next ``POST /api/auth/login`` lands them on the ``/settings/2fa`` enrollment "
        "screen before any other route works. Implements Decision F §1553 per-user "
        "override path (force-enroll direction). Four foot-gun guardrails: "
        "**cannot_target_self** (the operator self-enrolls via ``/settings/2fa``, not "
        "via this admin endpoint); **cannot_target_agent** (NFR5-INT-1 — the agent "
        "service account never enrolls); **totp_already_enrolled** 409 (the flag is "
        "meaningful only before initial enrollment; the ``totp_enroll_required`` gate "
        "requires ``totp_enabled_at IS NULL``); **already_force_enrolled** 409 "
        "(idempotent no-op is surfaced as an explicit error so the operator knows "
        "their action was redundant). Emits ``auth.totp.enrolled`` audit with "
        "``actor_user_id != entity_id`` AND ``after.force_enrolled = True`` — that "
        "payload shape discriminates this admin-side emission from the Story 7.2 "
        "user-side self-enrollment emission. The flag auto-clears one-shot on the "
        "next successful enrollment-confirm (no operator manual reset)."
    ),
)
def force_2fa_enrollment_admin_user(
    user_id: uuid.UUID,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    admin_id: uuid.UUID = current_admin,
) -> None:
    target = session.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
    if target.id == admin_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot_target_self")
    if target.role == UserRole.agent:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot_target_agent")
    if target.totp_enabled_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "totp_already_enrolled")
    if target.force_2fa_enrollment is True:
        raise HTTPException(status.HTTP_409_CONFLICT, "already_force_enrolled")

    target.force_2fa_enrollment = True
    session.add(target)
    session.commit()

    record_event(
        get_engine(),
        action="auth.totp.enrolled",
        entity_type="user",
        entity_id=target.id,
        actor_user_id=admin_id,
        after={"force_enrolled": True},
        request_id=request.headers.get("x-request-id"),
    )


@router.post(
    "/users/{user_id}/force-disable-2fa",
    status_code=204,
    summary="Force-disable 2FA for a user (admin-side lockout recovery)",
    description=(
        "Clears ``users.totp_enabled_at = NULL`` AND invalidates every active "
        "``recovery_codes`` row for the target user in a single atomic commit, then "
        "emits ``auth.totp.disabled`` audit with ``actor_user_id != entity_id`` AND "
        "``after.admin_override = True``. The Fernet-encrypted ``users.totp_secret`` "
        "ciphertext is RETAINED per epics §1799 + Story 7.5 retention policy — the "
        "user can later re-enroll with the same authenticator app without secret "
        "rotation. Unlike the user-side ``POST /api/auth/2fa/disable`` endpoint, "
        "this admin endpoint REQUIRES ONLY the ``current_admin`` cookie (no "
        "password+TOTP body): the lockout-recovery scenario presumes the target user "
        "CANNOT supply either, since that is the entire point of the endpoint. "
        "Three foot-gun guardrails: **cannot_target_self** (the operator uses the "
        "user-side disable flow with re-auth for their own 2FA — bypass would be a "
        "self-lockout vector); **cannot_target_agent** (NFR5-INT-1); "
        "**totp_not_enrolled** 409 (force-disable on a non-enrolled user is "
        "meaningless). This is Step 1 of the lost-2FA-AND-lost-recovery-codes "
        "recovery flow (epics §1817); Step 2 is the Story 8.5 password-reset "
        "endpoint."
    ),
)
def force_disable_2fa_admin_user(
    user_id: uuid.UUID,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    admin_id: uuid.UUID = current_admin,
) -> None:
    target = session.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
    if target.id == admin_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot_target_self")
    if target.role == UserRole.agent:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot_target_agent")
    if target.totp_enabled_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "totp_not_enrolled")

    now = datetime.datetime.now(datetime.UTC)
    # Atomic single-commit: invalidate active recovery codes + clear
    # totp_enabled_at. ``target.totp_secret`` is NOT mutated — the Fernet
    # ciphertext is retained per epics §1799 / Story 7.5 retention policy.
    result = session.execute(
        update(RecoveryCode)
        .where(RecoveryCode.user_id == target.id)
        .where(RecoveryCode.invalidated_at.is_(None))
        .values(invalidated_at=now)
    )
    invalidated_count = result.rowcount
    target.totp_enabled_at = None
    session.add(target)
    session.commit()

    record_event(
        get_engine(),
        action="auth.totp.disabled",
        entity_type="user",
        entity_id=target.id,
        actor_user_id=admin_id,
        after={"admin_override": True, "invalidated_count": invalidated_count},
        request_id=request.headers.get("x-request-id"),
    )
