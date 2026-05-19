"""Story 7.5 — backend tests for POST /api/auth/2fa/disable.

8 named tests T-DISABLE-1..8; test names are binding cross-references for
the dev-story task list (AC-7). Fixture style mirrors ``test_2fa_verify.py``
(fresh app + SQLite + fakeredis per test).
"""

from __future__ import annotations

import datetime
import json
import uuid
from unittest.mock import MagicMock

import bcrypt
import fakeredis.aioredis
import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.auth.jwt import encode_token
from app.core.config import get_settings
from app.core.db.models import AuditLog, RecoveryCode, User
from app.core.db.models._enums import UserRole
from app.core.db.session import get_engine
from app.main import create_app
from app.modules.auth.totp.service import (
    encrypt_secret,
    generate_recovery_codes_batch,
)

JWT_SECRET = "test-secret-not-real"
FERNET_KEY = "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM="
KNOWN_TOTP_SECRET = "JBSWY3DPEHPK3PXP"
PASSWORD = "Sup3rPassword!"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
    monkeypatch.setenv("TOTP_FERNET_KEY", FERNET_KEY)
    monkeypatch.setenv("COOKIE_SECURE", "false")
    # T-DISABLE-4 needs the post-disable login to take the single-factor
    # path; ensure the test user's role is NOT in enforce_2fa_for_roles.
    monkeypatch.setenv("ENFORCE_2FA_FOR_ROLES", "")

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
        yield c, fake
    get_settings.cache_clear()
    get_engine.cache_clear()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=4)).decode()


def _seed_user_with_totp(
    *,
    role: UserRole = UserRole.member,
    email_prefix: str = "u",
    totp_enabled: bool = True,
) -> User:
    engine = get_engine()
    settings = get_settings()
    with Session(engine) as s:
        u = User(
            email=f"{email_prefix}-{uuid.uuid4().hex[:6]}@example.com",
            display_name=email_prefix,
            role=role,
            password_hash=_hash_password(PASSWORD),
        )
        if totp_enabled:
            u.totp_secret = encrypt_secret(KNOWN_TOTP_SECRET, settings)
            u.totp_enabled_at = datetime.datetime.now(datetime.UTC)
        s.add(u)
        s.commit()
        s.refresh(u)
        return u


def _seed_recovery_batch(user_id: uuid.UUID) -> tuple[uuid.UUID, list[str]]:
    batch_id, pairs = generate_recovery_codes_batch()
    engine = get_engine()
    now = datetime.datetime.now(datetime.UTC)
    with Session(engine) as s:
        for _cleartext, code_hash in pairs:
            s.add(
                RecoveryCode(
                    user_id=user_id,
                    code_hash=code_hash,
                    batch_id=batch_id,
                    generated_at=now,
                )
            )
        s.commit()
    return batch_id, [cleartext for cleartext, _h in pairs]


def _login_as(c: TestClient, user: User) -> None:
    token = encode_token(
        subject=str(user.id),
        role=user.role.value,
        secret=JWT_SECRET,
        ttl_minutes=30,
    )
    c.cookies.set("portal_access", token, path="/api")


def _audit_rows(action: str, user_id: uuid.UUID | None = None) -> list[AuditLog]:
    engine = get_engine()
    with Session(engine) as s:
        stmt = select(AuditLog).where(AuditLog.action == action)
        if user_id is not None:
            stmt = stmt.where(AuditLog.actor_user_id == user_id)
        return list(s.exec(stmt).all())


def _now_code() -> str:
    return pyotp.TOTP(KNOWN_TOTP_SECRET).now()


def _reread_user(user_id: uuid.UUID) -> User:
    engine = get_engine()
    with Session(engine) as s:
        u = s.get(User, user_id)
    assert u is not None
    return u


# ---------------------------------------------------------------------------
# T-DISABLE-1..8
# ---------------------------------------------------------------------------


def test_disable_with_valid_password_and_totp_clears_totp_enabled_at_returns_204(client):
    c, _fake = client
    user = _seed_user_with_totp(email_prefix="dis")
    _seed_recovery_batch(user.id)
    _login_as(c, user)

    r = c.post(
        "/api/auth/2fa/disable",
        json={"password": PASSWORD, "totp_code": _now_code()},
    )
    assert r.status_code == 204, r.text
    assert r.content == b""

    refreshed = _reread_user(user.id)
    assert refreshed.totp_enabled_at is None


def test_disable_retains_users_totp_secret_fernet_ciphertext(client):
    c, _fake = client
    user = _seed_user_with_totp(email_prefix="dis-retain")
    _seed_recovery_batch(user.id)
    snapshot = _reread_user(user.id).totp_secret
    assert snapshot is not None
    _login_as(c, user)

    r = c.post(
        "/api/auth/2fa/disable",
        json={"password": PASSWORD, "totp_code": _now_code()},
    )
    assert r.status_code == 204, r.text

    refreshed = _reread_user(user.id)
    # epics §1719 retention rule — the Fernet ciphertext column stays
    # byte-identical so future re-enrollment with the same authenticator app
    # is possible without secret rotation.
    assert refreshed.totp_secret == snapshot


def test_disable_invalidates_all_active_recovery_codes(client):
    c, _fake = client
    user = _seed_user_with_totp(email_prefix="dis-invalidate")
    _seed_recovery_batch(user.id)
    _login_as(c, user)

    r = c.post(
        "/api/auth/2fa/disable",
        json={"password": PASSWORD, "totp_code": _now_code()},
    )
    assert r.status_code == 204, r.text

    engine = get_engine()
    with Session(engine) as s:
        rows = list(s.exec(select(RecoveryCode).where(RecoveryCode.user_id == user.id)).all())
    assert len(rows) == 8
    assert all(row.invalidated_at is not None for row in rows)


def test_disable_post_state_login_returns_normal_login_response_not_partial_auth(client):
    c, _fake = client
    user = _seed_user_with_totp(email_prefix="dis-login")
    _seed_recovery_batch(user.id)
    _login_as(c, user)

    r = c.post(
        "/api/auth/2fa/disable",
        json={"password": PASSWORD, "totp_code": _now_code()},
    )
    assert r.status_code == 204, r.text

    # Fresh login after disable should take the single-factor path.
    c.cookies.clear()
    r2 = c.post(
        "/api/auth/login",
        json={"email": user.email, "password": PASSWORD},
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["partial_auth"] is False
    assert body.get("totp_enroll_required") in (None, False)
    assert body["user"]["id"] == str(user.id)


def test_disable_emits_auth_totp_disabled_audit_row_with_invalidated_count(client):
    c, _fake = client
    user = _seed_user_with_totp(email_prefix="dis-audit")
    _seed_recovery_batch(user.id)
    _login_as(c, user)

    r = c.post(
        "/api/auth/2fa/disable",
        json={"password": PASSWORD, "totp_code": _now_code()},
    )
    assert r.status_code == 204, r.text

    rows = _audit_rows("auth.totp.disabled", user_id=user.id)
    assert len(rows) == 1
    row = rows[0]
    assert row.entity_type == "user"
    assert row.entity_id == user.id
    assert row.actor_user_id == user.id
    payload = json.loads(row.after_json)
    assert payload == {"invalidated_count": 8}


def test_disable_wrong_password_returns_401_emits_verify_fail_audit_no_state_mutation(client):
    c, _fake = client
    user = _seed_user_with_totp(email_prefix="dis-pw")
    _seed_recovery_batch(user.id)
    _login_as(c, user)
    snapshot_secret = _reread_user(user.id).totp_secret
    snapshot_enabled_at = _reread_user(user.id).totp_enabled_at

    r = c.post(
        "/api/auth/2fa/disable",
        json={"password": "wrong-pw", "totp_code": _now_code()},
    )
    assert r.status_code == 401, r.text
    assert r.json()["detail"] == "invalid_credentials"

    assert _audit_rows("auth.totp.disabled", user_id=user.id) == []
    fail_rows = _audit_rows("auth.totp.verify.fail", user_id=user.id)
    assert len(fail_rows) == 1
    payload = json.loads(fail_rows[0].after_json)
    assert payload == {"method": "disable_reauth", "reason": "password"}

    # No state mutation — totp_enabled_at + totp_secret unchanged + codes
    # remain active.
    refreshed = _reread_user(user.id)
    assert refreshed.totp_enabled_at == snapshot_enabled_at
    assert refreshed.totp_secret == snapshot_secret
    engine = get_engine()
    with Session(engine) as s:
        active = list(
            s.exec(
                select(RecoveryCode)
                .where(RecoveryCode.user_id == user.id)
                .where(RecoveryCode.invalidated_at.is_(None))
            ).all()
        )
    assert len(active) == 8


def test_disable_with_recovery_code_in_totp_code_field_returns_422_pydantic(client):
    c, _fake = client
    user = _seed_user_with_totp(email_prefix="dis-rcshape")
    _seed_recovery_batch(user.id)
    _login_as(c, user)

    r = c.post(
        "/api/auth/2fa/disable",
        json={"password": PASSWORD, "totp_code": "deadbeef"},
    )
    assert r.status_code == 422, r.text
    assert _audit_rows("auth.totp.disabled", user_id=user.id) == []


def test_disable_shares_login_ratelimit_budget_429_at_6th_attempt_across_login_verify_disable(
    client,
):
    c, _fake = client
    user = _seed_user_with_totp(email_prefix="dis-rl")
    _seed_recovery_batch(user.id)
    _login_as(c, user)

    # 3 failed login attempts (wrong password) -> count 1..3.
    for _ in range(3):
        r = c.post(
            "/api/auth/login",
            json={"email": user.email, "password": "wrong-pw"},
        )
        assert r.status_code == 401, r.text

    # 2 failed disable attempts (wrong password) -> count 4..5.
    for _ in range(2):
        r = c.post(
            "/api/auth/2fa/disable",
            json={"password": "wrong-pw", "totp_code": _now_code()},
        )
        assert r.status_code == 401, r.text

    # 6th attempt -> 429.
    r6 = c.post(
        "/api/auth/2fa/disable",
        json={"password": "wrong-pw", "totp_code": _now_code()},
    )
    assert r6.status_code == 429, r6.text
    body = r6.json()
    assert body["scope"] == "login"
