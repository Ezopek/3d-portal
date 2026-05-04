import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from app.core.audit import record_event
from app.core.auth.dependencies import current_admin
from app.core.auth.jwt import encode_token
from app.core.auth.password import verify_password
from app.core.config import Settings, get_settings
from app.core.db.models import User
from app.core.db.session import get_engine, get_session
from app.modules.auth.models import LoginRequest, MeResponse, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
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
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    token = encode_token(
        subject=str(user.id),
        role=user.role.value,
        secret=settings.jwt_secret,
        ttl_minutes=settings.jwt_ttl_minutes,
    )
    record_event(
        get_engine(),
        action="auth.login.success",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        after={"email": user.email},
    )
    return TokenResponse(access_token=token, expires_in=settings.jwt_ttl_minutes * 60)


@router.get("/me", response_model=MeResponse)
def me(
    session: Annotated[Session, Depends(get_session)],
    user_id: uuid.UUID = current_admin,
) -> MeResponse:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return MeResponse(
        id=user.id, email=user.email, display_name=user.display_name, role=user.role.value
    )


@router.post("/logout", status_code=204)
def logout() -> Response:
    # JWT is stateless on the server; client discards. Audit-only.
    return Response(status_code=204)
