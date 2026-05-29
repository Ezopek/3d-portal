"""Initiative 19 Story 31.2 — public /api/spools/* route surface tests.

Covers:
- AC-6 auth gate (401 anonymous + 401 invalid token, member + admin + agent 200).
- AC-3 + AC-4 projection from the canonical Redis cache through public DTOs.
- AC-3 cold-cache + Spoolman-down soft-fail (200 + empty arrays per FR19-FAILURE-1).
- AC-3 warm-cache + stale-serve (200 + populated body + old last_success_ts).
- AC-5 cost-data carry-through (every Decision AF field appears verbatim).
- AC-7 + AC-10 grep invariants: _PUBLIC_ROUTES byte-identical;
  no auth Depends on /api/share/<token>/* handlers (NFR10 preservation).

Test transport: httpx.AsyncClient + ASGITransport so the app and the
``fakeredis.aioredis`` instance live on the same event loop (TestClient's
sync portal would bind redis to a different loop than the test setup).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import fakeredis.aioredis
import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.auth.jwt import encode_token
from app.main import _PUBLIC_ROUTES, create_app
from app.modules.spools.models import (
    SpoolmanFilament,
    SpoolmanSnapshot,
    SpoolmanSpool,
    SpoolmanVendor,
)


@pytest_asyncio.fixture
async def asgi_app(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[AsyncClient, fakeredis.aioredis.FakeRedis]]:
    """Per-test app + fakeredis bound to the SAME event loop the requests run on.

    AsyncClient(transport=ASGITransport(app)) drives the app directly from the
    test's loop, so the fakeredis instance we create here can be both seeded by
    the test and accessed by the route handlers without the "Queue bound to a
    different loop" runtime error.
    """
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    monkeypatch.setenv("TOTP_FERNET_KEY", "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM=")

    from app.core.config import get_settings
    from app.core.db.session import get_engine, init_schema

    get_settings.cache_clear()
    get_engine.cache_clear()

    app = create_app()
    init_schema(get_engine())  # lifespan would do this in non-prod; we bypass it.

    fake = fakeredis.aioredis.FakeRedis()
    factory = MagicMock()
    factory.get = MagicMock(return_value=fake)

    async def _aclose() -> None:
        return None

    factory.aclose = _aclose
    app.state.redis = factory

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"X-Portal-Client": "web"},
    ) as ac:
        yield ac, fake

    get_settings.cache_clear()
    get_engine.cache_clear()


def _member_cookie() -> str:
    return encode_token(
        subject=str(uuid.uuid4()),
        role="member",
        secret="test",
        ttl_minutes=30,
    )


def _admin_cookie() -> str:
    return encode_token(
        subject=str(uuid.uuid4()),
        role="admin",
        secret="test",
        ttl_minutes=30,
    )


def _agent_cookie() -> str:
    return encode_token(
        subject=str(uuid.uuid4()),
        role="agent",
        secret="test",
        ttl_minutes=30,
    )


def _expired_cookie() -> str:
    return encode_token(
        subject=str(uuid.uuid4()),
        role="member",
        secret="test",
        ttl_minutes=-1,
    )


def _build_snapshot() -> SpoolmanSnapshot:
    return SpoolmanSnapshot(
        spools=[
            SpoolmanSpool(
                id=1,
                filament_id=10,
                price=42.5,
                remaining_weight=850.0,
                initial_weight=1000.0,
                used_weight=150.0,
                spool_weight=200.0,
                first_used=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
                last_used=datetime(2026, 5, 28, 14, 30, tzinfo=UTC),
                archived=False,
                lot_nr="ABC123",
            ),
            SpoolmanSpool(
                id=2,
                filament_id=11,
                price=None,
                remaining_weight=138.9,
                initial_weight=1000.0,
                used_weight=861.1,
                spool_weight=200.0,
                first_used=None,
                last_used=None,
                archived=True,
                lot_nr=None,
            ),
        ],
        filaments=[
            SpoolmanFilament(
                id=10,
                name="PLA Speed Matt White",
                vendor_id=100,
                vendor_name="Bambu Lab",
                material="PLA",
                color_hex="FFFFFF",
                price=99.9,
                weight=1000.0,
                spool_weight=200.0,
            ),
            SpoolmanFilament(
                id=11,
                name="PCTG Army Green",
                vendor_id=101,
                vendor_name="Polymaker",
                material="PCTG",
                color_hex="4B5320",
                price=140.0,
                weight=1000.0,
                spool_weight=200.0,
            ),
        ],
        vendors=[
            SpoolmanVendor(id=100, name="Bambu Lab"),
            SpoolmanVendor(id=101, name="Polymaker"),
        ],
        fetched_at=datetime(2026, 5, 29, 10, 0, tzinfo=UTC),
    )


async def _seed_cache(
    fake: fakeredis.aioredis.FakeRedis,
    snapshot: SpoolmanSnapshot,
    last_success_ts: datetime,
) -> None:
    await fake.set("spools:summary:v1", snapshot.model_dump_json(), ex=30)
    await fake.set("spools:summary:last-success-ts", last_success_ts.isoformat())


# ---------------------------------------------------------------------------
# TEST-1..3: anonymous → 401 on every route.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_anonymous_returns_401(asgi_app):
    ac, _ = asgi_app
    r = await ac.get("/api/spools/summary")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_spools_anonymous_returns_401(asgi_app):
    ac, _ = asgi_app
    r = await ac.get("/api/spools/spools")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_filaments_anonymous_returns_401(asgi_app):
    ac, _ = asgi_app
    r = await ac.get("/api/spools/filaments")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# TEST-4: warm cache + member → 200 + projected shape.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_member_returns_200_with_cached_payload(asgi_app):
    ac, fake = asgi_app
    snapshot = _build_snapshot()
    last_success = datetime(2026, 5, 29, 10, 0, 30, tzinfo=UTC)
    await _seed_cache(fake, snapshot, last_success)

    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.get("/api/spools/summary")

    assert r.status_code == 200
    body = r.json()
    assert len(body["spools"]) == 2
    assert len(body["filaments"]) == 2
    assert len(body["vendors"]) == 2
    assert body["fetched_at"] is not None
    assert body["last_success_ts"] is not None
    # Field-level checks: ids match, vendor flatten produced correct labels.
    assert body["filaments"][0]["vendor_name"] == "Bambu Lab"
    assert body["vendors"][0]["name"] == "Bambu Lab"
    assert body["spools"][1]["archived"] is True


# ---------------------------------------------------------------------------
# TEST-5: every Decision AF cost-relevant field surfaces verbatim.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_carries_cost_relevant_fields_end_to_end(asgi_app):
    ac, fake = asgi_app
    snapshot = _build_snapshot()
    await _seed_cache(fake, snapshot, datetime(2026, 5, 29, 10, 0, 30, tzinfo=UTC))

    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.get("/api/spools/summary")
    assert r.status_code == 200
    body = r.json()

    spool_one = body["spools"][0]
    assert spool_one["price"] == 42.5
    assert spool_one["remaining_weight"] == 850.0
    assert spool_one["initial_weight"] == 1000.0
    assert spool_one["used_weight"] == 150.0
    assert spool_one["spool_weight"] == 200.0
    assert spool_one["lot_nr"] == "ABC123"
    assert spool_one["first_used"] is not None
    assert spool_one["last_used"] is not None

    filament_one = body["filaments"][0]
    assert filament_one["price"] == 99.9
    assert filament_one["weight"] == 1000.0
    assert filament_one["spool_weight"] == 200.0
    assert filament_one["material"] == "PLA"
    assert filament_one["color_hex"] == "FFFFFF"


# ---------------------------------------------------------------------------
# TEST-6: cold cache + Spoolman down → 200 + empty arrays + null timestamps.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_cold_cache_returns_200_with_empty_arrays(asgi_app, monkeypatch):
    ac, _ = asgi_app

    async def _raise(*args, **kwargs):
        raise httpx.ConnectError("simulated outage")

    monkeypatch.setattr("app.modules.spools.client.SpoolmanClient._get", _raise, raising=True)

    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.get("/api/spools/summary")
    assert r.status_code == 200
    body = r.json()
    assert body == {
        "spools": [],
        "filaments": [],
        "vendors": [],
        "fetched_at": None,
        "last_success_ts": None,
    }


# ---------------------------------------------------------------------------
# TEST-7: warm cache + Spoolman down → 200 + populated body + old timestamp.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_warm_cache_with_old_last_success_ts_still_returns_200(asgi_app, monkeypatch):
    ac, fake = asgi_app
    snapshot = _build_snapshot()
    five_minutes_ago = datetime.now(UTC) - timedelta(minutes=5)
    await _seed_cache(fake, snapshot, five_minutes_ago)

    async def _raise(*args, **kwargs):
        raise httpx.ConnectError("simulated outage")

    monkeypatch.setattr("app.modules.spools.client.SpoolmanClient._get", _raise, raising=True)

    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.get("/api/spools/summary")
    assert r.status_code == 200
    body = r.json()
    assert len(body["spools"]) == 2
    # Stale-serve: last_success_ts preserves the 5-minute-old value.
    returned = datetime.fromisoformat(body["last_success_ts"])
    assert abs((returned - five_minutes_ago).total_seconds()) < 1.0


# ---------------------------------------------------------------------------
# TEST-8 + TEST-9: list-slice endpoints.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_spools_member_returns_200_with_projected_list(asgi_app):
    ac, fake = asgi_app
    snapshot = _build_snapshot()
    await _seed_cache(fake, snapshot, datetime(2026, 5, 29, 10, 0, 30, tzinfo=UTC))

    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.get("/api/spools/spools")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 2
    assert body[0]["id"] == 1
    assert body[0]["filament_id"] == 10
    assert body[0]["price"] == 42.5
    assert body[0]["remaining_weight"] == 850.0


@pytest.mark.asyncio
async def test_filaments_member_returns_200_with_projected_list(asgi_app):
    ac, fake = asgi_app
    snapshot = _build_snapshot()
    await _seed_cache(fake, snapshot, datetime(2026, 5, 29, 10, 0, 30, tzinfo=UTC))

    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.get("/api/spools/filaments")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 2
    assert body[0]["id"] == 10
    assert body[0]["vendor_name"] == "Bambu Lab"
    assert body[0]["price"] == 99.9
    assert body[0]["weight"] == 1000.0
    assert body[0]["spool_weight"] == 200.0


# ---------------------------------------------------------------------------
# TEST-10: admin cookie also authorized; agent cookie also authorized.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_token_also_authorized(asgi_app):
    ac, fake = asgi_app
    snapshot = _build_snapshot()
    await _seed_cache(fake, snapshot, datetime(2026, 5, 29, 10, 0, 30, tzinfo=UTC))

    ac.cookies.set("portal_access", _admin_cookie())
    r = await ac.get("/api/spools/summary")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_agent_token_also_authorized(asgi_app):
    ac, fake = asgi_app
    snapshot = _build_snapshot()
    await _seed_cache(fake, snapshot, datetime(2026, 5, 29, 10, 0, 30, tzinfo=UTC))

    ac.cookies.set("portal_access", _agent_cookie())
    r = await ac.get("/api/spools/summary")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# TEST-11: invalid token → 401.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_token_returns_401(asgi_app):
    ac, _ = asgi_app
    ac.cookies.set("portal_access", "garbage-not-a-jwt")
    r = await ac.get("/api/spools/summary")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_expired_token_returns_401(asgi_app):
    ac, _ = asgi_app
    ac.cookies.set("portal_access", _expired_cookie())
    r = await ac.get("/api/spools/summary")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# TEST-12: NFR10 grep invariant — no auth dep on /api/share/<token>/* handlers.
# ---------------------------------------------------------------------------


def test_share_router_files_have_no_auth_depends_on_anon_handlers():
    """Re-asserts the NFR10 credentialless contract.

    Reads ``apps/api/app/modules/share/router.py`` as text and checks every
    handler decorated with ``@router.get("/{token}...")`` (relative to the
    ``/api/share`` prefix). None of them may carry ``current_user`` /
    ``current_admin`` / ``current_member_or_admin`` symbols in the next ~2500
    chars (the handler body window). Story 31.2 leaves this file byte-
    identical to its pre-31.2 state — this test guards against a future
    PR that adds the new spools auth pattern to share by reflex.
    """
    import re

    share_router_path = (
        Path(__file__).resolve().parent.parent / "app" / "modules" / "share" / "router.py"
    )
    text = share_router_path.read_text()
    handler_pattern = re.compile(
        r'@router\.(get|post|put|delete|patch)\("/(\{token\}|\{token\}/[^"]*)"',
        re.MULTILINE,
    )
    violations: list[str] = []
    for match in handler_pattern.finditer(text):
        window = text[match.start() : match.start() + 2500]
        for symbol in ("current_user", "current_admin", "current_member_or_admin"):
            if symbol in window:
                violations.append(f"{match.group(0)} carries '{symbol}' within next 2500 chars")
                break
    assert not violations, (
        "NFR10 credentialless contract regression: /api/share/<token>/* handler "
        f"references an auth dep. Violations: {violations}"
    )


# ---------------------------------------------------------------------------
# TEST-13: _PUBLIC_ROUTES tuple byte-identical to pre-31.2.
# ---------------------------------------------------------------------------


def test_public_routes_tuple_unchanged():
    assert _PUBLIC_ROUTES == (
        "/api/health",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/auth/refresh",
        "/api/auth/register",
        "/api/auth/2fa/verify",
        "/api/auth/password-reset",
        "/api/share/{token}",
        "/api/share/{token}/files",
        "/api/share/{token}/files/{file_id}/content",
    )
