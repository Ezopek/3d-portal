"""Auth router — cookie-based sessions with refresh-token rotation."""
import datetime
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.audit import record_event
from app.core.auth.cookies import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    clear_session_cookies,
    set_session_cookies,
)
from app.core.auth.dependencies import current_user
from app.core.auth.jwt import encode_token
from app.core.auth.password import verify_password
from app.core.auth.refresh import (
    RotationOutcome,
    find_by_secret,
    new_refresh_row,
    rotate_refresh,
)
from app.core.config import Settings, get_settings
from app.core.db.models import RefreshToken, User
from app.core.db.session import get_engine, get_session
from app.modules.auth.models import (
    LoginRequest,
    LoginResponse,
    MeResponse,
)

_LOG = logging.getLogger("app.auth.refresh")

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else None)
    )
    ua = request.headers.get("user-agent")
    return (ip or None), (ua or None)


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    user = session.exec(select(User).where(User.email == payload.email)).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        record_event(
            get_engine(),
            action="auth.login.fail",
            entity_type="user",
            entity_id=None,
            actor_user_id=None,
            after={"email": payload.email},
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_credentials")

    ip, ua = _client_meta(request)
    secret, row = new_refresh_row(
        user_id=user.id, family_id=None, family_issued_at=None,
        ip=ip, user_agent=ua,
    )
    session.add(row)
    session.commit()

    access = encode_token(
        subject=str(user.id),
        role=user.role.value,
        secret=settings.jwt_secret,
        ttl_minutes=settings.jwt_ttl_minutes,
    )
    set_session_cookies(response, access=access, refresh=secret, settings=settings)
    record_event(
        get_engine(),
        action="auth.login.success",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        after={"email": user.email},
    )
    return LoginResponse(
        user=MeResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.role.value,
        )
    )


@router.get("/me", response_model=MeResponse)
def me(
    session: Annotated[Session, Depends(get_session)],
    user_id: uuid.UUID = current_user,
) -> MeResponse:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
    return MeResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role.value,
    )


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    """Idempotent. Tolerates missing cookies/auth — always succeed and clear."""
    refresh_secret = request.cookies.get(REFRESH_COOKIE)
    if refresh_secret:
        row = find_by_secret(session, refresh_secret)
        if row is not None and row.revoked_at is None:
            now = datetime.datetime.now(datetime.UTC)
            family_rows = session.exec(
                select(RefreshToken).where(
                    RefreshToken.family_id == row.family_id,
                    RefreshToken.revoked_at.is_(None),
                )
            ).all()
            for r in family_rows:
                r.revoked_at = now
                r.revoke_reason = "logout"
                session.add(r)
            session.commit()
            record_event(
                get_engine(),
                action="auth.logout",
                entity_type="user",
                entity_id=row.user_id,
                actor_user_id=row.user_id,
                after={"family_id": str(row.family_id)},
            )
    clear_session_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/refresh", response_model=LoginResponse)
def refresh(
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    secret = request.cookies.get(REFRESH_COOKIE)
    if not secret:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "no_refresh")

    ip, ua = _client_meta(request)

    # Concurrent refresh on the same family can race the partial UNIQUE.
    # The IntegrityError retry serializes them — the second attempt re-reads
    # the (now revoked) presented row and falls into the grace path.
    result = None
    for _attempt in range(3):
        presented = find_by_secret(session, secret)
        if presented is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_refresh")
        try:
            result = rotate_refresh(session, presented=presented, ip=ip, user_agent=ua)
            break
        except IntegrityError:
            session.rollback()
            continue
    if result is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "force_relogin")

    if result.outcome == RotationOutcome.expired:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "refresh_expired")
    if result.outcome == RotationOutcome.reuse_detected:
        session.commit()
        record_event(
            get_engine(),
            action="auth.refresh.reuse_detected",
            entity_type="user",
            entity_id=presented.user_id,
            actor_user_id=presented.user_id,
            after={"family_id": str(result.family_id), "ip": ip, "user_agent": ua},
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "force_relogin")
    if result.outcome == RotationOutcome.race_lost:
        # Benign race — no burn, just deny this attempt.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "force_relogin")
    if result.outcome == RotationOutcome.grace_ua_mismatch:
        _LOG.warning(
            "auth.refresh.grace_ua_mismatch",
            extra={
                "event.action": "auth.refresh.grace_ua_mismatch",
                "labels.family_id": str(result.family_id),
                "labels.user_agent": ua or "",
                "labels.ip": ip or "",
            },
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "force_relogin")

    # rotated OR grace_returned → issue cookies.
    # For grace_returned: rotate the active descendant to issue a fresh, usable secret.
    # (The active row's raw secret is not stored — only its hash — so we can't replay it.
    # Rotating it is safe: one active row in the family remains after each operation.)
    if result.outcome == RotationOutcome.grace_returned:
        assert result.active_row is not None
        grace_result = None
        for _attempt in range(3):
            try:
                grace_result = rotate_refresh(
                    session, presented=result.active_row, ip=ip, user_agent=ua
                )
                break
            except IntegrityError:
                session.rollback()
                continue
        if grace_result is None or grace_result.outcome != RotationOutcome.rotated:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "force_relogin")
        target = grace_result.new_row
        refresh_secret_to_set = grace_result.new_secret
    else:
        target = result.new_row
        refresh_secret_to_set = result.new_secret

    assert target is not None
    assert refresh_secret_to_set is not None
    user = session.get(User, target.user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "force_relogin")
    target.last_used_at = datetime.datetime.now(datetime.UTC)
    session.add(target)
    session.commit()

    access = encode_token(
        subject=str(user.id),
        role=user.role.value,
        secret=settings.jwt_secret,
        ttl_minutes=settings.jwt_ttl_minutes,
    )
    set_session_cookies(response, access=access, refresh=refresh_secret_to_set, settings=settings)
    _LOG.info(
        "auth.refresh.success",
        extra={
            "event.action": "auth.refresh.success",
            "labels.user_id": str(user.id),
            "labels.family_id": str(target.family_id),
            "labels.ip": ip or "",
            "labels.user_agent": ua or "",
        },
    )
    return LoginResponse(
        user=MeResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.role.value,
        )
    )
