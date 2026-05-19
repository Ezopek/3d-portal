"""Story 7.4 — login enforcement branch tests.

Six named tests T-ENFORCE-1..6 — names are binding cross-references for the
dev-story task list (AC-7). Per-test fixture pattern mirrors
``test_2fa_verify.py:44-70`` (monkeypatch.setenv + cache_clear + create_app
+ fakeredis stub).
"""

from __future__ import annotations

import datetime
import json
import uuid
from unittest.mock import MagicMock

import bcrypt
import fakeredis.aioredis
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.db.models import AuditLog, RefreshToken, User
from app.core.db.models._enums import UserRole
from app.core.db.session import get_engine
from app.main import create_app
from app.modules.auth.totp.service import encrypt_secret

JWT_SECRET = "test-secret-not-real"
FERNET_KEY = "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM="
KNOWN_TOTP_SECRET = "JBSWY3DPEHPK3PXP"
PASSWORD = "Sup3rPassword!"


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=4)).decode()


def _make_client(tmp_path, monkeypatch, *, enforce: str):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
    monkeypatch.setenv("TOTP_FERNET_KEY", FERNET_KEY)
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("ENFORCE_2FA_FOR_ROLES", enforce)
    get_settings.cache_clear()
    get_engine.cache_clear()
    app = create_app()
    fake = fakeredis.aioredis.FakeRedis()
    factory = MagicMock()
    factory.get = MagicMock(return_value=fake)

    async def _aclose():
        return None

    factory.aclose = _aclose
    c = TestClient(app)
    c.headers.update({"X-Portal-Client": "web"})
    c.__enter__()
    app.state.redis = factory
    return c, app


def _teardown(c: TestClient):
    c.__exit__(None, None, None)
    get_settings.cache_clear()
    get_engine.cache_clear()


def _seed_user(
    *,
    email_prefix: str = "u",
    role: UserRole = UserRole.member,
    with_totp: bool = False,
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
        if with_totp:
            u.totp_secret = encrypt_secret(KNOWN_TOTP_SECRET, settings)
            u.totp_enabled_at = datetime.datetime.now(datetime.UTC)
        s.add(u)
        s.commit()
        s.refresh(u)
        return u


def _audit_rows(action: str, user_id: uuid.UUID) -> list[AuditLog]:
    engine = get_engine()
    with Session(engine) as s:
        return list(
            s.exec(
                select(AuditLog)
                .where(AuditLog.action == action)
                .where(AuditLog.entity_id == user_id)
            ).all()
        )


def _refresh_count(user_id: uuid.UUID) -> int:
    engine = get_engine()
    with Session(engine) as s:
        return len(list(s.exec(select(RefreshToken).where(RefreshToken.user_id == user_id)).all()))


def test_login_member_in_enforce_list_no_totp_returns_totp_enroll_required_with_cookies(
    tmp_path, monkeypatch
):
    # T-ENFORCE-1
    c, _app = _make_client(tmp_path, monkeypatch, enforce="member")
    try:
        user = _seed_user(email_prefix="m1", role=UserRole.member, with_totp=False)
        r = c.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["partial_auth"] is False
        assert body["user"]["id"] == str(user.id)
        assert body["totp_enroll_required"] is True
        assert "portal_access" in r.cookies
        assert "portal_refresh" in r.cookies
        assert _refresh_count(user.id) == 1
    finally:
        _teardown(c)


def test_login_admin_not_in_enforce_list_returns_normal_response(tmp_path, monkeypatch):
    # T-ENFORCE-2 — admin role, enforce list is "member" only.
    c, _app = _make_client(tmp_path, monkeypatch, enforce="member")
    try:
        user = _seed_user(email_prefix="a1", role=UserRole.admin, with_totp=False)
        r = c.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["partial_auth"] is False
        assert body["user"]["id"] == str(user.id)
        assert body["totp_enroll_required"] is False
    finally:
        _teardown(c)


def test_login_member_not_in_enforce_list_returns_normal_response(tmp_path, monkeypatch):
    # T-ENFORCE-3 — default empty enforce list, member role.
    c, _app = _make_client(tmp_path, monkeypatch, enforce="")
    try:
        user = _seed_user(email_prefix="m2", role=UserRole.member, with_totp=False)
        r = c.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["partial_auth"] is False
        assert body["user"]["id"] == str(user.id)
        assert body["totp_enroll_required"] is False
    finally:
        _teardown(c)


def test_login_member_in_enforce_list_with_totp_enabled_returns_partial_auth_not_enroll_required(
    tmp_path, monkeypatch
):
    # T-ENFORCE-4 — mutual-exclusivity: TOTP-enabled members still take the
    # Story 7.3 verify path, NOT the Story 7.4 forced-enrollment path.
    c, _app = _make_client(tmp_path, monkeypatch, enforce="member")
    try:
        user = _seed_user(email_prefix="m3", role=UserRole.member, with_totp=True)
        r = c.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["partial_auth"] is True
        assert body["totp_required"] is True
        assert isinstance(body["partial_token"], str)
        assert "portal_access" not in r.cookies
        assert "portal_refresh" not in r.cookies
        assert _refresh_count(user.id) == 0
    finally:
        _teardown(c)


def test_login_member_in_enforce_list_no_totp_emits_audit_with_totp_enroll_required_true(
    tmp_path, monkeypatch
):
    # T-ENFORCE-5 — audit row carries the extended payload discriminator.
    c, _app = _make_client(tmp_path, monkeypatch, enforce="member")
    try:
        user = _seed_user(email_prefix="m4", role=UserRole.member, with_totp=False)
        r = c.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
        assert r.status_code == 200, r.text
        rows = _audit_rows("auth.login.success", user.id)
        assert len(rows) == 1
        payload = json.loads(rows[0].after_json or "{}")
        assert payload["email"] == user.email
        assert payload["totp_enroll_required"] is True
    finally:
        _teardown(c)


def test_login_member_not_in_enforce_list_emits_audit_without_totp_enroll_required_key(
    tmp_path, monkeypatch
):
    # T-ENFORCE-6 — non-forced-enrollment login keeps the existing audit shape.
    c, _app = _make_client(tmp_path, monkeypatch, enforce="")
    try:
        user = _seed_user(email_prefix="m5", role=UserRole.member, with_totp=False)
        r = c.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
        assert r.status_code == 200, r.text
        rows = _audit_rows("auth.login.success", user.id)
        assert len(rows) == 1
        payload = json.loads(rows[0].after_json or "{}")
        assert payload == {"email": user.email}
    finally:
        _teardown(c)
