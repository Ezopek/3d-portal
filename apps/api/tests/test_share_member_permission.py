"""Tests for the Initiative 5 member permission expansion (Story 6.5).

Covers AC-2 through AC-6 from the Story 6.5 spec:
- POST /api/admin/share with member cookie -> 201 (FR5-MEMBER-1)
- POST /api/admin/share with admin cookie -> 201 (regression)
- GET / DELETE /api/admin/share with member cookie -> 403 (per-route allowlist; FR5-MEMBER-2)
- GET /api/admin/audit, /api/admin/audit-log, /api/admin/invites (POST+GET),
  /api/admin/invites/{id}/revoke, /api/admin/sentry-test with member cookie
  -> 403 (FR5-MEMBER-2 verifier)
- Anonymous + agent + unknown-role cookies on POST /api/admin/share

Reuses the test_share_admin.py fixture shape (TestClient + fakeredis swap +
JWT cookie minting). Adds a member-role JWT alongside the admin one so each
test can pick the cookie state it needs.

Note on the seeded member User row: the dependency itself reads only the JWT
sub claim, BUT the audit_log table has a FK on actor_user_id -> user.id with
PRAGMA foreign_keys=ON, so the happy-path audit emission would IntegrityError
without a real user row. Seeding mirrors the Story 6.4 post-register state.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.auth.jwt import encode_token
from app.core.db.models import AuditLog, Model, User, UserRole
from app.core.db.session import get_engine
from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    from app.core.config import get_settings

    get_settings.cache_clear()
    get_engine.cache_clear()
    app = create_app()
    fake = fakeredis.aioredis.FakeRedis()
    factory = MagicMock()
    factory.get = MagicMock(return_value=fake)

    async def _aclose():
        return None

    factory.aclose = _aclose
    with TestClient(app) as c:
        c.headers.update({"X-Portal-Client": "web"})
        app.state.redis = factory
        engine = get_engine()
        with Session(engine) as s:
            admin = s.exec(select(User).where(User.email == "admin@localhost.localdomain")).first()
            admin_uuid = admin.id
            member = User(
                email=f"member-{uuid.uuid4().hex[:6]}@localhost.localdomain",
                display_name="Member",
                role=UserRole.member,
                password_hash="$2b$12$irrelevant.for.these.tests....................",
            )
            s.add(member)
            s.flush()
            member_uuid = member.id
            m1 = Model(
                slug=f"share-m1-{uuid.uuid4().hex[:6]}",
                name_en="M1",
            )
            m2 = Model(
                slug=f"share-m2-{uuid.uuid4().hex[:6]}",
                name_en="M2",
            )
            s.add(m1)
            s.add(m2)
            s.commit()
            model_ids = (m1.id, m2.id)
        admin_token = encode_token(
            subject=str(admin_uuid), role="admin", secret="test", ttl_minutes=30
        )
        member_token = encode_token(
            subject=str(member_uuid), role="member", secret="test", ttl_minutes=30
        )
        yield c, admin_token, admin_uuid, member_token, member_uuid, model_ids, fake
    get_settings.cache_clear()
    get_engine.cache_clear()


def _set_cookie(c: TestClient, token: str) -> None:
    c.cookies.set("portal_access", token)


def _clear_cookie(c: TestClient) -> None:
    c.cookies.clear()


def _audit_rows(action: str) -> list[AuditLog]:
    engine = get_engine()
    with Session(engine) as s:
        return list(s.exec(select(AuditLog).where(AuditLog.action == action)).all())


# ---------------------------------------------------------------------------
# AC-2: Member happy path on POST /api/admin/share
# ---------------------------------------------------------------------------


def test_member_create_share_returns_201_with_token(client):
    c, _, _, member_token, _, (mid, _), _ = client
    _set_cookie(c, member_token)
    r = c.post("/api/admin/share", json={"model_id": str(mid), "expires_in_hours": 24})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["url"].startswith("/share/")
    assert isinstance(body["token"], str) and len(body["token"]) > 0


def test_member_create_share_writes_audit_with_member_actor(client):
    c, _, _, member_token, member_uuid, (mid, _), _ = client
    _set_cookie(c, member_token)
    r = c.post("/api/admin/share", json={"model_id": str(mid), "expires_in_hours": 24})
    assert r.status_code == 201
    rows = _audit_rows("admin.share.create")
    assert len(rows) == 1
    assert rows[0].action == "admin.share.create"
    assert rows[0].actor_user_id == member_uuid
    after = json.loads(rows[0].after_json)
    assert after["model_id"] == str(mid)
    assert "token" in after


def test_member_create_share_writes_redis_key_consumable_by_public_route(client):
    c, _, _, member_token, _, (mid, _), _ = client
    _set_cookie(c, member_token)
    r = c.post("/api/admin/share", json={"model_id": str(mid), "expires_in_hours": 24})
    assert r.status_code == 201
    token = r.json()["token"]
    _clear_cookie(c)
    r2 = c.get(f"/api/share/{token}")
    assert r2.status_code == 200, r2.text
    assert r2.json()["id"] == str(mid)


# ---------------------------------------------------------------------------
# AC-3: Admin path regression
# ---------------------------------------------------------------------------


def test_admin_create_share_still_returns_201(client):
    c, admin_token, _, _, _, (mid, _), _ = client
    _set_cookie(c, admin_token)
    r = c.post("/api/admin/share", json={"model_id": str(mid), "expires_in_hours": 24})
    assert r.status_code == 201


def test_admin_create_share_audit_has_admin_actor(client):
    c, admin_token, admin_uuid, _, _, (mid, _), _ = client
    _set_cookie(c, admin_token)
    r = c.post("/api/admin/share", json={"model_id": str(mid), "expires_in_hours": 24})
    assert r.status_code == 201
    rows = _audit_rows("admin.share.create")
    assert len(rows) == 1
    assert rows[0].actor_user_id == admin_uuid


# ---------------------------------------------------------------------------
# AC-4: GET + DELETE stay admin-only
# ---------------------------------------------------------------------------


def test_member_list_share_returns_403_admin_required(client):
    c, _, _, member_token, _, _, _ = client
    _set_cookie(c, member_token)
    r = c.get("/api/admin/share")
    assert r.status_code == 403
    assert r.json()["detail"] == "admin_required"


def test_member_delete_share_returns_403_admin_required(client):
    c, _, _, member_token, _, _, _ = client
    _set_cookie(c, member_token)
    r = c.delete("/api/admin/share/some-fake-token")
    assert r.status_code == 403
    assert r.json()["detail"] == "admin_required"


# ---------------------------------------------------------------------------
# Anonymous regression
# ---------------------------------------------------------------------------


def test_anonymous_create_share_returns_401_missing_access(client):
    c, _, _, _, _, (mid, _), _ = client
    _clear_cookie(c)
    r = c.post("/api/admin/share", json={"model_id": str(mid), "expires_in_hours": 24})
    assert r.status_code == 401
    assert r.json()["detail"] == "missing_access"


def test_anonymous_list_share_returns_401_missing_access(client):
    c, _, _, _, _, _, _ = client
    _clear_cookie(c)
    r = c.get("/api/admin/share")
    assert r.status_code == 401
    assert r.json()["detail"] == "missing_access"


def test_anonymous_delete_share_returns_401_missing_access(client):
    c, _, _, _, _, _, _ = client
    _clear_cookie(c)
    r = c.delete("/api/admin/share/some-fake-token")
    assert r.status_code == 401
    assert r.json()["detail"] == "missing_access"


# ---------------------------------------------------------------------------
# Agent + unknown-role denial on POST /api/admin/share (AC-1 negative paths)
# ---------------------------------------------------------------------------


def test_agent_create_share_returns_403_member_or_admin_required(client):
    c, _, _, _, _, (mid, _), _ = client
    agent_token = encode_token(
        subject=str(uuid.uuid4()), role="agent", secret="test", ttl_minutes=30
    )
    _set_cookie(c, agent_token)
    r = c.post("/api/admin/share", json={"model_id": str(mid), "expires_in_hours": 24})
    assert r.status_code == 403
    assert r.json()["detail"] == "member_or_admin_required"


def test_unknown_role_create_share_returns_403_member_or_admin_required(client):
    c, _, _, _, _, (mid, _), _ = client
    bogus_token = encode_token(
        subject=str(uuid.uuid4()), role="banana", secret="test", ttl_minutes=30
    )
    _set_cookie(c, bogus_token)
    r = c.post("/api/admin/share", json={"model_id": str(mid), "expires_in_hours": 24})
    assert r.status_code == 403
    assert r.json()["detail"] == "member_or_admin_required"


# ---------------------------------------------------------------------------
# AC-5: FR5-MEMBER-2 denial surface across admin routes
# ---------------------------------------------------------------------------


def test_member_get_admin_audit_returns_403(client):
    c, _, _, member_token, _, _, _ = client
    _set_cookie(c, member_token)
    r = c.get("/api/admin/audit")
    assert r.status_code == 403
    assert r.json()["detail"] == "admin_required"


def test_member_get_admin_audit_log_returns_403(client):
    c, _, _, member_token, _, _, _ = client
    _set_cookie(c, member_token)
    r = c.get("/api/admin/audit-log")
    assert r.status_code == 403
    assert r.json()["detail"] == "admin_required"


def test_member_post_admin_invites_returns_403(client):
    c, _, _, member_token, _, _, _ = client
    _set_cookie(c, member_token)
    r = c.post("/api/admin/invites", json={"role": "member", "ttl_preset": "ONE_DAY"})
    assert r.status_code == 403
    assert r.json()["detail"] == "admin_required"


def test_member_get_admin_invites_returns_403(client):
    c, _, _, member_token, _, _, _ = client
    _set_cookie(c, member_token)
    r = c.get("/api/admin/invites")
    assert r.status_code == 403
    assert r.json()["detail"] == "admin_required"


def test_member_post_admin_invite_revoke_returns_403(client):
    c, _, _, member_token, _, _, _ = client
    _set_cookie(c, member_token)
    r = c.post(f"/api/admin/invites/{uuid.uuid4()}/revoke")
    assert r.status_code == 403
    assert r.json()["detail"] == "admin_required"


def test_member_post_admin_sentry_test_returns_403(client):
    c, _, _, member_token, _, _, _ = client
    _set_cookie(c, member_token)
    r = c.post("/api/admin/sentry-test")
    assert r.status_code == 403
    assert r.json()["detail"] == "admin_required"
