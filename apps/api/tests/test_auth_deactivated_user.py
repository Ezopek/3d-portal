"""Story 8.3 — AC-3 regression-fix tests for the is_active enforcement gate.

Closes the Story 8.1 gap: between Story 8.1 (column + middleware) and
Story 8.3 (the gates landed at the auth-router tier), a deactivated user
could still log in or refresh because the `is_active=False` state was
visible in the panel but NOT enforced. These 4 tests D1-D4 lock in the
end-to-end deactivation behavior per Decision I §1622-1623 and epics §1786
verbatim. D3 + D4 are golden-path regression guards proving the new gate
does not accidentally break active flows.
"""

from __future__ import annotations

import json

import pytest
from sqlmodel import Session, select

from app.core.auth.password import hash_password
from app.core.db.models import AuditLog, RefreshToken, User
from app.core.db.models._enums import UserRole
from app.core.db.session import get_engine

SEEDED_ADMIN_EMAIL = "admin@localhost.localdomain"


@pytest.fixture(autouse=True)
def _clear_user_and_audit_and_refresh_tables():
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


def _seed_member(email: str, password: str, *, is_active: bool = True) -> User:
    engine = get_engine()
    with Session(engine) as s:
        row = User(
            email=email,
            display_name=email.split("@")[0].title(),
            role=UserRole.member,
            password_hash=hash_password(password),
            is_active=is_active,
        )
        s.add(row)
        s.commit()
        s.refresh(row)
        return row


def _audit_rows() -> list[AuditLog]:
    engine = get_engine()
    with Session(engine) as s:
        return s.exec(select(AuditLog).order_by(AuditLog.at.asc())).all()


def _refresh_rows(user_id) -> list[RefreshToken]:
    engine = get_engine()
    with Session(engine) as s:
        return s.exec(select(RefreshToken).where(RefreshToken.user_id == user_id)).all()


def _set_user_active(user_id, *, is_active: bool) -> None:
    engine = get_engine()
    with Session(engine) as s:
        row = s.get(User, user_id)
        assert row is not None
        row.is_active = is_active
        s.add(row)
        s.commit()


# ---------------------------------------------------------------------------
# D1 — login deactivated user returns 401 account_deactivated
# ---------------------------------------------------------------------------
def test_login_deactivated_user_returns_401_account_deactivated(isolated_client):
    c, _ = isolated_client
    user = _seed_member("d1@test.example", "test-password-d1", is_active=False)

    r = c.post(
        "/api/auth/login",
        json={"email": "d1@test.example", "password": "test-password-d1"},
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "account_deactivated"

    # No session cookies issued.
    set_cookies = r.headers.get_list("set-cookie")
    cookie_blob = " ".join(set_cookies)
    assert "portal_access=" not in cookie_blob or "portal_access=;" in cookie_blob
    assert "portal_refresh=" not in cookie_blob or "portal_refresh=;" in cookie_blob

    rows = _audit_rows()
    assert len(rows) == 1
    ev = rows[0]
    assert ev.action == "auth.login.fail"
    assert ev.entity_id == user.id
    after = json.loads(ev.after_json)
    assert after["reason"] == "account_deactivated"


# ---------------------------------------------------------------------------
# D2 — refresh deactivated user returns 401 + burns family
# ---------------------------------------------------------------------------
def test_refresh_deactivated_user_returns_401_and_burns_family(isolated_client):
    c, _ = isolated_client
    user = _seed_member("d2@test.example", "test-password-d2")

    # Real login captures both cookies into the TestClient.
    r_login = c.post(
        "/api/auth/login",
        json={"email": "d2@test.example", "password": "test-password-d2"},
    )
    assert r_login.status_code == 200, r_login.text
    assert _refresh_rows(user.id) != []

    # Flip is_active=False DB-direct, then attempt refresh.
    _set_user_active(user.id, is_active=False)

    r_refresh = c.post("/api/auth/refresh")
    assert r_refresh.status_code == 401
    assert r_refresh.json()["detail"] == "account_deactivated"

    # All refresh-token rows must be revoked.
    rt_rows = _refresh_rows(user.id)
    assert rt_rows
    for row in rt_rows:
        assert row.revoked_at is not None

    rows = _audit_rows()
    # Find the auth.login.fail emitted by the refresh-gate.
    deactivated_events = [
        r
        for r in rows
        if r.action == "auth.login.fail"
        and r.after_json is not None
        and json.loads(r.after_json).get("reason") == "account_deactivated"
    ]
    assert len(deactivated_events) == 1
    ev = deactivated_events[0]
    after = json.loads(ev.after_json)
    assert "family_id" in after


# ---------------------------------------------------------------------------
# D3 — refresh active user still works (golden-path regression guard)
# ---------------------------------------------------------------------------
def test_refresh_active_user_still_works_golden_path(isolated_client):
    c, _ = isolated_client
    user = _seed_member("d3@test.example", "test-password-d3")

    r_login = c.post(
        "/api/auth/login",
        json={"email": "d3@test.example", "password": "test-password-d3"},
    )
    assert r_login.status_code == 200, r_login.text

    r_refresh = c.post("/api/auth/refresh")
    assert r_refresh.status_code == 200, r_refresh.text

    set_cookies = r_refresh.headers.get_list("set-cookie")
    cookie_blob = " ".join(set_cookies)
    assert "portal_refresh=" in cookie_blob

    rows = _audit_rows()
    deactivated_events = [
        r
        for r in rows
        if r.action == "auth.login.fail"
        and r.after_json is not None
        and json.loads(r.after_json).get("reason") == "account_deactivated"
    ]
    assert deactivated_events == []

    # At least one active row remains for the user (the new one minted by refresh).
    active_rows = [r for r in _refresh_rows(user.id) if r.revoked_at is None]
    assert active_rows


# ---------------------------------------------------------------------------
# D4 — login active user still works (golden-path regression guard)
# ---------------------------------------------------------------------------
def test_login_active_user_still_works_golden_path(isolated_client):
    c, _ = isolated_client
    _seed_member("d4@test.example", "test-password-d4")

    r = c.post(
        "/api/auth/login",
        json={"email": "d4@test.example", "password": "test-password-d4"},
    )
    assert r.status_code == 200, r.text

    set_cookies = r.headers.get_list("set-cookie")
    cookie_blob = " ".join(set_cookies)
    assert "portal_access=" in cookie_blob
    assert "portal_refresh=" in cookie_blob

    rows = _audit_rows()
    success_events = [r for r in rows if r.action == "auth.login.success"]
    assert len(success_events) >= 1
