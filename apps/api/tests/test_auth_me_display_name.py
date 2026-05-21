"""Tests for ``PATCH /api/auth/me/display-name`` (Story 12.3).

Self-service display-name edit endpoint. Auth required (current_user) —
anonymous requests get the 401 from the SoT default-deny gate. Emits a
``user.display_name.updated`` audit row on successful mutation (actor ==
target); no-op writes (post-strip equal to current value) are skipped
without emitting audit.

Reuses the session-scoped ``client`` fixture from conftest.py.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.auth.password import hash_password
from app.core.db.models import AuditLog, User
from app.core.db.models._enums import UserRole
from app.core.db.session import get_engine


def _login_as_member(client: TestClient) -> User:
    """Provision a fresh member account + log them in via the standard /login
    cookie flow. Returns the User row (re-queried so SQLModel doesn't hold a
    detached instance)."""
    with Session(get_engine()) as s:
        existing = s.exec(
            select(User).where(User.email == "displayname-member@example.com")
        ).first()
        if existing is None:
            user = User(
                email="displayname-member@example.com",
                display_name="legacy_local_part",
                role=UserRole.member,
                password_hash=hash_password("member-strong-pw-12+"),
            )
            s.add(user)
            s.commit()
            s.refresh(user)
        else:
            # Reset the display_name back to the legacy value between
            # tests so each test starts from a known baseline (the
            # session-scoped DB persists rows across tests).
            existing.display_name = "legacy_local_part"
            s.add(existing)
            s.commit()
            user = existing
        user_id = user.id

    r = client.post(
        "/api/auth/login",
        json={
            "email": "displayname-member@example.com",
            "password": "member-strong-pw-12+",
        },
    )
    assert r.status_code == 200, r.text

    with Session(get_engine()) as s:
        return s.get(User, user_id)


def _audit_rows(action: str) -> list[AuditLog]:
    with Session(get_engine()) as s:
        return list(s.exec(select(AuditLog).where(AuditLog.action == action)).all())


def _clear_display_name_audits() -> None:
    with Session(get_engine()) as s:
        rows = s.exec(select(AuditLog).where(AuditLog.action == "user.display_name.updated")).all()
        for r in rows:
            s.delete(r)
        s.commit()


def test_patch_display_name_anonymous_returns_401(client):
    """AC: anonymous PATCH returns 401 from the SoT default-deny gate."""
    r = client.patch("/api/auth/me/display-name", json={"display_name": "Hacker"})
    assert r.status_code == 401


def test_patch_display_name_happy_path_updates_and_audits(client):
    """AC: authenticated PATCH updates the row + emits an audit event with
    before/after pair (actor == target).
    """
    _clear_display_name_audits()
    user = _login_as_member(client)
    assert user.display_name == "legacy_local_part"
    user_id = user.id

    r = client.patch(
        "/api/auth/me/display-name",
        json={"display_name": "Foo Bar"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["display_name"] == "Foo Bar"
    assert body["email"] == "displayname-member@example.com"

    with Session(get_engine()) as s:
        refreshed = s.get(User, user_id)
        assert refreshed.display_name == "Foo Bar"

    rows = _audit_rows("user.display_name.updated")
    assert len(rows) == 1
    row = rows[0]
    assert row.entity_type == "user"
    assert row.entity_id == user_id
    assert row.actor_user_id == user_id
    before = json.loads(row.before_json)
    after = json.loads(row.after_json)
    assert before == {"display_name": "legacy_local_part"}
    assert after == {"display_name": "Foo Bar"}


def test_patch_display_name_trims_whitespace(client):
    """Surrounding whitespace is stripped before persistence."""
    _clear_display_name_audits()
    user = _login_as_member(client)
    user_id = user.id

    r = client.patch(
        "/api/auth/me/display-name",
        json={"display_name": "   Alice   "},
    )
    assert r.status_code == 200
    assert r.json()["display_name"] == "Alice"

    with Session(get_engine()) as s:
        refreshed = s.get(User, user_id)
        assert refreshed.display_name == "Alice"


def test_patch_display_name_whitespace_only_returns_422(client):
    """Pure-whitespace payloads are rejected at the handler layer (the schema
    floor only catches the literal empty string)."""
    _clear_display_name_audits()
    _login_as_member(client)
    r = client.patch(
        "/api/auth/me/display-name",
        json={"display_name": "   "},
    )
    assert r.status_code == 422
    assert _audit_rows("user.display_name.updated") == []


def test_patch_display_name_empty_string_returns_422(client):
    """Schema floor `min_length=1` rejects the literal empty string."""
    _login_as_member(client)
    r = client.patch(
        "/api/auth/me/display-name",
        json={"display_name": ""},
    )
    assert r.status_code == 422


def test_patch_display_name_too_long_returns_422(client):
    """Schema ceiling `max_length=120` rejects pathological lengths."""
    _login_as_member(client)
    r = client.patch(
        "/api/auth/me/display-name",
        json={"display_name": "a" * 121},
    )
    assert r.status_code == 422


def test_patch_display_name_noop_skips_audit(client):
    """When the post-strip new value equals the current persisted value, no
    audit row is emitted (write is skipped)."""
    _clear_display_name_audits()
    user = _login_as_member(client)
    current = user.display_name

    r = client.patch(
        "/api/auth/me/display-name",
        json={"display_name": current},
    )
    assert r.status_code == 200
    assert r.json()["display_name"] == current
    assert _audit_rows("user.display_name.updated") == []


def test_patch_display_name_max_length_boundary_accepted(client):
    """Exactly 120 chars is accepted (inclusive ceiling)."""
    _clear_display_name_audits()
    _login_as_member(client)
    value = "a" * 120
    r = client.patch(
        "/api/auth/me/display-name",
        json={"display_name": value},
    )
    assert r.status_code == 200
    assert r.json()["display_name"] == value


def test_patch_display_name_rejects_unknown_fields(client):
    """``extra="forbid"`` on the schema rejects unknown fields with 422 so
    typo'd payloads can't accidentally bypass the validation envelope."""
    _login_as_member(client)
    r = client.patch(
        "/api/auth/me/display-name",
        json={"display_name": "Foo", "role": "admin"},
    )
    assert r.status_code == 422
