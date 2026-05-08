"""apps/api/tests/test_auth_sessions.py"""
import datetime
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.auth.cookies import REFRESH_COOKIE
from app.core.db.models import RefreshToken
from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
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
               json={"email": "admin@example.com", "password": "p"},
               headers={"User-Agent": "device-A"})
        yield c
    get_settings.cache_clear()
    get_engine.cache_clear()


def _login_other_device(app) -> tuple[TestClient, str]:
    """Log in a second session in a separate client, return (client, refresh_cookie_value)."""
    sub = TestClient(app)
    sub.post("/api/auth/login",
             json={"email": "admin@example.com", "password": "p"},
             headers={"User-Agent": "device-B"})
    return sub, sub.cookies.get(REFRESH_COOKIE)


def test_sessions_list_marks_current(client):
    _login_other_device(client.app)
    r = client.get("/api/auth/sessions")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 2
    current = [i for i in items if i["is_current"]]
    assert len(current) == 1
    assert "device-A" in (current[0]["user_agent"] or "")


def test_sessions_delete_revokes_other_family(client):
    sub, other_refresh = _login_other_device(client.app)
    items = client.get("/api/auth/sessions").json()["items"]
    other_family = next(i for i in items if not i["is_current"])["family_id"]
    r = client.delete(f"/api/auth/sessions/{other_family}")
    assert r.status_code == 204
    # Other refresh now invalid — try refresh from sub client.
    sub.cookies.set(REFRESH_COOKIE, other_refresh, path="/api/auth")
    r2 = sub.post("/api/auth/refresh")
    assert r2.status_code == 401


def test_sessions_delete_other_users_family_returns_403(client, tmp_path, monkeypatch):
    items = client.get("/api/auth/sessions").json()["items"]
    family_id = items[0]["family_id"]

    # Create a second user, log in, attempt to delete first user's family.
    from app.core.auth.password import hash_password
    from app.core.db.models import User
    from app.core.db.session import get_engine
    with Session(get_engine()) as s:
        s.add(User(
            id=uuid.uuid4(), email="b@example.com", display_name="B", role="admin",
            password_hash=hash_password("p"),
            created_at=datetime.datetime.now(datetime.UTC),
        ))
        s.commit()
    sub = TestClient(client.app)
    sub.post("/api/auth/login",
             json={"email": "b@example.com", "password": "p"},
             headers={"User-Agent": "device-C"})
    r = sub.delete(f"/api/auth/sessions/{family_id}")
    assert r.status_code == 403


def test_sessions_delete_current_clears_cookies(client):
    items = client.get("/api/auth/sessions").json()["items"]
    current_family = next(i for i in items if i["is_current"])["family_id"]
    r = client.delete(f"/api/auth/sessions/{current_family}")
    assert r.status_code == 204
    # Subsequent /me 401
    r2 = client.get("/api/auth/me")
    assert r2.status_code == 401


