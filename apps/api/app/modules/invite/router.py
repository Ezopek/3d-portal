"""Public invite-token register endpoint for Initiative 5 (Story 6.4).

Mirrors the Init 0 auth-router shape in
``apps/api/app/modules/auth/router.py`` for cookie + audit emission, and
the Init 5 invite/admin_router.py for the ``_service(request)`` factory.

Audit actions emitted:
- ``auth.invite.used``      on successful consumption (entity_type=invite_token)
- ``auth.register.success`` on successful registration (entity_type=user)
- ``auth.register.fail``    on any failure path (entity_type=user)

Failure-path reasons (FR5-AUDIT-1 binding set; no synonyms):
- ``token_invalid``  — Redis miss + DB row absent OR expired
- ``token_consumed`` — Redis miss + DB row revoked OR used (incl. race-lost)
- ``weak_password``  — length<12 OR zxcvbn score<3
- ``email_taken``    — user table already has the requested email
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

import zxcvbn
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session, select

from app.core.audit import record_event
from app.core.auth.cookies import set_session_cookies
from app.core.auth.jwt import encode_token
from app.core.auth.password import hash_password
from app.core.auth.refresh import new_refresh_row
from app.core.config import Settings, get_settings
from app.core.db.models import User
from app.core.db.session import get_engine, get_session
from app.modules.auth.models import LoginResponse, MeResponse
from app.modules.invite import (
    InviteConsumed,
    InviteService,
    InviteToken,
    hash_token,
)
from app.modules.invite.schemas import RegisterRequest

_LOG = logging.getLogger("app.auth.register")
_MIN_PASSWORD_LEN = 12
_MIN_ZXCVBN_SCORE = 3

_LEN_MSG = "password must be at least 12 characters"
_SCORE_MSG = "password is too predictable; choose a stronger one"

router = APIRouter(prefix="/api/auth", tags=["auth", "invite"])


def _service(request: Request) -> InviteService:
    return InviteService(redis=request.app.state.redis.get(), engine=get_engine())


def _client_ip(request: Request) -> str:
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else None
    )
    return ip or "unknown"


def _diagnose_inactive_token(session: Session, token: str) -> tuple[int, str]:
    """Return (http_status, reason) for a Redis-miss token.

    Binding precedence (Dev Notes § "Token-state diagnosis algorithm"):
      1. DB row absent              → 404, token_invalid
      2. revoked_at IS NOT NULL     → 410, token_consumed
      3. used_at IS NOT NULL        → 410, token_consumed
      4. expired-naturally          → 404, token_invalid
    """
    row = session.exec(
        select(InviteToken).where(InviteToken.token_hash == hash_token(token))
    ).first()
    if row is None:
        return (404, "token_invalid")
    if row.revoked_at is not None:
        return (410, "token_consumed")
    if row.used_at is not None:
        return (410, "token_consumed")
    return (404, "token_invalid")


def _emit_fail(
    *,
    engine,
    reason: str,
    email: str,
    actor_user_id: uuid.UUID | None,
    entity_id: uuid.UUID | None,
    request_id: str | None,
) -> None:
    record_event(
        engine,
        action="auth.register.fail",
        entity_type="user",
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        after={"reason": reason, "email": email},
        request_id=request_id,
    )


@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Public invite-token registration",
    description=(
        "Consume an invite token + create the bound user account. "
        "Issues the standard portal_access (10min) + portal_refresh (30d) "
        "cookie pair; the client is logged in on response."
    ),
)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    engine = get_engine()
    request_id = request.headers.get("x-request-id")
    ip = _client_ip(request)
    service = _service(request)

    # Step 1: token validation (Redis primary, DB fallback for diagnosis).
    active = await service.validate_active(payload.token)
    if active is None:
        http_status, reason = _diagnose_inactive_token(session, payload.token)
        _emit_fail(
            engine=engine,
            reason=reason,
            email=payload.email,
            actor_user_id=None,
            entity_id=None,
            request_id=request_id,
        )
        raise HTTPException(http_status, reason)

    # Step 2: password validation (length first, then zxcvbn).
    if len(payload.password) < _MIN_PASSWORD_LEN:
        _emit_fail(
            engine=engine,
            reason="weak_password",
            email=payload.email,
            actor_user_id=None,
            entity_id=None,
            request_id=request_id,
        )
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, _LEN_MSG)
    score = zxcvbn.zxcvbn(payload.password)["score"]
    if score < _MIN_ZXCVBN_SCORE:
        _emit_fail(
            engine=engine,
            reason="weak_password",
            email=payload.email,
            actor_user_id=None,
            entity_id=None,
            request_id=request_id,
        )
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, _SCORE_MSG)

    # Step 3: email-uniqueness check.
    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing is not None:
        _emit_fail(
            engine=engine,
            reason="email_taken",
            email=payload.email,
            actor_user_id=None,
            entity_id=existing.id,
            request_id=request_id,
        )
        raise HTTPException(status.HTTP_409_CONFLICT, "email_taken")

    # Step 4: create user.
    display_name = payload.email.split("@", 1)[0]
    user = User(
        email=payload.email,
        display_name=display_name,
        role=active.role,
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # Step 5: consume invite (atomic predicate; raises InviteConsumed on race-lost).
    try:
        await service.consume(payload.token, used_by_user_id=user.id, used_from_ip=ip)
    except InviteConsumed:
        # Race: between validate_active() and consume(), the token was
        # consumed/revoked by another process. Compensation: delete the
        # orphan user row we just created and surface 410 to the caller.
        session.delete(user)
        session.commit()
        _emit_fail(
            engine=engine,
            reason="token_consumed",
            email=payload.email,
            actor_user_id=None,
            entity_id=None,
            request_id=request_id,
        )
        raise HTTPException(status.HTTP_410_GONE, "token_consumed") from None

    record_event(
        engine,
        action="auth.invite.used",
        entity_type="invite_token",
        entity_id=active.invite_id,
        actor_user_id=user.id,
        after={"used_from_ip": ip},
        request_id=request_id,
    )

    # Step 6: issue cookie pair + audit success.
    secret, refresh_row = new_refresh_row(
        user_id=user.id,
        family_id=None,
        family_issued_at=None,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    session.add(refresh_row)
    session.commit()

    access = encode_token(
        subject=str(user.id),
        role=user.role.value,
        secret=settings.jwt_secret,
        ttl_minutes=settings.jwt_ttl_minutes,
    )
    set_session_cookies(response, access=access, refresh=secret, settings=settings)

    record_event(
        engine,
        action="auth.register.success",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        after={
            "email": user.email,
            "role": user.role.value,
            "invite_id": str(active.invite_id),
        },
        request_id=request_id,
    )
    return LoginResponse(
        user=MeResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.role,
        )
    )
