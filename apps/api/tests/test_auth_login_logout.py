"""apps/api/tests/test_auth_login_logout.py"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.auth.cookies import ACCESS_COOKIE, REFRESH_COOKIE
from app.core.db.models import RefreshToken, User
from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/a.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "s")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    from app.core.config import get_settings
    from app.core.db.session import get_engine
    get_settings.cache_clear()
    get_engine.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        c.headers.update({"X-Portal-Client": "web"})
        yield c
    get_settings.cache_clear()
    get_engine.cache_clear()


def test_login_sets_both_cookies(client):
    r = client.post("/api/auth/login",
                    json={"email": "admin@example.com", "password": "pw"})
    assert r.status_code == 200
    assert ACCESS_COOKIE in r.cookies
    assert REFRESH_COOKIE in r.cookies
    body = r.json()
    assert body["user"]["email"] == "admin@example.com"
    assert body["user"]["role"] == "admin"
    assert "access_token" not in body  # legacy field gone


def test_login_creates_active_refresh_row(client):
    client.post("/api/auth/login",
                json={"email": "admin@example.com", "password": "pw"})
    from app.core.db.session import get_engine
    with Session(get_engine()) as s:
        rows = s.exec(select(RefreshToken)).all()
        assert len(rows) == 1
        assert rows[0].revoked_at is None
        assert rows[0].family_id is not None


def test_login_bad_password_rejects(client):
    r = client.post("/api/auth/login",
                    json={"email": "admin@example.com", "password": "wrong"})
    assert r.status_code == 401


def test_me_returns_current_user_via_cookie(client):
    client.post("/api/auth/login",
                json={"email": "admin@example.com", "password": "pw"})
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "admin@example.com"


def test_me_no_cookie_returns_missing_access(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401
    assert r.json()["detail"] == "missing_access"


def test_logout_revokes_family_and_clears_cookies(client):
    client.post("/api/auth/login",
                json={"email": "admin@example.com", "password": "pw"})
    r = client.post("/api/auth/logout")
    assert r.status_code == 204
    set_cookies = r.headers.get_list("set-cookie") if hasattr(r.headers, "get_list") else [
        v for k, v in r.headers.items() if k.lower() == "set-cookie"
    ]
    assert any(("portal_access" in c) and ("Max-Age=0" in c or 'expires=' in c.lower()) for c in set_cookies)
    assert any(("portal_refresh" in c) and ("Max-Age=0" in c or 'expires=' in c.lower()) for c in set_cookies)
    r2 = client.get("/api/auth/me")
    assert r2.status_code == 401


def test_logout_with_no_cookies_returns_204(client):
    r = client.post("/api/auth/logout")
    assert r.status_code == 204


def test_logout_idempotent_double_call(client):
    client.post("/api/auth/login",
                json={"email": "admin@example.com", "password": "pw"})
    a = client.post("/api/auth/logout")
    b = client.post("/api/auth/logout")
    assert a.status_code == 204
    assert b.status_code == 204
