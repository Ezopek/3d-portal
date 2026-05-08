"""apps/api/tests/test_auth_dependencies.py"""
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth.cookies import ACCESS_COOKIE
from app.core.auth.dependencies import current_admin, current_user
from app.core.auth.jwt import encode_token


@pytest.fixture
def app_with_protected_routes(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    from app.core.config import get_settings
    get_settings.cache_clear()

    app = FastAPI()

    @app.get("/admin-only")
    def _admin(uid: uuid.UUID = current_admin):
        return {"uid": str(uid)}

    @app.get("/user-only")
    def _user(uid: uuid.UUID = current_user):
        return {"uid": str(uid)}

    return app


def test_no_cookie_returns_missing_access(app_with_protected_routes):
    c = TestClient(app_with_protected_routes)
    r = c.get("/admin-only")
    assert r.status_code == 401
    assert r.json()["detail"] == "missing_access"


def test_expired_cookie_returns_access_expired(app_with_protected_routes):
    uid = uuid.uuid4()
    expired = encode_token(subject=str(uid), role="admin", secret="test", ttl_minutes=-1)
    c = TestClient(app_with_protected_routes)
    c.cookies.set(ACCESS_COOKIE, expired)
    r = c.get("/admin-only")
    assert r.status_code == 401
    assert r.json()["detail"] == "access_expired"


def test_invalid_cookie_returns_invalid_access(app_with_protected_routes):
    c = TestClient(app_with_protected_routes)
    c.cookies.set(ACCESS_COOKIE, "not.a.jwt")
    r = c.get("/admin-only")
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid_access"


def test_valid_cookie_admin_passes(app_with_protected_routes):
    uid = uuid.uuid4()
    t = encode_token(subject=str(uid), role="admin", secret="test", ttl_minutes=10)
    c = TestClient(app_with_protected_routes)
    c.cookies.set(ACCESS_COOKIE, t)
    r = c.get("/admin-only")
    assert r.status_code == 200
    assert r.json()["uid"] == str(uid)


def test_member_role_blocked_from_admin_route(app_with_protected_routes):
    uid = uuid.uuid4()
    t = encode_token(subject=str(uid), role="member", secret="test", ttl_minutes=10)
    c = TestClient(app_with_protected_routes)
    c.cookies.set(ACCESS_COOKIE, t)
    r = c.get("/admin-only")
    assert r.status_code == 403
    assert r.json()["detail"] == "admin_required"


def test_unknown_role_blocked_from_user_route(app_with_protected_routes):
    uid = uuid.uuid4()
    t = encode_token(subject=str(uid), role="banana", secret="test", ttl_minutes=10)
    c = TestClient(app_with_protected_routes)
    c.cookies.set(ACCESS_COOKIE, t)
    r = c.get("/user-only")
    assert r.status_code == 403
    assert r.json()["detail"] == "forbidden_role"
