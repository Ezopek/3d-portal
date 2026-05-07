"""apps/api/app/core/auth/cookies.py"""
from fastapi import Response

from app.core.config import Settings

ACCESS_COOKIE = "portal_access"
REFRESH_COOKIE = "portal_refresh"

ACCESS_PATH = "/api"
REFRESH_PATH = "/api/auth"

ACCESS_MAX_AGE = 10 * 60          # 10 min
REFRESH_MAX_AGE = 30 * 24 * 60 * 60  # 30 d


def set_access_cookie(resp: Response, token: str, settings: Settings) -> None:
    resp.set_cookie(
        ACCESS_COOKIE,
        token,
        max_age=ACCESS_MAX_AGE,
        path=ACCESS_PATH,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="strict",
    )


def set_refresh_cookie(resp: Response, secret: str, settings: Settings) -> None:
    resp.set_cookie(
        REFRESH_COOKIE,
        secret,
        max_age=REFRESH_MAX_AGE,
        path=REFRESH_PATH,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="strict",
    )


def set_session_cookies(
    resp: Response, *, access: str, refresh: str, settings: Settings
) -> None:
    set_access_cookie(resp, access, settings)
    set_refresh_cookie(resp, refresh, settings)


def clear_access_cookie(resp: Response) -> None:
    resp.delete_cookie(ACCESS_COOKIE, path=ACCESS_PATH)


def clear_refresh_cookie(resp: Response) -> None:
    resp.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH)


def clear_session_cookies(resp: Response) -> None:
    clear_access_cookie(resp)
    clear_refresh_cookie(resp)
