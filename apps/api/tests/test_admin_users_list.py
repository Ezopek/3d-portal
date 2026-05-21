"""Tests for the Initiative 5 admin Users list endpoint (Story 8.2).

Covers AC-1 through AC-3 from the Story 8.2 spec:
- GET /api/admin/users with pagination, search, sort_by, sort_order.
- Hygiene rule: password_hash + totp_secret never surfaced (Decision I).
- 403 for member-role; 401 for anonymous (FR5-MEMBER-2).

First Epic 8 backend test file binding the Story 8.1 ``isolated_client``
conftest fixture promotion (per Story 8.1 AC-7 last bullet). The autouse
fixture below preserves the seeded admin row between tests via the
``email != 'admin@localhost.localdomain'`` predicate so isolation does not
collide with session-scope schema bootstrap.
"""

from __future__ import annotations

import datetime
import uuid

import pytest
from sqlmodel import Session, select

from app.core.auth.jwt import encode_token
from app.core.db.models import AuditLog, User
from app.core.db.models._enums import UserRole
from app.core.db.session import get_engine

SEEDED_ADMIN_EMAIL = "admin@localhost.localdomain"
JWT_TEST_SECRET = "test-secret-not-real"


def _seed_members(
    session: Session,
    n: int,
    *,
    email_prefix: str = "member",
) -> list[uuid.UUID]:
    """Insert ``n`` deterministic member rows; return their UUIDs in insertion order."""
    inserted: list[uuid.UUID] = []
    for i in range(n):
        row = User(
            email=f"{email_prefix}{i}@test.example",
            display_name=f"Member {i}",
            role=UserRole.member,
            password_hash="bcrypt-test-hash",
        )
        session.add(row)
        session.flush()
        inserted.append(row.id)
    session.commit()
    return inserted


@pytest.fixture(autouse=True)
def _clear_user_and_audit_tables():
    """Wipe non-admin user + audit_log rows between tests; preserve seeded admin."""
    engine = get_engine()
    with Session(engine) as s:
        for row in s.exec(select(User).where(User.email != SEEDED_ADMIN_EMAIL)).all():
            s.delete(row)
        for row in s.exec(select(AuditLog)).all():
            s.delete(row)
        s.commit()
    yield


def _admin_token(client) -> str:
    """Mint an admin cookie token bound to the seeded admin row."""
    engine = get_engine()
    with Session(engine) as s:
        admin = s.exec(select(User).where(User.email == SEEDED_ADMIN_EMAIL)).first()
        assert admin is not None, "Seeded admin missing — conftest bootstrap regressed"
        admin_uuid = admin.id
    return encode_token(
        subject=str(admin_uuid), role="admin", secret=JWT_TEST_SECRET, ttl_minutes=30
    )


def _set_admin_cookie(client, token: str) -> None:
    client.cookies.set("portal_access", token)


# ---------------------------------------------------------------------------
# T1 — projection shape on empty DB (seeded admin only)
# ---------------------------------------------------------------------------


def test_admin_user_list_returns_seeded_admin_only_on_empty_db(isolated_client):
    c, _ = isolated_client
    _set_admin_cookie(c, _admin_token(c))
    r = c.get("/api/admin/users")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["page_size"] == 50
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["email"] == SEEDED_ADMIN_EMAIL
    assert item["role"] == "admin"
    assert item["is_active"] is True
    assert item["totp_enabled"] is False
    # Story 8.1 LastActiveMiddleware touches the admin row on the first request,
    # so last_active_at may be a recent ISO timestamp OR remain None depending on
    # timing — accept either.
    assert "last_active_at" in item
    assert item["last_active_at"] is None or isinstance(item["last_active_at"], str)
    # Hygiene-rule guard at the response layer.
    assert "password_hash" not in item
    assert "totp_secret" not in item


# ---------------------------------------------------------------------------
# T2 — pagination semantics
# ---------------------------------------------------------------------------


def test_admin_user_list_paginates_correctly(isolated_client):
    c, _ = isolated_client
    engine = get_engine()
    with Session(engine) as s:
        _seed_members(s, 75)
    _set_admin_cookie(c, _admin_token(c))

    r1 = c.get("/api/admin/users", params={"page": 1, "page_size": 25})
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["total"] == 76  # 75 members + 1 seeded admin
    assert body1["page"] == 1
    assert body1["page_size"] == 25
    assert len(body1["items"]) == 25

    r4 = c.get("/api/admin/users", params={"page": 4, "page_size": 25})
    assert r4.status_code == 200
    body4 = r4.json()
    assert body4["total"] == 76
    assert body4["page"] == 4
    assert len(body4["items"]) == 1  # 75 + 1 = 76, page 4 has the remaining 1 row

    # page=0 is rejected by FastAPI Query(ge=1) validation.
    r_invalid = c.get("/api/admin/users", params={"page": 0, "page_size": 25})
    assert r_invalid.status_code == 422


# ---------------------------------------------------------------------------
# T3 — search ilike (case-insensitive)
# ---------------------------------------------------------------------------


def test_admin_user_list_search_filters_by_email_substring(isolated_client):
    c, _ = isolated_client
    engine = get_engine()
    emails = ["alice@a", "alice2@a", "bob@b", "alex@a", "charlie@c"]
    with Session(engine) as s:
        for i, email in enumerate(emails):
            s.add(
                User(
                    email=email,
                    display_name=f"User {i}",
                    role=UserRole.member,
                    password_hash="bcrypt-test-hash",
                )
            )
        s.commit()
    _set_admin_cookie(c, _admin_token(c))

    # Search uses substring ilike. The seeded admin's email is
    # ``admin@localhost.localdomain`` and would match "al" (via "locALhost"),
    # so we pick ``@a`` which captures the alice* / alex@a members but NOT
    # the admin row (whose host part starts with @l).
    r_lower = c.get("/api/admin/users", params={"search": "@a"})
    assert r_lower.status_code == 200
    body_lower = r_lower.json()
    matched = {item["email"] for item in body_lower["items"]}
    assert matched == {"alice@a", "alice2@a", "alex@a"}
    assert body_lower["total"] == 3

    # Case-insensitive: uppercase should yield the exact same set.
    r_upper = c.get("/api/admin/users", params={"search": "@A"})
    assert r_upper.status_code == 200
    assert {item["email"] for item in r_upper.json()["items"]} == {
        "alice@a",
        "alice2@a",
        "alex@a",
    }

    r_empty = c.get("/api/admin/users", params={"search": ""})
    assert r_empty.status_code == 200
    assert r_empty.json()["total"] == 6  # 5 members + 1 seeded admin


# ---------------------------------------------------------------------------
# T4 — sort by email asc
# ---------------------------------------------------------------------------


def test_admin_user_list_sort_by_email_asc(isolated_client):
    c, _ = isolated_client
    engine = get_engine()
    emails = ["zeta@z", "alpha@a", "mike@m", "beta@b", "delta@d"]
    with Session(engine) as s:
        for i, email in enumerate(emails):
            s.add(
                User(
                    email=email,
                    display_name=f"User {i}",
                    role=UserRole.member,
                    password_hash="bcrypt-test-hash",
                )
            )
        s.commit()
    _set_admin_cookie(c, _admin_token(c))

    r = c.get(
        "/api/admin/users",
        params={"sort_by": "email", "sort_order": "asc"},
    )
    assert r.status_code == 200
    ordered = [item["email"] for item in r.json()["items"]]
    expected = sorted([SEEDED_ADMIN_EMAIL, *emails])
    assert ordered == expected


# ---------------------------------------------------------------------------
# T5 — sort by last_active_at desc places NULLs last
# ---------------------------------------------------------------------------


def test_admin_user_list_sort_by_last_active_at_desc_puts_nulls_last(isolated_client):
    c, _ = isolated_client
    engine = get_engine()
    early = datetime.datetime(2026, 5, 15, 10, 0, 0, tzinfo=datetime.UTC)
    late = datetime.datetime(2026, 5, 16, 10, 0, 0, tzinfo=datetime.UTC)
    with Session(engine) as s:
        s.add(
            User(
                email="early@x",
                display_name="Early",
                role=UserRole.member,
                password_hash="bcrypt-test-hash",
                last_active_at=early,
            )
        )
        s.add(
            User(
                email="late@x",
                display_name="Late",
                role=UserRole.member,
                password_hash="bcrypt-test-hash",
                last_active_at=late,
            )
        )
        s.add(
            User(
                email="never@x",
                display_name="Never",
                role=UserRole.member,
                password_hash="bcrypt-test-hash",
                last_active_at=None,
            )
        )
        s.commit()
    _set_admin_cookie(c, _admin_token(c))

    r = c.get(
        "/api/admin/users",
        params={
            "sort_by": "last_active_at",
            "sort_order": "desc",
            # exclude the seeded admin whose last_active_at value is timing-dependent
            "search": "@x",
        },
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert [item["email"] for item in items] == ["late@x", "early@x", "never@x"]


# ---------------------------------------------------------------------------
# T6 — totp_enabled derived from totp_enabled_at
# ---------------------------------------------------------------------------


def test_admin_user_list_derives_totp_enabled_from_totp_enabled_at(isolated_client):
    c, _ = isolated_client
    engine = get_engine()
    enabled_a = datetime.datetime(2026, 5, 10, tzinfo=datetime.UTC)
    enabled_b = datetime.datetime(2026, 5, 15, tzinfo=datetime.UTC)
    with Session(engine) as s:
        s.add(
            User(
                email="no-totp@x",
                display_name="No TOTP",
                role=UserRole.member,
                password_hash="bcrypt-test-hash",
                totp_enabled_at=None,
            )
        )
        s.add(
            User(
                email="totp-a@x",
                display_name="TOTP A",
                role=UserRole.member,
                password_hash="bcrypt-test-hash",
                totp_enabled_at=enabled_a,
            )
        )
        s.add(
            User(
                email="totp-b@x",
                display_name="TOTP B",
                role=UserRole.member,
                password_hash="bcrypt-test-hash",
                totp_enabled_at=enabled_b,
            )
        )
        s.commit()
    _set_admin_cookie(c, _admin_token(c))

    r = c.get(
        "/api/admin/users",
        params={"sort_by": "email", "sort_order": "asc", "search": "@x"},
    )
    assert r.status_code == 200
    by_email = {item["email"]: item["totp_enabled"] for item in r.json()["items"]}
    assert by_email == {"no-totp@x": False, "totp-a@x": True, "totp-b@x": True}


# ---------------------------------------------------------------------------
# T7 — confidentiality-tier columns never appear
# ---------------------------------------------------------------------------


def test_admin_user_list_omits_password_hash_and_totp_secret(isolated_client):
    c, _ = isolated_client
    engine = get_engine()
    with Session(engine) as s:
        s.add(
            User(
                email="leaktest@x",
                display_name="Leak Test",
                role=UserRole.member,
                password_hash="test-hash",
                totp_secret="test-ciphertext",
            )
        )
        s.commit()
    _set_admin_cookie(c, _admin_token(c))

    r = c.get("/api/admin/users")
    assert r.status_code == 200
    body = r.json()
    for item in body["items"]:
        assert "password_hash" not in item
        assert "totp_secret" not in item
    raw = r.text
    assert "test-hash" not in raw
    assert "test-ciphertext" not in raw


# ---------------------------------------------------------------------------
# T8 — auth surface: 403 for member, 401 anonymous
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# T9..T11 — Story 12.2 — optional is_active filter
# ---------------------------------------------------------------------------


def _seed_active_and_inactive_mix(session: Session) -> None:
    """Seed 3 active members + 2 inactive members alongside the seeded admin."""
    for i in range(3):
        session.add(
            User(
                email=f"active{i}@x",
                display_name=f"Active {i}",
                role=UserRole.member,
                password_hash="bcrypt-test-hash",
                is_active=True,
            )
        )
    for i in range(2):
        session.add(
            User(
                email=f"inactive{i}@x",
                display_name=f"Inactive {i}",
                role=UserRole.member,
                password_hash="bcrypt-test-hash",
                is_active=False,
            )
        )
    session.commit()


def test_admin_user_list_is_active_true_filters_out_inactive(isolated_client):
    """Story 12.2 AC-1: `?is_active=true` returns only active rows."""
    c, _ = isolated_client
    engine = get_engine()
    with Session(engine) as s:
        _seed_active_and_inactive_mix(s)
    _set_admin_cookie(c, _admin_token(c))

    r = c.get("/api/admin/users", params={"is_active": "true", "search": "@x"})
    assert r.status_code == 200, r.text
    body = r.json()
    emails = {item["email"] for item in body["items"]}
    # seeded admin filtered out via `search=@x`; only the 3 active members remain.
    assert emails == {"active0@x", "active1@x", "active2@x"}
    assert body["total"] == 3
    for item in body["items"]:
        assert item["is_active"] is True


def test_admin_user_list_is_active_false_returns_only_inactive(isolated_client):
    """Story 12.2 AC-1: `?is_active=false` returns only deactivated rows."""
    c, _ = isolated_client
    engine = get_engine()
    with Session(engine) as s:
        _seed_active_and_inactive_mix(s)
    _set_admin_cookie(c, _admin_token(c))

    r = c.get("/api/admin/users", params={"is_active": "false", "search": "@x"})
    assert r.status_code == 200, r.text
    body = r.json()
    emails = {item["email"] for item in body["items"]}
    assert emails == {"inactive0@x", "inactive1@x"}
    assert body["total"] == 2
    for item in body["items"]:
        assert item["is_active"] is False


def test_admin_user_list_without_is_active_param_returns_all_rows(isolated_client):
    """Story 12.2 AC-1: no `is_active` param → no filter (legacy behavior)."""
    c, _ = isolated_client
    engine = get_engine()
    with Session(engine) as s:
        _seed_active_and_inactive_mix(s)
    _set_admin_cookie(c, _admin_token(c))

    r = c.get("/api/admin/users", params={"search": "@x"})
    assert r.status_code == 200, r.text
    body = r.json()
    emails = {item["email"] for item in body["items"]}
    # All 5 (3 active + 2 inactive) seeded rows appear when the filter is absent.
    assert emails == {
        "active0@x",
        "active1@x",
        "active2@x",
        "inactive0@x",
        "inactive1@x",
    }
    assert body["total"] == 5


def test_admin_user_list_returns_403_for_member_role(isolated_client):
    c, _ = isolated_client
    member_token = encode_token(
        subject=str(uuid.uuid4()),
        role="member",
        secret=JWT_TEST_SECRET,
        ttl_minutes=30,
    )
    c.cookies.set("portal_access", member_token)
    r_member = c.get("/api/admin/users")
    assert r_member.status_code == 403
    assert r_member.json()["detail"] == "admin_required"

    c.cookies.clear()
    r_anon = c.get("/api/admin/users")
    assert r_anon.status_code == 401
    assert r_anon.json()["detail"] == "missing_access"
