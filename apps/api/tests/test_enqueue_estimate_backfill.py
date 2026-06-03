"""Tests for ``scripts.enqueue_estimate_backfill`` (EST-INGEST-1).

Runs against an isolated SQLite DB + a tmp content tree, with the slicer seams
injected (a fake arq pool, real tmp ``StlCache`` + ``EstimateStore``, a fake
resolver). Covers the three operator-facing behaviors: dry-run inventory, the
enqueue path, and the idempotent skip of an already-``fresh`` part.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from types import SimpleNamespace

from sqlmodel import Session

from app.core.db.models import Category, Model, ModelFile, ModelFileKind
from app.core.db.session import create_engine_for_url, init_schema
from app.modules.slicer.estimate_store import EstimateStore
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
from app.modules.slicer.stl_cache import StlCache
from app.modules.slicer.worker import SLICER_QUEUE_NAME
from scripts.enqueue_estimate_backfill import BackfillStats, run

STL_BYTES = b"solid part\nfacet\nendsolid part\n"
SHA256_OF_STL = hashlib.sha256(STL_BYTES).hexdigest()
BUNDLE_HASH = "c" * 64

PRESET = PrintIntentPreset(
    name="PLA standard",
    material_class="PLA",
    quality_tier="standard",
    printer_ref="creality-k1-max-microswiss-hf",
    is_default=True,
)


class _FakePool:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple, dict]] = []

    async def enqueue_job(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return SimpleNamespace(job_id=kwargs.get("_job_id"))


def _success_resolver(intent: PrintIntentPreset) -> ResolveSuccess:
    return ResolveSuccess(
        bundle=SlicerProfileBundle(
            bundle_hash=BUNDLE_HASH,
            orca_version="2.3.2",
            machine={},
            process={},
            filament={},
            source_snapshot_ref="s" * 64,
            created_at="2026-06-03T00:00:00+00:00",
        ),
        triple=ResolvedTriple(machine={}, process={}, filament={}),
        from_cache=False,
    )


def _failing_resolver(intent: PrintIntentPreset) -> ResolveFailure:
    return ResolveFailure(
        reason=ResolveReason.unsupported_material_class, message="no vendored profile"
    )


def _make_engine(tmp_path: Path):
    eng = create_engine_for_url(f"sqlite:///{tmp_path / 'backfill.db'}")
    init_schema(eng)
    return eng


def _seed_stl(
    session: Session,
    *,
    content_dir: Path,
    name: str = "part.stl",
    sha: str = SHA256_OF_STL,
    write: bool = True,
) -> ModelFile:
    cat = Category(slug=f"cat-{uuid.uuid4().hex[:8]}", name_en="cat")
    session.add(cat)
    session.commit()
    session.refresh(cat)
    model = Model(slug=f"m-{uuid.uuid4().hex[:8]}", name_en="m", category_id=cat.id)
    session.add(model)
    session.commit()
    session.refresh(model)
    storage_path = f"models/{model.id}/files/{name}"
    mf = ModelFile(
        model_id=model.id,
        kind=ModelFileKind.stl,
        original_name=name,
        storage_path=storage_path,
        sha256=sha,
        size_bytes=len(STL_BYTES),
        mime_type="model/stl",
    )
    session.add(mf)
    session.commit()
    session.refresh(mf)
    if write:
        abs_path = content_dir / storage_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_bytes(STL_BYTES)
    return mf


async def _run(engine, content_dir, *, pool, cache, store, resolver, dry_run=False):
    return await run(
        engine=engine,
        stl_cache=cache,
        estimate_store=store,
        resolve_fn=resolver,
        default_preset=PRESET,
        content_dir=content_dir,
        arq_pool=pool,
        dry_run=dry_run,
    )


async def test_dry_run_inventory_does_not_enqueue(tmp_path):
    engine = _make_engine(tmp_path)
    content_dir = tmp_path / "content"
    with Session(engine) as s:
        _seed_stl(s, content_dir=content_dir)
    pool, cache, store = _FakePool(), StlCache(tmp_path / "cache"), EstimateStore(tmp_path / "est")

    stats = await _run(
        engine,
        content_dir,
        pool=pool,
        cache=cache,
        store=store,
        resolver=_success_resolver,
        dry_run=True,
    )

    assert isinstance(stats, BackfillStats)
    assert stats.inspected == 1
    assert stats.would_enqueue == 1
    assert stats.enqueued == 0
    assert pool.calls == []
    # dry-run must NOT populate the cache.
    assert not cache.has(SHA256_OF_STL)


async def test_dry_run_classifies_missing_stl(tmp_path):
    engine = _make_engine(tmp_path)
    content_dir = tmp_path / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    with Session(engine) as s:
        _seed_stl(s, content_dir=content_dir, write=False)  # row but no bytes on disk
    pool, cache, store = _FakePool(), StlCache(tmp_path / "cache"), EstimateStore(tmp_path / "est")

    stats = await _run(
        engine,
        content_dir,
        pool=pool,
        cache=cache,
        store=store,
        resolver=_success_resolver,
        dry_run=True,
    )

    assert stats.inspected == 1
    assert stats.missing_stl == 1
    assert stats.would_enqueue == 0


async def test_enqueue_path_enqueues_and_caches(tmp_path):
    engine = _make_engine(tmp_path)
    content_dir = tmp_path / "content"
    with Session(engine) as s:
        _seed_stl(s, content_dir=content_dir)
    pool, cache, store = _FakePool(), StlCache(tmp_path / "cache"), EstimateStore(tmp_path / "est")

    stats = await _run(
        engine,
        content_dir,
        pool=pool,
        cache=cache,
        store=store,
        resolver=_success_resolver,
    )

    assert stats.inspected == 1
    assert stats.enqueued == 1
    assert stats.already_fresh == 0
    assert len(pool.calls) == 1
    args, kwargs = pool.calls[0]
    assert args == ("slice_estimate", SHA256_OF_STL, BUNDLE_HASH)
    assert kwargs["_queue_name"] == SLICER_QUEUE_NAME
    assert cache.has(SHA256_OF_STL)


async def test_enqueue_path_skips_already_fresh(tmp_path):
    engine = _make_engine(tmp_path)
    content_dir = tmp_path / "content"
    with Session(engine) as s:
        _seed_stl(s, content_dir=content_dir)
    pool, cache, store = _FakePool(), StlCache(tmp_path / "cache"), EstimateStore(tmp_path / "est")
    # Pre-seed a fresh estimate for (sha256, bundle_hash) — the idempotency pre-check.
    store.write(
        EstimateRecord(
            stl_hash=SHA256_OF_STL,
            bundle_hash=BUNDLE_HASH,
            orca_version="2.3.2",
            time_seconds=1800,
            filament_g=8.0,
            filament_mm=2000.0,
            filament_cm3=6.5,
            status=EstimateStatus.fresh,
            computed_at="2026-06-03T00:00:00+00:00",
        )
    )

    stats = await _run(
        engine,
        content_dir,
        pool=pool,
        cache=cache,
        store=store,
        resolver=_success_resolver,
    )

    assert stats.inspected == 1
    assert stats.already_fresh == 1
    assert stats.enqueued == 0
    assert pool.calls == []


async def test_enqueue_path_classifies_resolve_failure(tmp_path):
    engine = _make_engine(tmp_path)
    content_dir = tmp_path / "content"
    with Session(engine) as s:
        _seed_stl(s, content_dir=content_dir)
    pool, cache, store = _FakePool(), StlCache(tmp_path / "cache"), EstimateStore(tmp_path / "est")

    stats = await _run(
        engine,
        content_dir,
        pool=pool,
        cache=cache,
        store=store,
        resolver=_failing_resolver,
    )

    assert stats.inspected == 1
    assert stats.resolve_failed == 1
    assert stats.enqueued == 0
    assert pool.calls == []


async def test_only_stl_rows_are_inspected(tmp_path):
    engine = _make_engine(tmp_path)
    content_dir = tmp_path / "content"
    with Session(engine) as s:
        _seed_stl(s, content_dir=content_dir)
        # An image row must NOT be inspected by the estimate backfill.
        cat = Category(slug="img-cat", name_en="c")
        s.add(cat)
        s.commit()
        s.refresh(cat)
        model = Model(slug="img-m", name_en="m", category_id=cat.id)
        s.add(model)
        s.commit()
        s.refresh(model)
        s.add(
            ModelFile(
                model_id=model.id,
                kind=ModelFileKind.image,
                original_name="pic.png",
                storage_path=f"models/{model.id}/files/pic.png",
                sha256="d" * 64,
                size_bytes=1,
                mime_type="image/png",
            )
        )
        s.commit()
    pool, cache, store = _FakePool(), StlCache(tmp_path / "cache"), EstimateStore(tmp_path / "est")

    stats = await _run(
        engine,
        content_dir,
        pool=pool,
        cache=cache,
        store=store,
        resolver=_success_resolver,
    )

    assert stats.inspected == 1  # only the STL row
    assert stats.enqueued == 1
