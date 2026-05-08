"""Auth router — cookie-based sessions with refresh-token rotation."""
import datetime
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
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
from app.core.auth.refresh import find_by_secret, new_refresh_row
from app.core.config import Settings, get_settings
from app.core.db.models import RefreshToken, User
from app.core.db.session import get_engine, get_session
from app.modules.auth.models import (
    LoginRequest,
    LoginResponse,
    MeResponse,
)

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
