"""Catalog-STL estimate ingestion service (EST-INGEST-1).

The Epic 32 slicer stack ships every primitive to slice an STL and read its
estimate, but nothing connects a *real catalog STL part* to the ``(stl_hash,
bundle_hash)`` key the estimate store is read by, and nothing triggers a first
slice. This service is that connective tissue: for a catalog STL ``ModelFile`` it

    1. validates the part is ``kind=stl`` (others are skipped, never inspected);
    2. resolves its on-disk path UNDER the content root (path-escape ⇒ classified
       ``error``; missing/unreadable ⇒ classified ``missing_stl``);
    3. resolves the configurable default print-intent preset to a persisted bundle
       via the injected resolver (which writes the REAL ``BundleStore`` so the
       worker can ``load_bundle``); a classified ``ResolveFailure`` ⇒ no enqueue,
       status ``resolve_failed`` carrying the ``ResolveReason``;
    4. uses ``ModelFile.sha256`` (proven byte-equal to ``compute_stl_hash`` — see
       ``tests/test_slicer_ingest.py``, so NO migration) as the candidate
       ``stl_hash`` for an idempotency pre-check against ``EstimateStore.read``: a
       ``fresh`` record ⇒ no enqueue (``already_fresh``);
    5. otherwise enqueues the first slice via ``enqueue_slice_estimate`` — which
       freshly content-hashes the STL bytes, populates the ``StlCache``, and
       enqueues the deduped ``(stl_hash, bundle_hash)`` job on ``arq:slicer``.

Every outcome is a typed, classified ``IngestResult`` and is logged — never a
silent zero and never a silent skip (the Epic 32 no-silent-zero contract extended
to the ingestion seam). The service is pure and seam-injected: the arq pool, STL
cache, estimate store, resolver function, default preset, and content root are all
parameters, so it never touches global settings and is fully unit-testable.

It re-uses the Epic 32 primitives byte-for-byte and re-implements NONE of hashing,
store layout, concurrency, dedupe, or queue routing.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from app.core.db.models import ModelFile, ModelFileKind
from app.modules.slicer.enqueue import enqueue_slice_estimate
from app.modules.slicer.estimate_store import EstimateStore
from app.modules.slicer.models import (
    EstimateStatus,
    PrintIntentPreset,
    ResolveOutcome,
    ResolveReason,
    ResolveSuccess,
)
from app.modules.slicer.stl_cache import StlCache, is_content_hash

_LOG = logging.getLogger("app.modules.slicer.ingest")

# The resolver seam: a callable mapping an intent to a classified resolve outcome.
# Production wires ``resolve_intent`` (settings-backed, real writing BundleStore +
# AttributionStore); tests inject a fake returning success/failure. Kept as a plain
# callable so the service never re-implements or re-wires the resolver itself.
ResolverFn = Callable[[PrintIntentPreset], ResolveOutcome]


class IngestStatus(StrEnum):
    """Classified per-part ingestion outcome (the no-silent-skip contract).

    Every branch of the I/O matrix maps to exactly one of these; a caller (the
    backfill script) tallies them into an operator summary. ``enqueued`` is the
    only status that triggers a slice; the rest are explicit, logged non-actions.
    """

    enqueued = "enqueued"
    already_fresh = "already_fresh"
    resolve_failed = "resolve_failed"
    missing_stl = "missing_stl"
    skipped_non_stl = "skipped_non_stl"
    error = "error"


@dataclass(frozen=True)
class IngestResult:
    """Typed result of ingesting one ``ModelFile`` — never a bare bool/None.

    ``stl_hash`` / ``bundle_hash`` / ``job_id`` are present on the paths that reach
    them (``enqueued`` carries all three; ``already_fresh`` carries the two hashes);
    ``resolve_reason`` is set ONLY on ``resolve_failed``. ``message`` carries
    human-readable detail for the classified-failure paths.
    """

    model_file_id: uuid.UUID
    status: IngestStatus
    stl_hash: str | None = None
    bundle_hash: str | None = None
    job_id: str | None = None
    resolve_reason: ResolveReason | None = None
    message: str | None = None


async def ingest_stl_part(
    model_file: ModelFile,
    *,
    arq_pool: Any,
    stl_cache: StlCache,
    estimate_store: EstimateStore,
    resolve_fn: ResolverFn,
    default_preset: PrintIntentPreset,
    content_dir: Path,
) -> IngestResult:
    """Ingest one catalog STL ``ModelFile``: resolve, pre-check, idempotently enqueue.

    Returns a classified :class:`IngestResult`; NEVER raises for an expected branch
    (missing STL, path escape, resolve failure) — each is caught, classified, and
    logged so the backfill continues to the next part.
    """
    fid = model_file.id

    # (1) STL parts only — image/source/3mf/stl_preview are not inspected.
    if model_file.kind != ModelFileKind.stl:
        _LOG.debug("skip non-stl ModelFile %s (kind=%s)", fid, model_file.kind)
        return IngestResult(model_file_id=fid, status=IngestStatus.skipped_non_stl)

    # (2) resolve the on-disk path UNDER the content root (path-escape guard mirrors
    # enqueue_thumbnail_backfill.py). A malformed/escaping storage_path ⇒ error;
    # a missing/unreadable file ⇒ missing_stl. Both skip the part and continue.
    content_root = Path(content_dir).resolve()
    abs_path = (content_root / model_file.storage_path).resolve()
    try:
        abs_path.relative_to(content_root)
    except ValueError:
        _LOG.warning("path-escape on ModelFile %s (%s) — skipped", fid, model_file.storage_path)
        return IngestResult(
            model_file_id=fid,
            status=IngestStatus.error,
            message=f"storage_path escapes content root: {model_file.storage_path!r}",
        )
    if not abs_path.is_file():
        _LOG.warning("missing STL for ModelFile %s (%s)", fid, model_file.storage_path)
        return IngestResult(
            model_file_id=fid,
            status=IngestStatus.missing_stl,
            message=f"STL not found on disk: {model_file.storage_path!r}",
        )

    # (3) resolve the default preset to a persisted bundle. A classified failure is
    # NOT an exception — surface the reason, no enqueue (no silent wrong default).
    outcome = resolve_fn(default_preset)
    if not isinstance(outcome, ResolveSuccess):
        _LOG.warning(
            "resolve failed for ModelFile %s: %s (%s)", fid, outcome.reason, outcome.message
        )
        return IngestResult(
            model_file_id=fid,
            status=IngestStatus.resolve_failed,
            resolve_reason=outcome.reason,
            message=outcome.message,
        )
    bundle_hash = outcome.bundle.bundle_hash

    # (4) idempotency pre-check. ``ModelFile.sha256`` IS the stl_hash the slicer mints
    # and reads by (proven byte-equal to compute_stl_hash — no migration). A defensive
    # well-formedness guard: a malformed stored hash classifies as error rather than
    # raising deep in a path-build (it cannot happen for a real kind=stl row).
    candidate_stl_hash = model_file.sha256
    if not is_content_hash(candidate_stl_hash):
        _LOG.warning(
            "ModelFile %s carries a non-content-hash sha256 %r — skipped",
            fid,
            candidate_stl_hash,
        )
        return IngestResult(
            model_file_id=fid,
            status=IngestStatus.error,
            bundle_hash=bundle_hash,
            message=f"ModelFile.sha256 is not a well-formed content hash: {candidate_stl_hash!r}",
        )

    existing = estimate_store.read(candidate_stl_hash, bundle_hash)
    if existing is not None and existing.status == EstimateStatus.fresh:
        _LOG.info(
            "already fresh — no enqueue for ModelFile %s (%s, %s)",
            fid,
            candidate_stl_hash,
            bundle_hash,
        )
        return IngestResult(
            model_file_id=fid,
            status=IngestStatus.already_fresh,
            stl_hash=candidate_stl_hash,
            bundle_hash=bundle_hash,
        )

    # (5) enqueue the first slice. enqueue_slice_estimate freshly content-hashes the
    # STL bytes (the canonical, path-safe stl_hash), populates the cache, and enqueues
    # the deterministic deduped job — a re-run while one is queued/running is a no-op.
    enqueued = await enqueue_slice_estimate(
        arq_pool,
        source_stl=abs_path,
        bundle_hash=bundle_hash,
        stl_cache=stl_cache,
    )
    _LOG.info(
        "enqueued slice for ModelFile %s (%s, %s) job_id=%s",
        fid,
        enqueued.stl_hash,
        bundle_hash,
        enqueued.job_id,
    )
    return IngestResult(
        model_file_id=fid,
        status=IngestStatus.enqueued,
        stl_hash=enqueued.stl_hash,
        bundle_hash=bundle_hash,
        job_id=enqueued.job_id,
    )


async def ingest_stl_for_default_matrix(
    model_file: ModelFile,
    *,
    resolved_cells: list[Any],
    arq_pool: Any,
    stl_cache: StlCache,
    estimate_store: EstimateStore,
    content_dir: Path,
) -> list[IngestResult]:
    """Ingest one catalog STL for every resolved default-matrix cell (Story 35.6, AC-7).

    For each ``ResolvedMatrixCell`` with ``bundle_hash is not None``, calls
    :func:`ingest_stl_part` with a synthetic resolver that always returns the
    pre-resolved bundle — so the freshness-check + enqueue path runs without
    re-resolving. Cells with ``bundle_hash=None`` are logged and excluded.
    A classified failure on one cell does NOT stop the others.
    """
    from app.modules.slicer.models import (
        ResolvedTriple,
        ResolveSuccess,
        SlicerProfileBundle,
    )

    results: list[IngestResult] = []
    for rc in resolved_cells:
        if rc.bundle_hash is None:
            _LOG.info(
                "matrix_ingest.skip_unresolved",
                extra={
                    "labels.offer_id": rc.cell.offer_id,
                    "labels.material": rc.cell.material,
                },
            )
            continue

        _bh = rc.bundle_hash

        def _preset_resolver(_intent: PrintIntentPreset, _bundle_hash: str = _bh) -> ResolveSuccess:
            return ResolveSuccess(
                bundle=SlicerProfileBundle(
                    bundle_hash=_bundle_hash,
                    orca_version="",
                    machine={},
                    process={},
                    filament={},
                    source_snapshot_ref=_bundle_hash,
                    created_at="",
                ),
                triple=ResolvedTriple(machine={}, process={}, filament={}),
                from_cache=True,
            )

        result = await ingest_stl_part(
            model_file,
            arq_pool=arq_pool,
            stl_cache=stl_cache,
            estimate_store=estimate_store,
            resolve_fn=_preset_resolver,
            default_preset=PrintIntentPreset(
                name=f"{rc.cell.material} default",
                material_class="PLA",
                quality_tier="standard",
                printer_ref="placeholder",
            ),
            content_dir=content_dir,
        )
        results.append(result)
    return results


async def ingest_model_estimates(
    model_files: Iterable[ModelFile],
    *,
    arq_pool: Any,
    stl_cache: StlCache,
    estimate_store: EstimateStore,
    resolve_fn: ResolverFn,
    default_preset: PrintIntentPreset,
    content_dir: Path,
) -> list[IngestResult]:
    """Ingest every ``kind=stl`` part in ``model_files``; return one result per part.

    Non-STL parts are filtered out (not inspected, not reported) — the caller passes
    a model's files and this walks only the STL parts. Each part is ingested
    independently: a classified failure on one never blocks the next.
    """
    results: list[IngestResult] = []
    for model_file in model_files:
        if model_file.kind != ModelFileKind.stl:
            continue
        results.append(
            await ingest_stl_part(
                model_file,
                arq_pool=arq_pool,
                stl_cache=stl_cache,
                estimate_store=estimate_store,
                resolve_fn=resolve_fn,
                default_preset=default_preset,
                content_dir=content_dir,
            )
        )
    return results
