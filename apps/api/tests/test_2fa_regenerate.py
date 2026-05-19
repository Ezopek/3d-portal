"""Story 7.5 — backend tests for POST /api/auth/2fa/recovery-codes/regenerate.

9 named tests T-REGEN-1..9; test names are binding cross-references for the
dev-story task list (AC-7). Fixture style mirrors ``test_2fa_verify.py``
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


def _count_recovery(user_id: uuid.UUID) -> tuple[int, int, int]:
    """Return (total, active, invalidated) recovery_codes for the user."""
    engine = get_engine()
    with Session(engine) as s:
        rows = list(s.exec(select(RecoveryCode).where(RecoveryCode.user_id == user_id)).all())
    active = sum(1 for r in rows if r.invalidated_at is None and r.used_at is None)
    invalidated = sum(1 for r in rows if r.invalidated_at is not None)
    return len(rows), active, invalidated


# ---------------------------------------------------------------------------
# T-REGEN-1..9
# ---------------------------------------------------------------------------


def test_regenerate_with_valid_password_and_totp_invalidates_prior_batch_returns_8_new_codes(
    client,
):
    c, _fake = client
    user = _seed_user_with_totp(email_prefix="regen")
    old_batch_id, _ = _seed_recovery_batch(user.id)
    _login_as(c, user)

    r = c.post(
        "/api/auth/2fa/recovery-codes/regenerate",
        json={"password": PASSWORD, "totp_code": _now_code()},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["recovery_codes"]) == 8
    assert all(len(c) == 8 for c in body["recovery_codes"])
    new_batch_id = uuid.UUID(body["batch_id"])
    assert new_batch_id != old_batch_id

    # All old rows now invalidated; 8 fresh rows exist for the new batch.
    engine = get_engine()
    with Session(engine) as s:
        old_rows = list(
            s.exec(
                select(RecoveryCode)
                .where(RecoveryCode.user_id == user.id)
                .where(RecoveryCode.batch_id == old_batch_id)
            ).all()
        )
        new_rows = list(
            s.exec(
                select(RecoveryCode)
                .where(RecoveryCode.user_id == user.id)
                .where(RecoveryCode.batch_id == new_batch_id)
            ).all()
        )
    assert len(old_rows) == 8
    assert all(row.invalidated_at is not None for row in old_rows)
    assert len(new_rows) == 8
    assert all(row.invalidated_at is None and row.used_at is None for row in new_rows)


def test_regenerate_emits_auth_recovery_codes_regenerated_audit_row_with_invalidated_count(client):
    c, _fake = client
    user = _seed_user_with_totp(email_prefix="regen-audit")
    _seed_recovery_batch(user.id)
    _login_as(c, user)

    r = c.post(
        "/api/auth/2fa/recovery-codes/regenerate",
        json={"password": PASSWORD, "totp_code": _now_code()},
    )
    assert r.status_code == 200, r.text
    new_batch_id = r.json()["batch_id"]

    rows = _audit_rows("auth.recovery_codes.regenerated", user_id=user.id)
    assert len(rows) == 1
    row = rows[0]
    assert row.entity_type == "user"
    assert row.entity_id == user.id
    assert row.actor_user_id == user.id
    payload = json.loads(row.after_json)
    assert payload == {
        "batch_id": new_batch_id,
        "codes_count": 8,
        "invalidated_count": 8,
    }


def test_regenerate_after_partial_consumption_invalidated_count_reflects_active_only(client):
    c, _fake = client
    user = _seed_user_with_totp(email_prefix="regen-partial")
    _batch_id, cleartext_codes = _seed_recovery_batch(user.id)
    _login_as(c, user)

    # Mark 3 codes as already used (used_at set, invalidated_at still NULL).
    engine = get_engine()
    used_at = datetime.datetime.now(datetime.UTC)
    with Session(engine) as s:
        rows = list(s.exec(select(RecoveryCode).where(RecoveryCode.user_id == user.id)).all())
        for code in cleartext_codes[:3]:
            for row in rows:
                if bcrypt.checkpw(code.encode(), row.code_hash.encode()):
                    row.used_at = used_at
                    s.add(row)
                    break
        s.commit()

    r = c.post(
        "/api/auth/2fa/recovery-codes/regenerate",
        json={"password": PASSWORD, "totp_code": _now_code()},
    )
    assert r.status_code == 200, r.text

    rows = _audit_rows("auth.recovery_codes.regenerated", user_id=user.id)
    assert len(rows) == 1
    payload = json.loads(rows[0].after_json)
    assert payload["invalidated_count"] == 5

    # The 3 consumed rows keep used_at IS NOT NULL AND invalidated_at IS NULL.
    with Session(engine) as s:
        rows = list(
            s.exec(
                select(RecoveryCode)
                .where(RecoveryCode.user_id == user.id)
                .where(RecoveryCode.used_at.is_not(None))
            ).all()
        )
    assert len(rows) == 3
    assert all(r.invalidated_at is None for r in rows)


def test_regenerate_wrong_password_returns_401_emits_verify_fail_audit_no_state_mutation(client):
    c, _fake = client
    user = _seed_user_with_totp(email_prefix="regen-pw")
    _batch_id, _ = _seed_recovery_batch(user.id)
    _login_as(c, user)
    total_before, active_before, _ = _count_recovery(user.id)

    r = c.post(
        "/api/auth/2fa/recovery-codes/regenerate",
        json={"password": "wrong-pw", "totp_code": _now_code()},
    )
    assert r.status_code == 401, r.text
    assert r.json()["detail"] == "invalid_credentials"

    assert _audit_rows("auth.recovery_codes.regenerated", user_id=user.id) == []
    fail_rows = _audit_rows("auth.totp.verify.fail", user_id=user.id)
    assert len(fail_rows) == 1
    payload = json.loads(fail_rows[0].after_json)
    assert payload == {"method": "regenerate_reauth", "reason": "password"}

    total_after, active_after, _ = _count_recovery(user.id)
    assert total_after == total_before
    assert active_after == active_before


def test_regenerate_wrong_totp_returns_401_emits_verify_fail_audit_no_state_mutation(client):
    c, _fake = client
    user = _seed_user_with_totp(email_prefix="regen-totp")
    _seed_recovery_batch(user.id)
    _login_as(c, user)
    total_before, active_before, _ = _count_recovery(user.id)

    real = _now_code()
    wrong = "000000" if real != "000000" else "111111"
    r = c.post(
        "/api/auth/2fa/recovery-codes/regenerate",
        json={"password": PASSWORD, "totp_code": wrong},
    )
    assert r.status_code == 401, r.text
    assert r.json()["detail"] == "invalid_credentials"

    assert _audit_rows("auth.recovery_codes.regenerated", user_id=user.id) == []
    fail_rows = _audit_rows("auth.totp.verify.fail", user_id=user.id)
    assert len(fail_rows) == 1
    payload = json.loads(fail_rows[0].after_json)
    assert payload == {"method": "regenerate_reauth", "reason": "totp"}

    total_after, active_after, _ = _count_recovery(user.id)
    assert total_after == total_before
    assert active_after == active_before


def test_regenerate_agent_role_returns_403(client):
    c, _fake = client
    user = _seed_user_with_totp(role=UserRole.agent, email_prefix="agent", totp_enabled=True)
    _login_as(c, user)

    r = c.post(
        "/api/auth/2fa/recovery-codes/regenerate",
        json={"password": PASSWORD, "totp_code": _now_code()},
    )
    assert r.status_code == 403, r.text
    assert r.json()["detail"] == "agent_role_forbidden"


def test_regenerate_with_recovery_code_in_totp_code_field_returns_422_pydantic(client):
    c, _fake = client
    user = _seed_user_with_totp(email_prefix="regen-rcshape")
    _seed_recovery_batch(user.id)
    _login_as(c, user)

    r = c.post(
        "/api/auth/2fa/recovery-codes/regenerate",
        json={"password": PASSWORD, "totp_code": "deadbeef"},
    )
    assert r.status_code == 422, r.text
    assert _audit_rows("auth.recovery_codes.regenerated", user_id=user.id) == []


def test_regenerate_not_enrolled_returns_409_totp_not_enrolled(client):
    c, _fake = client
    user = _seed_user_with_totp(email_prefix="regen-noten", totp_enabled=False)
    _login_as(c, user)

    r = c.post(
        "/api/auth/2fa/recovery-codes/regenerate",
        json={"password": PASSWORD, "totp_code": "123456"},
    )
    assert r.status_code == 409, r.text
    assert r.json()["detail"] == "totp_not_enrolled"


def test_regenerate_shares_login_ratelimit_budget_429_at_6th_attempt_across_login_verify_regenerate(
    client,
):
    c, _fake = client
    user = _seed_user_with_totp(email_prefix="regen-rl")
    _seed_recovery_batch(user.id)
    _login_as(c, user)

    # 3 failed login attempts (wrong password) -> count 1..3.
    for _ in range(3):
        r = c.post(
            "/api/auth/login",
            json={"email": user.email, "password": "wrong-pw"},
        )
        # Login returns 401 with partial-auth gated behind correct password.
        assert r.status_code == 401, r.text

    # 2 failed regenerate attempts (wrong password) -> count 4..5.
    for _ in range(2):
        r = c.post(
            "/api/auth/2fa/recovery-codes/regenerate",
            json={"password": "wrong-pw", "totp_code": _now_code()},
        )
        assert r.status_code == 401, r.text

    # 6th attempt must trip the shared budget.
    r6 = c.post(
        "/api/auth/2fa/recovery-codes/regenerate",
        json={"password": "wrong-pw", "totp_code": _now_code()},
    )
    assert r6.status_code == 429, r6.text
    body = r6.json()
    assert body["scope"] == "login"
