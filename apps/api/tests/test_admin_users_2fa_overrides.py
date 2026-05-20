"""Story 8.4 — backend tests for the admin 2FA override endpoints.

12 named tests F1-F12 binding AC-3..AC-6 (per AC-7 table). Covers both
admin-side endpoints:

* ``POST /api/admin/users/{id}/force-2fa-enrollment`` — flag set + audit
  with ``actor!=target, after.force_enrolled=true`` + 4 guards
  (cannot_target_self, cannot_target_agent, totp_already_enrolled 409,
  already_force_enrolled 409).
* ``POST /api/admin/users/{id}/force-disable-2fa`` — atomic clear of
  ``users.totp_enabled_at`` + invalidation of all active recovery_codes +
  audit with ``actor!=target, after.admin_override=true,
  after.invalidated_count`` + 3 guards (cannot_target_self,
  cannot_target_agent, totp_not_enrolled 409).

Helpers (``_admin_token``, ``_set_admin_cookie``, ``_seed_user``,
``_seed_recovery_codes``) are duplicated inline from
``test_admin_users_mutations.py`` per the Story 8.3 §6
deliberate-duplication rule (helper extraction is a Story 8.5+
refactor candidate).
"""

from __future__ import annotations

import datetime
import json
import uuid

import bcrypt
import pyotp
import pytest
from sqlmodel import Session, select

from app.core.auth.jwt import encode_token
from app.core.config import get_settings
from app.core.db.models import AuditLog, RecoveryCode, User
from app.core.db.models._enums import UserRole
from app.core.db.session import get_engine
from app.modules.auth.totp.service import encrypt_secret

SEEDED_ADMIN_EMAIL = "admin@localhost.localdomain"
JWT_TEST_SECRET = "test-secret-not-real"
KNOWN_TOTP_SECRET = "JBSWY3DPEHPK3PXP"
PASSWORD = "Sup3rPassword!"


@pytest.fixture(autouse=True)
def _clear_user_audit_and_recovery_tables():
    """Wipe non-admin user + audit + recovery-code rows between tests.

    Extends Story 8.3's ``_clear_user_and_audit_and_refresh_tables`` shape
    to also wipe ``RecoveryCode`` since F6 + F12 seed recovery-code rows.
    """
    engine = get_engine()
    with Session(engine) as s:
        for row in s.exec(select(RecoveryCode)).all():
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
    force_2fa_enrollment: bool = False,
    totp_enabled: bool = False,
) -> uuid.UUID:
    engine = get_engine()
    settings = get_settings()
    with Session(engine) as s:
        row = User(
            email=email,
            display_name=email.split("@")[0].title(),
            role=role,
            password_hash=_hash_password(PASSWORD),
            is_active=is_active,
            force_2fa_enrollment=force_2fa_enrollment,
        )
        if totp_enabled:
            row.totp_secret = encrypt_secret(KNOWN_TOTP_SECRET, settings)
            row.totp_enabled_at = datetime.datetime.now(datetime.UTC)
        s.add(row)
        s.flush()
        s.commit()
        return row.id


def _seed_recovery_codes(user_id: uuid.UUID, count: int = 3) -> uuid.UUID:
    """Mint ``count`` active recovery-code rows for the target user.

    All rows share a single batch_id; bcrypt hashes are unique per row.
    None of the rows are pre-invalidated — the force-disable handler is
    expected to flip ``invalidated_at`` on every one of them.
    """
    engine = get_engine()
    now = datetime.datetime.now(datetime.UTC)
    batch_id = uuid.uuid4()
    with Session(engine) as s:
        for i in range(count):
            code_hash = bcrypt.hashpw(
                f"code-{i}-{user_id}".encode(), bcrypt.gensalt(rounds=4)
            ).decode()
            s.add(
                RecoveryCode(
                    user_id=user_id,
                    code_hash=code_hash,
                    batch_id=batch_id,
                    generated_at=now,
                )
            )
        s.commit()
    return batch_id


def _audit_rows() -> list[AuditLog]:
    engine = get_engine()
    with Session(engine) as s:
        return list(s.exec(select(AuditLog).order_by(AuditLog.at.asc())).all())


def _read_user(user_id: uuid.UUID) -> User:
    engine = get_engine()
    with Session(engine) as s:
        u = s.get(User, user_id)
    assert u is not None
    return u


def _read_recovery_codes(user_id: uuid.UUID) -> list[RecoveryCode]:
    engine = get_engine()
    with Session(engine) as s:
        return list(s.exec(select(RecoveryCode).where(RecoveryCode.user_id == user_id)).all())


# ---------------------------------------------------------------------------
# F1 — force-enrollment sets flag + emits audit with after.force_enrolled=True
# ---------------------------------------------------------------------------
def test_force_enrollment_sets_flag_and_emits_audit_with_force_enrolled_true(
    isolated_client,
):
    c, _ = isolated_client
    member_id = _seed_user("f1@test.example")
    _set_admin_cookie(c)

    r = c.post(f"/api/admin/users/{member_id}/force-2fa-enrollment")
    assert r.status_code == 204, r.text

    user = _read_user(member_id)
    assert user.force_2fa_enrollment is True
    assert user.totp_enabled_at is None

    rows = _audit_rows()
    assert len(rows) == 1
    ev = rows[0]
    assert ev.action == "auth.totp.enrolled"
    assert ev.actor_user_id == _get_admin_id()
    assert ev.entity_id == member_id
    assert json.loads(ev.after_json) == {"force_enrolled": True}


# ---------------------------------------------------------------------------
# F2 — force-enrollment on already-enrolled user returns 409
# ---------------------------------------------------------------------------
def test_force_enrollment_already_enrolled_returns_409(isolated_client):
    c, _ = isolated_client
    member_id = _seed_user("f2@test.example", totp_enabled=True)
    _set_admin_cookie(c)

    r = c.post(f"/api/admin/users/{member_id}/force-2fa-enrollment")
    assert r.status_code == 409, r.text
    assert r.json()["detail"] == "totp_already_enrolled"

    user = _read_user(member_id)
    assert user.force_2fa_enrollment is False
    assert len(_audit_rows()) == 0


# ---------------------------------------------------------------------------
# F3 — force-enrollment on already-flagged user returns 409
# ---------------------------------------------------------------------------
def test_force_enrollment_already_flagged_returns_409(isolated_client):
    c, _ = isolated_client
    member_id = _seed_user("f3@test.example", force_2fa_enrollment=True)
    _set_admin_cookie(c)

    r = c.post(f"/api/admin/users/{member_id}/force-2fa-enrollment")
    assert r.status_code == 409, r.text
    assert r.json()["detail"] == "already_force_enrolled"

    user = _read_user(member_id)
    assert user.force_2fa_enrollment is True
    assert len(_audit_rows()) == 0


# ---------------------------------------------------------------------------
# F4 — force-enrollment on self returns 400 cannot_target_self
# ---------------------------------------------------------------------------
def test_force_enrollment_self_returns_400_cannot_target_self(isolated_client):
    c, _ = isolated_client
    _set_admin_cookie(c)
    admin_id = _get_admin_id()

    r = c.post(f"/api/admin/users/{admin_id}/force-2fa-enrollment")
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == "cannot_target_self"
    assert len(_audit_rows()) == 0


# ---------------------------------------------------------------------------
# F5 — force-enrollment on agent returns 400 cannot_target_agent
# ---------------------------------------------------------------------------
def test_force_enrollment_agent_returns_400_cannot_target_agent(isolated_client):
    c, _ = isolated_client
    agent_id = _seed_user("f5-agent@test.example", role=UserRole.agent)
    _set_admin_cookie(c)

    r = c.post(f"/api/admin/users/{agent_id}/force-2fa-enrollment")
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == "cannot_target_agent"

    user = _read_user(agent_id)
    assert user.force_2fa_enrollment is False
    assert len(_audit_rows()) == 0


# ---------------------------------------------------------------------------
# F6 — force-disable clears totp + invalidates recovery codes + audits
# ---------------------------------------------------------------------------
def test_force_disable_clears_totp_invalidates_recovery_codes_and_audits_admin_override(
    isolated_client,
):
    c, _ = isolated_client
    member_id = _seed_user("f6@test.example", totp_enabled=True)
    _seed_recovery_codes(member_id, count=3)
    _set_admin_cookie(c)

    pre_user = _read_user(member_id)
    assert pre_user.totp_enabled_at is not None
    assert pre_user.totp_secret is not None

    r = c.post(f"/api/admin/users/{member_id}/force-disable-2fa")
    assert r.status_code == 204, r.text

    user = _read_user(member_id)
    assert user.totp_enabled_at is None
    # Fernet ciphertext is RETAINED per epics §1799.
    assert user.totp_secret is not None
    assert user.totp_secret == pre_user.totp_secret

    codes = _read_recovery_codes(member_id)
    assert len(codes) == 3
    for code in codes:
        assert code.invalidated_at is not None

    rows = _audit_rows()
    assert len(rows) == 1
    ev = rows[0]
    assert ev.action == "auth.totp.disabled"
    assert ev.actor_user_id == _get_admin_id()
    assert ev.entity_id == member_id
    after = json.loads(ev.after_json)
    assert after == {"admin_override": True, "invalidated_count": 3}


# ---------------------------------------------------------------------------
# F7 — force-disable on non-enrolled user returns 409
# ---------------------------------------------------------------------------
def test_force_disable_not_enrolled_returns_409(isolated_client):
    c, _ = isolated_client
    member_id = _seed_user("f7@test.example", totp_enabled=False)
    _set_admin_cookie(c)

    r = c.post(f"/api/admin/users/{member_id}/force-disable-2fa")
    assert r.status_code == 409, r.text
    assert r.json()["detail"] == "totp_not_enrolled"

    user = _read_user(member_id)
    assert user.totp_enabled_at is None
    assert len(_audit_rows()) == 0


# ---------------------------------------------------------------------------
# F8 — force-disable on self returns 400 cannot_target_self
# ---------------------------------------------------------------------------
def test_force_disable_self_returns_400(isolated_client):
    c, _ = isolated_client
    _set_admin_cookie(c)
    admin_id = _get_admin_id()

    r = c.post(f"/api/admin/users/{admin_id}/force-disable-2fa")
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == "cannot_target_self"
    assert len(_audit_rows()) == 0


# ---------------------------------------------------------------------------
# F9 — force-disable on agent returns 400 cannot_target_agent
# ---------------------------------------------------------------------------
def test_force_disable_agent_returns_400(isolated_client):
    c, _ = isolated_client
    # Agent never enrolls — seed with totp_enabled=False. The role guard
    # fires BEFORE the not-enrolled guard per the handler's call order.
    agent_id = _seed_user("f9-agent@test.example", role=UserRole.agent, totp_enabled=False)
    _set_admin_cookie(c)

    r = c.post(f"/api/admin/users/{agent_id}/force-disable-2fa")
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == "cannot_target_agent"
    assert len(_audit_rows()) == 0


# ---------------------------------------------------------------------------
# F10 — force-enrollment as member role returns 403
# ---------------------------------------------------------------------------
def test_force_enrollment_member_role_returns_403(isolated_client):
    c, _ = isolated_client
    target_id = _seed_user("f10-target@test.example")
    member_id = _seed_user("f10-member@test.example")
    c.cookies.set("portal_access", _token_for(member_id, "member"))

    r = c.post(f"/api/admin/users/{target_id}/force-2fa-enrollment")
    assert r.status_code == 403, r.text
    assert len(_audit_rows()) == 0


# ---------------------------------------------------------------------------
# F11 — force-disable as member role returns 403
# ---------------------------------------------------------------------------
def test_force_disable_member_role_returns_403(isolated_client):
    c, _ = isolated_client
    target_id = _seed_user("f11-target@test.example", totp_enabled=True)
    member_id = _seed_user("f11-member@test.example")
    c.cookies.set("portal_access", _token_for(member_id, "member"))

    r = c.post(f"/api/admin/users/{target_id}/force-disable-2fa")
    assert r.status_code == 403, r.text
    assert len(_audit_rows()) == 0


# ---------------------------------------------------------------------------
# F12 — flag auto-clears when target enrolls via /2fa/enroll/confirm
# ---------------------------------------------------------------------------
def test_force_enrollment_flag_cleared_on_subsequent_enrollment_confirm(isolated_client):
    c, _ = isolated_client
    member_id = _seed_user(
        "f12-target@test.example",
        force_2fa_enrollment=True,
        totp_enabled=False,
    )

    # As-member: enroll, then confirm. The flag must auto-clear.
    c.cookies.set("portal_access", _token_for(member_id, "member"))
    r = c.post("/api/auth/2fa/enroll")
    assert r.status_code == 200, r.text
    body = r.json()
    enrollment_token = body["enrollment_token"]
    manual_secret = body["manual_secret"]

    code = pyotp.TOTP(manual_secret).now()
    r2 = c.post(
        "/api/auth/2fa/enroll/confirm",
        json={"enrollment_token": enrollment_token, "code": code},
    )
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    assert len(body2["recovery_codes"]) == 8

    user = _read_user(member_id)
    assert user.force_2fa_enrollment is False
    # Self-enrollment audit row still present with the Story 7.2 payload shape
    # (actor_user_id == entity_id, after.batch_id + after.codes_count).
    enrolled_rows = [r for r in _audit_rows() if r.action == "auth.totp.enrolled"]
    assert len(enrolled_rows) == 1
    ev = enrolled_rows[0]
    assert ev.actor_user_id == member_id
    assert ev.entity_id == member_id
    after = json.loads(ev.after_json)
    assert after["codes_count"] == 8
    assert "batch_id" in after
