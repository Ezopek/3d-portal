import uuid

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app.core.auth.dependencies import _resolve_user, current_admin
from app.core.auth.jwt import encode_token
from app.core.config import get_settings

# A fixed UUID used as the subject in dependency tests.
_ADMIN_UUID = "00000000-0000-0000-0000-000000000007"


@pytest.fixture
def app_with_protected_route():
    app = FastAPI()

    @app.get("/protected")
    def _route(user_id: uuid.UUID = current_admin):
        return {"user_id": str(user_id)}

    return app


def test_no_token_returns_401(app_with_protected_route):
    client = TestClient(app_with_protected_route)
    assert client.get("/protected").status_code == 401


def test_valid_admin_token_returns_subject(app_with_protected_route):
    settings = get_settings()
    token = encode_token(
        subject=_ADMIN_UUID,
        role="admin",
        secret=settings.jwt_secret,
        ttl_minutes=settings.jwt_ttl_minutes,
    )
    client = TestClient(app_with_protected_route)
    r = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == {"user_id": _ADMIN_UUID}


def test_member_role_returns_403(app_with_protected_route):
    settings = get_settings()
    token = encode_token(
        subject=_ADMIN_UUID,
        role="member",
        secret=settings.jwt_secret,
        ttl_minutes=settings.jwt_ttl_minutes,
    )
    client = TestClient(app_with_protected_route)
    r = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_resolve_user_accepts_admin_role():
    settings = get_settings()
    sub = uuid.uuid4()
    token = encode_token(subject=str(sub), role="admin", secret=settings.jwt_secret, ttl_minutes=30)
    assert _resolve_user(_creds(token), settings) == sub


def test_resolve_user_accepts_member_role():
    settings = get_settings()
    sub = uuid.uuid4()
    token = encode_token(
        subject=str(sub), role="member", secret=settings.jwt_secret, ttl_minutes=30
    )
    assert _resolve_user(_creds(token), settings) == sub


def test_resolve_user_accepts_agent_role():
    settings = get_settings()
    sub = uuid.uuid4()
    token = encode_token(subject=str(sub), role="agent", secret=settings.jwt_secret, ttl_minutes=30)
    assert _resolve_user(_creds(token), settings) == sub


def test_resolve_user_rejects_unknown_role():
    settings = get_settings()
    sub = uuid.uuid4()
    token = encode_token(
        subject=str(sub), role="superuser", secret=settings.jwt_secret, ttl_minutes=30
    )
    with pytest.raises(HTTPException) as exc:
        _resolve_user(_creds(token), settings)
    assert exc.value.status_code == 403


def test_resolve_user_rejects_missing_token():
    settings = get_settings()
    with pytest.raises(HTTPException) as exc:
        _resolve_user(None, settings)
    assert exc.value.status_code == 401


def test_resolve_user_rejects_invalid_token():
    settings = get_settings()
    with pytest.raises(HTTPException) as exc:
        _resolve_user(_creds("not.a.jwt"), settings)
    assert exc.value.status_code == 401


def test_resolve_user_rejects_malformed_subject():
    settings = get_settings()
    token = encode_token(
        subject="not-a-uuid", role="admin", secret=settings.jwt_secret, ttl_minutes=30
    )
    with pytest.raises(HTTPException) as exc:
        _resolve_user(_creds(token), settings)
    assert exc.value.status_code == 401
