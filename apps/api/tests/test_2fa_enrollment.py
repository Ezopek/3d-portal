"""Story 7.2 — backend tests for TOTP enrollment endpoints + service helpers.

Covers AC-3 through AC-7 + AC-12 verbatim. 18 named tests T1-T18 — the
names are binding cross-references for the dev-story task list.

Fixture style mirrors ``test_share_admin.py`` (per-test fresh SQLite +
fakeredis swap into ``app.state.redis``) so the session-scoped
``_isolated_db`` from conftest does not bleed audit rows / user table
state across tests.
"""

from __future__ import annotations

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
    Settings2faService,
    decrypt_secret,
    encrypt_secret,
    generate_recovery_codes_batch,
)

JWT_SECRET = "test-secret-not-real"
FERNET_KEY = "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM="


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


def _seed_user(
    *,
    role: UserRole = UserRole.member,
    email_prefix: str = "u",
    totp_enabled: bool = False,
) -> User:
    engine = get_engine()
    with Session(engine) as s:
        u = User(
            email=f"{email_prefix}-{uuid.uuid4().hex[:6]}@test.local",
            display_name=email_prefix,
            role=role,
            password_hash="x",
        )
        if totp_enabled:
            import datetime as _dt

            u.totp_secret = encrypt_secret("JBSWY3DPEHPK3PXP", get_settings())
            u.totp_enabled_at = _dt.datetime.now(_dt.UTC)
        s.add(u)
        s.commit()
        s.refresh(u)
        return u


def _login_as(c: TestClient, user: User) -> None:
    token = encode_token(
        subject=str(user.id),
        role=user.role.value,
        secret=JWT_SECRET,
        ttl_minutes=30,
    )
    c.cookies.set("portal_access", token, path="/api")


def _redis_get(c: TestClient, fake, key: str):
    async def _do():
        return await fake.get(key)

    return c.portal.call(_do)


def _redis_ttl(c: TestClient, fake, key: str):
    async def _do():
        return await fake.ttl(key)

    return c.portal.call(_do)


def _enroll_and_get_token(c: TestClient, fake, user: User) -> tuple[str, str]:
    """POST /api/auth/2fa/enroll for the given user; return (token, secret)."""
    _login_as(c, user)
    r = c.post("/api/auth/2fa/enroll")
    assert r.status_code == 200, r.text
    body = r.json()
    token = body["enrollment_token"]
    secret = body["manual_secret"]
    return token, secret


# ---------------------------------------------------------------------------
# T1-T6 — POST /2fa/enroll behaviour
# ---------------------------------------------------------------------------


def test_enroll_requires_auth(client):
    c, _ = client
    r = c.post("/api/auth/2fa/enroll")
    assert r.status_code == 401
    assert r.json()["detail"] == "missing_access"


def test_enroll_forbidden_for_agent_role(client):
    c, fake = client
    agent = _seed_user(role=UserRole.agent, email_prefix="agent")
    _login_as(c, agent)
    r = c.post("/api/auth/2fa/enroll")
    assert r.status_code == 403
    assert r.json()["detail"] == "agent_role_forbidden"

    async def _scan():
        keys = []
        async for k in fake.scan_iter(match="totp:enroll:*"):
            keys.append(k)
        return keys

    assert c.portal.call(_scan) == []


def test_enroll_returns_qr_svg_manual_secret_token(client):
    c, _ = client
    user = _seed_user(role=UserRole.member, email_prefix="m")
    _login_as(c, user)
    r = c.post("/api/auth/2fa/enroll")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["qr_svg"].startswith("<?xml") or body["qr_svg"].startswith("<svg")
    assert "<svg" in body["qr_svg"]
    assert len(body["manual_secret"]) == 32
    assert body["manual_secret"].isalnum()
    assert len(body["enrollment_token"]) >= 20


def test_enroll_stashes_redis_payload_with_user_id_and_secret_ttl_600(client):
    c, fake = client
    user = _seed_user(role=UserRole.member, email_prefix="m")
    _login_as(c, user)
    r = c.post("/api/auth/2fa/enroll")
    assert r.status_code == 200
    token = r.json()["enrollment_token"]
    raw = _redis_get(c, fake, f"totp:enroll:{token}")
    assert raw is not None
    payload = json.loads(raw)
    assert payload["user_id"] == str(user.id)
    assert payload["secret"] == r.json()["manual_secret"]
    ttl = _redis_ttl(c, fake, f"totp:enroll:{token}")
    assert 595 <= ttl <= 600


def test_enroll_409_if_user_already_enrolled(client):
    c, _ = client
    user = _seed_user(role=UserRole.member, email_prefix="m", totp_enabled=True)
    _login_as(c, user)
    r = c.post("/api/auth/2fa/enroll")
    assert r.status_code == 409
    assert r.json()["detail"] == "totp_already_enrolled"


def test_enroll_500_if_totp_fernet_key_empty(client):
    c, _ = client
    user = _seed_user(role=UserRole.member, email_prefix="m")
    settings = get_settings()
    original = settings.totp_fernet_key
    settings.totp_fernet_key = ""
    try:
        _login_as(c, user)
        r = c.post("/api/auth/2fa/enroll")
        assert r.status_code == 500
        assert r.json()["detail"] == "totp_not_configured"
    finally:
        settings.totp_fernet_key = original


# ---------------------------------------------------------------------------
# T7-T13 — POST /2fa/enroll/confirm behaviour
# ---------------------------------------------------------------------------


def test_confirm_invalid_token_404(client):
    c, _ = client
    user = _seed_user(role=UserRole.member, email_prefix="m")
    _login_as(c, user)
    r = c.post(
        "/api/auth/2fa/enroll/confirm",
        json={"enrollment_token": "x" * 32, "code": "123456"},
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "enrollment_token_invalid"


def test_confirm_user_mismatch_403(client):
    c, fake = client
    user_a = _seed_user(role=UserRole.member, email_prefix="a")
    user_b = _seed_user(role=UserRole.member, email_prefix="b")
    token_a, _ = _enroll_and_get_token(c, fake, user_a)

    _login_as(c, user_b)
    raw = _redis_get(c, fake, f"totp:enroll:{token_a}")
    secret_a = json.loads(raw)["secret"]
    code = pyotp.TOTP(secret_a).now()

    r = c.post(
        "/api/auth/2fa/enroll/confirm",
        json={"enrollment_token": token_a, "code": code},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "enrollment_token_user_mismatch"


def test_confirm_invalid_code_422(client):
    c, fake = client
    user = _seed_user(role=UserRole.member, email_prefix="m")
    token, secret = _enroll_and_get_token(c, fake, user)
    # Use a deliberately wrong code that pyotp won't match in ±1 window.
    real = pyotp.TOTP(secret).now()
    wrong = "000000" if real != "000000" else "111111"
    r = c.post(
        "/api/auth/2fa/enroll/confirm",
        json={"enrollment_token": token, "code": wrong},
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "invalid_code"

    engine = get_engine()
    with Session(engine) as s:
        u = s.get(User, user.id)
        assert u.totp_enabled_at is None
        assert u.totp_secret is None


def test_confirm_golden_path_persists_fernet_ciphertext_and_8_recovery_codes(client):
    c, fake = client
    user = _seed_user(role=UserRole.member, email_prefix="m")
    token, secret = _enroll_and_get_token(c, fake, user)
    code = pyotp.TOTP(secret).now()
    r = c.post(
        "/api/auth/2fa/enroll/confirm",
        json={"enrollment_token": token, "code": code},
    )
    assert r.status_code == 200, r.text

    engine = get_engine()
    with Session(engine) as s:
        u = s.get(User, user.id)
        assert u.totp_enabled_at is not None
        # Stored value is Fernet ciphertext, NOT the base32 cleartext.
        assert u.totp_secret is not None
        assert u.totp_secret != secret
        # Round-trip via the service helper proves Fernet-shaped ciphertext.
        assert decrypt_secret(u.totp_secret, get_settings()) == secret

        rows = list(s.exec(select(RecoveryCode).where(RecoveryCode.user_id == u.id)).all())
        assert len(rows) == 8
        batch_ids = {row.batch_id for row in rows}
        assert len(batch_ids) == 1
        for row in rows:
            assert row.code_hash.startswith("$2b$12$")


def test_confirm_response_returns_8_cleartext_codes_8char_lowercase_hex(client):
    c, fake = client
    user = _seed_user(role=UserRole.member, email_prefix="m")
    token, secret = _enroll_and_get_token(c, fake, user)
    code = pyotp.TOTP(secret).now()
    r = c.post(
        "/api/auth/2fa/enroll/confirm",
        json={"enrollment_token": token, "code": code},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["recovery_codes"]) == 8
    seen = set()
    for c_text in body["recovery_codes"]:
        assert len(c_text) == 8
        assert all(ch in "0123456789abcdef" for ch in c_text)
        seen.add(c_text)
    assert len(seen) == 8  # 8 unique codes
    uuid.UUID(body["batch_id"])
    assert body["generated_at"]


def test_confirm_emits_one_audit_row_action_totp_enrolled_entity_type_user(client):
    c, fake = client
    user = _seed_user(role=UserRole.member, email_prefix="m")
    token, secret = _enroll_and_get_token(c, fake, user)
    code = pyotp.TOTP(secret).now()
    r = c.post(
        "/api/auth/2fa/enroll/confirm",
        json={"enrollment_token": token, "code": code},
    )
    assert r.status_code == 200
    batch_id = r.json()["batch_id"]

    engine = get_engine()
    with Session(engine) as s:
        rows = list(s.exec(select(AuditLog).where(AuditLog.action == "auth.totp.enrolled")).all())
    assert len(rows) == 1
    row = rows[0]
    assert row.entity_type == "user"
    assert row.entity_id == user.id
    assert row.actor_user_id == user.id
    payload = json.loads(row.after_json)
    assert payload == {"batch_id": batch_id, "codes_count": 8}
    # No cleartext / hash / ciphertext leaked into the audit row.
    assert secret not in (row.after_json or "")
    assert row.before_json is None
    for code_text in r.json()["recovery_codes"]:
        assert code_text not in (row.after_json or "")


def test_confirm_deletes_redis_enrollment_token_on_success(client):
    c, fake = client
    user = _seed_user(role=UserRole.member, email_prefix="m")
    token, secret = _enroll_and_get_token(c, fake, user)
    code = pyotp.TOTP(secret).now()
    r = c.post(
        "/api/auth/2fa/enroll/confirm",
        json={"enrollment_token": token, "code": code},
    )
    assert r.status_code == 200
    assert _redis_get(c, fake, f"totp:enroll:{token}") is None


# ---------------------------------------------------------------------------
# T14-T15 — encryption round-trip + /me non-leakage
# ---------------------------------------------------------------------------


def test_decrypt_secret_roundtrips_to_original_cleartext(client):
    _c, _ = client
    # ensure settings cache is populated under the fixture's env
    settings = get_settings()
    sample = pyotp.random_base32()
    ciphertext = encrypt_secret(sample, settings)
    assert ciphertext != sample
    assert decrypt_secret(ciphertext, settings) == sample
    # The batch generator returns bcrypt-hashed pairs that verify against
    # their cleartexts — sanity check on the Decision E §1524 contract.
    _batch_id, pairs = generate_recovery_codes_batch()
    assert len(pairs) == 8
    for cleartext, digest in pairs:
        assert digest.startswith("$2b$12$")
        assert bcrypt.checkpw(cleartext.encode(), digest.encode())


def test_me_endpoint_response_does_not_leak_totp_secret_field(client):
    c, fake = client
    user = _seed_user(role=UserRole.member, email_prefix="m")
    token, secret = _enroll_and_get_token(c, fake, user)
    code = pyotp.TOTP(secret).now()
    r = c.post(
        "/api/auth/2fa/enroll/confirm",
        json={"enrollment_token": token, "code": code},
    )
    assert r.status_code == 200

    me = c.get("/api/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert set(body.keys()) == {"id", "email", "display_name", "role"}
    assert "totp_secret" not in body
    assert "totp_enabled_at" not in body


# ---------------------------------------------------------------------------
# T16-T18 — GET /2fa/status
# ---------------------------------------------------------------------------


def test_status_disabled_for_user_without_enrollment(client):
    c, _ = client
    user = _seed_user(role=UserRole.member, email_prefix="m")
    _login_as(c, user)
    r = c.get("/api/auth/2fa/status")
    assert r.status_code == 200
    assert r.json() == {
        "enabled": False,
        "batch_id": None,
        "generated_at": None,
        "codes_remaining": None,
    }


def test_status_enabled_returns_active_batch_metadata(client):
    c, fake = client
    user = _seed_user(role=UserRole.member, email_prefix="m")
    token, secret = _enroll_and_get_token(c, fake, user)
    code = pyotp.TOTP(secret).now()
    confirm = c.post(
        "/api/auth/2fa/enroll/confirm",
        json={"enrollment_token": token, "code": code},
    )
    assert confirm.status_code == 200
    expected_batch = confirm.json()["batch_id"]

    r = c.get("/api/auth/2fa/status")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert body["batch_id"] == expected_batch
    assert body["codes_remaining"] == 8
    assert body["generated_at"] is not None


def test_status_agent_role_always_disabled(client):
    c, _ = client
    agent = _seed_user(role=UserRole.agent, email_prefix="agent")
    _login_as(c, agent)
    r = c.get("/api/auth/2fa/status")
    assert r.status_code == 200
    assert r.json() == {
        "enabled": False,
        "batch_id": None,
        "generated_at": None,
        "codes_remaining": None,
    }


# ---------------------------------------------------------------------------
# Settings2faService sanity — imported to keep the public symbol exercised.
# ---------------------------------------------------------------------------


def test_settings2faservice_is_importable_as_public_symbol():
    assert Settings2faService is not None
