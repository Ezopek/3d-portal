"""Story 7.3 — backend tests for POST /api/auth/2fa/verify + login partial-auth.

18 named tests T1-T18 — names are binding cross-references for the dev-story
task list (AC-11). Fixture style mirrors ``test_2fa_enrollment.py`` (fresh
app + SQLite + fakeredis per test).
"""

from __future__ import annotations

import asyncio
import datetime
import json
import secrets
import uuid
from unittest.mock import MagicMock

import bcrypt
import fakeredis.aioredis
import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.db.models import AuditLog, RecoveryCode, RefreshToken, User
from app.core.db.models._enums import UserRole
from app.core.db.session import get_engine
from app.main import create_app
from app.modules.auth.totp.service import (
    encrypt_secret,
    generate_recovery_codes_batch,
)

JWT_SECRET = "test-secret-not-real"
FERNET_KEY = "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM="
KNOWN_TOTP_SECRET = "JBSWY3DPEHPK3PXP"  # canonical pyotp docs example


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Fresh app + DB + fakeredis per test."""
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


PASSWORD = "Sup3rPassword!"


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=4)).decode()


def _seed_user_no_totp(*, email_prefix: str = "u") -> User:
    engine = get_engine()
    with Session(engine) as s:
        u = User(
            email=f"{email_prefix}-{uuid.uuid4().hex[:6]}@example.com",
            display_name=email_prefix,
            role=UserRole.member,
            password_hash=_hash_password(PASSWORD),
        )
        s.add(u)
        s.commit()
        s.refresh(u)
        return u


def _seed_user_with_totp(
    *,
    email_prefix: str = "u",
    role: UserRole = UserRole.member,
    secret: str = KNOWN_TOTP_SECRET,
) -> User:
    engine = get_engine()
    settings = get_settings()
    with Session(engine) as s:
        u = User(
            email=f"{email_prefix}-{uuid.uuid4().hex[:6]}@example.com",
            display_name=email_prefix,
            role=role,
            password_hash=_hash_password(PASSWORD),
            totp_secret=encrypt_secret(secret, settings),
            totp_enabled_at=datetime.datetime.now(datetime.UTC),
        )
        s.add(u)
        s.commit()
        s.refresh(u)
        return u


def _seed_recovery_batch(user_id: uuid.UUID) -> tuple[uuid.UUID, list[str]]:
    """Mint + INSERT 8 recovery codes for ``user_id``; return cleartext list."""
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


def _stash_partial(fake, user_id: uuid.UUID, *, ttl: int = 300) -> str:
    """Pre-write a partial_token into fakeredis; return the token."""
    token = secrets.token_urlsafe(32)
    payload = json.dumps({"user_id": str(user_id), "ip": "", "ua": ""})

    async def _do():
        await fake.set(f"totp:partial:{token}", payload.encode(), ex=ttl)

    asyncio.get_event_loop().run_until_complete(_do()) if False else None
    # Use the TestClient portal to run async correctly under the running loop.
    return token


def _portal_run(c: TestClient, coro_fn):
    return c.portal.call(coro_fn)


def _redis_set_partial(c: TestClient, fake, user_id: uuid.UUID, *, ttl: int = 300) -> str:
    token = secrets.token_urlsafe(32)
    payload = json.dumps({"user_id": str(user_id), "ip": "", "ua": ""})

    async def _do():
        await fake.set(f"totp:partial:{token}", payload.encode(), ex=ttl)

    _portal_run(c, _do)
    return token


def _redis_get_partial(c: TestClient, fake, token: str):
    async def _do():
        return await fake.get(f"totp:partial:{token}")

    return _portal_run(c, _do)


def _redis_ttl_partial(c: TestClient, fake, token: str) -> int:
    async def _do():
        return await fake.ttl(f"totp:partial:{token}")

    return _portal_run(c, _do)


def _audit_rows(action: str, user_id: uuid.UUID | None = None) -> list[AuditLog]:
    engine = get_engine()
    with Session(engine) as s:
        stmt = select(AuditLog).where(AuditLog.action == action)
        if user_id is not None:
            stmt = stmt.where(AuditLog.actor_user_id == user_id)
        return list(s.exec(stmt).all())


def _refresh_count(user_id: uuid.UUID) -> int:
    engine = get_engine()
    with Session(engine) as s:
        return len(list(s.exec(select(RefreshToken).where(RefreshToken.user_id == user_id)).all()))


# ---------------------------------------------------------------------------
# T1-T5 — POST /api/auth/login partial-auth branch
# ---------------------------------------------------------------------------


def test_login_with_totp_enabled_returns_partial_auth_no_cookies(client):
    c, _fake = client
    user = _seed_user_with_totp(email_prefix="enrolled")
    r = c.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body == {
        "partial_auth": True,
        "totp_required": True,
        "partial_token": body["partial_token"],
    }
    assert isinstance(body["partial_token"], str)
    assert len(body["partial_token"]) >= 20
    # No session cookies set on the partial-auth branch.
    assert "portal_access" not in r.cookies
    assert "portal_refresh" not in r.cookies


def test_login_partial_auth_does_not_emit_auth_login_success_audit_row(client):
    c, _fake = client
    user = _seed_user_with_totp(email_prefix="enrolled")
    r = c.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
    assert r.status_code == 200
    rows = _audit_rows("auth.login.success", user_id=user.id)
    assert rows == []


def test_login_partial_auth_stashes_redis_payload_with_user_id_ttl_300(client):
    c, fake = client
    user = _seed_user_with_totp(email_prefix="enrolled")
    r = c.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
    assert r.status_code == 200
    token = r.json()["partial_token"]
    raw = _redis_get_partial(c, fake, token)
    assert raw is not None
    payload = json.loads(raw)
    assert payload["user_id"] == str(user.id)
    assert "ip" in payload
    assert "ua" in payload
    ttl = _redis_ttl_partial(c, fake, token)
    assert 295 <= ttl <= 300


def test_login_partial_auth_does_not_create_refresh_token_row(client):
    c, _fake = client
    user = _seed_user_with_totp(email_prefix="enrolled")
    r = c.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
    assert r.status_code == 200
    assert _refresh_count(user.id) == 0


def test_login_single_factor_path_unchanged_for_user_without_totp_enabled(client):
    c, _fake = client
    user = _seed_user_no_totp(email_prefix="plain")
    r = c.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["partial_auth"] is False
    assert body["user"]["id"] == str(user.id)
    assert body["user"]["email"] == user.email
    # Cookies are set; refresh row exists; audit success row emitted.
    assert "portal_access" in r.cookies
    assert "portal_refresh" in r.cookies
    assert _refresh_count(user.id) == 1
    assert len(_audit_rows("auth.login.success", user_id=user.id)) == 1


# ---------------------------------------------------------------------------
# T6-T10 — POST /api/auth/2fa/verify success paths
# ---------------------------------------------------------------------------


def test_verify_with_correct_totp_returns_login_response_sets_cookies(client):
    c, fake = client
    user = _seed_user_with_totp(email_prefix="totp")
    token = _redis_set_partial(c, fake, user.id)
    code = pyotp.TOTP(KNOWN_TOTP_SECRET).now()
    r = c.post(
        "/api/auth/2fa/verify",
        json={"partial_token": token, "code": code},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["partial_auth"] is False
    assert body["user"]["id"] == str(user.id)
    assert "portal_access" in r.cookies
    assert "portal_refresh" in r.cookies
    assert _refresh_count(user.id) == 1


def test_verify_with_correct_totp_emits_auth_totp_verify_success_audit_row(client):
    c, fake = client
    user = _seed_user_with_totp(email_prefix="totp")
    token = _redis_set_partial(c, fake, user.id)
    code = pyotp.TOTP(KNOWN_TOTP_SECRET).now()
    r = c.post("/api/auth/2fa/verify", json={"partial_token": token, "code": code})
    assert r.status_code == 200
    success_rows = _audit_rows("auth.totp.verify.success", user_id=user.id)
    assert len(success_rows) == 1
    row = success_rows[0]
    assert row.entity_type == "user"
    assert row.entity_id == user.id
    assert row.actor_user_id == user.id
    payload = json.loads(row.after_json)
    assert payload == {"method": "totp"}
    # NO recovery_code.used row, NO login.success row.
    assert _audit_rows("auth.recovery_code.used", user_id=user.id) == []
    assert _audit_rows("auth.login.success", user_id=user.id) == []


def test_verify_with_correct_totp_deletes_partial_token_from_redis(client):
    c, fake = client
    user = _seed_user_with_totp(email_prefix="totp")
    token = _redis_set_partial(c, fake, user.id)
    code = pyotp.TOTP(KNOWN_TOTP_SECRET).now()
    r = c.post("/api/auth/2fa/verify", json={"partial_token": token, "code": code})
    assert r.status_code == 200
    assert _redis_get_partial(c, fake, token) is None


def test_verify_with_correct_recovery_code_consumes_row_sets_used_at(client):
    c, fake = client
    user = _seed_user_with_totp(email_prefix="rec")
    _batch_id, cleartext_codes = _seed_recovery_batch(user.id)
    token = _redis_set_partial(c, fake, user.id)
    # Use the 2nd cleartext code in the batch.
    pick = cleartext_codes[1]
    r = c.post("/api/auth/2fa/verify", json={"partial_token": token, "code": pick})
    assert r.status_code == 200, r.text

    engine = get_engine()
    with Session(engine) as s:
        used = list(
            s.exec(
                select(RecoveryCode)
                .where(RecoveryCode.user_id == user.id)
                .where(RecoveryCode.used_at.is_not(None))
            ).all()
        )
    assert len(used) == 1
    # The consumed row matches the cleartext we submitted.
    assert bcrypt.checkpw(pick.encode(), used[0].code_hash.encode())
    delta = abs((datetime.datetime.now(datetime.UTC) - used[0].used_at).total_seconds())
    assert delta < 10


def test_verify_with_correct_recovery_code_emits_two_audit_rows_recovery_code_used_then_totp_verify_success(  # noqa: E501
    client,
):
    c, fake = client
    user = _seed_user_with_totp(email_prefix="rec")
    batch_id, cleartext_codes = _seed_recovery_batch(user.id)
    token = _redis_set_partial(c, fake, user.id)
    pick = cleartext_codes[0]
    r = c.post("/api/auth/2fa/verify", json={"partial_token": token, "code": pick})
    assert r.status_code == 200, r.text

    used_rows = _audit_rows("auth.recovery_code.used", user_id=user.id)
    assert len(used_rows) == 1
    used_row = used_rows[0]
    assert used_row.entity_type == "recovery_code"
    assert used_row.actor_user_id == user.id
    payload = json.loads(used_row.after_json)
    assert payload["batch_id"] == str(batch_id)
    assert "used_at" in payload
    # Cleartext code MUST NOT leak into the audit row.
    assert pick not in (used_row.after_json or "")

    success_rows = _audit_rows("auth.totp.verify.success", user_id=user.id)
    assert len(success_rows) == 1
    success_payload = json.loads(success_rows[0].after_json)
    assert success_payload == {"method": "recovery_code"}


# ---------------------------------------------------------------------------
# T11-T17 — failure + race paths
# ---------------------------------------------------------------------------


def test_verify_with_consumed_recovery_code_returns_401_invalid_code(client):
    c, fake = client
    user = _seed_user_with_totp(email_prefix="rec")
    _batch_id, cleartext_codes = _seed_recovery_batch(user.id)
    pick = cleartext_codes[2]
    # Pre-mark the row used directly via DB.
    engine = get_engine()
    with Session(engine) as s:
        rows = list(s.exec(select(RecoveryCode).where(RecoveryCode.user_id == user.id)).all())
        for row in rows:
            if bcrypt.checkpw(pick.encode(), row.code_hash.encode()):
                row.used_at = datetime.datetime.now(datetime.UTC)
                s.add(row)
                break
        s.commit()
    token = _redis_set_partial(c, fake, user.id)
    r = c.post("/api/auth/2fa/verify", json={"partial_token": token, "code": pick})
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid_code"


def test_verify_with_invalidated_recovery_code_returns_401_invalid_code(client):
    c, fake = client
    user = _seed_user_with_totp(email_prefix="rec")
    _batch_id, cleartext_codes = _seed_recovery_batch(user.id)
    pick = cleartext_codes[3]
    engine = get_engine()
    with Session(engine) as s:
        rows = list(s.exec(select(RecoveryCode).where(RecoveryCode.user_id == user.id)).all())
        for row in rows:
            if bcrypt.checkpw(pick.encode(), row.code_hash.encode()):
                row.invalidated_at = datetime.datetime.now(datetime.UTC)
                s.add(row)
                break
        s.commit()
    token = _redis_set_partial(c, fake, user.id)
    r = c.post("/api/auth/2fa/verify", json={"partial_token": token, "code": pick})
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid_code"


def test_verify_with_wrong_totp_code_returns_401_emits_fail_audit_no_token_consumption(client):
    c, fake = client
    user = _seed_user_with_totp(email_prefix="totp")
    token = _redis_set_partial(c, fake, user.id)
    real = pyotp.TOTP(KNOWN_TOTP_SECRET).now()
    wrong = "000000" if real != "000000" else "111111"
    r = c.post("/api/auth/2fa/verify", json={"partial_token": token, "code": wrong})
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid_code"

    fail_rows = _audit_rows("auth.totp.verify.fail", user_id=user.id)
    assert len(fail_rows) == 1
    payload = json.loads(fail_rows[0].after_json)
    assert payload == {"method": "totp"}
    # Partial token still in Redis (not consumed on failure).
    assert _redis_get_partial(c, fake, token) is not None
    assert _refresh_count(user.id) == 0


def test_verify_with_wrong_recovery_code_returns_401_emits_fail_audit_no_token_consumption(client):
    c, fake = client
    user = _seed_user_with_totp(email_prefix="rec")
    _seed_recovery_batch(user.id)
    token = _redis_set_partial(c, fake, user.id)
    # 8-char lowercase hex that is NOT in the batch (random fresh).
    bogus = "deadbeef"
    r = c.post("/api/auth/2fa/verify", json={"partial_token": token, "code": bogus})
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid_code"

    fail_rows = _audit_rows("auth.totp.verify.fail", user_id=user.id)
    assert len(fail_rows) == 1
    payload = json.loads(fail_rows[0].after_json)
    assert payload == {"method": "recovery_code"}
    assert _redis_get_partial(c, fake, token) is not None
    # No recovery_codes row mutated.
    engine = get_engine()
    with Session(engine) as s:
        used = list(
            s.exec(
                select(RecoveryCode)
                .where(RecoveryCode.user_id == user.id)
                .where(RecoveryCode.used_at.is_not(None))
            ).all()
        )
    assert used == []


def test_verify_with_malformed_code_returns_422_pydantic_validation(client):
    c, fake = client
    user = _seed_user_with_totp(email_prefix="totp")
    token = _redis_set_partial(c, fake, user.id)
    r = c.post("/api/auth/2fa/verify", json={"partial_token": token, "code": "abc"})
    assert r.status_code == 422
    assert _audit_rows("auth.totp.verify.fail", user_id=user.id) == []
    assert _audit_rows("auth.totp.verify.success", user_id=user.id) == []


def test_verify_with_expired_partial_token_returns_401_partial_token_invalid(client):
    c, fake = client
    user = _seed_user_with_totp(email_prefix="totp")
    token = _redis_set_partial(c, fake, user.id, ttl=1)
    # Fakeredis honours TTL via monotonic clock; sleep past expiry.

    async def _wait():
        await asyncio.sleep(1.5)

    _portal_run(c, _wait)
    code = pyotp.TOTP(KNOWN_TOTP_SECRET).now()
    r = c.post("/api/auth/2fa/verify", json={"partial_token": token, "code": code})
    assert r.status_code == 401
    assert r.json()["detail"] == "partial_token_invalid"
    # No audit emission for the no-safe-attribution branch.
    assert _audit_rows("auth.totp.verify.fail", user_id=user.id) == []


def test_verify_with_user_disabled_totp_between_step1_and_step2_returns_401(client):
    c, fake = client
    user = _seed_user_with_totp(email_prefix="totp")
    token = _redis_set_partial(c, fake, user.id)
    # Simulate admin-disable race: flip totp_enabled_at to None.
    engine = get_engine()
    with Session(engine) as s:
        db_user = s.get(User, user.id)
        db_user.totp_enabled_at = None
        s.add(db_user)
        s.commit()
    code = pyotp.TOTP(KNOWN_TOTP_SECRET).now()
    r = c.post("/api/auth/2fa/verify", json={"partial_token": token, "code": code})
    assert r.status_code == 401
    assert r.json()["detail"] == "partial_token_invalid"


# ---------------------------------------------------------------------------
# T18 — shared rate-limit budget
# ---------------------------------------------------------------------------


def test_ratelimit_shared_budget_login_plus_verify_hits_429_at_6th_attempt(client):
    c, fake = client
    user = _seed_user_with_totp(email_prefix="rl")
    # 4 wrong-password POSTs to /login → each 401, count 1..4.
    for _ in range(4):
        r = c.post(
            "/api/auth/login",
            json={"email": user.email, "password": "wrong-pw"},
        )
        assert r.status_code == 401, r.text
    # 1 wrong-code verify POST → 401, count = 5.
    token = _redis_set_partial(c, fake, user.id)
    r5 = c.post(
        "/api/auth/2fa/verify",
        json={"partial_token": token, "code": "000000"},
    )
    assert r5.status_code == 401, r5.text
    # 6th attempt — whether login or verify — must trip the shared budget.
    r6 = c.post(
        "/api/auth/login",
        json={"email": user.email, "password": "wrong-pw"},
    )
    assert r6.status_code == 429, r6.text
    body = r6.json()
    assert body["scope"] == "login"
    assert "Retry-After" in r6.headers
