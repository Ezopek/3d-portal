"""Tests for the Story 32.4 estimate invalidation / recompute engine (Decision AJ second half).

Pure app-side surface (FR20-CACHE-1 transitions + NFR20-REPRODUCIBLE-1 cost-only-arithmetic
+ NFR20-RESOURCE-1 recompute dedup):

- ``EstimateStore.mark_stale`` / ``mark_queued`` / ``update_cost`` — force-publish status/cost
  transitions under the Story 32.3 per-record lock, preserving last-known numerics so a
  superseded estimate stays SERVABLE (never hidden, never coerced to ``fresh`` — R9).
- ``recompute.recompute_cost_only`` — ``cost = filament_g x price_per_gram`` in-place, NO arq
  enqueue / NO Orca subprocess, in well under a second (the R1 self-DoS guard, OD-7).
- ``recompute.enqueue_recompute`` — by-hash idempotent re-slice enqueue riding the Story 32.2
  ``_job_id`` dedupe (no ``stl_cache`` repopulate — the STL is already content-addressed).
- ``recompute.invalidate`` — the Decision AJ recompute-trigger dispatch: cost-only → arithmetic
  (no enqueue); slice-affecting → stale + enqueue + queued.
- ``EstimateStore.iter_stl_estimates`` / ``iter_all_estimates`` + the bulk helpers — enumeration
  primitives reusing the Story 32.3 fan-out layout.

No subprocess, no real Orca, no clock in any assertion (``computed_at`` is the only
non-deterministic field and is excluded — AC-12).
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import math
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.modules.slicer.enqueue import slice_job_id
from app.modules.slicer.estimate_store import EstimateStore
from app.modules.slicer.models import (
    EstimateFailureReason,
    EstimateRecord,
    EstimateStatus,
    SliceWarning,
)
from app.modules.slicer.recompute import (
    RecomputeTrigger,
    enqueue_recompute,
    invalidate,
    invalidate_bulk,
    recompute_cost_only,
    recompute_cost_only_bulk,
)
from app.modules.slicer.worker import SLICER_QUEUE_NAME
from app.modules.slicer.worker_job import SLICE_JOB_NAME

REPO_ROOT = Path(__file__).resolve().parents[3]

STL_HASH = "a" * 64
BUNDLE_HASH = "b" * 64
NEW_BUNDLE_HASH = "c" * 64  # the re-slice target after a bundle-changing trigger (old != new)
ORIGINAL_COMPUTED_AT = "2026-06-01T00:00:00+00:00"


# === record builders =========================================================


def _fresh(*, computed_at=ORIGINAL_COMPUTED_AT, **kw) -> EstimateRecord:
    base = dict(
        stl_hash=STL_HASH,
        bundle_hash=BUNDLE_HASH,
        orca_version="2.3.2",
        time_seconds=12947,
        filament_g=76.76,
        filament_mm=25735.79,
        filament_cm3=61.90,
        filament_cost=4.60,
        settings_ids={"filament_settings_id": "AI Rosa3D PLA Starter"},
        warnings=[SliceWarning(message="floating cantilever")],
        status=EstimateStatus.fresh,
        computed_at=computed_at,
    )
    base.update(kw)
    return EstimateRecord(**base)


def _failed(*, reason=EstimateFailureReason.parse_failure, computed_at=ORIGINAL_COMPUTED_AT, **kw):
    base = dict(
        stl_hash=STL_HASH,
        bundle_hash=BUNDLE_HASH,
        orca_version="2.3.2",
        status=EstimateStatus.failed,
        reason=reason,
        computed_at=computed_at,
    )
    base.update(kw)
    return EstimateRecord(**base)


class _FakePool:
    """Records enqueue_job kwargs so a test can assert the dedupe contract (or its absence)."""

    def __init__(self) -> None:
        self.calls: list[tuple[tuple, dict]] = []

    async def enqueue_job(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return SimpleNamespace(job_id=kwargs.get("_job_id"))


# === AC-1: mark_stale (fresh → stale, servable, never hidden) ================


def test_mark_stale_fresh_preserves_numerics_and_computed_at(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    updated = store.mark_stale(STL_HASH, BUNDLE_HASH)
    assert updated is not None
    assert updated.status == EstimateStatus.stale
    # Every numeric + provenance field preserved (the record stays servable).
    assert updated.time_seconds == 12947
    assert updated.filament_g == pytest.approx(76.76)
    assert updated.filament_mm == pytest.approx(25735.79)
    assert updated.filament_cm3 == pytest.approx(61.90)
    assert updated.filament_cost == pytest.approx(4.60)
    assert updated.settings_ids == {"filament_settings_id": "AI Rosa3D PLA Starter"}
    assert updated.warnings[0].message == "floating cantilever"
    assert updated.orca_version == "2.3.2"
    # The ORIGINAL computed_at is preserved (when it was last validly computed).
    assert updated.computed_at == ORIGINAL_COMPUTED_AT
    # Persisted to disk, not just returned.
    assert store.read(STL_HASH, BUNDLE_HASH).status == EstimateStatus.stale


def test_mark_stale_is_idempotent_on_already_stale(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    first = store.mark_stale(STL_HASH, BUNDLE_HASH)
    again = store.mark_stale(STL_HASH, BUNDLE_HASH)
    assert again is not None
    assert again.status == EstimateStatus.stale
    # No computed_at churn on the idempotent re-mark.
    assert again.computed_at == first.computed_at == ORIGINAL_COMPUTED_AT


def test_mark_stale_idempotent_on_queued(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    store.mark_queued(STL_HASH, BUNDLE_HASH)
    result = store.mark_stale(STL_HASH, BUNDLE_HASH)
    # A queued record is not dragged back to stale — mark_stale no-ops over it.
    assert result is not None
    assert result.status == EstimateStatus.queued


def test_mark_stale_on_failed_record_is_noop_stays_failed(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_failed())
    result = store.mark_stale(STL_HASH, BUNDLE_HASH)
    assert result is not None
    assert result.status == EstimateStatus.failed  # a failed record has no estimate to go stale
    assert result.filament_g is None  # never fabricated


def test_mark_stale_on_miss_returns_none(tmp_path):
    store = EstimateStore(tmp_path)
    assert store.mark_stale(STL_HASH, BUNDLE_HASH) is None  # never fabricate a record


def test_stale_record_is_returned_by_read_not_hidden(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    store.mark_stale(STL_HASH, BUNDLE_HASH)
    got = store.read(STL_HASH, BUNDLE_HASH)
    # Explicit-stale contract: read returns the stale record verbatim, never coerced to
    # fresh, never dropped (R9 — a superseded estimate is served WITH its flag).
    assert got is not None
    assert got.status == EstimateStatus.stale
    assert got.filament_g == pytest.approx(76.76)


# === AC-2: mark_queued (stale|fresh → queued) ================================


def test_mark_queued_from_stale_preserves_numerics(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    store.mark_stale(STL_HASH, BUNDLE_HASH)
    updated = store.mark_queued(STL_HASH, BUNDLE_HASH)
    assert updated is not None
    assert updated.status == EstimateStatus.queued
    assert updated.filament_g == pytest.approx(76.76)
    assert updated.computed_at == ORIGINAL_COMPUTED_AT


def test_mark_queued_from_fresh_preserves_numerics(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    updated = store.mark_queued(STL_HASH, BUNDLE_HASH)
    assert updated is not None
    assert updated.status == EstimateStatus.queued
    assert updated.time_seconds == 12947
    assert updated.computed_at == ORIGINAL_COMPUTED_AT


def test_mark_queued_idempotent(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    first = store.mark_queued(STL_HASH, BUNDLE_HASH)
    again = store.mark_queued(STL_HASH, BUNDLE_HASH)
    assert again is not None
    assert again.status == EstimateStatus.queued
    assert again.computed_at == first.computed_at == ORIGINAL_COMPUTED_AT


def test_mark_queued_on_failed_is_noop(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_failed())
    result = store.mark_queued(STL_HASH, BUNDLE_HASH)
    assert result is not None
    assert result.status == EstimateStatus.failed  # never queue over a good-number-less failure


def test_mark_queued_on_miss_returns_none(tmp_path):
    store = EstimateStore(tmp_path)
    assert store.mark_queued(STL_HASH, BUNDLE_HASH) is None


# === AC-3: cost-only arithmetic recompute (NO re-slice — the load-bearing rule) ===


def test_cost_only_recompute_updates_cost_from_mass_and_price(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh(filament_g=80.0, filament_cost=4.60))
    updated = recompute_cost_only(store, STL_HASH, BUNDLE_HASH, price_per_gram=0.05)
    assert updated is not None
    assert updated.filament_cost == pytest.approx(80.0 * 0.05)  # 4.00


def test_cost_only_recompute_does_not_enqueue_any_slice(tmp_path, monkeypatch):
    # THE load-bearing R1 self-DoS guard: a cost-only change must NEVER reach the slicer
    # queue. There is no arq_pool parameter at all, and the engine spawns no subprocess.
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    pool = _FakePool()

    def _boom_enqueue(*a, **k):  # pragma: no cover - only fires on a contract breach
        raise AssertionError("cost-only recompute must not enqueue any slice job")

    monkeypatch.setattr(pool, "enqueue_job", _boom_enqueue)
    recompute_cost_only(store, STL_HASH, BUNDLE_HASH, price_per_gram=0.05)
    assert pool.calls == []
    # recompute_cost_only takes no pool — assert the signature carries no enqueue surface.
    params = inspect.signature(recompute_cost_only).parameters
    assert "arq_pool" not in params
    assert "source_stl" not in params


def test_cost_only_recompute_does_not_spawn_subprocess(tmp_path, monkeypatch):
    import subprocess

    def _boom(*a, **k):  # pragma: no cover - only fires on a contract breach
        raise AssertionError("cost-only recompute must not spawn a subprocess / Orca")

    monkeypatch.setattr(subprocess, "Popen", _boom)
    monkeypatch.setattr(subprocess, "run", _boom)
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    recompute_cost_only(store, STL_HASH, BUNDLE_HASH, price_per_gram=0.05)
    # Defense in depth: the module never even imports subprocess.
    source = (REPO_ROOT / "apps/api/app/modules/slicer/recompute.py").read_text(encoding="utf-8")
    assert "import subprocess" not in source


def test_cost_only_recompute_preserves_slice_numerics_and_status(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh(filament_g=80.0))
    updated = recompute_cost_only(store, STL_HASH, BUNDLE_HASH, price_per_gram=0.05)
    assert updated is not None
    # Only cost (+ computed_at) changes; the slice-derived numerics + status are immutable.
    assert updated.status == EstimateStatus.fresh
    assert updated.time_seconds == 12947
    assert updated.filament_g == pytest.approx(80.0)
    assert updated.filament_mm == pytest.approx(25735.79)
    assert updated.filament_cm3 == pytest.approx(61.90)
    assert updated.settings_ids == {"filament_settings_id": "AI Rosa3D PLA Starter"}


def test_cost_only_recompute_keeps_status_for_stale_record(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh(filament_g=80.0))
    store.mark_stale(STL_HASH, BUNDLE_HASH)
    updated = recompute_cost_only(store, STL_HASH, BUNDLE_HASH, price_per_gram=0.05)
    # A cost change does NOT touch the slice-output lifecycle: a stale record stays stale.
    assert updated is not None
    assert updated.status == EstimateStatus.stale
    assert updated.filament_cost == pytest.approx(4.0)


@pytest.mark.parametrize("bad", [None, math.nan, math.inf, -math.inf])
def test_cost_only_recompute_rejects_non_finite_price(tmp_path, bad):
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    with pytest.raises(ValueError):
        recompute_cost_only(store, STL_HASH, BUNDLE_HASH, price_per_gram=bad)
    # Never silently wrote a 0/nan/negative cost — the record is untouched.
    assert store.read(STL_HASH, BUNDLE_HASH).filament_cost == pytest.approx(4.60)


def test_cost_only_recompute_rejects_negative_price(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    with pytest.raises(ValueError):
        recompute_cost_only(store, STL_HASH, BUNDLE_HASH, price_per_gram=-0.01)
    assert store.read(STL_HASH, BUNDLE_HASH).filament_cost == pytest.approx(4.60)


def test_cost_only_recompute_on_failed_record_is_noop_none(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_failed())
    # A failed estimate has no mass to multiply — never fabricate a cost onto a failure.
    assert recompute_cost_only(store, STL_HASH, BUNDLE_HASH, price_per_gram=0.05) is None
    assert store.read(STL_HASH, BUNDLE_HASH).status == EstimateStatus.failed


def test_cost_only_recompute_on_miss_returns_none(tmp_path):
    store = EstimateStore(tmp_path)
    assert recompute_cost_only(store, STL_HASH, BUNDLE_HASH, price_per_gram=0.05) is None


def test_cost_only_recompute_completes_well_under_one_second(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    start = time.perf_counter()
    recompute_cost_only(store, STL_HASH, BUNDLE_HASH, price_per_gram=0.05)
    elapsed = time.perf_counter() - start
    # NFR20-REPRODUCIBLE-1: the path is arithmetic + one file write, not a slice. CI headroom.
    assert elapsed < 0.5


# === AC-4: idempotent recompute enqueue (re-slice path) ======================


def test_enqueue_recompute_uses_deterministic_job_id():
    pool = _FakePool()
    asyncio.run(enqueue_recompute(pool, stl_hash=STL_HASH, bundle_hash=BUNDLE_HASH))
    _, kwargs = pool.calls[0]
    assert kwargs["_job_id"] == f"slice:{STL_HASH}:{BUNDLE_HASH}"
    assert kwargs["_job_id"] == slice_job_id(STL_HASH, BUNDLE_HASH)


def test_enqueue_recompute_targets_slicer_queue():
    pool = _FakePool()
    asyncio.run(enqueue_recompute(pool, stl_hash=STL_HASH, bundle_hash=BUNDLE_HASH))
    _, kwargs = pool.calls[0]
    assert kwargs["_queue_name"] == SLICER_QUEUE_NAME
    args, _ = pool.calls[0]
    assert args == (SLICE_JOB_NAME, STL_HASH, BUNDLE_HASH)  # name + 2 hashes ONLY


def test_enqueue_recompute_is_idempotent_dedupe():
    pool = _FakePool()
    asyncio.run(enqueue_recompute(pool, stl_hash=STL_HASH, bundle_hash=BUNDLE_HASH))
    asyncio.run(enqueue_recompute(pool, stl_hash=STL_HASH, bundle_hash=BUNDLE_HASH))
    # Both enqueues carry the SAME _job_id — arq drops the duplicate (NFR20-RESOURCE-1).
    assert pool.calls[0][1]["_job_id"] == pool.calls[1][1]["_job_id"]


def test_enqueue_recompute_does_not_repopulate_stl_cache():
    # A recompute is a by-hash re-run for an already-cached STL — no source_stl, no
    # populate_from_source, no stl_cache parameter (distinct from the 32.2 first enqueue).
    params = inspect.signature(enqueue_recompute).parameters
    assert "source_stl" not in params
    assert "stl_cache" not in params


def test_enqueue_recompute_rejects_malformed_hash():
    pool = _FakePool()
    with pytest.raises(ValueError, match="content hash"):
        asyncio.run(enqueue_recompute(pool, stl_hash="../../etc", bundle_hash=BUNDLE_HASH))
    assert pool.calls == []  # nothing enqueued on a malformed key


# === AC-5: recompute-trigger dispatch (the Decision AJ table) ================


def test_recompute_trigger_enum_covers_decision_aj_table():
    # The exhaustiveness guard against R9: every architecture recompute-trigger-table row
    # has a RecomputeTrigger value, so the table cannot grow a silent gap.
    assert {t.value for t in RecomputeTrigger} == {
        "stl_content_change",
        "bundle_retune",
        "orca_upgrade",
        "spoolman_mapped_override",
        "spoolman_cost_only",
    }


def test_dispatch_cost_only_takes_arithmetic_path_no_enqueue(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh(filament_g=80.0))
    pool = _FakePool()
    result = asyncio.run(
        invalidate(
            store,
            pool,
            trigger=RecomputeTrigger.spoolman_cost_only,
            stl_hash=STL_HASH,
            bundle_hash=BUNDLE_HASH,
            price_per_gram=0.05,
        )
    )
    assert result is not None
    assert result.filament_cost == pytest.approx(4.0)
    assert result.status == EstimateStatus.fresh  # cost-only never invalidates the slice output
    assert pool.calls == []  # the R1 guard: a price tick NEVER reaches the slicer queue


def test_dispatch_cost_only_without_price_raises(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    pool = _FakePool()
    with pytest.raises(ValueError):
        asyncio.run(
            invalidate(
                store,
                pool,
                trigger=RecomputeTrigger.spoolman_cost_only,
                stl_hash=STL_HASH,
                bundle_hash=BUNDLE_HASH,
            )
        )
    assert pool.calls == []


def test_dispatch_bundle_retune_marks_stale_then_enqueues_then_queued(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    pool = _FakePool()
    result = asyncio.run(
        invalidate(
            store,
            pool,
            trigger=RecomputeTrigger.bundle_retune,
            stl_hash=STL_HASH,
            bundle_hash=BUNDLE_HASH,
        )
    )
    # stale → queued lifecycle: the record ends queued (servable last-known numbers).
    assert result is not None
    assert result.status == EstimateStatus.queued
    assert result.filament_g == pytest.approx(76.76)
    # An idempotent re-slice was enqueued onto the slicer queue.
    assert len(pool.calls) == 1
    args, kwargs = pool.calls[0]
    assert args == (SLICE_JOB_NAME, STL_HASH, BUNDLE_HASH)
    assert kwargs["_job_id"] == slice_job_id(STL_HASH, BUNDLE_HASH)


def test_dispatch_orca_upgrade_marks_stale_and_enqueues(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    pool = _FakePool()
    result = asyncio.run(
        invalidate(
            store,
            pool,
            trigger=RecomputeTrigger.orca_upgrade,
            stl_hash=STL_HASH,
            bundle_hash=BUNDLE_HASH,
        )
    )
    assert result is not None
    assert result.status == EstimateStatus.queued
    assert len(pool.calls) == 1


def test_dispatch_mapped_override_marks_stale_and_enqueues(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    pool = _FakePool()
    result = asyncio.run(
        invalidate(
            store,
            pool,
            trigger=RecomputeTrigger.spoolman_mapped_override,
            stl_hash=STL_HASH,
            bundle_hash=BUNDLE_HASH,
        )
    )
    assert result is not None
    assert result.status == EstimateStatus.queued
    assert len(pool.calls) == 1


def test_dispatch_stl_content_change_is_new_key_no_transition(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    pool = _FakePool()
    result = asyncio.run(
        invalidate(
            store,
            pool,
            trigger=RecomputeTrigger.stl_content_change,
            stl_hash=STL_HASH,
            bundle_hash=BUNDLE_HASH,
        )
    )
    # A content change is a NEW key (natural cache miss handled by the 32.2 first enqueue);
    # no in-place transition here, no enqueue, the old key is left for a future GC (AC-9).
    assert result is None
    assert pool.calls == []
    assert store.read(STL_HASH, BUNDLE_HASH).status == EstimateStatus.fresh  # old key untouched


# === AC-5 (review-fix): bundle-CHANGING triggers — old stale key vs new re-slice key ===
#
# A bundle_retune / spoolman_mapped_override changes the bundle_hash: the OLD record is the
# superseded key (marked stale, kept SERVABLE — never served as fresh, R9) and the NEW bundle is
# the re-slice target. invalidate names which hash is which (old `bundle_hash`, `new_bundle_hash`)
# so the old record can NOT be left fresh while the recompute is enqueued for the new key.


def test_dispatch_bundle_retune_old_stale_new_is_reslice_target(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh())  # the OLD (stl, old_bundle) record
    pool = _FakePool()
    asyncio.run(
        invalidate(
            store,
            pool,
            trigger=RecomputeTrigger.bundle_retune,
            stl_hash=STL_HASH,
            bundle_hash=BUNDLE_HASH,  # OLD key
            new_bundle_hash=NEW_BUNDLE_HASH,  # NEW re-slice target
        )
    )
    # The OLD record is marked stale (NOT left fresh) and stays servable with its numerics.
    old = store.read(STL_HASH, BUNDLE_HASH)
    assert old is not None
    assert old.status == EstimateStatus.stale
    assert old.filament_g == pytest.approx(76.76)
    # The enqueued re-slice targets the NEW bundle, not the old one.
    assert len(pool.calls) == 1
    args, kwargs = pool.calls[0]
    assert args == (SLICE_JOB_NAME, STL_HASH, NEW_BUNDLE_HASH)
    assert kwargs["_job_id"] == slice_job_id(STL_HASH, NEW_BUNDLE_HASH)


def test_dispatch_bundle_retune_old_key_is_not_left_fresh(tmp_path):
    # The exact bug the review caught: passing the new bundle must NOT leave the old estimate
    # readable as fresh, and the recompute must target the NEW bundle (not the old).
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    pool = _FakePool()
    asyncio.run(
        invalidate(
            store,
            pool,
            trigger=RecomputeTrigger.bundle_retune,
            stl_hash=STL_HASH,
            bundle_hash=BUNDLE_HASH,
            new_bundle_hash=NEW_BUNDLE_HASH,
        )
    )
    assert store.read(STL_HASH, BUNDLE_HASH).status != EstimateStatus.fresh
    # The new key did not exist yet — a natural miss the worker fills fresh (no fabricated record).
    assert store.read(STL_HASH, NEW_BUNDLE_HASH) is None


def test_dispatch_mapped_override_enqueues_new_bundle_not_old(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    pool = _FakePool()
    asyncio.run(
        invalidate(
            store,
            pool,
            trigger=RecomputeTrigger.spoolman_mapped_override,
            stl_hash=STL_HASH,
            bundle_hash=BUNDLE_HASH,
            new_bundle_hash=NEW_BUNDLE_HASH,
        )
    )
    assert store.read(STL_HASH, BUNDLE_HASH).status == EstimateStatus.stale
    args, _ = pool.calls[0]
    assert args == (SLICE_JOB_NAME, STL_HASH, NEW_BUNDLE_HASH)


def test_dispatch_bundle_retune_marks_new_target_queued_when_already_cached(tmp_path):
    # If the NEW bundle already has a servable estimate (it was sliced before), the recompute
    # target is marked queued (recompute in flight, last numbers still served); the OLD record
    # is independently stale.
    store = EstimateStore(tmp_path)
    store.write(_fresh())  # old key
    store.write(_fresh(bundle_hash=NEW_BUNDLE_HASH, filament_g=50.0))  # pre-existing new key
    pool = _FakePool()
    result = asyncio.run(
        invalidate(
            store,
            pool,
            trigger=RecomputeTrigger.bundle_retune,
            stl_hash=STL_HASH,
            bundle_hash=BUNDLE_HASH,
            new_bundle_hash=NEW_BUNDLE_HASH,
        )
    )
    assert store.read(STL_HASH, BUNDLE_HASH).status == EstimateStatus.stale  # old
    assert result is not None
    assert result.status == EstimateStatus.queued  # the new recompute target
    assert result.bundle_hash == NEW_BUNDLE_HASH
    assert store.read(STL_HASH, NEW_BUNDLE_HASH).status == EstimateStatus.queued


def test_dispatch_same_bundle_when_new_hash_omitted_is_in_place_lifecycle(tmp_path):
    # orca_upgrade whose hash is unchanged (new_bundle_hash omitted) => in-place stale -> queued
    # on the SAME key (the explicit same-old/new contract — acceptable when the hash is unchanged).
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    pool = _FakePool()
    result = asyncio.run(
        invalidate(
            store,
            pool,
            trigger=RecomputeTrigger.orca_upgrade,
            stl_hash=STL_HASH,
            bundle_hash=BUNDLE_HASH,
        )
    )
    assert result is not None
    assert result.status == EstimateStatus.queued
    args, _ = pool.calls[0]
    assert args == (SLICE_JOB_NAME, STL_HASH, BUNDLE_HASH)


def test_dispatch_cost_only_rejects_bundle_hash_change(tmp_path):
    # OD-7: a cost-only change is in-place arithmetic — it can NEVER change the bundle hash.
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    pool = _FakePool()
    with pytest.raises(ValueError):
        asyncio.run(
            invalidate(
                store,
                pool,
                trigger=RecomputeTrigger.spoolman_cost_only,
                stl_hash=STL_HASH,
                bundle_hash=BUNDLE_HASH,
                new_bundle_hash=NEW_BUNDLE_HASH,
                price_per_gram=0.05,
            )
        )
    assert pool.calls == []  # nothing enqueued on the contract breach


# === AC-6: enumeration + bulk primitives =====================================


def _seed_three_bundles(store) -> list[str]:
    bundles = ["c" * 64, "d" * 64, "e" * 64]
    for b in bundles:
        store.write(_fresh(bundle_hash=b))
    return bundles


def test_iter_stl_estimates_yields_all_bundle_variants_for_one_stl(tmp_path):
    store = EstimateStore(tmp_path)
    bundles = _seed_three_bundles(store)
    got = {r.bundle_hash for r in store.iter_stl_estimates(STL_HASH)}
    assert got == set(bundles)


def test_iter_stl_estimates_ignores_lock_and_tmp_sidecars(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh(bundle_hash="c" * 64))
    stl_dir = tmp_path / "estimates" / STL_HASH[:2] / STL_HASH
    (stl_dir / f".{'c' * 64}.json.lock").write_text("", encoding="utf-8")
    (stl_dir / f".{'c' * 64}.json.abcd.tmp").write_text("garbage", encoding="utf-8")
    records = list(store.iter_stl_estimates(STL_HASH))
    assert len(records) == 1  # only the *.json record, never the sidecars
    assert records[0].bundle_hash == "c" * 64


def test_iter_stl_estimates_on_missing_stl_yields_nothing(tmp_path):
    store = EstimateStore(tmp_path)
    assert list(store.iter_stl_estimates(STL_HASH)) == []
    # A malformed hash also yields nothing (never raises, never builds a path).
    assert list(store.iter_stl_estimates("../../etc")) == []


def test_iter_all_estimates_walks_full_subtree(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh(stl_hash="a" * 64, bundle_hash="c" * 64))
    store.write(_fresh(stl_hash="f" * 64, bundle_hash="d" * 64))
    keys = {(r.stl_hash, r.bundle_hash) for r in store.iter_all_estimates()}
    assert keys == {("a" * 64, "c" * 64), ("f" * 64, "d" * 64)}


def test_iter_all_estimates_empty_store_yields_nothing(tmp_path):
    store = EstimateStore(tmp_path)
    assert list(store.iter_all_estimates()) == []


def test_bulk_cost_recompute_applies_to_each_key_no_enqueue(tmp_path):
    store = EstimateStore(tmp_path)
    bundles = _seed_three_bundles(store)
    keys = [(STL_HASH, b) for b in bundles]
    results = recompute_cost_only_bulk(store, keys, price_per_gram=0.05)
    assert len([r for r in results if r is not None]) == 3
    for b in bundles:
        assert store.read(STL_HASH, b).filament_cost == pytest.approx(76.76 * 0.05)


def test_bulk_invalidate_marks_each_stale_and_enqueues_each(tmp_path):
    store = EstimateStore(tmp_path)
    bundles = _seed_three_bundles(store)
    keys = [(STL_HASH, b) for b in bundles]
    pool = _FakePool()
    results = asyncio.run(
        invalidate_bulk(store, pool, trigger=RecomputeTrigger.orca_upgrade, keys=keys)
    )
    assert all(r is not None and r.status == EstimateStatus.queued for r in results)
    # One deduped enqueue per key (distinct job ids per distinct key).
    assert len(pool.calls) == 3
    job_ids = {kwargs["_job_id"] for _, kwargs in pool.calls}
    assert job_ids == {slice_job_id(STL_HASH, b) for b in bundles}


def test_bulk_invalidate_supports_old_new_bundle_triples(tmp_path):
    # A bulk bundle-changing trigger may supply (stl, old_bundle, new_bundle) triples so each
    # old record is marked stale while the recompute is enqueued for the corresponding new key.
    store = EstimateStore(tmp_path)
    store.write(_fresh(bundle_hash="d" * 64))
    pool = _FakePool()
    keys = [(STL_HASH, "d" * 64, "e" * 64)]  # (stl, old, new)
    asyncio.run(invalidate_bulk(store, pool, trigger=RecomputeTrigger.bundle_retune, keys=keys))
    assert store.read(STL_HASH, "d" * 64).status == EstimateStatus.stale
    args, _ = pool.calls[0]
    assert args == (SLICE_JOB_NAME, STL_HASH, "e" * 64)


# === AC-7: Story 32.5 coordination boundary (engine here, wiring there) ======


def test_recompute_does_not_import_or_read_spools_module():
    source = (REPO_ROOT / "apps/api/app/modules/slicer/recompute.py").read_text(encoding="utf-8")
    # The engine takes price_per_gram / bundle_hash as inputs — it never reads Spoolman.
    assert "app.modules.spools" not in source
    assert "import spools" not in source


def test_cost_only_input_is_price_per_gram_not_spoolman_entity():
    params = inspect.signature(recompute_cost_only).parameters
    assert "price_per_gram" in params  # a scalar (currency per gram), not a Spoolman record
    assert "filament" not in params
    assert "spool" not in params


# === AC-8: observability (no g-code, no full record dump) ====================


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.NOTSET)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def recompute_log():
    logger = logging.getLogger("app.modules.slicer.recompute")
    prev_level, prev_disabled = logger.level, logger.disabled
    handler = _ListHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.disabled = False
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(prev_level)
        logger.disabled = prev_disabled


def test_cost_only_recompute_emits_arithmetic_path_tag(tmp_path, recompute_log):
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    recompute_cost_only(store, STL_HASH, BUNDLE_HASH, price_per_gram=0.05)
    assert recompute_log.records, "expected a recompute log line"
    rec = recompute_log.records[-1].__dict__
    assert rec["labels.recompute_path"] == "arithmetic"  # confirms it never hit the slicer queue
    assert rec["labels.stl_hash"] == STL_HASH
    assert rec["labels.bundle_hash"] == BUNDLE_HASH
    assert rec["labels.estimate_status"] == "fresh"


def test_invalidate_emits_trigger_and_status_tags(tmp_path, recompute_log):
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    pool = _FakePool()
    asyncio.run(
        invalidate(
            store,
            pool,
            trigger=RecomputeTrigger.bundle_retune,
            stl_hash=STL_HASH,
            bundle_hash=BUNDLE_HASH,
        )
    )
    tagged = [r for r in recompute_log.records if "labels.trigger" in r.__dict__]
    assert tagged
    rec = tagged[-1].__dict__
    assert rec["labels.trigger"] == "bundle_retune"
    assert rec["labels.estimate_status"] == "queued"


def test_bulk_invalidate_emits_count(tmp_path, recompute_log):
    store = EstimateStore(tmp_path)
    bundles = _seed_three_bundles(store)
    keys = [(STL_HASH, b) for b in bundles]
    pool = _FakePool()
    asyncio.run(invalidate_bulk(store, pool, trigger=RecomputeTrigger.orca_upgrade, keys=keys))
    counted = [r for r in recompute_log.records if "labels.count" in r.__dict__]
    assert counted
    assert counted[-1].__dict__["labels.count"] == 3  # never silently truncated


def test_recompute_never_logs_full_record_or_gcode(tmp_path, recompute_log):
    store = EstimateStore(tmp_path)
    store.write(_fresh())
    recompute_cost_only(store, STL_HASH, BUNDLE_HASH, price_per_gram=0.05)
    pool = _FakePool()
    asyncio.run(
        invalidate(
            store,
            pool,
            trigger=RecomputeTrigger.bundle_retune,
            stl_hash=STL_HASH,
            bundle_hash=BUNDLE_HASH,
        )
    )
    assert recompute_log.records
    for record in recompute_log.records:
        msg = record.getMessage()
        # Never a full EstimateRecord JSON dump, never g-code body.
        assert "filament_settings_id" not in msg
        assert "G1 " not in msg
        for value in record.__dict__.values():
            if isinstance(value, str):
                assert "settings_ids" not in value
                assert "G1 X" not in value


# === AC-10: NFR20-CONTAINER-1 grep invariant =================================


def test_no_bench_or_windows_path_literal_in_recompute():
    import re

    full = re.compile(r"/mnt/c|fenrir|\.exe|[Ww]indows", re.IGNORECASE)
    path = REPO_ROOT / "apps/api/app/modules/slicer/recompute.py"
    assert not full.search(path.read_text(encoding="utf-8"))


# === AC-12: determinism + transition concurrency =============================


def test_cost_only_recompute_is_idempotent_given_same_inputs(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_fresh(filament_g=80.0))
    first = recompute_cost_only(store, STL_HASH, BUNDLE_HASH, price_per_gram=0.05)
    second = recompute_cost_only(store, STL_HASH, BUNDLE_HASH, price_per_gram=0.05)
    # Same (record, price) ⇒ same cost (computed_at excluded — the only non-deterministic field).
    assert first.filament_cost == second.filament_cost == pytest.approx(4.0)


def test_concurrent_transition_is_serialized_no_torn_write(tmp_path, monkeypatch):
    """Two threads race mark_stale on the same fresh record; the per-record lock serializes
    them so the published file is always complete valid JSON and the original computed_at is
    preserved (mirrors the Story 32.3 fresh-write concurrency test for the transition path).
    """
    store = EstimateStore(tmp_path)
    store.write(_fresh(filament_g=11.11, computed_at="2026-01-01T00:00:00+00:00"))
    publish_started = threading.Event()
    release_publish = threading.Event()
    orig_publish = EstimateStore._atomic_publish

    def slow_publish(path, content):
        publish_started.set()
        assert release_publish.wait(timeout=5)
        return orig_publish(path, content)

    monkeypatch.setattr(EstimateStore, "_atomic_publish", staticmethod(slow_publish))

    t1 = threading.Thread(target=store.mark_stale, args=(STL_HASH, BUNDLE_HASH))
    t1.start()
    assert publish_started.wait(timeout=5)  # writer #1 holds the lock, mid-publish
    t2 = threading.Thread(target=store.mark_stale, args=(STL_HASH, BUNDLE_HASH))
    t2.start()
    release_publish.set()
    t1.join(timeout=5)
    t2.join(timeout=5)
    assert not t1.is_alive() and not t2.is_alive()

    got = store.read(STL_HASH, BUNDLE_HASH)
    assert got is not None
    assert got.status == EstimateStatus.stale  # complete, valid record (no torn write)
    assert got.computed_at == "2026-01-01T00:00:00+00:00"  # original preserved through transition
    assert got.filament_g == pytest.approx(11.11)
