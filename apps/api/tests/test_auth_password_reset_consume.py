"""Story 8.5 — backend tests for the public password-reset consume endpoint.

10 named tests C1-C10 covering ``POST /api/auth/password-reset`` per the
spec AC-7 table. Verifies the 4-step deterministic sequence (atomic claim
→ password validation → user lookup → password update + success audit),
the uniform 404 ``token_invalid`` for never-existed / expired / consumed
states, the audit-emission entity_id asymmetry pre/post-claim, the
zero-cookie response, and the asyncio.gather concurrency invariant that
exactly one of two parallel consumes wins.
"""

from __future__ import annotations

import asyncio
import json
import secrets
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
STRONG_NEW_PASSWORD = "Br3ezy-mountain-pa$$word-2026"


@pytest.fixture(autouse=True)
def _clear_user_and_audit_tables():
    """Wipe non-admin user + audit rows between tests."""
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


def _admin_token() -> str:
    return encode_token(
        subject=str(_get_admin_id()),
        role="admin",
        secret=JWT_TEST_SECRET,
        ttl_minutes=30,
    )


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


def _read_user(user_id: uuid.UUID) -> User | None:
    engine = get_engine()
    with Session(engine) as s:
        return s.get(User, user_id)


def _mint_reset_token(client, target_id: uuid.UUID) -> str:
    """Mint a reset token via the admin endpoint and return the token string."""
    _set_admin_cookie(client)
    r = client.post(f"/api/admin/users/{target_id}/password-reset")
    assert r.status_code == 201, r.text
    token = r.json()["reset_url"].removeprefix("/reset-password?token=")
    client.cookies.clear()
    return token


# ---------------------------------------------------------------------------
# C1 — golden-path consume returns 204 + password updated + success audit
# ---------------------------------------------------------------------------
def test_consume_golden_path_updates_password_and_emits_completed_audit(
    isolated_client,
):
    c, _ = isolated_client
    target_id = _seed_user("c1@test.example")
    token = _mint_reset_token(c, target_id)

    r = c.post(
        "/api/auth/password-reset",
        json={"token": token, "new_password": STRONG_NEW_PASSWORD},
    )
    assert r.status_code == 204, r.text

    # Password is hashed and matches the new plaintext.
    user = _read_user(target_id)
    assert user is not None
    assert bcrypt.checkpw(STRONG_NEW_PASSWORD.encode(), user.password_hash.encode())

    # Two audit rows: initiated (admin) + completed (self).
    rows = _audit_rows()
    completed = [r for r in rows if r.action == "auth.password.reset.completed"]
    assert len(completed) == 1
    ev = completed[0]
    assert ev.actor_user_id == target_id
    assert ev.entity_id == target_id
    assert json.loads(ev.after_json) == {"email": user.email}


# ---------------------------------------------------------------------------
# C2 — consume with invalid token returns 404 token_invalid
# ---------------------------------------------------------------------------
def test_consume_invalid_token_returns_404_with_token_invalid_audit(isolated_client):
    c, _ = isolated_client
    bogus_token = secrets.token_urlsafe(32)  # 43 chars, never minted

    r = c.post(
        "/api/auth/password-reset",
        json={"token": bogus_token, "new_password": STRONG_NEW_PASSWORD},
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "token_invalid"

    rows = [r for r in _audit_rows() if r.action == "auth.password.reset.completed"]
    assert len(rows) == 1
    ev = rows[0]
    assert ev.entity_id is None
    assert ev.actor_user_id is None
    assert json.loads(ev.after_json) == {"reason": "token_invalid"}


# ---------------------------------------------------------------------------
# C3 — second consume of the same token returns 404 token_invalid (uniform)
# ---------------------------------------------------------------------------
def test_consume_already_consumed_token_returns_uniform_404(isolated_client):
    c, _ = isolated_client
    target_id = _seed_user("c3@test.example")
    token = _mint_reset_token(c, target_id)

    r1 = c.post(
        "/api/auth/password-reset",
        json={"token": token, "new_password": STRONG_NEW_PASSWORD},
    )
    assert r1.status_code == 204

    r2 = c.post(
        "/api/auth/password-reset",
        json={"token": token, "new_password": STRONG_NEW_PASSWORD},
    )
    assert r2.status_code == 404
    assert r2.json()["detail"] == "token_invalid"

    completed = [r for r in _audit_rows() if r.action == "auth.password.reset.completed"]
    # one success + one token_invalid
    assert len(completed) == 2
    reasons = sorted(json.loads(r.after_json).get("reason") or "success" for r in completed)
    assert reasons == ["success", "token_invalid"]


# ---------------------------------------------------------------------------
# C4 — consume with expired token returns 404 token_invalid
# ---------------------------------------------------------------------------
def test_consume_expired_token_returns_404(isolated_client):
    c, fake = isolated_client
    target_id = _seed_user("c4@test.example")
    token = _mint_reset_token(c, target_id)

    # Simulate expiration by deleting the Redis key directly.
    async def _expire():
        await fake.delete(f"invite:reset:{token}")

    c.portal.call(_expire)

    r = c.post(
        "/api/auth/password-reset",
        json={"token": token, "new_password": STRONG_NEW_PASSWORD},
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "token_invalid"


# ---------------------------------------------------------------------------
# C5 — consume with too-short password returns 422 + weak_password audit
# ---------------------------------------------------------------------------
def test_consume_short_password_returns_422_with_weak_password_audit(
    isolated_client,
):
    c, fake = isolated_client
    target_id = _seed_user("c5@test.example")
    token = _mint_reset_token(c, target_id)

    r = c.post(
        "/api/auth/password-reset",
        json={"token": token, "new_password": "short"},
    )
    assert r.status_code == 422
    assert r.json()["detail"].startswith("password must be at least 12")

    completed = [r for r in _audit_rows() if r.action == "auth.password.reset.completed"]
    assert len(completed) == 1
    ev = completed[0]
    # Codex P2 fix-up: password validated BEFORE token claim → entity_id is
    # None at audit time (user identity unknown pre-claim) and the token
    # stays in Redis for retry. Was: entity_id=target_id, token consumed.
    assert ev.entity_id is None
    assert json.loads(ev.after_json) == {"reason": "weak_password"}

    # Token preserved on weak-password — user can retry with stronger pw.
    async def _keys():
        return await fake.keys("invite:reset:*")

    keys = c.portal.call(_keys)
    assert len(keys) == 1


# ---------------------------------------------------------------------------
# C6 — consume with weak zxcvbn password returns 422 + weak_password audit
# ---------------------------------------------------------------------------
def test_consume_weak_zxcvbn_password_returns_422(isolated_client):
    c, fake = isolated_client
    target_id = _seed_user("c6@test.example")
    token = _mint_reset_token(c, target_id)

    # 13 chars but trivially predictable → zxcvbn score < 3.
    r = c.post(
        "/api/auth/password-reset",
        json={"token": token, "new_password": "passwordpassw"},
    )
    assert r.status_code == 422
    assert r.json()["detail"].startswith("password is too predictable")

    completed = [r for r in _audit_rows() if r.action == "auth.password.reset.completed"]
    assert len(completed) == 1
    # Codex P2 fix-up: validated pre-claim → entity_id None + token retained.
    assert completed[0].entity_id is None
    assert json.loads(completed[0].after_json) == {"reason": "weak_password"}

    async def _keys():
        return await fake.keys("invite:reset:*")

    # Token preserved for retry — only consumed on successful commit path.
    assert len(c.portal.call(_keys)) == 1


# ---------------------------------------------------------------------------
# C7 — target row deleted between mint and consume → 404 user_not_found
# ---------------------------------------------------------------------------
def test_consume_deleted_user_returns_404_with_user_not_found_audit(
    isolated_client,
):
    c, _ = isolated_client
    target_id = _seed_user("c7@test.example")
    token = _mint_reset_token(c, target_id)

    # Delete the target row before consume.
    engine = get_engine()
    with Session(engine) as s:
        row = s.get(User, target_id)
        assert row is not None
        s.delete(row)
        s.commit()

    r = c.post(
        "/api/auth/password-reset",
        json={"token": token, "new_password": STRONG_NEW_PASSWORD},
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "user_not_found"

    completed = [r for r in _audit_rows() if r.action == "auth.password.reset.completed"]
    assert len(completed) == 1
    ev = completed[0]
    assert ev.entity_id == target_id
    assert json.loads(ev.after_json) == {"reason": "user_not_found"}


# ---------------------------------------------------------------------------
# C8 — consume succeeds for deactivated user; login still blocked
# ---------------------------------------------------------------------------
def test_consume_succeeds_for_deactivated_user_but_login_still_blocked(
    isolated_client,
):
    c, _ = isolated_client
    target_id = _seed_user("c8@test.example", is_active=False)
    token = _mint_reset_token(c, target_id)

    r = c.post(
        "/api/auth/password-reset",
        json={"token": token, "new_password": STRONG_NEW_PASSWORD},
    )
    assert r.status_code == 204, r.text

    # Password updated.
    user = _read_user(target_id)
    assert user is not None
    assert bcrypt.checkpw(STRONG_NEW_PASSWORD.encode(), user.password_hash.encode())

    # Story 8.3 is_active gate continues to fire on login.
    login = c.post(
        "/api/auth/login",
        json={"email": "c8@test.example", "password": STRONG_NEW_PASSWORD},
    )
    assert login.status_code == 401


# ---------------------------------------------------------------------------
# C9 — concurrent consume on same token: exactly one 204 + one 404
# ---------------------------------------------------------------------------
def test_consume_concurrent_claims_exactly_one_wins(isolated_client):
    """The atomic GETDEL guarantees mutual exclusion.

    Direct service-level concurrency assertion: we drive
    ``PasswordResetService.claim`` against the fake redis from two
    asyncio.gather'd coroutines and assert exactly one returns the
    bound user_id while the other returns ``None``. This is the C9
    binding verification of the architecture's single-use semantics —
    if a non-atomic SET+GET+DEL snuck in, both claims would observe
    the value and pass.
    """
    from app.modules.auth.password_reset.service import PasswordResetService

    c, fake = isolated_client
    target_id = _seed_user("c9@test.example")
    token = _mint_reset_token(c, target_id)
    service = PasswordResetService(redis=fake)

    async def _both():
        return await asyncio.gather(service.claim(token), service.claim(token))

    a, b = c.portal.call(_both)
    outcomes = [a, b]
    hits = [o for o in outcomes if o is not None]
    misses = [o for o in outcomes if o is None]
    assert len(hits) == 1
    assert len(misses) == 1
    assert hits[0] == target_id


# ---------------------------------------------------------------------------
# C10 — consume response does NOT issue portal_access / portal_refresh cookies
# ---------------------------------------------------------------------------
def test_consume_does_not_issue_session_cookies(isolated_client):
    c, _ = isolated_client
    target_id = _seed_user("c10@test.example")
    token = _mint_reset_token(c, target_id)
    c.cookies.clear()

    r = c.post(
        "/api/auth/password-reset",
        json={"token": token, "new_password": STRONG_NEW_PASSWORD},
    )
    assert r.status_code == 204

    set_cookie_headers = [v for (k, v) in r.headers.items() if k.lower() == "set-cookie"]
    for sc in set_cookie_headers:
        assert "portal_access" not in sc
        assert "portal_refresh" not in sc
