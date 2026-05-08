"""apps/api/tests/test_auth_refresh.py"""
import datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.auth.cookies import ACCESS_COOKIE, REFRESH_COOKIE
from app.core.db.models import RefreshToken
from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/r.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "p")
    monkeypatch.setenv("JWT_SECRET", "s")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    from app.core.config import get_settings
    from app.core.db.session import get_engine
    get_settings.cache_clear()
    get_engine.cache_clear()
    with TestClient(create_app()) as c:
        c.post("/api/auth/login",
               json={"email": "admin@example.com", "password": "p"})
        yield c
    get_settings.cache_clear()
    get_engine.cache_clear()


def _get_refresh_cookie(client) -> str | None:
    """Read the refresh cookie, tolerating multiple path entries."""
    values = [ck.value for ck in client.cookies.jar if ck.name == REFRESH_COOKIE]
    return values[-1] if values else None


def test_refresh_happy_path_rotates(client):
    old_refresh = _get_refresh_cookie(client)
    old_access = client.cookies.get(ACCESS_COOKIE)
    r = client.post("/api/auth/refresh")
    assert r.status_code == 200
    new_refresh = _get_refresh_cookie(client)
    new_access = client.cookies.get(ACCESS_COOKIE)
    assert new_refresh != old_refresh
    assert new_access != old_access
    body = r.json()
    assert body["user"]["email"] == "admin@example.com"


def test_refresh_with_no_cookie_returns_no_refresh(client):
    client.cookies.delete(REFRESH_COOKIE)
    r = client.post("/api/auth/refresh")
    assert r.status_code == 401
    assert r.json()["detail"] == "no_refresh"


def test_refresh_with_garbage_returns_invalid_refresh(client):
    client.cookies.set(REFRESH_COOKIE, "garbage", path="/api/auth")
    r = client.post("/api/auth/refresh")
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid_refresh"


def test_refresh_with_expired_returns_refresh_expired(client):
    """Backdate expires_at on the active row."""
    from app.core.db.session import get_engine
    with Session(get_engine()) as s:
        row = s.exec(select(RefreshToken)).first()
        row.expires_at = datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=1)
        s.add(row)
        s.commit()
    r = client.post("/api/auth/refresh")
    assert r.status_code == 401
    assert r.json()["detail"] == "refresh_expired"
