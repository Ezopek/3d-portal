"""Initiative 19 Story 31.1 — pytest coverage for the Spoolman client +
SpoolsService cache topology + arq cron registration.

Tests realize AC-10 verbatim: TEST-1..TEST-11 unit suite + TEST-LIVE-1
env-gated live integration. AC-9 leader-election is exercised by TEST-3;
AC-6 observability labels by TEST-9 + TEST-10; AC-8 cron registration by
TEST-11.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import fakeredis.aioredis
import httpx
import pytest

from app.core.config import Settings, get_settings
from app.core.redis import RedisFactory
from app.modules.spools.client import (
    SpoolmanCircuitOpenError,
    SpoolmanClient,
)
from app.modules.spools.models import (
    SpoolmanFilament,
    SpoolmanSnapshot,
    SpoolmanSpool,
    SpoolmanVendor,
)
from app.modules.spools.service import SpoolsService

_CACHE_KEY = "spools:summary:v1"
_LAST_SUCCESS_KEY = "spools:summary:last-success-ts"
_LOCK_KEY = "spools:poll-lock"


class _CaptureHandler(logging.Handler):
    """Per-test logging handler that records LogRecords for assertion.

    Attached directly to the module logger so it survives the suite-wide
    ``configure_logging()`` reset (the API lifespan replaces root handlers,
    which evicts ``caplog``'s capture — see conftest's ``client`` fixture).
    """

    def __init__(self, logger_name: str, level: int) -> None:
        super().__init__(level=level)
        self.records: list[logging.LogRecord] = []
        self._logger = logging.getLogger(logger_name)
        self._prior_level = self._logger.level
        self._prior_disabled = self._logger.disabled
        # Some full-suite tests exercise logging configuration paths that can
        # leave named loggers disabled. This capture helper asserts the
        # Story 31.1 AC-6 log contract directly on the module logger, so it
        # must restore an enabled state for the duration of the assertion and
        # then put the prior logger state back in ``detach()``.
        self._logger.disabled = False
        self._logger.setLevel(level)
        self._logger.addHandler(self)

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def detach(self) -> None:
        self._logger.removeHandler(self)
        self._logger.setLevel(self._prior_level)
        self._logger.disabled = self._prior_disabled


def _attach_capture_handler(logger_name: str, *, level: int = logging.INFO) -> _CaptureHandler:
    return _CaptureHandler(logger_name, level)


# ---- T7.2 — settings fixture ------------------------------------------------


@pytest.fixture
def spoolman_settings_overrides(monkeypatch: pytest.MonkeyPatch):
    """Set SPOOLMAN_URL + SPOOLMAN_AUTH_TOKEN via env and clear the cached
    ``Settings`` singleton so the next ``get_settings()`` sees them."""

    def _apply(url: str = "http://spoolman:8000", token: str = "") -> Settings:
        monkeypatch.setenv("SPOOLMAN_URL", url)
        monkeypatch.setenv("SPOOLMAN_AUTH_TOKEN", token)
        get_settings.cache_clear()
        return get_settings()

    yield _apply
    get_settings.cache_clear()


# ---- T7.3 — mock_spoolman_client fixture + helper handlers -----------------


def _spool_fixture(id_: int, name_suffix: str = "") -> dict[str, Any]:
    return {
        "id": id_,
        "filament_id": 100 + id_,
        "price": 25.0 + id_,
        "remaining_weight": 750.0 - id_,
        "initial_weight": 1000.0,
        "used_weight": 250.0 + id_,
        "spool_weight": 200.0,
        "first_used": "2026-01-10T12:00:00+00:00",
        "last_used": "2026-05-29T08:00:00+00:00",
        "archived": False,
        "lot_nr": f"LOT-{id_:03d}{name_suffix}",
    }


def _filament_fixture(id_: int) -> dict[str, Any]:
    return {
        "id": id_,
        "name": f"PLA-Test-Mat-{id_}",
        "vendor_id": 1,
        "vendor_name": "TestVendor",
        "material": "PLA",
        "color_hex": f"AB{id_:04X}",
        "price": 20.0,
        "weight": 1000.0,
        "spool_weight": 200.0,
    }


def _vendor_fixture() -> dict[str, Any]:
    return {"id": 1, "name": "TestVendor"}


def make_happy_handler(
    *,
    spools: list[dict[str, Any]] | None = None,
    filaments: list[dict[str, Any]] | None = None,
    vendors: list[dict[str, Any]] | None = None,
):
    spools = spools if spools is not None else [_spool_fixture(i) for i in range(1, 4)]
    filaments = filaments if filaments is not None else [_filament_fixture(i) for i in range(1, 3)]
    vendors = vendors if vendors is not None else [_vendor_fixture()]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/spool":
            return httpx.Response(200, json=spools)
        if request.url.path == "/api/v1/filament":
            return httpx.Response(200, json=filaments)
        if request.url.path == "/api/v1/vendor":
            return httpx.Response(200, json=vendors)
        return httpx.Response(404, json={"detail": "not found"})

    return handler


def make_error_handler(exc: type[Exception] = httpx.ConnectError, message: str = "boom"):
    def handler(request: httpx.Request) -> httpx.Response:
        raise exc(message)

    return handler


def make_client_with_handler(
    handler, *, base_url: str = "http://spoolman:8000", auth_token: str = ""
) -> SpoolmanClient:
    client = SpoolmanClient(base_url=base_url, auth_token=auth_token)
    # Swap in MockTransport — keeps the SpoolmanClient signature stable while
    # letting tests intercept the network surface.
    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        timeout=httpx.Timeout(5.0),
    )
    return client


@pytest.fixture
async def fake_redis_factory():
    fake = fakeredis.aioredis.FakeRedis()
    factory = RedisFactory(client=fake)
    yield factory, fake
    await fake.aclose()


async def test_models_flatten_live_spoolman_nested_vendor_and_filament_shape() -> None:
    """Regression from live Spoolman 0.23.1 smoke: list endpoints return
    nested ``vendor`` / ``filament`` objects, while the portal cache schema
    carries flattened IDs/names for downstream DTO projection.
    """
    filament = SpoolmanFilament.model_validate(
        {
            "id": 18,
            "name": "PLA Speed Matt White",
            "vendor": {"id": 2, "name": "Rosa3D"},
            "vendor_id": None,
            "vendor_name": None,
            "material": "PLA",
            "color_hex": "ffffff",
            "price": 79.9,
            "weight": 1000.0,
            "spool_weight": 250.0,
        }
    )
    spool = SpoolmanSpool.model_validate(
        {
            "id": 21,
            "filament": {"id": 18, "spool_weight": 250.0},
            "filament_id": None,
            "spool_weight": None,
            "remaining_weight": 138.94,
            "initial_weight": 1000.0,
            "used_weight": 861.06,
            "archived": False,
        }
    )

    assert filament.vendor_id == 2
    assert filament.vendor_name == "Rosa3D"
    assert spool.filament_id == 18
    assert spool.spool_weight == 250.0


# ---- TEST-1 -----------------------------------------------------------------


async def test_client_list_spools_happy_path_parses_response() -> None:
    """TEST-1 — ``list_spools()`` parses a 3-spool fixture into typed models
    with the full Decision AF cost-relevant field surface populated."""
    handler = make_happy_handler()
    client = make_client_with_handler(handler)
    try:
        result = await client.list_spools()
    finally:
        await client.aclose()
    assert len(result) == 3
    assert all(isinstance(s, SpoolmanSpool) for s in result)
    first = result[0]
    assert first.id == 1
    assert first.filament_id == 101
    assert first.remaining_weight == 749.0
    assert first.price == 26.0
    assert first.lot_nr == "LOT-001"
    assert first.initial_weight == 1000.0
    assert first.used_weight == 251.0
    assert first.spool_weight == 200.0


# ---- TEST-2 -----------------------------------------------------------------


async def test_client_authorization_header_omitted_when_token_empty() -> None:
    """TEST-2 — Authorization header is absent on empty token, present and
    correctly formatted on non-empty token (AC-3)."""
    seen_headers: list[httpx.Headers] = []

    def inspector(request: httpx.Request) -> httpx.Response:
        seen_headers.append(request.headers)
        return httpx.Response(200, json=[])

    # Empty token — no Authorization header.
    client_empty = make_client_with_handler(inspector, auth_token="")
    try:
        await client_empty.list_spools()
    finally:
        await client_empty.aclose()
    assert seen_headers, "handler was never invoked"
    assert "authorization" not in {k.lower() for k in seen_headers[-1]}

    # Non-empty token — Authorization: Bearer <token>.
    client_with_token = make_client_with_handler(inspector, auth_token="sekret-token")
    try:
        await client_with_token.list_filaments()
    finally:
        await client_with_token.aclose()
    assert seen_headers[-1].get("authorization") == "Bearer sekret-token"


# ---- TEST-3 -----------------------------------------------------------------


async def test_service_refresh_summary_under_lock_contention_runs_once(
    fake_redis_factory,
) -> None:
    """TEST-3 — two parallel ``refresh_summary()`` calls: exactly one acquires
    the SETNX lock + writes; the other returns ``None`` without calling any
    client method. AC-9 enforcement."""
    factory, _fake = fake_redis_factory

    mock_client = AsyncMock(spec=SpoolmanClient)
    mock_client.list_spools.return_value = [SpoolmanSpool.model_validate(_spool_fixture(1))]
    mock_client.list_filaments.return_value = [
        SpoolmanFilament.model_validate(_filament_fixture(1))
    ]
    mock_client.list_vendors.return_value = [SpoolmanVendor.model_validate(_vendor_fixture())]

    service = SpoolsService(redis_factory=factory, client=mock_client)

    results = await asyncio.gather(
        asyncio.create_task(service.refresh_summary()),
        asyncio.create_task(service.refresh_summary()),
    )
    non_none = [r for r in results if r is not None]
    assert len(non_none) == 1, f"expected exactly one winner, got {results}"
    assert isinstance(non_none[0], SpoolmanSnapshot)
    # Each list_* method called exactly once total across the two parallel
    # tasks — the loser short-circuited before touching the client.
    assert mock_client.list_spools.call_count == 1
    assert mock_client.list_filaments.call_count == 1
    assert mock_client.list_vendors.call_count == 1
    assert mock_client.list_spools.call_args.kwargs == {"lock_held": True}
    assert mock_client.list_filaments.call_args.kwargs == {"lock_held": True}
    assert mock_client.list_vendors.call_args.kwargs == {"lock_held": True}


# ---- TEST-4 -----------------------------------------------------------------


async def test_service_get_summary_cache_warm_skips_client(fake_redis_factory) -> None:
    """TEST-4 — warm cache: ``get_summary()`` returns the deserialized snapshot
    without calling any client method."""
    factory, fake = fake_redis_factory
    snapshot = SpoolmanSnapshot(
        spools=[SpoolmanSpool.model_validate(_spool_fixture(7))],
        filaments=[SpoolmanFilament.model_validate(_filament_fixture(7))],
        vendors=[SpoolmanVendor.model_validate(_vendor_fixture())],
        fetched_at=datetime(2026, 5, 29, 9, 0, tzinfo=UTC),
    )
    await fake.set(_CACHE_KEY, snapshot.model_dump_json())

    mock_client = AsyncMock(spec=SpoolmanClient)
    service = SpoolsService(redis_factory=factory, client=mock_client)

    result = await service.get_summary()

    assert result is not None
    assert len(result.spools) == 1
    assert result.spools[0].id == 7
    mock_client.list_spools.assert_not_called()
    mock_client.list_filaments.assert_not_called()
    mock_client.list_vendors.assert_not_called()


# ---- TEST-5 -----------------------------------------------------------------


async def test_service_get_summary_cache_miss_triggers_single_live_fetch(
    fake_redis_factory,
) -> None:
    """TEST-5 — cold cache: ``get_summary()`` triggers one live fetch, the
    cache + ``last-success-ts`` are populated, and ``list_spools`` is called
    exactly once."""
    factory, fake = fake_redis_factory
    assert await fake.get(_CACHE_KEY) is None

    mock_client = AsyncMock(spec=SpoolmanClient)
    mock_client.list_spools.return_value = [SpoolmanSpool.model_validate(_spool_fixture(2))]
    mock_client.list_filaments.return_value = [
        SpoolmanFilament.model_validate(_filament_fixture(2))
    ]
    mock_client.list_vendors.return_value = [SpoolmanVendor.model_validate(_vendor_fixture())]

    service = SpoolsService(redis_factory=factory, client=mock_client)

    result = await service.get_summary()

    assert result is not None
    assert result.spools[0].id == 2
    assert mock_client.list_spools.call_count == 1
    assert await fake.get(_CACHE_KEY) is not None
    assert await fake.get(_LAST_SUCCESS_KEY) is not None


# ---- TEST-6 -----------------------------------------------------------------


async def test_service_get_summary_cache_empty_and_spoolman_down_returns_none(
    fake_redis_factory,
) -> None:
    """TEST-6 — FR19-FAILURE-1 cold-start contract: empty cache + Spoolman
    down → ``get_summary()`` returns ``None`` without raising, cache stays
    empty, ``last-success-ts`` stays absent."""
    factory, fake = fake_redis_factory

    mock_client = AsyncMock(spec=SpoolmanClient)
    mock_client.list_spools.side_effect = httpx.ConnectError("upstream unreachable")
    mock_client.list_filaments.side_effect = httpx.ConnectError("upstream unreachable")
    mock_client.list_vendors.side_effect = httpx.ConnectError("upstream unreachable")

    service = SpoolsService(redis_factory=factory, client=mock_client)

    result = await service.get_summary()

    assert result is None
    assert await fake.get(_CACHE_KEY) is None
    assert await fake.get(_LAST_SUCCESS_KEY) is None


async def test_service_get_summary_cache_empty_and_spoolman_schema_drift_returns_none(
    fake_redis_factory,
) -> None:
    """Regression for Codex review: malformed/schema-drift Spoolman JSON
    is logged by the client and soft-fails at the service boundary instead of
    escaping from ``get_summary()`` as a cascading request-path 500.
    """
    factory, fake = fake_redis_factory

    def malformed_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/spool":
            return httpx.Response(200, json=[{"not_id": "schema drift"}])
        return httpx.Response(200, json=[])

    client = make_client_with_handler(malformed_handler)
    try:
        service = SpoolsService(redis_factory=factory, client=client)
        assert await service.get_summary() is None
        assert await fake.get(_CACHE_KEY) is None
        assert await fake.get(_LAST_SUCCESS_KEY) is None
    finally:
        await client.aclose()


async def test_service_get_summary_cold_cache_lock_contention_waits_for_leader(
    fake_redis_factory,
) -> None:
    """Cold-cache read path waits briefly for a concurrent lock holder to
    populate Redis, avoiding a false unavailable state when Spoolman is healthy.
    """
    factory, _fake = fake_redis_factory
    release = asyncio.Event()

    mock_client = AsyncMock(spec=SpoolmanClient)

    async def slow_spools(*, lock_held: bool | None = None):
        await release.wait()
        return [SpoolmanSpool.model_validate(_spool_fixture(4))]

    mock_client.list_spools.side_effect = slow_spools
    mock_client.list_filaments.return_value = [
        SpoolmanFilament.model_validate(_filament_fixture(4))
    ]
    mock_client.list_vendors.return_value = [SpoolmanVendor.model_validate(_vendor_fixture())]

    service = SpoolsService(redis_factory=factory, client=mock_client)
    first = asyncio.create_task(service.get_summary())
    await asyncio.sleep(0)
    second = asyncio.create_task(service.get_summary())
    release.set()

    first_result, second_result = await asyncio.gather(first, second)

    assert first_result is not None
    assert second_result is not None
    assert first_result.spools[0].id == 4
    assert second_result.spools[0].id == 4
    assert mock_client.list_spools.call_count == 1


async def test_service_get_summary_lock_release_race_retries_live_fetch(
    fake_redis_factory,
) -> None:
    """Cold-cache race: the leader can release the lock before the contender
    observes it. The contender must still perform a final live refresh instead
    of returning a false unavailable state.
    """
    factory, _fake = fake_redis_factory
    mock_client = AsyncMock(spec=SpoolmanClient)
    mock_client.list_spools.return_value = [SpoolmanSpool.model_validate(_spool_fixture(5))]
    mock_client.list_filaments.return_value = [
        SpoolmanFilament.model_validate(_filament_fixture(5))
    ]
    mock_client.list_vendors.return_value = [SpoolmanVendor.model_validate(_vendor_fixture())]

    service = SpoolsService(redis_factory=factory, client=mock_client)
    original_refresh = service.refresh_summary
    calls = 0

    async def racey_refresh():
        nonlocal calls
        calls += 1
        if calls == 1:
            return None
        return await original_refresh()

    service.refresh_summary = racey_refresh  # type: ignore[method-assign]

    result = await service.get_summary()

    assert result is not None
    assert result.spools[0].id == 5
    assert calls == 2


async def test_service_refresh_summary_lock_release_is_ownership_safe_under_ttl_expiry_race(
    fake_redis_factory,
) -> None:
    """Regression for adversarial review: if the SETNX lease expires mid-poll
    and a second worker acquires its own lock, the first worker's ``finally``
    MUST NOT delete the second worker's lock value. Lock release has to be
    ownership-safe (per-refresh unique token + compare-and-delete) rather
    than an unconditional ``DEL`` of the contract key.
    """
    factory, fake = fake_redis_factory
    intruder_token = b"intruder-token-v2"

    mock_client = AsyncMock(spec=SpoolmanClient)

    async def hijack_lock(*, lock_held: bool | None = None):
        # Simulate TTL expiry + second-worker takeover while the first poll
        # is still in flight: overwrite the lock value with a foreign token
        # the way Redis would after our lease expired and another worker
        # SETNX'd a fresh value of its own.
        await fake.set(_LOCK_KEY, intruder_token)
        return [SpoolmanSpool.model_validate(_spool_fixture(1))]

    mock_client.list_spools.side_effect = hijack_lock
    mock_client.list_filaments.return_value = [
        SpoolmanFilament.model_validate(_filament_fixture(1))
    ]
    mock_client.list_vendors.return_value = [SpoolmanVendor.model_validate(_vendor_fixture())]

    service = SpoolsService(redis_factory=factory, client=mock_client)
    await service.refresh_summary()

    # The intruder's lock MUST survive — the first worker's finally has to
    # compare-and-delete on its own token, not unconditionally ``DEL`` the
    # contract key.
    assert await fake.get(_LOCK_KEY) == intruder_token


async def test_service_refresh_summary_drains_sibling_calls_before_lock_release(
    fake_redis_factory,
) -> None:
    """Regression for review: if one Spoolman call fails, ``refresh_summary``
    drains sibling calls before deleting the SETNX lock, avoiding in-flight
    calls against a soon-to-close shared client.
    """
    factory, fake = fake_redis_factory
    sibling_finished = False

    mock_client = AsyncMock(spec=SpoolmanClient)

    async def fail_fast(*, lock_held: bool | None = None):
        raise httpx.ConnectError("spool endpoint down")

    async def slow_filaments(*, lock_held: bool | None = None):
        nonlocal sibling_finished
        await asyncio.sleep(0.05)
        sibling_finished = True
        return [SpoolmanFilament.model_validate(_filament_fixture(4))]

    mock_client.list_spools.side_effect = fail_fast
    mock_client.list_filaments.side_effect = slow_filaments
    mock_client.list_vendors.return_value = [SpoolmanVendor.model_validate(_vendor_fixture())]

    service = SpoolsService(redis_factory=factory, client=mock_client)

    assert await service.refresh_summary() is None
    assert sibling_finished is True
    assert await fake.exists(_LOCK_KEY) == 0


# ---- TEST-7 -----------------------------------------------------------------


async def test_service_get_summary_cache_warm_and_spoolman_down_serves_stale(
    fake_redis_factory,
) -> None:
    """TEST-7 — FR19-FAILURE-1 stale-serve contract: warm cache + Spoolman
    down → ``get_summary()`` returns the cached snapshot and
    ``get_last_success_ts()`` returns the original timestamp untouched."""
    factory, fake = fake_redis_factory
    stale_ts = datetime(2026, 5, 29, 8, 55, tzinfo=UTC)
    snapshot = SpoolmanSnapshot(
        spools=[SpoolmanSpool.model_validate(_spool_fixture(9))],
        filaments=[SpoolmanFilament.model_validate(_filament_fixture(9))],
        vendors=[SpoolmanVendor.model_validate(_vendor_fixture())],
        fetched_at=stale_ts,
    )
    await fake.set(_CACHE_KEY, snapshot.model_dump_json())
    await fake.set(_LAST_SUCCESS_KEY, stale_ts.isoformat())

    mock_client = AsyncMock(spec=SpoolmanClient)
    mock_client.list_spools.side_effect = httpx.ConnectError("upstream unreachable")
    mock_client.list_filaments.side_effect = httpx.ConnectError("upstream unreachable")
    mock_client.list_vendors.side_effect = httpx.ConnectError("upstream unreachable")

    service = SpoolsService(redis_factory=factory, client=mock_client)

    result = await service.get_summary()
    last = await service.get_last_success_ts()

    assert result is not None
    assert result.spools[0].id == 9
    assert last == stale_ts


# ---- TEST-8 -----------------------------------------------------------------


async def test_client_circuit_breaker_opens_after_three_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TEST-8 — 3 consecutive failures open the breaker; the 4th call short-
    circuits without an HTTP attempt; reopens after the 30s window elapses."""
    hits = 0

    def failing_handler(request: httpx.Request) -> httpx.Response:
        nonlocal hits
        hits += 1
        raise httpx.ConnectError("flapping")

    client = make_client_with_handler(failing_handler)

    # Control the monotonic clock the client uses for the open-window math.
    fake_now = [0.0]

    def fake_monotonic() -> float:
        return fake_now[0]

    monkeypatch.setattr("app.modules.spools.client.time.monotonic", fake_monotonic)

    try:
        for _ in range(3):
            with pytest.raises(httpx.ConnectError):
                await client.list_spools()
        assert hits == 3

        # Breaker is now open — 4th call short-circuits.
        with pytest.raises(SpoolmanCircuitOpenError):
            await client.list_spools()
        assert hits == 3, "breaker did not short-circuit"

        # Fast-forward past the 30s open window — next call retries the HTTP
        # surface (and fails again, since the handler is still angry).
        fake_now[0] += 31.0
        with pytest.raises(httpx.ConnectError):
            await client.list_spools()
        assert hits == 4
    finally:
        await client.aclose()


# ---- TEST-9 -----------------------------------------------------------------


async def test_observability_labels_present_on_client_log() -> None:
    """TEST-9 — successful call emits one ``spools.client.call`` record with
    the AC-6 labels: ``external_service``, ``endpoint``, ``duration_ms`` int,
    ``entity_count`` matching the fixture.

    Uses a per-test handler attached directly to the module logger so the
    suite-wide ``configure_logging()`` reset (which replaces root handlers)
    cannot evict the capture surface mid-suite.
    """
    captured = _attach_capture_handler("app.modules.spools.client")
    handler = make_happy_handler()
    client = make_client_with_handler(handler)
    try:
        result = await client.list_spools()
    finally:
        await client.aclose()
        captured.detach()

    call_records = [r for r in captured.records if r.getMessage() == "spools.client.call"]
    assert call_records, "no spools.client.call record captured"
    rec = call_records[-1]
    extras = rec.__dict__
    assert extras["labels.external_service"] == "spoolman"
    assert extras["labels.endpoint"] == "GET /api/v1/spool"
    assert isinstance(extras["labels.duration_ms"], int)
    assert extras["labels.entity_count"] == len(result)


async def test_observability_lock_label_present_on_refresh_client_log() -> None:
    """AC-6 — refresh-path client calls carry ``labels.lock_acquired`` on
    the per-call structured record, not only on the aggregate service log.
    """
    captured = _attach_capture_handler("app.modules.spools.client")
    handler = make_happy_handler()
    client = make_client_with_handler(handler)
    try:
        await client.list_spools(lock_held=True)
    finally:
        await client.aclose()
        captured.detach()

    rec = [r for r in captured.records if r.getMessage() == "spools.client.call"][-1]
    assert rec.__dict__["labels.lock_acquired"] is True


# ---- TEST-10 ----------------------------------------------------------------


async def test_observability_response_body_not_logged_at_info() -> None:
    """TEST-10 — verbatim response-body strings (filament name, color hex,
    lot number) MUST NOT appear in any captured log record's message or
    ``extra`` values. Brainstorm anti-pattern 8 + Decision AD enforcement."""
    sentinel_name = "PLA-Test-Mat-1"
    sentinel_color = "AB0001"
    sentinel_lot = "LOT-001"
    captured = _attach_capture_handler("app.modules.spools.client", level=logging.DEBUG)
    handler = make_happy_handler()
    client = make_client_with_handler(handler)
    try:
        await client.list_spools()
        await client.list_filaments()
        await client.list_vendors()
    finally:
        await client.aclose()
        captured.detach()

    sentinels = (sentinel_name, sentinel_color, sentinel_lot)
    for record in captured.records:
        rendered = record.getMessage()
        for sentinel in sentinels:
            assert sentinel not in rendered, (
                f"response body leaked into log message: {rendered!r} contains {sentinel!r}"
            )
        for key, value in record.__dict__.items():
            if isinstance(value, str):
                for sentinel in sentinels:
                    assert sentinel not in value, (
                        f"response body leaked into log extra[{key!r}]: {value!r}"
                    )


# ---- TEST-11 ----------------------------------------------------------------


def test_arq_cron_poll_spoolman_summary_registered_at_60s_cadence() -> None:
    """TEST-11 — ``WorkerSettings.functions`` includes
    ``poll_spoolman_summary`` and ``cron_jobs`` carries a matching entry with
    ``second={0}`` (60s cadence). AC-8 enforcement."""
    from app.workers import WorkerSettings
    from app.workers.spoolman_poll import poll_spoolman_summary

    assert poll_spoolman_summary in WorkerSettings.functions

    matching = [
        c
        for c in WorkerSettings.cron_jobs
        if getattr(c, "coroutine", None) is poll_spoolman_summary
    ]
    assert len(matching) == 1, (
        f"expected exactly one poll_spoolman_summary cron entry, got {matching}"
    )
    assert matching[0].second == {0}


# ---- TEST-LIVE-1 ------------------------------------------------------------


@pytest.mark.skipif(
    os.environ.get("SPOOLMAN_LIVE_TEST") != "1",
    reason="live Spoolman not reachable; opt in via SPOOLMAN_LIVE_TEST=1",
)
async def test_spoolman_live_smoke_contract(spoolman_settings_overrides) -> None:
    """TEST-LIVE-1 — real Spoolman 0.23.1 contract pin. Default-skipped in CI.
    When enabled: ``list_spools()`` + ``list_filaments()`` + ``list_vendors()``
    each parse against the live response shape."""
    settings = spoolman_settings_overrides(
        url=os.environ.get("SPOOLMAN_URL", "http://localhost:7912"),
        token=os.environ.get("SPOOLMAN_AUTH_TOKEN", ""),
    )
    async with SpoolmanClient(
        base_url=settings.spoolman_url,
        auth_token=settings.spoolman_auth_token,
    ) as client:
        spools = await client.list_spools()
        filaments = await client.list_filaments()
        vendors = await client.list_vendors()
    assert spools, "live Spoolman returned no spools"
    assert filaments, "live Spoolman returned no filaments"
    assert vendors, "live Spoolman returned no vendors"
    assert all(isinstance(s, SpoolmanSpool) for s in spools)
    assert all(isinstance(f, SpoolmanFilament) for f in filaments)
    assert all(isinstance(v, SpoolmanVendor) for v in vendors)
