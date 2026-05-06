"""Tests for the /api/admin/sentry-test endpoint that deliberately raises."""

import pytest
from fastapi.testclient import TestClient

from app.core.auth.jwt import encode_token
from app.main import create_app

# A fixed UUID used for non-admin "wrong role" token tests (never looked up in DB).
_NON_ADMIN_UUID = "00000000-0000-0000-0000-000000000042"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/a.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    from app.core.config import get_settings
    from app.core.db.session import get_engine as ge

    get_settings.cache_clear()
    ge.cache_clear()
    app = create_app()
    # raise_server_exceptions=False so the deliberate RuntimeError surfaces
    # as an HTTP 500 (matching prod behaviour) instead of bubbling up into
    # the test runner.
    with TestClient(app, raise_server_exceptions=False) as c:
        # Retrieve the seeded admin user UUID for the token.
        from sqlmodel import Session, select

        from app.core.db.models import User

        engine = ge()
        with Session(engine) as s:
            user = s.exec(select(User).where(User.email == "admin@localhost.localdomain")).first()
            user_id = user.id
        token = encode_token(subject=str(user_id), role="admin", secret="test", ttl_minutes=30)
        yield c, token
    get_settings.cache_clear()
    from app.core.db.session import get_engine as ge2

    ge2.cache_clear()


def test_sentry_test_requires_admin_jwt(client) -> None:
    c, _ = client
    r = c.post("/api/admin/sentry-test")
    assert r.status_code == 401


def test_sentry_test_rejects_non_admin_jwt(client) -> None:
    c, _ = client
    user_token = encode_token(subject=_NON_ADMIN_UUID, role="user", secret="test", ttl_minutes=30)
    r = c.post(
        "/api/admin/sentry-test",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 403


def test_sentry_test_returns_500_for_admin(client) -> None:
    c, token = client
    r = c.post(
        "/api/admin/sentry-test",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 500
