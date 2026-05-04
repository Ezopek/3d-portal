import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.auth.jwt import TokenError, decode_token
from app.core.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)

_ALLOWED_ROLES: frozenset[str] = frozenset({"admin", "agent", "member"})


def _resolve_admin(
    creds: HTTPAuthorizationCredentials | None,
    settings: Settings,
) -> uuid.UUID:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    try:
        claims = decode_token(creds.credentials, secret=settings.jwt_secret)
    except TokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc
    if claims.get("role") != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin role required")
    try:
        return uuid.UUID(claims["sub"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed subject claim") from exc


def _resolve_user(
    creds: HTTPAuthorizationCredentials | None,
    settings: Settings,
) -> uuid.UUID:
    """Resolve the authenticated user id, accepting any known role.

    Used by endpoints that any logged-in user may call (e.g. /api/auth/me).
    Rejects unknown roles with 403 — the role enum is closed.
    """
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    try:
        claims = decode_token(creds.credentials, secret=settings.jwt_secret)
    except TokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc
    if claims.get("role") not in _ALLOWED_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Unknown role")
    try:
        return uuid.UUID(claims["sub"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed subject claim") from exc


def _current_admin_dep(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> uuid.UUID:
    return _resolve_admin(creds, settings)


def _current_user_dep(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> uuid.UUID:
    return _resolve_user(creds, settings)


current_admin = Depends(_current_admin_dep)
current_user = Depends(_current_user_dep)
