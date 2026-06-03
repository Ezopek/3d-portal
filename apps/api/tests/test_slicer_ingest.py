"""Tests for the catalog-STL estimate ingestion service (EST-INGEST-1).

The service connects a real catalog STL ``ModelFile`` to the ``(stl_hash,
bundle_hash)`` key the estimate store is read by, and idempotently triggers the
first slice via the Epic 32 primitives. It re-uses (never re-implements):

    * ``resolve`` / ``resolve_intent``     — persists the bundle in the real BundleStore
    * ``StlCache.populate_from_source``    — content-hashes + caches the STL bytes
    * ``enqueue_slice_estimate`` (+ ``slice_job_id``) — deduped enqueue
    * ``EstimateStore.read``               — idempotency pre-check

Two test layers:

    1. The sha256-equality PROOF gate — ``ModelFile.sha256`` for a ``kind=stl`` row
       IS the byte-exact ``compute_stl_hash`` the slicer mints/reads/dedupes by, so
       the part->hash mapping needs no migration.
    2. Every I/O-matrix branch of the service, with seams injected (a fake arq pool
       capturing ``enqueue_job``, a real tmp ``StlCache`` + ``EstimateStore``, and a
       fake resolver returning success/failure) plus one real-``resolve`` happy path
       proving the bundle is persisted in the real ``BundleStore``.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from types import SimpleNamespace

from app.core.db.models import ModelFile, ModelFileKind
from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.enqueue import slice_job_id
from app.modules.slicer.estimate_store import EstimateStore
from app.modules.slicer.ingest import (
    IngestResult,
    IngestStatus,
    ingest_model_estimates,
    ingest_stl_part,
)
from app.modules.slicer.models import (
    EstimateRecord,
    EstimateStatus,
    PrintIntentPreset,
    ResolvedTriple,
    ResolveFailure,
    ResolveReason,
    ResolveSuccess,
    SlicerProfileBundle,
)
from app.modules.slicer.overrides import NoopOverrideProvider
from app.modules.slicer.resolver import VendoredProfileSource, resolve
from app.modules.slicer.stl_cache import StlCache, compute_stl_hash, validate_content_hash
from app.modules.slicer.validation import NullCliValidator
from app.modules.slicer.worker import SLICER_QUEUE_NAME

FIXTURES = Path(__file__).parent / "fixtures" / "slicer"

STL_BYTES = b"solid cube\nfacet normal 0 0 0\nendsolid cube\n"
SHA256_OF_STL = hashlib.sha256(STL_BYTES).hexdigest()

BUNDLE_HASH = "b" * 64

DEFAULT_PRESET = PrintIntentPreset(
    name="PLA standard",
    material_class="PLA",
    quality_tier="standard",
    printer_ref="creality-k1-max-microswiss-hf",
    is_default=True,
)


# --- seams ----------------------------------------------------------------------


class _FakePool:
    """Records ``enqueue_job`` calls so a test can assert the dedupe contract."""

    def __init__(self) -> None:
        self.calls: list[tuple[tuple, dict]] = []

    async def enqueue_job(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return SimpleNamespace(job_id=kwargs.get("_job_id"))


def _bundle(bundle_hash: str = BUNDLE_HASH) -> SlicerProfileBundle:
    return SlicerProfileBundle(
        bundle_hash=bundle_hash,
        orca_version="2.3.2",
        machine={"name": "m"},
        process={"name": "p"},
        filament={"name": "f"},
        source_snapshot_ref="s" * 64,
        created_at="2026-06-03T00:00:00+00:00",
    )


def _success_resolver(bundle_hash: str = BUNDLE_HASH):
    def _resolve(intent: PrintIntentPreset) -> ResolveSuccess:
        return ResolveSuccess(
            bundle=_bundle(bundle_hash),
            triple=ResolvedTriple(machine={}, process={}, filament={}),
            from_cache=False,
        )

    return _resolve


def _failing_resolver(reason: ResolveReason = ResolveReason.unsupported_material_class):
    def _resolve(intent: PrintIntentPreset) -> ResolveFailure:
        return ResolveFailure(reason=reason, message=f"classified: {reason}")

    return _resolve


def _model_file(
    *,
    content_dir: Path,
    kind: ModelFileKind = ModelFileKind.stl,
    storage_path: str = "models/m/files/part.stl",
    sha256: str = SHA256_OF_STL,
    write_bytes: bytes | None = STL_BYTES,
) -> ModelFile:
    if write_bytes is not None:
        abs_path = content_dir / storage_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_bytes(write_bytes)
    return ModelFile(
        id=uuid.uuid4(),
        model_id=uuid.uuid4(),
        kind=kind,
        original_name="part.stl",
        storage_path=storage_path,
        sha256=sha256,
        size_bytes=len(write_bytes) if write_bytes is not None else 0,
        mime_type="model/stl",
    )


def _fresh_record(stl_hash: str, bundle_hash: str) -> EstimateRecord:
    return EstimateRecord(
        stl_hash=stl_hash,
        bundle_hash=bundle_hash,
        orca_version="2.3.2",
        time_seconds=3600,
        filament_g=12.5,
        filament_mm=4200.0,
        filament_cm3=10.0,
        status=EstimateStatus.fresh,
        computed_at="2026-06-03T00:00:00+00:00",
    )


def _failed_record(stl_hash: str, bundle_hash: str) -> EstimateRecord:
    return EstimateRecord(
        stl_hash=stl_hash,
        bundle_hash=bundle_hash,
        orca_version="2.3.2",
        status=EstimateStatus.failed,
        reason="parse_failure",
        computed_at="2026-06-03T00:00:00+00:00",
    )


async def _ingest(model_file, *, pool, cache, store, resolver, content_dir):
    return await ingest_stl_part(
        model_file,
        arq_pool=pool,
        stl_cache=cache,
        estimate_store=store,
        resolve_fn=resolver,
        default_preset=DEFAULT_PRESET,
        content_dir=content_dir,
    )


# === sha256-equality PROOF gate (no-migration load-bearing contract) ============


def test_compute_stl_hash_equals_streaming_sha256_of_same_bytes(tmp_path):
    """compute_stl_hash IS plain streaming hashlib.sha256 over the STL bytes."""
    src = tmp_path / "part.stl"
    src.write_bytes(STL_BYTES)

    computed = compute_stl_hash(src)

    # The value admin upload (_write_atomic) and hydrate (_sha256_of_file) mint:
    # both are plain streaming hashlib.sha256 of the raw bytes.
    assert computed == hashlib.sha256(STL_BYTES).hexdigest()
    # 64 lowercase hex, and accepted by the slicer path-safety gate.
    assert computed == computed.lower()
    assert len(computed) == 64
    assert validate_content_hash(computed) == computed


def test_compute_stl_hash_matches_hydrate_sha256_helper(tmp_path):
    """The hydrate verify path (disk_sha == master_sha) mints the same value."""
    from scripts.hydrate_local_tree import _sha256_of_file

    src = tmp_path / "part.stl"
    src.write_bytes(STL_BYTES)

    assert compute_stl_hash(src) == _sha256_of_file(src)


def test_model_file_sha256_equals_cache_populate_hash(tmp_path):
    """A kind=stl ModelFile.sha256 == the hash populate_from_source mints + caches.

    This is the part->stl_hash linkage the service relies on WITHOUT a migration:
    the value the row already carries is the value the slicer reads/dedupes by.
    """
    content_dir = tmp_path / "content"
    row = _model_file(content_dir=content_dir)
    cache = StlCache(tmp_path / "cache")

    populated_hash = cache.populate_from_source(content_dir / row.storage_path)

    assert populated_hash == row.sha256
    assert cache.has(populated_hash)


# === I/O matrix: first slice (happy path, fake resolver) ========================


async def test_first_slice_enqueues_deduped_job(tmp_path):
    content_dir = tmp_path / "content"
    row = _model_file(content_dir=content_dir)
    pool, cache, store = _FakePool(), StlCache(tmp_path / "cache"), EstimateStore(tmp_path / "est")

    result = await _ingest(
        row,
        pool=pool,
        cache=cache,
        store=store,
        resolver=_success_resolver(),
        content_dir=content_dir,
    )

    assert result.status == IngestStatus.enqueued
    assert result.stl_hash == SHA256_OF_STL
    assert result.bundle_hash == BUNDLE_HASH
    assert result.job_id == slice_job_id(SHA256_OF_STL, BUNDLE_HASH)
    # exactly one job, routed to the slicer queue, carrying the (stl, bundle) tuple.
    assert len(pool.calls) == 1
    args, kwargs = pool.calls[0]
    assert args == ("slice_estimate", SHA256_OF_STL, BUNDLE_HASH)
    assert kwargs["_job_id"] == slice_job_id(SHA256_OF_STL, BUNDLE_HASH)
    assert kwargs["_queue_name"] == SLICER_QUEUE_NAME
    # the STL is present in the cache for the worker to read.
    assert cache.has(SHA256_OF_STL)


async def test_first_slice_with_real_resolver_persists_bundle(tmp_path):
    """Acceptance: a real resolve persists the bundle in the real writing BundleStore."""
    content_dir = tmp_path / "content"
    row = _model_file(content_dir=content_dir)
    pool, cache, store = _FakePool(), StlCache(tmp_path / "cache"), EstimateStore(tmp_path / "est")
    bundle_store = BundleStore(tmp_path / "bundles")

    def real_resolver(intent: PrintIntentPreset):
        return resolve(
            intent,
            source=VendoredProfileSource(FIXTURES),
            store=bundle_store,
            override_provider=NoopOverrideProvider(),
            validator=NullCliValidator(),
            orca_version="2.3.2",
        )

    result = await _ingest(
        row,
        pool=pool,
        cache=cache,
        store=store,
        resolver=real_resolver,
        content_dir=content_dir,
    )

    assert result.status == IngestStatus.enqueued
    assert result.bundle_hash is not None
    # the worker can load_bundle: the bundle is in the REAL writing store.
    assert bundle_store.has_bundle(result.bundle_hash)
    assert cache.has(result.stl_hash)
    assert len(pool.calls) == 1


# === I/O matrix: idempotency ====================================================


async def test_already_fresh_skips_enqueue(tmp_path):
    content_dir = tmp_path / "content"
    row = _model_file(content_dir=content_dir)
    pool, cache, store = _FakePool(), StlCache(tmp_path / "cache"), EstimateStore(tmp_path / "est")
    store.write(_fresh_record(SHA256_OF_STL, BUNDLE_HASH))

    result = await _ingest(
        row,
        pool=pool,
        cache=cache,
        store=store,
        resolver=_success_resolver(),
        content_dir=content_dir,
    )

    assert result.status == IngestStatus.already_fresh
    assert result.stl_hash == SHA256_OF_STL
    assert result.bundle_hash == BUNDLE_HASH
    assert pool.calls == []


async def test_failed_record_re_enqueues(tmp_path):
    """A non-fresh (failed/stale/queued) record must re-slice."""
    content_dir = tmp_path / "content"
    row = _model_file(content_dir=content_dir)
    pool, cache, store = _FakePool(), StlCache(tmp_path / "cache"), EstimateStore(tmp_path / "est")
    store.write(_failed_record(SHA256_OF_STL, BUNDLE_HASH))

    result = await _ingest(
        row,
        pool=pool,
        cache=cache,
        store=store,
        resolver=_success_resolver(),
        content_dir=content_dir,
    )

    assert result.status == IngestStatus.enqueued
    assert len(pool.calls) == 1


async def test_re_running_ingest_uses_deterministic_job_id(tmp_path):
    """In-flight dedupe: a second enqueue of the same key carries the same _job_id."""
    content_dir = tmp_path / "content"
    row = _model_file(content_dir=content_dir)
    pool, cache, store = _FakePool(), StlCache(tmp_path / "cache"), EstimateStore(tmp_path / "est")

    r1 = await _ingest(
        row,
        pool=pool,
        cache=cache,
        store=store,
        resolver=_success_resolver(),
        content_dir=content_dir,
    )
    r2 = await _ingest(
        row,
        pool=pool,
        cache=cache,
        store=store,
        resolver=_success_resolver(),
        content_dir=content_dir,
    )

    assert r1.job_id == r2.job_id == slice_job_id(SHA256_OF_STL, BUNDLE_HASH)
    assert pool.calls[0][1]["_job_id"] == pool.calls[1][1]["_job_id"]


# === I/O matrix: classified failures (no silent zero, never raise) ==============


async def test_resolve_failed_carries_reason_and_skips_enqueue(tmp_path):
    content_dir = tmp_path / "content"
    row = _model_file(content_dir=content_dir)
    pool, cache, store = _FakePool(), StlCache(tmp_path / "cache"), EstimateStore(tmp_path / "est")

    result = await _ingest(
        row,
        pool=pool,
        cache=cache,
        store=store,
        resolver=_failing_resolver(ResolveReason.unsupported_material_class),
        content_dir=content_dir,
    )

    assert result.status == IngestStatus.resolve_failed
    assert result.resolve_reason == ResolveReason.unsupported_material_class
    assert result.bundle_hash is None
    assert pool.calls == []


async def test_missing_stl_skips_enqueue(tmp_path):
    content_dir = tmp_path / "content"
    # storage_path points nowhere — no bytes written.
    row = _model_file(content_dir=content_dir, write_bytes=None)
    pool, cache, store = _FakePool(), StlCache(tmp_path / "cache"), EstimateStore(tmp_path / "est")

    result = await _ingest(
        row,
        pool=pool,
        cache=cache,
        store=store,
        resolver=_success_resolver(),
        content_dir=content_dir,
    )

    assert result.status == IngestStatus.missing_stl
    assert pool.calls == []


async def test_path_escape_is_classified_error(tmp_path):
    content_dir = tmp_path / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    # An escaping storage_path: write the bytes OUTSIDE content_dir so existence
    # alone cannot mask the escape, then assert the guard fires.
    escape_target = tmp_path / "escape.stl"
    escape_target.write_bytes(STL_BYTES)
    row = _model_file(content_dir=content_dir, storage_path="../escape.stl", write_bytes=None)
    pool, cache, store = _FakePool(), StlCache(tmp_path / "cache"), EstimateStore(tmp_path / "est")

    result = await _ingest(
        row,
        pool=pool,
        cache=cache,
        store=store,
        resolver=_success_resolver(),
        content_dir=content_dir,
    )

    assert result.status == IngestStatus.error
    assert pool.calls == []


async def test_non_stl_kind_is_skipped(tmp_path):
    content_dir = tmp_path / "content"
    row = _model_file(
        content_dir=content_dir, kind=ModelFileKind.image, storage_path="models/m/files/pic.png"
    )
    pool, cache, store = _FakePool(), StlCache(tmp_path / "cache"), EstimateStore(tmp_path / "est")

    result = await _ingest(
        row,
        pool=pool,
        cache=cache,
        store=store,
        resolver=_success_resolver(),
        content_dir=content_dir,
    )

    assert result.status == IngestStatus.skipped_non_stl
    assert pool.calls == []


# === ingest_model_estimates: walk a model's parts ===============================


async def test_ingest_model_estimates_processes_only_stl_parts(tmp_path):
    content_dir = tmp_path / "content"
    stl_row = _model_file(content_dir=content_dir, storage_path="models/m/files/a.stl")
    img_row = _model_file(
        content_dir=content_dir, kind=ModelFileKind.image, storage_path="models/m/files/a.png"
    )
    pool, cache, store = _FakePool(), StlCache(tmp_path / "cache"), EstimateStore(tmp_path / "est")

    results = await ingest_model_estimates(
        [stl_row, img_row],
        arq_pool=pool,
        stl_cache=cache,
        estimate_store=store,
        resolve_fn=_success_resolver(),
        default_preset=DEFAULT_PRESET,
        content_dir=content_dir,
    )

    # only the STL part is inspected/enqueued.
    assert [r.model_file_id for r in results] == [stl_row.id]
    assert results[0].status == IngestStatus.enqueued
    assert len(pool.calls) == 1


async def test_ingest_result_is_returned_type(tmp_path):
    content_dir = tmp_path / "content"
    row = _model_file(content_dir=content_dir)
    pool, cache, store = _FakePool(), StlCache(tmp_path / "cache"), EstimateStore(tmp_path / "est")

    result = await _ingest(
        row,
        pool=pool,
        cache=cache,
        store=store,
        resolver=_success_resolver(),
        content_dir=content_dir,
    )

    assert isinstance(result, IngestResult)
    assert result.model_file_id == row.id
