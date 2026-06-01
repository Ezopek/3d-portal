"""API-side idempotent slice enqueue (Story 32.2, AC-2/AC-4, Decision AI).

The enqueue helper runs on the API side: it computes/ensures the STL content hash,
populates the content-hash cache from the ``.190``-mirrored catalog STL copy (OD-8),
and enqueues the idempotent ``(stl_hash, bundle_hash)`` 2-tuple onto the dedicated
slicer queue with a deterministic ``_job_id`` so a duplicate enqueue while one is
queued/running is a de-dup no-op (arq drops the duplicate job_id).

No profile JSON, STL bytes, or file paths travel in the payload (AC-2) — the content
hash is the only STL reference that crosses the queue.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.modules.slicer.stl_cache import StlCache, validate_content_hash
from app.modules.slicer.worker import SLICER_QUEUE_NAME
from app.modules.slicer.worker_job import SLICE_JOB_NAME


def slice_job_id(stl_hash: str, bundle_hash: str) -> str:
    """Deterministic dedupe key — because "idempotent dedupe on the complete
    ``(stl_hash, bundle_hash)`` reproducibility key — Decision AI § Concurrency;
    identical work must never double-run (NFR20-RESOURCE-1)" (AC-10).
    """
    return f"slice:{stl_hash}:{bundle_hash}"


@dataclass(frozen=True)
class EnqueueResult:
    """What the enqueue helper returns to the caller."""

    stl_hash: str
    bundle_hash: str
    job_id: str
    job: Any


async def enqueue_slice_estimate(
    arq_pool: Any,
    *,
    source_stl: Path,
    bundle_hash: str,
    stl_cache: StlCache,
) -> EnqueueResult:
    """Populate the STL cache from the mirrored catalog copy + enqueue the deduped job.

    ``source_stl`` is the ``.190``-mirrored catalog STL (the portal-content copy at
    ``models/{model_id}/files/{file_uuid}.stl``) — NEVER an external/source host
    (OD-8). The worker reads only the cache; the only reference enqueued is the hash.
    """
    # stl_hash is freshly computed (always well-formed); bundle_hash is caller-supplied
    # (the Story 32.1 resolve result), so validate it here BEFORE it is woven into the
    # _job_id and the cache/store path lookups the worker will run (review fix #2).
    validate_content_hash(bundle_hash)
    stl_hash = stl_cache.populate_from_source(source_stl)
    job_id = slice_job_id(stl_hash, bundle_hash)
    job = await arq_pool.enqueue_job(
        SLICE_JOB_NAME,
        stl_hash,
        bundle_hash,
        _job_id=job_id,
        _queue_name=SLICER_QUEUE_NAME,
    )
    return EnqueueResult(stl_hash=stl_hash, bundle_hash=bundle_hash, job_id=job_id, job=job)
