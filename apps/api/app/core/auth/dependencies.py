"""apps/api/app/core/auth/dependencies.py"""
import uuid
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status

from app.core.auth.cookies import ACCESS_COOKIE
from app.core.auth.jwt import TokenError, decode_token
from app.core.config import Settings, get_settings

_ALLOWED_ROLES: frozenset[str] = frozenset({"admin", "agent", "member"})


def _decode(
    token: str | None, settings: Settings
) -> dict[str, object]:
    if token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing_access")
    try:
        return decode_token(token, secret=settings.jwt_secret)
    except TokenError as exc:
        msg = str(exc).lower()
        if "expired" in msg:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "access_expired") from exc
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_access") from exc


def _resolve_admin(claims: dict[str, object]) -> uuid.UUID:
    if claims.get("role") != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin_required")
    try:
        return uuid.UUID(str(claims["sub"]))
    except (KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_access") from exc


def _resolve_user(claims: dict[str, object]) -> uuid.UUID:
    if claims.get("role") not in _ALLOWED_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden_role")
    try:
        return uuid.UUID(str(claims["sub"]))
    except (KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_access") from exc


def _current_admin_dep(
    portal_access: Annotated[str | None, Cookie(alias=ACCESS_COOKIE)] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
) -> uuid.UUID:
    return _resolve_admin(_decode(portal_access, settings))


def _current_user_dep(
    portal_access: Annotated[str | None, Cookie(alias=ACCESS_COOKIE)] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
) -> uuid.UUID:
    return _resolve_user(_decode(portal_access, settings))


current_admin = Depends(_current_admin_dep)
current_user = Depends(_current_user_dep)
