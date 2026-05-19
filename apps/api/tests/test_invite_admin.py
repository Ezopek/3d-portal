"""Tests for the Initiative 5 invite-token admin router (Story 6.3).

Covers AC-1 through AC-6 from the Story 6.3 spec:
- POST /api/admin/invites (generate)
- GET  /api/admin/invites (list with status filter + pagination)
- POST /api/admin/invites/{id}/revoke (revoke)

Reuses the `test_share_admin.py` fixture shape verbatim (TestClient +
fakeredis swap + admin-JWT cookie). DB-side isolation comes from the
session-scope ``_isolated_db`` autouse fixture in conftest.py; the
per-test autouse below clears ``invite_tokens`` and ``audit_log`` rows
so each test sees only its own emissions.
"""

from __future__ import annotations

import datetime
import json
import uuid
from unittest.mock import MagicMock

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.auth.jwt import encode_token
from app.core.db.models import AuditLog, User
from app.core.db.session import get_engine
from app.main import create_app
from app.modules.invite import InviteService, InviteToken, hash_token


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
            user = s.exec(select(User).where(User.email == "admin@localhost.localdomain")).first()
            admin_uuid = user.id
        admin_token = encode_token(
            subject=str(admin_uuid), role="admin", secret="test", ttl_minutes=30
        )
        yield c, admin_token, admin_uuid, fake
    get_settings.cache_clear()
    get_engine.cache_clear()


@pytest.fixture(autouse=True)
def _clear_invite_and_audit_tables():
    """Wipe invite_tokens + audit_log between tests for assertion isolation."""
    engine = get_engine()
    with Session(engine) as s:
        for row in s.exec(select(InviteToken)).all():
            s.delete(row)
        for row in s.exec(select(AuditLog)).all():
            s.delete(row)
        s.commit()
    yield


def _set_admin_cookie(c: TestClient, token: str) -> None:
    c.cookies.set("portal_access", token)


def _set_member_cookie(c: TestClient) -> str:
    """Mint a member-role cookie and set it. Returns the member UUID."""
    member_uuid = uuid.uuid4()
    member_token = encode_token(
        subject=str(member_uuid), role="member", secret="test", ttl_minutes=30
    )
    c.cookies.set("portal_access", member_token)
    return str(member_uuid)


def _audit_rows(action: str) -> list[AuditLog]:
    engine = get_engine()
    with Session(engine) as s:
        return list(s.exec(select(AuditLog).where(AuditLog.action == action)).all())


def _invite_row(invite_id: uuid.UUID) -> InviteToken | None:
    engine = get_engine()
    with Session(engine) as s:
        return s.get(InviteToken, invite_id)


def _seed_invite(
    *,
    role: str = "member",
    ttl_seconds: int = 604800,
    generated_at: datetime.datetime | None = None,
    used_at: datetime.datetime | None = None,
    used_by_user_id: uuid.UUID | None = None,
    used_from_ip: str | None = None,
    revoked_at: datetime.datetime | None = None,
    generated_by_user_id: uuid.UUID | None = None,
) -> InviteToken:
    """Direct INSERT into invite_tokens — bypasses the service layer."""
    engine = get_engine()
    now = datetime.datetime.now(datetime.UTC)
    row = InviteToken(
        token_hash=hash_token(uuid.uuid4().hex),
        role=role,
        generated_by_user_id=generated_by_user_id,
        generated_at=generated_at or now,
        ttl_seconds=ttl_seconds,
        used_at=used_at,
        used_by_user_id=used_by_user_id,
        used_from_ip=used_from_ip,
        revoked_at=revoked_at,
    )
    with Session(engine) as s:
        s.add(row)
        s.commit()
        s.refresh(row)
    return row


# ---------------------------------------------------------------------------
# POST /api/admin/invites — generate (AC-1, AC-4, AC-6)
# ---------------------------------------------------------------------------


def test_generate_invite_requires_admin_cookie(client):
    c, _, _, _ = client
    r = c.post("/api/admin/invites", json={"role": "member", "ttl_preset": "SEVEN_DAYS"})
    assert r.status_code == 401
    assert r.json()["detail"] == "missing_access"


def test_generate_invite_member_returns_403(client):
    c, _, _, _ = client
    _set_member_cookie(c)
    r = c.post("/api/admin/invites", json={"role": "member", "ttl_preset": "SEVEN_DAYS"})
    assert r.status_code == 403
    assert r.json()["detail"] == "admin_required"


def test_generate_invite_returns_token_and_audit_row(client):
    c, admin_token, admin_uuid, _fake_redis = client
    _set_admin_cookie(c, admin_token)
    before = datetime.datetime.now(datetime.UTC)
    r = c.post("/api/admin/invites", json={"role": "member", "ttl_seconds": 604800})
    after = datetime.datetime.now(datetime.UTC)

    assert r.status_code == 201
    body = r.json()
    assert set(body.keys()) == {
        "invite_id",
        "token",
        "registration_url",
        "role",
        "ttl_seconds",
        "expires_at",
    }
    invite_id = uuid.UUID(body["invite_id"])
    token = body["token"]
    assert len(token) == 43
    assert body["registration_url"] == f"/register?token={token}"
    assert body["role"] == "member"
    assert body["ttl_seconds"] == 604800

    # expires_at = generated_at + ttl_seconds (within tolerance of the request window)
    expires_at = datetime.datetime.fromisoformat(body["expires_at"])
    lower = before + datetime.timedelta(seconds=604800) - datetime.timedelta(seconds=2)
    upper = after + datetime.timedelta(seconds=604800) + datetime.timedelta(seconds=2)
    assert lower <= expires_at <= upper

    # DB row matches
    row = _invite_row(invite_id)
    assert row is not None
    assert row.generated_by_user_id == admin_uuid
    assert row.role == "member"
    assert row.ttl_seconds == 604800
    assert row.token_hash == hash_token(token)

    # Audit row
    audits = _audit_rows("auth.invite.generated")
    assert len(audits) == 1
    audit = audits[0]
    assert audit.entity_type == "invite_token"
    assert audit.entity_id == invite_id
    assert audit.actor_user_id == admin_uuid
    payload = json.loads(audit.after_json)
    assert payload.get("role") == "member"
    assert payload.get("ttl_seconds") == 604800


def test_generate_invite_with_ttl_preset_resolves_to_seconds(client):
    c, admin_token, _, _ = client
    _set_admin_cookie(c, admin_token)
    r = c.post("/api/admin/invites", json={"role": "member", "ttl_preset": "ONE_DAY"})
    assert r.status_code == 201
    body = r.json()
    assert body["ttl_seconds"] == 86400


def test_generate_invite_rejects_both_ttl_fields(client):
    c, admin_token, _, _ = client
    _set_admin_cookie(c, admin_token)
    r = c.post(
        "/api/admin/invites",
        json={"role": "member", "ttl_preset": "ONE_DAY", "ttl_seconds": 86400},
    )
    assert r.status_code == 422


def test_generate_invite_rejects_neither_ttl_field(client):
    c, admin_token, _, _ = client
    _set_admin_cookie(c, admin_token)
    r = c.post("/api/admin/invites", json={"role": "member"})
    assert r.status_code == 422


def test_generate_invite_rejects_agent_role(client):
    c, admin_token, _, _ = client
    _set_admin_cookie(c, admin_token)
    r = c.post("/api/admin/invites", json={"role": "agent", "ttl_seconds": 86400})
    assert r.status_code == 422


def test_generate_invite_rejects_short_ttl_seconds(client):
    c, admin_token, _, _ = client
    _set_admin_cookie(c, admin_token)
    r = c.post("/api/admin/invites", json={"role": "member", "ttl_seconds": 59})
    assert r.status_code == 422


def test_generate_invite_rejects_long_ttl_seconds(client):
    c, admin_token, _, _ = client
    _set_admin_cookie(c, admin_token)
    r = c.post("/api/admin/invites", json={"role": "member", "ttl_seconds": 7776001})
    assert r.status_code == 422


def test_generate_invite_audit_payload_omits_cleartext_token(client):
    c, admin_token, _, _ = client
    _set_admin_cookie(c, admin_token)
    r = c.post("/api/admin/invites", json={"role": "member", "ttl_preset": "ONE_DAY"})
    assert r.status_code == 201
    token = r.json()["token"]
    audits = _audit_rows("auth.invite.generated")
    assert len(audits) == 1
    payload = json.loads(audits[0].after_json)
    assert "token" not in payload
    assert "token_hash" not in payload
    assert token not in (audits[0].after_json or "")


def test_generate_invite_csrf_header_required(client):
    c, admin_token, _, _ = client
    _set_admin_cookie(c, admin_token)
    c.headers.pop("X-Portal-Client", None)
    r = c.post("/api/admin/invites", json={"role": "member", "ttl_preset": "ONE_DAY"})
    assert r.status_code == 403
    assert r.json()["detail"] == "csrf_required"


# ---------------------------------------------------------------------------
# GET /api/admin/invites — list (AC-2, AC-4, AC-6)
# ---------------------------------------------------------------------------


def _seed_one_per_status(admin_uuid: uuid.UUID) -> dict[str, InviteToken]:
    """Seed 4 rows: active, used, expired, revoked. Returns the rows by status."""
    now = datetime.datetime.now(datetime.UTC)
    active = _seed_invite(
        role="member",
        ttl_seconds=86400,
        generated_at=now - datetime.timedelta(seconds=60),
        generated_by_user_id=admin_uuid,
    )
    used = _seed_invite(
        role="member",
        ttl_seconds=86400,
        generated_at=now - datetime.timedelta(seconds=120),
        used_at=now - datetime.timedelta(seconds=30),
        used_by_user_id=admin_uuid,
        used_from_ip="127.0.0.1",
        generated_by_user_id=admin_uuid,
    )
    expired = _seed_invite(
        role="member",
        ttl_seconds=60,
        generated_at=now - datetime.timedelta(seconds=3600),
        generated_by_user_id=admin_uuid,
    )
    revoked = _seed_invite(
        role="member",
        ttl_seconds=86400,
        generated_at=now - datetime.timedelta(seconds=180),
        revoked_at=now - datetime.timedelta(seconds=20),
        generated_by_user_id=admin_uuid,
    )
    return {"active": active, "used": used, "expired": expired, "revoked": revoked}


def test_list_invites_requires_admin_cookie(client):
    c, _, _, _ = client
    r = c.get("/api/admin/invites")
    assert r.status_code == 401


def test_list_invites_member_returns_403(client):
    c, _, _, _ = client
    _set_member_cookie(c)
    r = c.get("/api/admin/invites")
    assert r.status_code == 403


def test_list_invites_default_returns_all_statuses(client):
    c, admin_token, admin_uuid, _ = client
    _seed_one_per_status(admin_uuid)
    _set_admin_cookie(c, admin_token)
    r = c.get("/api/admin/invites")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 4
    assert len(body["items"]) == 4
    statuses = {item["status"] for item in body["items"]}
    assert statuses == {"active", "used", "expired", "revoked"}


def test_list_invites_status_active_filters_correctly(client):
    c, admin_token, admin_uuid, _ = client
    seeded = _seed_one_per_status(admin_uuid)
    _set_admin_cookie(c, admin_token)
    r = c.get("/api/admin/invites?status=active")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["invite_id"] == str(seeded["active"].id)
    assert body["items"][0]["status"] == "active"


def test_list_invites_status_used_filters_correctly(client):
    c, admin_token, admin_uuid, _ = client
    seeded = _seed_one_per_status(admin_uuid)
    _set_admin_cookie(c, admin_token)
    r = c.get("/api/admin/invites?status=used")
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["invite_id"] == str(seeded["used"].id)


def test_list_invites_status_expired_filters_correctly(client):
    c, admin_token, admin_uuid, _ = client
    seeded = _seed_one_per_status(admin_uuid)
    _set_admin_cookie(c, admin_token)
    r = c.get("/api/admin/invites?status=expired")
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["invite_id"] == str(seeded["expired"].id)


def test_list_invites_status_revoked_filters_correctly(client):
    c, admin_token, admin_uuid, _ = client
    seeded = _seed_one_per_status(admin_uuid)
    _set_admin_cookie(c, admin_token)
    r = c.get("/api/admin/invites?status=revoked")
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["invite_id"] == str(seeded["revoked"].id)


def test_list_invites_status_invalid_returns_422(client):
    c, admin_token, _, _ = client
    _set_admin_cookie(c, admin_token)
    r = c.get("/api/admin/invites?status=bogus")
    assert r.status_code == 422


def test_list_invites_pagination_first_page(client):
    c, admin_token, admin_uuid, _ = client
    _seed_one_per_status(admin_uuid)
    _set_admin_cookie(c, admin_token)
    r = c.get("/api/admin/invites?page=1&page_size=2")
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert body["total"] == 4
    assert len(body["items"]) == 2


def test_list_invites_pagination_beyond_last_page_returns_empty(client):
    c, admin_token, admin_uuid, _ = client
    _seed_one_per_status(admin_uuid)
    _set_admin_cookie(c, admin_token)
    r = c.get("/api/admin/invites?page=99&page_size=10")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 4
    assert body["items"] == []


def test_list_invites_pagination_page_size_upper_bound(client):
    c, admin_token, _, _ = client
    _set_admin_cookie(c, admin_token)
    r = c.get("/api/admin/invites?page_size=201")
    assert r.status_code == 422


def test_list_invites_response_never_includes_cleartext_token(client):
    c, admin_token, admin_uuid, _ = client
    _seed_one_per_status(admin_uuid)
    _set_admin_cookie(c, admin_token)
    r = c.get("/api/admin/invites")
    assert r.status_code == 200
    body = r.json()
    for item in body["items"]:
        assert "token" not in item
        assert "token_hash" not in item


def test_list_invites_ordering_is_generated_at_desc(client):
    c, admin_token, admin_uuid, _ = client
    now = datetime.datetime.now(datetime.UTC)
    oldest = _seed_invite(
        ttl_seconds=86400,
        generated_at=now - datetime.timedelta(seconds=300),
        generated_by_user_id=admin_uuid,
    )
    middle = _seed_invite(
        ttl_seconds=86400,
        generated_at=now - datetime.timedelta(seconds=200),
        generated_by_user_id=admin_uuid,
    )
    newest = _seed_invite(
        ttl_seconds=86400,
        generated_at=now - datetime.timedelta(seconds=100),
        generated_by_user_id=admin_uuid,
    )
    _set_admin_cookie(c, admin_token)
    r = c.get("/api/admin/invites")
    body = r.json()
    order = [item["invite_id"] for item in body["items"]]
    assert order == [str(newest.id), str(middle.id), str(oldest.id)]


# ---------------------------------------------------------------------------
# POST /api/admin/invites/{id}/revoke — revoke (AC-3, AC-4, AC-6)
# ---------------------------------------------------------------------------


def test_revoke_invite_requires_admin_cookie(client):
    c, _, _, _ = client
    r = c.post(f"/api/admin/invites/{uuid.uuid4()}/revoke")
    assert r.status_code == 401


def test_revoke_invite_member_returns_403(client):
    c, _, _, _ = client
    _set_member_cookie(c)
    r = c.post(f"/api/admin/invites/{uuid.uuid4()}/revoke")
    assert r.status_code == 403


def test_revoke_invite_happy_path_returns_204_and_audits(client):
    c, admin_token, admin_uuid, _fake_redis = client
    _set_admin_cookie(c, admin_token)
    # Generate via service so Redis key exists
    gen = c.post("/api/admin/invites", json={"role": "member", "ttl_preset": "ONE_DAY"})
    invite_id = uuid.UUID(gen.json()["invite_id"])

    before = datetime.datetime.now(datetime.UTC)
    r = c.post(f"/api/admin/invites/{invite_id}/revoke")
    after = datetime.datetime.now(datetime.UTC)
    assert r.status_code == 204
    assert r.content == b""

    row = _invite_row(invite_id)
    assert row.revoked_at is not None
    lower = before - datetime.timedelta(seconds=5)
    upper = after + datetime.timedelta(seconds=5)
    assert lower <= row.revoked_at <= upper

    audits = _audit_rows("auth.invite.revoked")
    assert len(audits) == 1
    audit = audits[0]
    assert audit.entity_type == "invite_token"
    assert audit.entity_id == invite_id
    assert audit.actor_user_id == admin_uuid
    payload = json.loads(audit.after_json)
    assert payload.get("invite_id") == str(invite_id)
    assert "token" not in payload


def test_revoke_invite_makes_token_unusable_via_service(client):
    c, admin_token, _, fake_redis = client
    _set_admin_cookie(c, admin_token)
    gen = c.post("/api/admin/invites", json={"role": "member", "ttl_preset": "ONE_DAY"})
    invite_id = uuid.UUID(gen.json()["invite_id"])
    token = gen.json()["token"]

    r = c.post(f"/api/admin/invites/{invite_id}/revoke")
    assert r.status_code == 204

    # FR5-INVITE-3: a revoked invite is no longer consumable. Verify via the
    # service-layer boundary (validate_active). The fakeredis async client is
    # bound to the TestClient's event loop, so run the coroutine on that loop
    # via the Starlette TestClient's anyio blocking portal.
    service = InviteService(redis=fake_redis, engine=get_engine())
    active = c.portal.call(service.validate_active, token)
    assert active is None


def test_revoke_invite_nonexistent_id_returns_404(client):
    c, admin_token, _, _ = client
    _set_admin_cookie(c, admin_token)
    r = c.post(f"/api/admin/invites/{uuid.uuid4()}/revoke")
    assert r.status_code == 404


def test_revoke_invite_already_used_returns_409(client):
    c, admin_token, admin_uuid, _ = client
    _set_admin_cookie(c, admin_token)
    now = datetime.datetime.now(datetime.UTC)
    row = _seed_invite(
        ttl_seconds=86400,
        generated_at=now - datetime.timedelta(seconds=120),
        used_at=now - datetime.timedelta(seconds=30),
        used_by_user_id=admin_uuid,
        used_from_ip="127.0.0.1",
        generated_by_user_id=admin_uuid,
    )
    r = c.post(f"/api/admin/invites/{row.id}/revoke")
    assert r.status_code == 409


def test_revoke_invite_already_revoked_returns_409(client):
    c, admin_token, admin_uuid, _ = client
    _set_admin_cookie(c, admin_token)
    now = datetime.datetime.now(datetime.UTC)
    row = _seed_invite(
        ttl_seconds=86400,
        generated_at=now - datetime.timedelta(seconds=120),
        revoked_at=now - datetime.timedelta(seconds=20),
        generated_by_user_id=admin_uuid,
    )
    r = c.post(f"/api/admin/invites/{row.id}/revoke")
    assert r.status_code == 409


def test_revoke_invite_csrf_header_required(client):
    c, admin_token, _, _ = client
    _set_admin_cookie(c, admin_token)
    c.headers.pop("X-Portal-Client", None)
    r = c.post(f"/api/admin/invites/{uuid.uuid4()}/revoke")
    assert r.status_code == 403
    assert r.json()["detail"] == "csrf_required"
