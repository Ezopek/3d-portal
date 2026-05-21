"""Tests for the Initiative 5 public invite-token register endpoint (Story 6.4).

Covers AC-1 through AC-7 from the Story 6.4 spec:
- POST /api/auth/register (happy path + token diagnosis + password + email collision)

Reuses the `test_invite_admin.py` fixture shape (TestClient + fakeredis
swap into ``app.state.redis``), dropping the admin-cookie yield because
the register surface is anonymous. The autouse table-clear is extended
to ``User`` + ``RefreshToken`` so the per-test isolation covers the new
rows this story creates.

Async helpers run via ``c.portal.call(...)`` so the fakeredis client
stays bound to the TestClient's anyio event loop (see Story 6.3 fixture
note in ``test_invite_admin.py`` for the same workaround).
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

from app.core.auth.password import hash_password, verify_password
from app.core.auth.refresh import hash_refresh_secret
from app.core.db.models import AuditLog, RefreshToken, User
from app.core.db.models._enums import UserRole
from app.core.db.session import get_engine
from app.main import create_app
from app.modules.invite import InviteService, InviteToken

PASSWORD_STRONG = "correct horse battery staple"


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
        yield c, admin_uuid, fake
    get_settings.cache_clear()
    get_engine.cache_clear()


@pytest.fixture(autouse=True)
def _clear_tables():
    """Wipe invite_tokens + audit_log + non-admin users + refresh_tokens between tests."""
    engine = get_engine()
    with Session(engine) as s:
        for row in s.exec(select(RefreshToken)).all():
            s.delete(row)
        for row in s.exec(select(InviteToken)).all():
            s.delete(row)
        for row in s.exec(select(AuditLog)).all():
            s.delete(row)
        for row in s.exec(select(User).where(User.email != "admin@localhost.localdomain")).all():
            s.delete(row)
        s.commit()
    yield


def _audit_rows(action: str) -> list[AuditLog]:
    engine = get_engine()
    with Session(engine) as s:
        return list(s.exec(select(AuditLog).where(AuditLog.action == action)).all())


def _user_by_email(email: str) -> User | None:
    engine = get_engine()
    with Session(engine) as s:
        return s.exec(select(User).where(User.email == email)).first()


def _invite_row(invite_id: uuid.UUID) -> InviteToken | None:
    engine = get_engine()
    with Session(engine) as s:
        return s.get(InviteToken, invite_id)


def _gen_invite(
    c: TestClient,
    fake,
    *,
    generated_by_user_id: uuid.UUID,
    ttl_seconds: int = 604800,
    role: str = "member",
) -> tuple[str, uuid.UUID]:
    """Generate an invite via the real service on the TestClient anyio loop."""
    svc = InviteService(redis=fake, engine=get_engine())

    async def _do():
        return await svc.generate_invite(
            role=UserRole(role),
            ttl_seconds=ttl_seconds,
            generated_by_user_id=generated_by_user_id,
        )

    result = c.portal.call(_do)
    return result.token, result.invite.id


def _redis_get(c: TestClient, fake, key: str):
    async def _do():
        return await fake.get(key)

    return c.portal.call(_do)


def _redis_delete(c: TestClient, fake, key: str) -> None:
    async def _do():
        await fake.delete(key)

    c.portal.call(_do)


def _service_revoke(c: TestClient, fake, invite_id: uuid.UUID) -> None:
    svc = InviteService(redis=fake, engine=get_engine())

    async def _do():
        await svc.revoke(invite_id)

    c.portal.call(_do)


def _service_consume(
    c: TestClient,
    fake,
    token: str,
    *,
    used_by_user_id: uuid.UUID,
    used_from_ip: str,
) -> None:
    svc = InviteService(redis=fake, engine=get_engine())

    async def _do():
        await svc.consume(token, used_by_user_id=used_by_user_id, used_from_ip=used_from_ip)

    c.portal.call(_do)


# ---------------------------------------------------------------------------
# AC-1 — happy path
# ---------------------------------------------------------------------------


def test_register_happy_path_creates_user_and_consumes_invite(client):
    c, admin_uuid, fake = client
    token, invite_id = _gen_invite(c, fake, generated_by_user_id=admin_uuid)

    before = datetime.datetime.now(datetime.UTC)
    r = c.post(
        "/api/auth/register",
        json={"token": token, "email": "newbie@example.com", "password": PASSWORD_STRONG},
    )
    after = datetime.datetime.now(datetime.UTC)

    assert r.status_code == 201, r.text
    body = r.json()
    # Story 7.3 added the ``partial_auth`` discriminator to LoginResponse;
    # Story 7.4 added ``totp_enroll_required``. Both are present on every
    # LoginResponse, set to False on plain full-auth (non-enrolling) responses.
    assert set(body.keys()) == {"partial_auth", "user", "totp_enroll_required"}
    assert body["partial_auth"] is False
    assert body["totp_enroll_required"] is False
    user_payload = body["user"]
    assert user_payload["email"] == "newbie@example.com"
    assert user_payload["display_name"] == "newbie"
    assert user_payload["role"] == "member"
    uuid.UUID(user_payload["id"])

    # Cookies set on response
    assert r.cookies.get("portal_access") is not None
    assert r.cookies.get("portal_refresh") is not None

    # User row exists + password verifiable
    user = _user_by_email("newbie@example.com")
    assert user is not None
    assert user.role.value == "member"
    assert user.display_name == "newbie"
    assert verify_password(PASSWORD_STRONG, user.password_hash)
    created_at = user.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=datetime.UTC)
    assert (
        before - datetime.timedelta(seconds=5)
        <= created_at
        <= after + datetime.timedelta(seconds=5)
    )

    # invite row marked used
    invite = _invite_row(invite_id)
    assert invite is not None
    assert invite.used_at is not None
    assert invite.used_by_user_id == user.id
    assert invite.used_from_ip == "testclient"

    # Redis key gone
    assert _redis_get(c, fake, f"invite:token:{token}") is None


def test_register_sets_both_session_cookies_and_me_succeeds(client):
    c, admin_uuid, fake = client
    token, _ = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    r = c.post(
        "/api/auth/register",
        json={"token": token, "email": "newbie@example.com", "password": PASSWORD_STRONG},
    )
    assert r.status_code == 201

    me = c.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "newbie@example.com"


def test_register_emits_three_audit_rows_no_cleartext_token(client):
    c, admin_uuid, fake = client
    token, invite_id = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    r = c.post(
        "/api/auth/register",
        json={"token": token, "email": "newbie@example.com", "password": PASSWORD_STRONG},
    )
    assert r.status_code == 201
    user = _user_by_email("newbie@example.com")
    assert user is not None

    used = _audit_rows("auth.invite.used")
    success = _audit_rows("auth.register.success")
    failed = _audit_rows("auth.register.fail")
    assert len(used) == 1
    assert len(success) == 1
    assert failed == []

    used_row = used[0]
    assert used_row.entity_type == "invite_token"
    assert used_row.entity_id == invite_id
    assert used_row.actor_user_id == user.id
    used_payload = json.loads(used_row.after_json)
    assert used_payload == {"used_from_ip": "testclient"}
    assert "token" not in used_payload
    assert token not in (used_row.after_json or "")

    success_row = success[0]
    assert success_row.entity_type == "user"
    assert success_row.entity_id == user.id
    assert success_row.actor_user_id == user.id
    success_payload = json.loads(success_row.after_json)
    assert success_payload["email"] == "newbie@example.com"
    assert success_payload["role"] == "member"
    assert success_payload["invite_id"] == str(invite_id)
    assert "token" not in success_payload
    assert token not in (success_row.after_json or "")


def test_register_creates_refresh_token_row_with_fresh_family(client):
    c, admin_uuid, fake = client
    token, _ = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    r = c.post(
        "/api/auth/register",
        json={"token": token, "email": "newbie@example.com", "password": PASSWORD_STRONG},
    )
    assert r.status_code == 201
    refresh_secret = r.cookies.get("portal_refresh")
    user = _user_by_email("newbie@example.com")

    engine = get_engine()
    with Session(engine) as s:
        rows = list(s.exec(select(RefreshToken).where(RefreshToken.user_id == user.id)).all())
    assert len(rows) == 1
    row = rows[0]
    assert row.revoked_at is None
    assert row.token_hash == hash_refresh_secret(refresh_secret)


def test_register_display_name_derived_from_email_local_part(client):
    c, admin_uuid, fake = client
    token, _ = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    r = c.post(
        "/api/auth/register",
        json={
            "token": token,
            "email": "alice.smith@example.com",
            "password": PASSWORD_STRONG,
        },
    )
    assert r.status_code == 201
    assert r.json()["user"]["display_name"] == "alice.smith"
    user = _user_by_email("alice.smith@example.com")
    assert user.display_name == "alice.smith"


# ---------------------------------------------------------------------------
# AC-2 — token state diagnosis
# ---------------------------------------------------------------------------


def test_register_token_never_existed_returns_404_token_invalid(client):
    c, _, _ = client
    bogus = "x" * 43
    r = c.post(
        "/api/auth/register",
        json={"token": bogus, "email": "valid@example.com", "password": PASSWORD_STRONG},
    )
    assert r.status_code == 404
    assert r.json() == {"detail": "token_invalid"}

    failed = _audit_rows("auth.register.fail")
    assert len(failed) == 1
    payload = json.loads(failed[0].after_json)
    assert payload == {"reason": "token_invalid", "email": "valid@example.com"}
    assert failed[0].entity_type == "user"
    assert failed[0].entity_id is None
    assert failed[0].actor_user_id is None

    assert _user_by_email("valid@example.com") is None
    assert _audit_rows("auth.register.success") == []


def test_register_revoked_token_returns_410_token_consumed(client):
    c, admin_uuid, fake = client
    token, invite_id = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    _service_revoke(c, fake, invite_id)

    r = c.post(
        "/api/auth/register",
        json={"token": token, "email": "valid@example.com", "password": PASSWORD_STRONG},
    )
    assert r.status_code == 410
    assert r.json() == {"detail": "token_consumed"}

    failed = _audit_rows("auth.register.fail")
    assert len(failed) == 1
    payload = json.loads(failed[0].after_json)
    assert payload == {"reason": "token_consumed", "email": "valid@example.com"}


def test_register_used_token_returns_410_token_consumed(client):
    c, admin_uuid, fake = client
    token, _ = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    seed_user_id = uuid.uuid4()
    engine = get_engine()
    with Session(engine) as s:
        s.add(
            User(
                id=seed_user_id,
                email="seed@example.com",
                display_name="seed",
                role="member",
                password_hash=hash_password("seed_password_strong"),
            )
        )
        s.commit()
    _service_consume(c, fake, token, used_by_user_id=seed_user_id, used_from_ip="setup")

    r = c.post(
        "/api/auth/register",
        json={"token": token, "email": "valid@example.com", "password": PASSWORD_STRONG},
    )
    assert r.status_code == 410
    assert r.json() == {"detail": "token_consumed"}


def test_register_expired_token_returns_404_token_invalid(client):
    c, admin_uuid, fake = client
    token, invite_id = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    _redis_delete(c, fake, f"invite:token:{token}")
    engine = get_engine()
    with Session(engine) as s:
        row = s.get(InviteToken, invite_id)
        row.generated_at = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
            seconds=row.ttl_seconds * 2
        )
        s.add(row)
        s.commit()

    r = c.post(
        "/api/auth/register",
        json={"token": token, "email": "valid@example.com", "password": PASSWORD_STRONG},
    )
    assert r.status_code == 404
    assert r.json() == {"detail": "token_invalid"}


def test_register_double_consume_first_succeeds_second_returns_410(client):
    c, admin_uuid, fake = client
    token, _ = _gen_invite(c, fake, generated_by_user_id=admin_uuid)

    r1 = c.post(
        "/api/auth/register",
        json={"token": token, "email": "first@example.com", "password": PASSWORD_STRONG},
    )
    assert r1.status_code == 201

    c.cookies.clear()

    r2 = c.post(
        "/api/auth/register",
        json={"token": token, "email": "second@example.com", "password": PASSWORD_STRONG},
    )
    assert r2.status_code == 410
    assert r2.json() == {"detail": "token_consumed"}
    assert _user_by_email("second@example.com") is None


# ---------------------------------------------------------------------------
# AC-3 — password validation
# ---------------------------------------------------------------------------


def test_register_weak_password_short_returns_422_length_message(client):
    c, admin_uuid, fake = client
    token, _ = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    r = c.post(
        "/api/auth/register",
        json={"token": token, "email": "valid@example.com", "password": "abc12"},
    )
    assert r.status_code == 422
    assert r.json() == {"detail": "password must be at least 12 characters"}


def test_register_weak_password_low_score_returns_422_zxcvbn_message(client):
    c, admin_uuid, fake = client
    token, _ = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    r = c.post(
        "/api/auth/register",
        json={"token": token, "email": "valid@example.com", "password": "password123!"},
    )
    assert r.status_code == 422
    assert r.json() == {"detail": "password is too predictable; choose a stronger one"}


def test_register_weak_password_short_and_strong_returns_422_length_message(client):
    """Case C — length wins precedence over zxcvbn."""
    c, admin_uuid, fake = client
    token, _ = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    r = c.post(
        "/api/auth/register",
        json={"token": token, "email": "valid@example.com", "password": "x*7M&!q9z"},
    )
    assert r.status_code == 422
    assert r.json() == {"detail": "password must be at least 12 characters"}


def test_register_weak_password_audit_omits_password_value(client):
    c, admin_uuid, fake = client
    token, _ = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    r = c.post(
        "/api/auth/register",
        json={"token": token, "email": "valid@example.com", "password": "abc12"},
    )
    assert r.status_code == 422
    failed = _audit_rows("auth.register.fail")
    assert len(failed) == 1
    audit = failed[0]
    payload = json.loads(audit.after_json)
    assert payload == {"reason": "weak_password", "email": "valid@example.com"}
    assert "password" not in payload  # no "password" KEY in the dict
    assert "abc12" not in audit.after_json


def test_register_weak_password_does_not_consume_invite(client):
    c, admin_uuid, fake = client
    token, invite_id = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    r = c.post(
        "/api/auth/register",
        json={"token": token, "email": "valid@example.com", "password": "abc12"},
    )
    assert r.status_code == 422
    assert _redis_get(c, fake, f"invite:token:{token}") is not None
    invite = _invite_row(invite_id)
    assert invite.used_at is None
    assert _audit_rows("auth.invite.used") == []


# ---------------------------------------------------------------------------
# AC-4 — email collision
# ---------------------------------------------------------------------------


def test_register_email_taken_returns_409(client):
    c, admin_uuid, fake = client
    engine = get_engine()
    existing_id = uuid.uuid4()
    with Session(engine) as s:
        s.add(
            User(
                id=existing_id,
                email="taken@example.com",
                display_name="Taken",
                role="member",
                password_hash=hash_password("preexisting_password_strong"),
            )
        )
        s.commit()
    token, _ = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    r = c.post(
        "/api/auth/register",
        json={"token": token, "email": "taken@example.com", "password": PASSWORD_STRONG},
    )
    assert r.status_code == 409
    assert r.json() == {"detail": "email_taken"}

    failed = _audit_rows("auth.register.fail")
    assert len(failed) == 1
    audit = failed[0]
    assert audit.entity_type == "user"
    assert audit.entity_id == existing_id
    payload = json.loads(audit.after_json)
    assert payload == {"reason": "email_taken", "email": "taken@example.com"}


def test_register_email_taken_does_not_consume_invite(client):
    c, admin_uuid, fake = client
    engine = get_engine()
    with Session(engine) as s:
        s.add(
            User(
                email="taken@example.com",
                display_name="Taken",
                role="member",
                password_hash=hash_password("preexisting_password_strong"),
            )
        )
        s.commit()
    token, invite_id = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    r = c.post(
        "/api/auth/register",
        json={"token": token, "email": "taken@example.com", "password": PASSWORD_STRONG},
    )
    assert r.status_code == 409
    assert _redis_get(c, fake, f"invite:token:{token}") is not None
    invite = _invite_row(invite_id)
    assert invite.used_at is None
    assert _audit_rows("auth.invite.used") == []


def test_register_duplicate_email_race_returns_409_and_audits(client, monkeypatch):
    """Race: another writer inserts a user with the same email AFTER our
    uniqueness SELECT passes but BEFORE the commit. The unique constraint
    must convert that into the same 409 + audit signature as the SELECT
    path — not a 500."""
    c, admin_uuid, fake = client
    token, _ = _gen_invite(c, fake, generated_by_user_id=admin_uuid)

    racer_id = uuid.uuid4()
    real_hash_password = hash_password

    def _hash_then_seed_competitor(plaintext):
        """Hook called between SELECT and commit inside the register handler.

        Mirrors the timing of a real concurrent register call by inserting
        a competing user with the same email on a fresh Session — the
        request's own Session won't see it until commit time, when the
        UNIQUE constraint fires."""
        engine = get_engine()
        with Session(engine) as competing:
            already = competing.exec(select(User).where(User.email == "race@example.com")).first()
            if already is None:
                competing.add(
                    User(
                        id=racer_id,
                        email="race@example.com",
                        display_name="race",
                        role="member",
                        password_hash=real_hash_password("racer_password_strong"),
                    )
                )
                competing.commit()
        return real_hash_password(plaintext)

    monkeypatch.setattr(
        "app.modules.invite.router.hash_password",
        _hash_then_seed_competitor,
    )

    r = c.post(
        "/api/auth/register",
        json={"token": token, "email": "race@example.com", "password": PASSWORD_STRONG},
    )
    assert r.status_code == 409, r.text
    assert r.json() == {"detail": "email_taken"}

    failed = _audit_rows("auth.register.fail")
    assert len(failed) == 1
    audit = failed[0]
    assert audit.entity_type == "user"
    assert audit.entity_id == racer_id
    payload = json.loads(audit.after_json)
    assert payload == {"reason": "email_taken", "email": "race@example.com"}

    # The would-be user row never persisted — only the racer remains.
    engine = get_engine()
    with Session(engine) as s:
        users = list(s.exec(select(User).where(User.email == "race@example.com")).all())
    assert len(users) == 1
    assert users[0].id == racer_id

    # Invite token must not have been consumed.
    assert _audit_rows("auth.invite.used") == []


def test_register_email_taken_does_not_mutate_existing_user(client):
    c, admin_uuid, fake = client
    engine = get_engine()
    with Session(engine) as s:
        existing = User(
            email="taken@example.com",
            display_name="Taken",
            role="member",
            password_hash=hash_password("preexisting_password_strong"),
        )
        s.add(existing)
        s.commit()
        s.refresh(existing)
        existing_hash = existing.password_hash
        existing_id = existing.id
    token, _ = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    r = c.post(
        "/api/auth/register",
        json={"token": token, "email": "taken@example.com", "password": PASSWORD_STRONG},
    )
    assert r.status_code == 409
    with Session(engine) as s:
        user = s.get(User, existing_id)
    assert user.password_hash == existing_hash
    assert verify_password("preexisting_password_strong", user.password_hash)


# ---------------------------------------------------------------------------
# Pydantic + CSRF schema-layer rejections
# ---------------------------------------------------------------------------


def test_register_invalid_email_rfc_returns_422(client):
    c, admin_uuid, fake = client
    token, _ = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    r = c.post(
        "/api/auth/register",
        json={"token": token, "email": "not-an-email", "password": PASSWORD_STRONG},
    )
    assert r.status_code == 422
    assert _audit_rows("auth.register.fail") == []


def test_register_csrf_header_required_returns_403(client):
    c, admin_uuid, fake = client
    token, _ = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    c.headers.pop("X-Portal-Client", None)
    r = c.post(
        "/api/auth/register",
        json={"token": token, "email": "valid@example.com", "password": PASSWORD_STRONG},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "csrf_required"


def test_register_missing_token_field_returns_422(client):
    c, _, _ = client
    r = c.post(
        "/api/auth/register",
        json={"email": "valid@example.com", "password": PASSWORD_STRONG},
    )
    assert r.status_code == 422


def test_register_missing_email_field_returns_422(client):
    c, _, _ = client
    r = c.post(
        "/api/auth/register",
        json={"token": "x" * 43, "password": PASSWORD_STRONG},
    )
    assert r.status_code == 422


def test_register_missing_password_field_returns_422(client):
    c, _, _ = client
    r = c.post(
        "/api/auth/register",
        json={"token": "x" * 43, "email": "valid@example.com"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Story 12.3 — optional display_name on register
# ---------------------------------------------------------------------------


def test_register_with_display_name_uses_supplied_value(client):
    """AC: user-supplied display_name overrides the email-prefix derivation."""
    c, admin_uuid, fake = client
    token, _ = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    r = c.post(
        "/api/auth/register",
        json={
            "token": token,
            "email": "alice.smith@example.com",
            "password": PASSWORD_STRONG,
            "display_name": "Alice Smith",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["user"]["display_name"] == "Alice Smith"
    user = _user_by_email("alice.smith@example.com")
    assert user.display_name == "Alice Smith"


def test_register_without_display_name_falls_back_to_email_prefix(client):
    """AC: when display_name absent, behaviour falls back to legacy
    email-local-part derivation (Story 6.4 contract)."""
    c, admin_uuid, fake = client
    token, _ = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    r = c.post(
        "/api/auth/register",
        json={
            "token": token,
            "email": "bob@example.com",
            "password": PASSWORD_STRONG,
        },
    )
    assert r.status_code == 201
    assert r.json()["user"]["display_name"] == "bob"
    user = _user_by_email("bob@example.com")
    assert user.display_name == "bob"


def test_register_with_whitespace_only_display_name_falls_back_to_email_prefix(client):
    """Pure-whitespace display_name strips to empty → email-prefix fallback."""
    c, admin_uuid, fake = client
    token, _ = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    r = c.post(
        "/api/auth/register",
        json={
            "token": token,
            "email": "carol@example.com",
            "password": PASSWORD_STRONG,
            "display_name": "   ",
        },
    )
    assert r.status_code == 201
    assert r.json()["user"]["display_name"] == "carol"


def test_register_display_name_trims_whitespace(client):
    """Leading/trailing whitespace is stripped before persistence."""
    c, admin_uuid, fake = client
    token, _ = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    r = c.post(
        "/api/auth/register",
        json={
            "token": token,
            "email": "dave@example.com",
            "password": PASSWORD_STRONG,
            "display_name": "  Dave Doe  ",
        },
    )
    assert r.status_code == 201
    assert r.json()["user"]["display_name"] == "Dave Doe"


def test_register_with_too_long_display_name_returns_422(client):
    """Schema ceiling `max_length=120` rejects pathological lengths."""
    c, admin_uuid, fake = client
    token, _ = _gen_invite(c, fake, generated_by_user_id=admin_uuid)
    r = c.post(
        "/api/auth/register",
        json={
            "token": token,
            "email": "eve@example.com",
            "password": PASSWORD_STRONG,
            "display_name": "x" * 121,
        },
    )
    assert r.status_code == 422
