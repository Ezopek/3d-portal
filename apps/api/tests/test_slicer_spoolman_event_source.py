"""SPOOL-EVT-1 — the live Spoolman-change event source (poll-diff trigger).

Three layers under test:

1. ``SpoolmanInvalidationHandler.handle`` — the snapshot diff → ``lookup_affected_keys`` →
   ``apply_spoolman_filament_change`` dispatch (no-op / cost-only / mapped-override /
   missing-attribution / added-ref / empty-keys).
2. ``SpoolsService.refresh_summary(change_handler=…)`` — previous-snapshot retention, the
   first-poll warmup (no dispatch), the request-path isolation, and handler-error isolation.
3. ``poll_spoolman_summary`` cron — that it actually wires a real handler onto the poll.

All on-disk (tmp_path) + fakeredis; no Orca, no httpx, no real Redis.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import fakeredis.aioredis
import pytest

from app.core.redis import RedisFactory
from app.modules.slicer.attribution_store import AttributionStore
from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.estimate_store import EstimateStore
from app.modules.slicer.models import (
    EstimateRecord,
    EstimateStatus,
    PrintIntentPreset,
)
from app.modules.slicer.overrides import SpoolmanOverrideProvider, spoolman_filament_ref
from app.modules.slicer.resolver import VendoredProfileSource, resolve
from app.modules.slicer.spoolman_event_source import (
    SpoolmanInvalidationHandler,
    build_spoolman_invalidation_handler,
)
from app.modules.slicer.validation import NullCliValidator
from app.modules.slicer.worker_job import SLICE_JOB_NAME
from app.modules.spools.models import SpoolmanFilament, SpoolmanSnapshot
from app.modules.spools.service import SpoolsService

FIXTURES = Path(__file__).parent / "fixtures" / "slicer"

_STL_HASH = "a" * 64

_PLA_INTENT = PrintIntentPreset(
    name="PLA standard",
    material_class="PLA",
    quality_tier="standard",
    printer_ref="creality-k1-max-microswiss-hf",
)


# --- fixtures / helpers (mirror test_slicer_spoolman_overrides.py) -------------------


def _filament(ref_id: int = 1, *, extra: dict[str, str] | None = None, **kw) -> SpoolmanFilament:
    base = dict(
        id=ref_id,
        name=f"Rosa3D PLA Starter {ref_id}",
        vendor_name="Rosa3D",
        material="PLA",
        price=20.0,
        weight=1000.0,
        extra=extra or {},
    )
    base.update(kw)
    return SpoolmanFilament.model_validate(base)


def _pinned(filament: SpoolmanFilament) -> PrintIntentPreset:
    return _PLA_INTENT.model_copy(update={"spoolman_filament_ref": spoolman_filament_ref(filament)})


def _resolved_hash(filament: SpoolmanFilament, store: BundleStore) -> str:
    provider = SpoolmanOverrideProvider({spoolman_filament_ref(filament): filament})
    out = resolve(
        _pinned(filament),
        source=VendoredProfileSource(FIXTURES),
        store=store,
        override_provider=provider,
        validator=NullCliValidator(),
        orca_version="2.3.2",
    )
    return out.bundle.bundle_hash


def _fresh_estimate(stl_hash: str, bundle_hash: str, *, cost: float = 4.60) -> EstimateRecord:
    return EstimateRecord(
        stl_hash=stl_hash,
        bundle_hash=bundle_hash,
        orca_version="2.3.2",
        time_seconds=12947,
        filament_g=76.76,
        filament_mm=25735.79,
        filament_cm3=61.90,
        filament_cost=cost,
        status=EstimateStatus.fresh,
        computed_at="2026-06-01T00:00:00+00:00",
    )


def _snapshot(*filaments: SpoolmanFilament) -> SpoolmanSnapshot:
    return SpoolmanSnapshot(
        spools=[], filaments=list(filaments), vendors=[], fetched_at=datetime.now(UTC)
    )


class _FakePool:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple, dict]] = []

    async def enqueue_job(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return SimpleNamespace(job_id=kwargs.get("_job_id"))


def _handler(tmp_path: Path, pool: _FakePool) -> tuple[SpoolmanInvalidationHandler, Any]:
    estimate_store = EstimateStore(tmp_path / "est")
    attribution_store = AttributionStore(tmp_path / "bundles")
    bundle_store = BundleStore(tmp_path / "bundles")
    handler = SpoolmanInvalidationHandler(
        estimate_store=estimate_store,
        attribution_store=attribution_store,
        bundle_store=bundle_store,
        source=VendoredProfileSource(FIXTURES),
        arq_pool=pool,
        orca_version="2.3.2",
    )
    return handler, SimpleNamespace(estimate=estimate_store, attribution=attribution_store)


# === Layer 1 — SpoolmanInvalidationHandler.handle =====================================


def test_handle_noop_diff_does_not_dispatch(tmp_path):
    # Identical snapshots ⇒ classify is None for every ref ⇒ never even scans the estimate
    # store, never dispatches.
    pool = _FakePool()
    handler, stores = _handler(tmp_path, pool)
    f = _filament(price=20.0, extra={"nozzle_temperature": "230"})
    old_hash = _resolved_hash(f, BundleStore(tmp_path / "scratch"))
    stores.attribution.record(spoolman_filament_ref(f), _pinned(f), old_hash)
    stores.estimate.write(_fresh_estimate(_STL_HASH, old_hash))

    asyncio.run(handler.handle(_snapshot(f), _snapshot(f.model_copy())))

    assert pool.calls == []
    assert stores.estimate.read(_STL_HASH, old_hash).status == EstimateStatus.fresh


def test_handle_irrelevant_field_change_does_not_dispatch(tmp_path):
    # A color edit is neither mapped nor price/weight ⇒ classify None ⇒ no dispatch.
    pool = _FakePool()
    handler, stores = _handler(tmp_path, pool)
    old_f = _filament(color_hex="AABBCC")
    new_f = _filament(color_hex="DDEEFF")
    old_hash = _resolved_hash(old_f, BundleStore(tmp_path / "scratch"))
    stores.attribution.record(spoolman_filament_ref(old_f), _pinned(old_f), old_hash)
    stores.estimate.write(_fresh_estimate(_STL_HASH, old_hash))

    asyncio.run(handler.handle(_snapshot(old_f), _snapshot(new_f)))

    assert pool.calls == []


def test_handle_cost_only_change_recomputes_in_place_no_enqueue(tmp_path):
    # THE R1 self-DoS guard at the event-source layer: a price tick on a known filament
    # recomputes cost arithmetically and NEVER reaches the slicer queue.
    pool = _FakePool()
    handler, stores = _handler(tmp_path, pool)
    old_f = _filament(price=20.0, weight=1000.0, extra={"nozzle_temperature": "230"})
    new_f = _filament(price=50.0, weight=1000.0, extra={"nozzle_temperature": "230"})
    bundle_hash = _resolved_hash(old_f, BundleStore(tmp_path / "scratch"))
    stores.attribution.record(spoolman_filament_ref(old_f), _pinned(old_f), bundle_hash)
    stores.estimate.write(_fresh_estimate(_STL_HASH, bundle_hash))

    asyncio.run(handler.handle(_snapshot(old_f), _snapshot(new_f)))

    assert pool.calls == []  # NEVER reaches the slicer queue
    rec = stores.estimate.read(_STL_HASH, bundle_hash)
    # cost = filament_g * price_per_gram = 76.76 * (50/1000) = 3.838
    assert rec.filament_cost == pytest.approx(76.76 * 0.05)


def test_handle_mapped_override_change_marks_stale_and_enqueues_new(tmp_path):
    pool = _FakePool()
    handler, stores = _handler(tmp_path, pool)
    old_f = _filament(extra={"filament_max_volumetric_speed": "8.0"})
    new_f = _filament(extra={"filament_max_volumetric_speed": "12.0"})
    old_hash = _resolved_hash(old_f, BundleStore(tmp_path / "scratch_old"))
    new_hash = _resolved_hash(new_f, BundleStore(tmp_path / "scratch_new"))
    assert old_hash != new_hash
    stores.attribution.record(spoolman_filament_ref(old_f), _pinned(old_f), old_hash)
    stores.estimate.write(_fresh_estimate(_STL_HASH, old_hash))

    asyncio.run(handler.handle(_snapshot(old_f), _snapshot(new_f)))

    # OLD record marked stale, NEW re-slice enqueued against the re-resolved bundle hash.
    assert stores.estimate.read(_STL_HASH, old_hash).status == EstimateStatus.stale
    assert len(pool.calls) == 1
    args, _ = pool.calls[0]
    assert args == (SLICE_JOB_NAME, _STL_HASH, new_hash)


def test_handle_missing_attribution_produces_no_dispatch(tmp_path):
    # A real (cost-only) change but NO attribution record for the ref ⇒ lookup returns [] ⇒
    # nothing dispatched, the estimate is left untouched.
    pool = _FakePool()
    handler, stores = _handler(tmp_path, pool)
    old_f = _filament(price=20.0, extra={"nozzle_temperature": "230"})
    new_f = _filament(price=50.0, extra={"nozzle_temperature": "230"})
    bundle_hash = _resolved_hash(old_f, BundleStore(tmp_path / "scratch"))
    stores.estimate.write(_fresh_estimate(_STL_HASH, bundle_hash))  # estimate but NO attribution

    asyncio.run(handler.handle(_snapshot(old_f), _snapshot(new_f)))

    assert pool.calls == []
    rec = stores.estimate.read(_STL_HASH, bundle_hash)
    assert rec.status == EstimateStatus.fresh
    assert rec.filament_cost == pytest.approx(4.60)  # unchanged


def test_handle_added_ref_produces_no_dispatch(tmp_path):
    # A filament present only in the NEW snapshot (newly added inventory) has no prior state
    # to diff ⇒ no dispatch.
    pool = _FakePool()
    handler, _stores = _handler(tmp_path, pool)
    new_f = _filament(2, price=20.0, extra={"nozzle_temperature": "230"})

    asyncio.run(handler.handle(_snapshot(), _snapshot(new_f)))

    assert pool.calls == []


def test_handle_attribution_without_estimates_does_not_dispatch(tmp_path):
    # Attribution pin known but NO estimate computed for the bundle yet ⇒ empty affected_keys
    # ⇒ skip (no enqueue, no wasted re-resolve). A mapped change to make the point sharp.
    pool = _FakePool()
    handler, stores = _handler(tmp_path, pool)
    old_f = _filament(extra={"filament_max_volumetric_speed": "8.0"})
    new_f = _filament(extra={"filament_max_volumetric_speed": "12.0"})
    old_hash = _resolved_hash(old_f, BundleStore(tmp_path / "scratch"))
    stores.attribution.record(spoolman_filament_ref(old_f), _pinned(old_f), old_hash)
    # deliberately NO estimate written for old_hash

    asyncio.run(handler.handle(_snapshot(old_f), _snapshot(new_f)))

    assert pool.calls == []


# === Layer 2 — SpoolsService.refresh_summary(change_handler=…) =========================


class _RecordingHandler:
    def __init__(self) -> None:
        self.calls: list[tuple[SpoolmanSnapshot, SpoolmanSnapshot]] = []

    async def handle(self, previous: SpoolmanSnapshot, current: SpoolmanSnapshot) -> None:
        self.calls.append((previous, current))


class _BoomHandler:
    def __init__(self) -> None:
        self.calls = 0

    async def handle(self, previous: SpoolmanSnapshot, current: SpoolmanSnapshot) -> None:
        self.calls += 1
        raise RuntimeError("handler boom")


_PREV_KEY = "spools:summary:prev:v1"


class _StubClient:
    """Minimal SpoolmanClient stand-in returning a configurable filament list."""

    def __init__(self, filaments: list[SpoolmanFilament]) -> None:
        self._filaments = filaments

    async def list_spools(self, *, lock_held: bool = False):
        return []

    async def list_filaments(self, *, lock_held: bool = False):
        return list(self._filaments)

    async def list_vendors(self, *, lock_held: bool = False):
        return []


@pytest.fixture
async def fake_redis_factory():
    fake = fakeredis.aioredis.FakeRedis()
    factory = RedisFactory(client=fake)
    yield factory, fake
    await fake.aclose()


async def test_first_poll_warms_baseline_without_dispatch(fake_redis_factory):
    factory, fake = fake_redis_factory
    handler = _RecordingHandler()
    service = SpoolsService(redis_factory=factory, client=_StubClient([_filament()]))

    snapshot = await service.refresh_summary(change_handler=handler)

    assert snapshot is not None
    # Baseline warmed (prev key written) but the handler was NOT invoked on the first poll.
    assert handler.calls == []
    assert await fake.get(_PREV_KEY) is not None


async def test_second_poll_invokes_handler_and_advances_baseline(fake_redis_factory):
    factory, fake = fake_redis_factory
    handler = _RecordingHandler()
    old_f = _filament(price=20.0)
    new_f = _filament(price=50.0)
    # First poll warms baseline with old_f.
    service = SpoolsService(redis_factory=factory, client=_StubClient([old_f]))
    await service.refresh_summary(change_handler=handler)
    # Second poll sees new_f.
    service2 = SpoolsService(redis_factory=factory, client=_StubClient([new_f]))
    await service2.refresh_summary(change_handler=handler)

    assert len(handler.calls) == 1
    previous, current = handler.calls[0]
    assert previous.filaments[0].price == 20.0
    assert current.filaments[0].price == 50.0
    # Baseline advanced to the new snapshot.
    advanced = SpoolmanSnapshot.model_validate_json(await fake.get(_PREV_KEY))
    assert advanced.filaments[0].price == 50.0


async def test_handler_error_does_not_break_poll_or_advance_baseline(fake_redis_factory):
    factory, fake = fake_redis_factory
    boom = _BoomHandler()
    old_f = _filament(price=20.0)
    new_f = _filament(price=50.0)
    # Warm baseline with old_f via a no-op recording handler.
    await SpoolsService(redis_factory=factory, client=_StubClient([old_f])).refresh_summary(
        change_handler=_RecordingHandler()
    )
    # Second poll: handler raises.
    snapshot = await SpoolsService(
        redis_factory=factory, client=_StubClient([new_f])
    ).refresh_summary(change_handler=boom)

    assert boom.calls == 1
    # The poll still succeeded (cache written, snapshot returned).
    assert snapshot is not None and snapshot.filaments[0].price == 50.0
    # Baseline NOT advanced — still the old snapshot, so the delta re-diffs next tick.
    still = SpoolmanSnapshot.model_validate_json(await fake.get(_PREV_KEY))
    assert still.filaments[0].price == 20.0


async def test_request_path_refresh_does_not_dispatch_or_retain(fake_redis_factory):
    # get_summary's cold-cache fallback calls refresh_summary WITHOUT a change_handler, so it
    # must not write the prev-snapshot baseline nor dispatch.
    factory, fake = fake_redis_factory
    service = SpoolsService(redis_factory=factory, client=_StubClient([_filament()]))

    snapshot = await service.get_summary()

    assert snapshot is not None
    assert await fake.get(_PREV_KEY) is None


# === Layer 3 — cron wiring ============================================================


async def test_cron_passes_real_handler_to_refresh(monkeypatch):
    from app.workers import spoolman_poll

    captured: dict[str, Any] = {}

    async def _fake_refresh(self, *, change_handler=None):
        captured["handler"] = change_handler
        return None

    monkeypatch.setattr(SpoolsService, "refresh_summary", _fake_refresh)

    pool = _FakePool()
    rc = await spoolman_poll.poll_spoolman_summary({"redis": pool})

    assert rc == 0  # refresh returned None
    assert isinstance(captured["handler"], SpoolmanInvalidationHandler)
    # The handler was wired with the cron-provided arq pool.
    assert captured["handler"]._arq_pool is pool


def test_build_handler_from_settings_uses_provided_pool():
    pool = _FakePool()
    handler = build_spoolman_invalidation_handler(pool)
    assert isinstance(handler, SpoolmanInvalidationHandler)
    assert handler._arq_pool is pool
