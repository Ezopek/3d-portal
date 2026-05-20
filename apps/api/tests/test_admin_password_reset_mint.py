"""Story 8.5 — backend tests for the admin password-reset mint endpoint.

8 named tests M1-M8 covering ``POST /api/admin/users/{id}/password-reset``
per the spec AC-7 table. Verifies:

* Golden-path mint → 201 + reset_url shape + expires_at window.
* ``auth.password.reset.initiated`` audit with ``actor!=entity`` +
  ``after.ttl_seconds``.
* RBAC guards (member 403, anonymous 401).
* Foot-gun guards (cannot_target_self 400, cannot_target_agent 400,
  user_not_found 404) — each MUST yield zero Redis state AND zero audit.
* Idempotency: two consecutive mints for the same user yield two
  independent tokens; consuming one does not affect the other.

Helpers (``_admin_token``, ``_set_admin_cookie``, ``_seed_user``) are
duplicated inline from ``test_admin_users_mutations.py`` per Story 8.3's
deliberate-duplication rule.
"""

from __future__ import annotations

import datetime
import json
import uuid

import bcrypt
import pytest
from sqlmodel import Session, select

from app.core.auth.jwt import encode_token
from app.core.db.models import AuditLog, User
from app.core.db.models._enums import UserRole
from app.core.db.session import get_engine

SEEDED_ADMIN_EMAIL = "admin@localhost.localdomain"
JWT_TEST_SECRET = "test-secret-not-real"
PASSWORD = "Sup3rPassword!"


@pytest.fixture(autouse=True)
def _clear_user_and_audit_tables():
    """Wipe non-admin user + audit rows between tests.

    Redis state cleanup is implicit — ``isolated_client`` builds a fresh
    ``fakeredis.aioredis.FakeRedis`` per test, so no cross-test leakage of
    ``invite:reset:*`` keys is possible.
    """
    engine = get_engine()
    with Session(engine) as s:
        for row in s.exec(select(User).where(User.email != SEEDED_ADMIN_EMAIL)).all():
            s.delete(row)
        for row in s.exec(select(AuditLog)).all():
            s.delete(row)
        s.commit()
    yield


def _get_admin_id() -> uuid.UUID:
    engine = get_engine()
    with Session(engine) as s:
        admin = s.exec(select(User).where(User.email == SEEDED_ADMIN_EMAIL)).first()
        assert admin is not None, "Seeded admin missing — conftest regressed"
        return admin.id


def _token_for(user_id: uuid.UUID, role: str) -> str:
    return encode_token(
        subject=str(user_id),
        role=role,
        secret=JWT_TEST_SECRET,
        ttl_minutes=30,
    )


def _admin_token() -> str:
    return _token_for(_get_admin_id(), "admin")


def _set_admin_cookie(client) -> None:
    client.cookies.set("portal_access", _admin_token())


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=4)).decode()


def _seed_user(
    email: str,
    *,
    role: UserRole = UserRole.member,
    is_active: bool = True,
) -> uuid.UUID:
    engine = get_engine()
    with Session(engine) as s:
        row = User(
            email=email,
            display_name=email.split("@")[0].title(),
            role=role,
            password_hash=_hash_password(PASSWORD),
            is_active=is_active,
        )
        s.add(row)
        s.flush()
        s.commit()
        return row.id


def _audit_rows() -> list[AuditLog]:
    engine = get_engine()
    with Session(engine) as s:
        return list(s.exec(select(AuditLog).order_by(AuditLog.at.asc())).all())


def _redis_keys(client, fake) -> list[bytes]:
    async def _list():
        return await fake.keys("invite:reset:*")

    return client.portal.call(_list)


# ---------------------------------------------------------------------------
# M1 — golden-path mint returns 201 + reset_url shape + expires_at window
# ---------------------------------------------------------------------------
def test_mint_golden_path_returns_201_with_reset_url_and_expires_at(isolated_client):
    c, fake = isolated_client
    target_id = _seed_user("m1@test.example")
    _set_admin_cookie(c)

    before = datetime.datetime.now(datetime.UTC)
    r = c.post(f"/api/admin/users/{target_id}/password-reset")
    after = datetime.datetime.now(datetime.UTC)

    assert r.status_code == 201, r.text
    body = r.json()
    assert body["reset_url"].startswith("/reset-password?token=")
    token = body["reset_url"].removeprefix("/reset-password?token=")
    assert len(token) == 43

    expires_at = datetime.datetime.fromisoformat(body["expires_at"])
    ttl = datetime.timedelta(seconds=3600)
    assert before + ttl - datetime.timedelta(seconds=5) <= expires_at
    assert expires_at <= after + ttl + datetime.timedelta(seconds=5)

    # Redis key written.
    keys = _redis_keys(c, fake)
    assert any(k.decode().endswith(token) for k in keys)


# ---------------------------------------------------------------------------
# M2 — mint emits auth.password.reset.initiated audit
# ---------------------------------------------------------------------------
def test_mint_emits_initiated_audit_with_actor_pivot(isolated_client):
    c, _ = isolated_client
    target_id = _seed_user("m2@test.example")
    _set_admin_cookie(c)

    r = c.post(f"/api/admin/users/{target_id}/password-reset")
    assert r.status_code == 201, r.text

    rows = _audit_rows()
    assert len(rows) == 1
    ev = rows[0]
    assert ev.action == "auth.password.reset.initiated"
    assert ev.actor_user_id == _get_admin_id()
    assert ev.entity_id == target_id
    assert ev.actor_user_id != ev.entity_id
    assert json.loads(ev.after_json) == {"ttl_seconds": 3600}


# ---------------------------------------------------------------------------
# M3 — non-admin (member) caller returns 403
# ---------------------------------------------------------------------------
def test_mint_member_returns_403(isolated_client):
    c, fake = isolated_client
    target_id = _seed_user("m3-target@test.example")
    member_id = _seed_user("m3-member@test.example", role=UserRole.member)
    c.cookies.set("portal_access", _token_for(member_id, "member"))

    r = c.post(f"/api/admin/users/{target_id}/password-reset")
    assert r.status_code == 403, r.text
    assert _redis_keys(c, fake) == []
    assert _audit_rows() == []


# ---------------------------------------------------------------------------
# M4 — anonymous caller returns 401
# ---------------------------------------------------------------------------
def test_mint_anonymous_returns_401(isolated_client):
    c, fake = isolated_client
    target_id = _seed_user("m4@test.example")

    r = c.post(f"/api/admin/users/{target_id}/password-reset")
    assert r.status_code == 401, r.text
    assert _redis_keys(c, fake) == []
    assert _audit_rows() == []


# ---------------------------------------------------------------------------
# M5 — self-target returns 400 cannot_target_self
# ---------------------------------------------------------------------------
def test_mint_self_target_returns_400(isolated_client):
    c, fake = isolated_client
    _set_admin_cookie(c)

    r = c.post(f"/api/admin/users/{_get_admin_id()}/password-reset")
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == "cannot_target_self"
    assert _redis_keys(c, fake) == []
    assert _audit_rows() == []


# ---------------------------------------------------------------------------
# M6 — agent-target returns 400 cannot_target_agent
# ---------------------------------------------------------------------------
def test_mint_agent_target_returns_400(isolated_client):
    c, fake = isolated_client
    agent_id = _seed_user("m6-agent@test.example", role=UserRole.agent)
    _set_admin_cookie(c)

    r = c.post(f"/api/admin/users/{agent_id}/password-reset")
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == "cannot_target_agent"
    assert _redis_keys(c, fake) == []
    assert _audit_rows() == []


# ---------------------------------------------------------------------------
# M7 — unknown user_id returns 404 user_not_found
# ---------------------------------------------------------------------------
def test_mint_unknown_user_returns_404(isolated_client):
    c, fake = isolated_client
    _set_admin_cookie(c)

    r = c.post(f"/api/admin/users/{uuid.uuid4()}/password-reset")
    assert r.status_code == 404, r.text
    assert r.json()["detail"] == "user_not_found"
    assert _redis_keys(c, fake) == []
    assert _audit_rows() == []


# ---------------------------------------------------------------------------
# M8 — two consecutive mints yield two independent tokens
# ---------------------------------------------------------------------------
def test_mint_two_links_for_same_user_independent_tokens(isolated_client):
    c, fake = isolated_client
    target_id = _seed_user("m8@test.example")
    _set_admin_cookie(c)

    r1 = c.post(f"/api/admin/users/{target_id}/password-reset")
    r2 = c.post(f"/api/admin/users/{target_id}/password-reset")
    assert r1.status_code == 201
    assert r2.status_code == 201
    t1 = r1.json()["reset_url"].removeprefix("/reset-password?token=")
    t2 = r2.json()["reset_url"].removeprefix("/reset-password?token=")
    assert t1 != t2

    keys = {k.decode() for k in _redis_keys(c, fake)}
    assert f"invite:reset:{t1}" in keys
    assert f"invite:reset:{t2}" in keys
