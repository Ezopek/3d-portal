"""Story 8.3 — backend mutation tests for the per-user actions surface.

Covers AC-1 (PATCH /api/admin/users/{id}), AC-2 (POST .../force-logout),
and AC-4 (UserMutationRequest schema invariants). 12 tests M1-M12 binding
the four foot-gun guardrails + the audit-emission contract for the four
new action names (user.role_changed / user.deactivated / user.reactivated /
user.force_logout) per FR5-AUDIT-1.

Helpers are duplicated inline from ``test_admin_users_list.py`` per the
Story 8.3 §6 file-structure note (helper extraction is a Story 8.4+
deliberate refactor candidate, NOT a 8.3 accidental side-effect).
"""

from __future__ import annotations

import datetime
import hashlib
import json
import secrets
import uuid

import pytest
from sqlmodel import Session, select

from app.core.auth.jwt import encode_token
from app.core.db.models import AuditLog, RefreshToken, User
from app.core.db.models._enums import UserRole
from app.core.db.session import get_engine

SEEDED_ADMIN_EMAIL = "admin@localhost.localdomain"
JWT_TEST_SECRET = "test-secret-not-real"


def _seed_active_refresh_token(
    session: Session,
    user_id: uuid.UUID,
    *,
    family_id: uuid.UUID | None = None,
) -> RefreshToken:
    """Mint an active refresh-token row for the target user."""
    now = datetime.datetime.now(datetime.UTC)
    secret = secrets.token_urlsafe(32)
    row = RefreshToken(
        id=uuid.uuid4(),
        user_id=user_id,
        family_id=family_id or uuid.uuid4(),
        family_issued_at=now,
        token_hash=hashlib.sha256(secret.encode()).hexdigest(),
        issued_at=now,
        expires_at=now + datetime.timedelta(days=30),
        last_used_at=now,
        ip="127.0.0.1",
        user_agent="test-ua",
    )
    session.add(row)
    session.flush()
    return row


@pytest.fixture(autouse=True)
def _clear_user_and_audit_and_refresh_tables():
    """Wipe non-admin user + audit + refresh-token rows between tests."""
    engine = get_engine()
    with Session(engine) as s:
        for row in s.exec(select(RefreshToken)).all():
            s.delete(row)
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


def _admin_token() -> str:
    return encode_token(
        subject=str(_get_admin_id()),
        role="admin",
        secret=JWT_TEST_SECRET,
        ttl_minutes=30,
    )


def _set_admin_cookie(client) -> None:
    client.cookies.set("portal_access", _admin_token())


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
            password_hash="bcrypt-test-hash",
            is_active=is_active,
        )
        s.add(row)
        s.flush()
        s.commit()
        return row.id


def _audit_rows() -> list[AuditLog]:
    engine = get_engine()
    with Session(engine) as s:
        return s.exec(select(AuditLog).order_by(AuditLog.at.asc())).all()


def _refresh_rows(user_id: uuid.UUID) -> list[RefreshToken]:
    engine = get_engine()
    with Session(engine) as s:
        return s.exec(select(RefreshToken).where(RefreshToken.user_id == user_id)).all()


# ---------------------------------------------------------------------------
# M1 — PATCH role mutation emits user.role_changed
# ---------------------------------------------------------------------------
def test_patch_user_role_emits_user_role_changed(isolated_client):
    c, _ = isolated_client
    member_id = _seed_user("m1@test.example")
    _set_admin_cookie(c)
    r = c.patch(f"/api/admin/users/{member_id}", json={"role": "admin"})
    assert r.status_code == 204, r.text

    engine = get_engine()
    with Session(engine) as s:
        user = s.get(User, member_id)
        assert user is not None and user.role == UserRole.admin

    rows = _audit_rows()
    assert len(rows) == 1
    ev = rows[0]
    assert ev.action == "user.role_changed"
    assert ev.actor_user_id == _get_admin_id()
    assert ev.entity_id == member_id
    assert json.loads(ev.before_json) == {"role": "member"}
    assert json.loads(ev.after_json) == {"role": "admin"}


# ---------------------------------------------------------------------------
# M2 — PATCH is_active=False emits user.deactivated + burns all families
# ---------------------------------------------------------------------------
def test_patch_user_is_active_false_emits_user_deactivated_and_burns_families(
    isolated_client,
):
    c, _ = isolated_client
    member_id = _seed_user("m2@test.example")
    engine = get_engine()
    with Session(engine) as s:
        _seed_active_refresh_token(s, member_id)
        _seed_active_refresh_token(s, member_id)
        s.commit()
    _set_admin_cookie(c)

    r = c.patch(f"/api/admin/users/{member_id}", json={"is_active": False})
    assert r.status_code == 204, r.text

    with Session(engine) as s:
        user = s.get(User, member_id)
        assert user is not None and user.is_active is False
    rt_rows = _refresh_rows(member_id)
    assert len(rt_rows) == 2
    for row in rt_rows:
        assert row.revoked_at is not None
        assert row.revoke_reason == "force_deactivation"

    rows = _audit_rows()
    assert len(rows) == 1
    ev = rows[0]
    assert ev.action == "user.deactivated"
    assert ev.actor_user_id == _get_admin_id()
    assert ev.entity_id == member_id
    assert json.loads(ev.before_json) == {"is_active": True}
    assert json.loads(ev.after_json) == {"is_active": False}


# ---------------------------------------------------------------------------
# M3 — PATCH is_active=True (reactivate) emits user.reactivated
# ---------------------------------------------------------------------------
def test_patch_user_is_active_true_after_false_emits_user_reactivated(isolated_client):
    c, _ = isolated_client
    member_id = _seed_user("m3@test.example", is_active=False)
    _set_admin_cookie(c)

    r = c.patch(f"/api/admin/users/{member_id}", json={"is_active": True})
    assert r.status_code == 204, r.text

    engine = get_engine()
    with Session(engine) as s:
        user = s.get(User, member_id)
        assert user is not None and user.is_active is True

    rows = _audit_rows()
    assert len(rows) == 1
    ev = rows[0]
    assert ev.action == "user.reactivated"
    assert json.loads(ev.before_json) == {"is_active": False}
    assert json.loads(ev.after_json) == {"is_active": True}


# ---------------------------------------------------------------------------
# M4 — PATCH self returns 400 cannot_target_self
# ---------------------------------------------------------------------------
def test_patch_self_returns_400_cannot_target_self(isolated_client):
    c, _ = isolated_client
    _set_admin_cookie(c)
    admin_id = _get_admin_id()

    r1 = c.patch(f"/api/admin/users/{admin_id}", json={"role": "member"})
    assert r1.status_code == 400
    assert r1.json()["detail"] == "cannot_target_self"

    r2 = c.patch(f"/api/admin/users/{admin_id}", json={"is_active": False})
    assert r2.status_code == 400
    assert r2.json()["detail"] == "cannot_target_self"

    engine = get_engine()
    with Session(engine) as s:
        admin = s.get(User, admin_id)
        assert admin is not None
        assert admin.role == UserRole.admin
        assert admin.is_active is True
    assert _audit_rows() == []


# ---------------------------------------------------------------------------
# M5 — PATCH agent row returns 400 cannot_target_agent
# ---------------------------------------------------------------------------
def test_patch_agent_row_returns_400_cannot_target_agent(isolated_client):
    c, _ = isolated_client
    agent_id = _seed_user("agent@test.example", role=UserRole.agent)
    _set_admin_cookie(c)

    r1 = c.patch(f"/api/admin/users/{agent_id}", json={"is_active": False})
    assert r1.status_code == 400
    assert r1.json()["detail"] == "cannot_target_agent"

    r2 = c.patch(f"/api/admin/users/{agent_id}", json={"role": "member"})
    assert r2.status_code == 400
    assert r2.json()["detail"] == "cannot_target_agent"

    engine = get_engine()
    with Session(engine) as s:
        agent = s.get(User, agent_id)
        assert agent is not None and agent.is_active is True
        assert agent.role == UserRole.agent
    assert _audit_rows() == []


# ---------------------------------------------------------------------------
# M6 — PATCH promote-to-agent returns 400 cannot_promote_to_agent
# ---------------------------------------------------------------------------
def test_patch_promote_to_agent_returns_400_cannot_promote_to_agent(isolated_client):
    c, _ = isolated_client
    member_id = _seed_user("m6@test.example")
    _set_admin_cookie(c)

    r = c.patch(f"/api/admin/users/{member_id}", json={"role": "agent"})
    assert r.status_code == 400
    assert r.json()["detail"] == "cannot_promote_to_agent"

    engine = get_engine()
    with Session(engine) as s:
        user = s.get(User, member_id)
        assert user is not None and user.role == UserRole.member
    assert _audit_rows() == []


# ---------------------------------------------------------------------------
# M7 — PATCH unknown field returns 422 (extra="forbid")
# ---------------------------------------------------------------------------
def test_patch_unknown_field_returns_422_extra_forbid(isolated_client):
    c, _ = isolated_client
    member_id = _seed_user("m7@test.example")
    _set_admin_cookie(c)

    r = c.patch(
        f"/api/admin/users/{member_id}",
        json={"role": "admin", "force_2fa_enrollment": True},
    )
    assert r.status_code == 422

    engine = get_engine()
    with Session(engine) as s:
        user = s.get(User, member_id)
        assert user is not None and user.role == UserRole.member
    assert _audit_rows() == []


# ---------------------------------------------------------------------------
# M8 — PATCH empty body returns 400 no_mutation_provided
# ---------------------------------------------------------------------------
def test_patch_empty_body_returns_400_no_mutation_provided(isolated_client):
    c, _ = isolated_client
    member_id = _seed_user("m8@test.example")
    _set_admin_cookie(c)

    r = c.patch(f"/api/admin/users/{member_id}", json={})
    assert r.status_code == 400
    assert r.json()["detail"] == "no_mutation_provided"
    assert _audit_rows() == []


# ---------------------------------------------------------------------------
# M9 — PATCH no-op mutation emits no audit
# ---------------------------------------------------------------------------
def test_patch_noop_mutation_emits_no_audit(isolated_client):
    c, _ = isolated_client
    member_id = _seed_user("m9@test.example")
    _set_admin_cookie(c)

    r = c.patch(
        f"/api/admin/users/{member_id}",
        json={"role": "member", "is_active": True},
    )
    assert r.status_code == 204, r.text
    assert _audit_rows() == []

    engine = get_engine()
    with Session(engine) as s:
        user = s.get(User, member_id)
        assert user is not None
        assert user.role == UserRole.member
        assert user.is_active is True


# ---------------------------------------------------------------------------
# M10 — PATCH returns 403 for member-role cookie
# ---------------------------------------------------------------------------
def test_patch_returns_403_for_member_role(isolated_client):
    c, _ = isolated_client
    member_id = _seed_user("m10@test.example")
    member_token = encode_token(
        subject=str(uuid.uuid4()),
        role="member",
        secret=JWT_TEST_SECRET,
        ttl_minutes=30,
    )
    c.cookies.set("portal_access", member_token)

    r = c.patch(f"/api/admin/users/{member_id}", json={"role": "admin"})
    assert r.status_code == 403
    assert _audit_rows() == []


# ---------------------------------------------------------------------------
# M11 — POST force-logout revokes all families + emits user.force_logout
# ---------------------------------------------------------------------------
def test_force_logout_revokes_all_families_and_emits_user_force_logout(isolated_client):
    c, _ = isolated_client
    member_id = _seed_user("m11@test.example")
    engine = get_engine()
    # The partial-unique index ``ux_refresh_tokens_family_active`` permits at
    # most one active row per family, so the AC-5 §M11 "3 active rows across
    # 2 distinct families" is technically infeasible at the schema layer; we
    # honor the spec's INTENT (force-logout burns every active row + audit
    # revoked_count matches reality) by seeding 3 distinct families with one
    # active row each.
    with Session(engine) as s:
        _seed_active_refresh_token(s, member_id)
        _seed_active_refresh_token(s, member_id)
        _seed_active_refresh_token(s, member_id)
        s.commit()
    _set_admin_cookie(c)

    r = c.post(f"/api/admin/users/{member_id}/force-logout")
    assert r.status_code == 204, r.text

    rt_rows = _refresh_rows(member_id)
    assert len(rt_rows) == 3
    for row in rt_rows:
        assert row.revoked_at is not None
        assert row.revoke_reason == "admin_force_logout"

    rows = _audit_rows()
    assert len(rows) == 1
    ev = rows[0]
    assert ev.action == "user.force_logout"
    assert ev.actor_user_id == _get_admin_id()
    assert ev.entity_id == member_id
    assert json.loads(ev.after_json)["revoked_count"] == 3


# ---------------------------------------------------------------------------
# M12 — POST force-logout self + agent return 400
# ---------------------------------------------------------------------------
def test_force_logout_self_and_agent_return_400(isolated_client):
    c, _ = isolated_client
    _set_admin_cookie(c)

    r_self = c.post(f"/api/admin/users/{_get_admin_id()}/force-logout")
    assert r_self.status_code == 400
    assert r_self.json()["detail"] == "cannot_target_self"

    agent_id = _seed_user("agent2@test.example", role=UserRole.agent)
    r_agent = c.post(f"/api/admin/users/{agent_id}/force-logout")
    assert r_agent.status_code == 400
    assert r_agent.json()["detail"] == "cannot_target_agent"

    assert _audit_rows() == []
