"""apps/api/tests/test_csrf_middleware.py"""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/c.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "p")
    monkeypatch.setenv("JWT_SECRET", "s")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    from app.core.config import get_settings
    from app.core.db.session import get_engine
    get_settings.cache_clear()
    get_engine.cache_clear()
    with TestClient(create_app()) as c:
        # NOTE: deliberately NOT setting X-Portal-Client by default; each test sets it.
        yield c


def test_post_without_header_blocked(client):
    r = client.post("/api/auth/login",
                    json={"email": "admin@example.com", "password": "p"})
    assert r.status_code == 403
    assert r.json()["detail"] == "csrf_required"


def test_post_with_header_allowed(client):
    r = client.post("/api/auth/login",
                    json={"email": "admin@example.com", "password": "p"},
                    headers={"X-Portal-Client": "web"})
    assert r.status_code == 200


def test_get_without_header_allowed(client):
    r = client.get("/api/health")
    assert r.status_code == 200


def test_share_post_exempt(client):
    """Mutating POST to /api/share/* is NOT blocked.

    /api/share/* may not have a real POST endpoint; the test confirms the
    middleware does not gate the path. Use a path that returns 404 or 405
    from the router — anything except 403 means we got past the middleware.
    """
    r = client.post("/api/share/does-not-exist", json={})
    assert r.status_code != 403  # 404, 405, etc. all OK


def test_delete_unsafe_blocked(client):
    r = client.delete("/api/admin/audit-log")
    assert r.status_code == 403
    assert r.json()["detail"] == "csrf_required"


def test_options_request_not_blocked(client):
    r = client.options("/api/auth/login")
    # 200 or 405 — anything but 403.
    assert r.status_code != 403
