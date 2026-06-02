"""Estimate invalidation / recompute engine (Story 32.4, Decision AJ second half).

This is a thin orchestration layer over the Story 32.3 ``EstimateStore`` + the Story 32.2
enqueue — it introduces NO new persistence mechanism (the append-only file store is reused;
transitions are atomic rewrites of existing records) and NO HTTP surface (zero routes; the
estimate read/recompute-trigger API is Story 32.6 / a future ops surface).

It realizes two things from the exhaustive Decision AJ **recompute-trigger table**:

1. **The cost-only-arithmetic rule (OD-7, the load-bearing efficiency decision).** A Spoolman
   cost-only price tick recomputes ``filament_cost = filament_g x price_per_gram`` *in place*,
   with NO arq enqueue and NO Orca subprocess, in well under a second. Re-slicing for a price
   change wastes minutes of CPU — the Pre-Mortem flagged "re-slicing on every Spoolman price
   tick" as the top self-inflicted-DoS risk (R1). The ``invalidate`` dispatch is the single
   chokepoint that guarantees a ``spoolman_cost_only`` trigger can NEVER reach the enqueue path.

2. **Hash-driven invalidation (the stale + idempotent re-slice path).** A bundle re-tune / Orca
   upgrade / Spoolman mapped-override changes ``bundle_hash``, so the superseded estimate is
   marked ``stale`` (kept SERVABLE with its last-known numbers — R9: never served as ``fresh``,
   never hidden), an idempotent re-slice is enqueued onto the Story 32.2 ``arq:slicer`` queue
   (riding the ``_job_id`` dedupe so a duplicate trigger while one recompute is in flight is a
   no-op), and the record is marked ``queued``.

**Story 32.5 coordination boundary (AC-7) — engine here, event-wiring there.** This module
takes ``price_per_gram`` and the old/new ``bundle_hash`` pair as CALLER-supplied inputs. It does
NOT read Spoolman, does NOT compute ``price_per_gram = filament.price / filament.weight``, does
NOT resolve a ``spool.price`` override, does NOT map ``filament.extra`` onto the filament JSON,
and does NOT compute ``spoolman_overrides_ref`` / the new ``bundle_hash``. The old→new bundle
mapping is computed by Story 32.1 resolve / Story 32.5 Spoolman linkage and is PASSED IN: for a
bundle-changing trigger the caller passes the OLD key (marked stale) plus the NEW re-slice-target
hash, so :func:`invalidate` never has to guess which hash is which. The dispatch functions are
the seam Story 32.5 (and a future ops trigger) call; this module proves them correct under unit
tests with injected fakes. Input contract for the cost path: *grams x (currency per gram) =
currency*; the caller owns currency/units.

[Source: architecture.md § Decision AJ — recompute-trigger table + cost-only-arithmetic rule]
"""

from __future__ import annotations

import logging
import math
from collections.abc import Iterable
from enum import StrEnum
from typing import Any

import sentry_sdk
from opentelemetry import trace

from app.modules.slicer.enqueue import EnqueueResult, slice_job_id
from app.modules.slicer.estimate_store import EstimateStore
from app.modules.slicer.models import EstimateRecord
from app.modules.slicer.stl_cache import validate_content_hash
from app.modules.slicer.worker import SLICER_QUEUE_NAME
from app.modules.slicer.worker_job import SLICE_JOB_NAME

logger = logging.getLogger(__name__)
_tracer = trace.get_tracer(__name__)


class RecomputeTrigger(StrEnum):
    """The exhaustive Decision AJ recompute-trigger kinds (AC-5).

    Every architecture recompute-trigger-table row maps to exactly one value, so the table
    cannot grow a silent gap (the R9 "cache key incomplete → stale served as fresh" guard).
    Each value names the table row it implements:

    - ``stl_content_change`` — ``stl_hash`` changes ⇒ new key ⇒ new estimate; old key orphaned
      (GC later, AC-9). No in-place transition here.
    - ``bundle_retune`` — new ``SlicerProfileBundle`` ⇒ new ``bundle_hash``; old estimate
      ``stale``, requeued against the new bundle.
    - ``orca_upgrade`` — ``orca_version`` ∈ ``bundle_hash`` ⇒ hash changes; all estimates
      effectively stale (bulk recompute via the AC-6 primitives).
    - ``spoolman_mapped_override`` — a mapped field (volumetric speed / temp / density) folded
      into ``bundle_hash`` via ``spoolman_overrides_ref`` changes ⇒ dependent estimates stale.
    - ``spoolman_cost_only`` — ``spool.price`` changes, density unchanged ⇒ OD-7 cheap
      arithmetic recompute WITHOUT re-slicing.
    """

    stl_content_change = "stl_content_change"
    bundle_retune = "bundle_retune"
    orca_upgrade = "orca_upgrade"
    spoolman_mapped_override = "spoolman_mapped_override"
    spoolman_cost_only = "spoolman_cost_only"


#: The slice-affecting triggers — anything that changes the slicer OUTPUT routes to the
#: stale + idempotent re-slice path (distinct from the OD-7 cost-only arithmetic path).
_RESLICE_TRIGGERS = frozenset(
    {
        RecomputeTrigger.bundle_retune,
        RecomputeTrigger.orca_upgrade,
        RecomputeTrigger.spoolman_mapped_override,
    }
)


def _guard_price_per_gram(price_per_gram: float | None) -> None:
    """Reject a ``None``/``nan``/``inf``/negative price BEFORE any write (the data-integrity
    contract): a bad caller input must raise ``ValueError``, NEVER silently write ``cost = 0``,
    ``nan``, or a negative cost. The Story 32.3 ``_reject_non_finite`` field-validator is the
    defense-in-depth backstop at the model edge.
    """
    if price_per_gram is None:
        raise ValueError("price_per_gram is required and must be a finite, non-negative number")
    if not math.isfinite(price_per_gram):
        raise ValueError(f"price_per_gram must be finite (never nan/inf), got {price_per_gram!r}")
    if price_per_gram < 0:
        raise ValueError(f"price_per_gram must be non-negative, got {price_per_gram!r}")


def recompute_cost_only(
    store: EstimateStore,
    stl_hash: str,
    bundle_hash: str,
    *,
    price_per_gram: float,
) -> EstimateRecord | None:
    """Recompute ``filament_cost`` arithmetically, in place, with NO re-slice (OD-7, AC-3).

    ``cost = filament_g x price_per_gram`` — because **"OD-7 / Decision AJ cost-only-arithmetic
    rule — cost is derived post-slice arithmetic (mass x price/gram), never a slice input; the
    formula IS the contract, and re-slicing for a price change is the R1 self-DoS this rule
    forbids"**. The function touches ONLY the ``EstimateStore`` (one read + one atomic write):
    NO arq job is enqueued, NO slicer worker is invoked, NO Orca subprocess is spawned (there is
    no ``arq_pool`` parameter — the enqueue surface is structurally absent).

    A servable record (``fresh``/``stale``/``queued`` — anything carrying ``filament_g``) has
    its cost updated and ``computed_at`` re-stamped; ``status`` and every slice-derived numeric
    are unchanged (a cost change does NOT invalidate the slice output). A ``failed`` record or
    one whose ``filament_g`` is ``None`` ⇒ ``None`` (never fabricate a cost onto a failure); a
    miss ⇒ ``None``. A non-finite/negative ``price_per_gram`` raises ``ValueError``.
    """
    _guard_price_per_gram(price_per_gram)
    record = store.read(stl_hash, bundle_hash)
    if record is None or record.filament_g is None:
        return None
    with _tracer.start_as_current_span("slicer.recompute") as span:
        span.set_attribute("slicer.stl_hash", stl_hash)
        span.set_attribute("slicer.bundle_hash", bundle_hash)
        span.set_attribute("slicer.trigger", RecomputeTrigger.spoolman_cost_only.value)
        updated = store.update_cost(stl_hash, bundle_hash, price_per_gram=price_per_gram)
        if updated is None:
            return None
        span.set_attribute("slicer.estimate_status", updated.status.value)
        _emit_recompute(
            updated,
            trigger=RecomputeTrigger.spoolman_cost_only,
            recompute_path="arithmetic",
        )
    return updated


async def enqueue_recompute(
    arq_pool: Any,
    *,
    stl_hash: str,
    bundle_hash: str,
) -> EnqueueResult:
    """Enqueue an idempotent re-slice for an ALREADY-cached ``(stl_hash, bundle_hash)`` (AC-4).

    Rides the Story 32.2 ``_job_id = slice_job_id(stl_hash, bundle_hash)`` (= ``"slice:<stl>:
    <bundle>"``) so a duplicate recompute trigger while one is queued/running is an arq de-dup
    no-op (NFR20-RESOURCE-1 / Decision AI § Concurrency). Reuses ``slice_job_id`` /
    ``SLICE_JOB_NAME`` / ``SLICER_QUEUE_NAME`` verbatim — the job-id shape and the queue name
    are NOT re-derived.

    Unlike the Story 32.2 ``enqueue_slice_estimate`` (which takes a ``source_stl: Path`` and
    calls ``stl_cache.populate_from_source`` because it is the *first* enqueue), a recompute is
    by definition a re-run for a key whose STL is already content-addressed in the cache (a
    bundle re-tune / Orca upgrade / mapped-override does NOT change ``stl_hash``), so this
    enqueues **by hash directly** — no ``source_stl``, no ``stl_cache``, no re-population. If
    the STL is somehow absent from the cache the worker classifies a typed ``missing_stl``
    ``SliceOutcome`` (Story 32.2) — a typed failure, never a silent zero. The enqueue does NOT
    write the estimate record — the worker's ``slice_estimate`` persist (Story 32.3) owns the
    fresh terminus of the ``stale → queued → fresh`` lifecycle.
    """
    # Both hashes are caller-supplied (a recompute target); validate BEFORE either is woven
    # into the _job_id / queue payload so a malformed/traversal-shaped hash never reaches the
    # queue (the Story 32.2 enqueue review-fix #2 discipline).
    validate_content_hash(stl_hash)
    validate_content_hash(bundle_hash)
    job_id = slice_job_id(stl_hash, bundle_hash)
    job = await arq_pool.enqueue_job(
        SLICE_JOB_NAME,
        stl_hash,
        bundle_hash,
        _job_id=job_id,
        _queue_name=SLICER_QUEUE_NAME,
    )
    return EnqueueResult(stl_hash=stl_hash, bundle_hash=bundle_hash, job_id=job_id, job=job)


async def invalidate(
    store: EstimateStore,
    arq_pool: Any,
    *,
    trigger: RecomputeTrigger,
    stl_hash: str,
    bundle_hash: str,
    new_bundle_hash: str | None = None,
    price_per_gram: float | None = None,
) -> EstimateRecord | None:
    """The Decision AJ recompute-trigger dispatch — the single cheap-vs-expensive chokepoint.

    Every trigger routes to exactly one of the two recompute paths, so the table cannot grow a
    silent gap (R9). The R1 self-DoS guard lives here: a ``spoolman_cost_only`` trigger can
    NEVER reach the enqueue path.

    **The old-key vs new-key contract (AC-5).** ``bundle_hash`` is always the OLD/current key —
    the record being invalidated (marked stale) or, for the cost path, recomputed in place.
    ``new_bundle_hash`` is the NEW re-slice target for the *bundle-CHANGING* triggers:

    - ``bundle_retune`` / ``spoolman_mapped_override`` change the ``bundle_hash`` (a re-tuned
      ``SlicerProfileBundle`` / a mapped Spoolman override folded into ``spoolman_overrides_ref``
      ⇒ a NEW hash, resolved by Story 32.1 resolve / Story 32.5 linkage and **passed in** — this
      engine does not derive the old→new mapping, AC-7). The caller passes the changed hash as
      ``new_bundle_hash`` so the OLD record is marked stale while the re-slice is enqueued for the
      NEW key. (Omitting ``new_bundle_hash`` for these is only correct in the degenerate case
      where the hash genuinely did not change.)
    - ``orca_upgrade`` MAY leave the ``bundle_hash`` unchanged; ``new_bundle_hash=None`` is the
      explicit "same key" contract (in-place ``stale → queued`` on the one key).

    Paths:

    - ``spoolman_cost_only`` → the cheap arithmetic path (:func:`recompute_cost_only`); NO
      ``mark_stale``, NO enqueue. ``price_per_gram`` is REQUIRED (a missing one is a
      ``ValueError``, not a silent skip). A cost change is in-place arithmetic and can NEVER
      change the key — a distinct ``new_bundle_hash`` is a contract breach (``ValueError``).
    - ``bundle_retune`` / ``orca_upgrade`` / ``spoolman_mapped_override`` → the stale + idempotent
      re-slice path: ``mark_stale(old)`` → :func:`enqueue_recompute`\\ ``(new)`` →
      ``mark_queued(new)``. The OLD record stays SERVABLE as ``stale`` (never served as fresh —
      R9); the NEW key is the re-slice target (a brand-new bundle is a natural miss the worker
      fills ``fresh``; a previously-sliced bundle is marked ``queued``, recompute in flight). The
      worker's ``slice_estimate`` persist is the ``fresh`` terminus. Returns the recompute
      target's resulting record (``queued`` if it already had a servable estimate, else ``None``
      for a brand-new-key miss — the old stale record is read back by key, not returned here).
    - ``stl_content_change`` → no in-place transition: a new ``stl_hash`` is a new key ⇒ a
      natural cache miss ⇒ a normal first enqueue via the Story 32.2 ``enqueue_slice_estimate``;
      the old key is orphaned for a future GC (orphan GC is out of scope, AC-9). Returns ``None``.
    """
    if trigger == RecomputeTrigger.spoolman_cost_only:
        if new_bundle_hash is not None and new_bundle_hash != bundle_hash:
            raise ValueError(
                "spoolman_cost_only is in-place arithmetic (OD-7) — it must not change the "
                "bundle hash; pass bundle_hash only, never a distinct new_bundle_hash"
            )
        if price_per_gram is None:
            raise ValueError("spoolman_cost_only requires price_per_gram (no silent skip)")
        return recompute_cost_only(store, stl_hash, bundle_hash, price_per_gram=price_per_gram)

    if trigger in _RESLICE_TRIGGERS:
        # bundle_hash = the OLD/superseded key; target = the NEW re-slice key. They DIFFER for a
        # bundle_retune / spoolman_mapped_override (the caller passes the changed new_bundle_hash);
        # they coincide for an orca_upgrade whose hash is unchanged (new_bundle_hash omitted).
        target_bundle_hash = bundle_hash if new_bundle_hash is None else new_bundle_hash
        # Old record superseded → stale (kept servable, never served as fresh — R9). When old ==
        # new this is the start of the in-place stale → queued lifecycle.
        store.mark_stale(stl_hash, bundle_hash)
        # Re-slice the NEW key (not the old one — that was the review-critical bug). A brand-new
        # bundle is a natural miss the worker fills fresh; the by-hash enqueue rides the 32.2
        # _job_id dedupe.
        await enqueue_recompute(arq_pool, stl_hash=stl_hash, bundle_hash=target_bundle_hash)
        # Mark the RECOMPUTE TARGET queued (recompute in flight). A brand-new key is a miss ⇒
        # None (no fabricated record); a previously-sliced bundle (or the old==new in-place case)
        # transitions to queued while still serving its last numbers.
        queued = store.mark_queued(stl_hash, target_bundle_hash)
        _emit_invalidate(
            stl_hash,
            old_bundle_hash=bundle_hash,
            new_bundle_hash=target_bundle_hash,
            trigger=trigger,
            record=queued,
        )
        return queued

    if trigger == RecomputeTrigger.stl_content_change:
        # New key, new estimate — handled by content-addressing (the 32.2 first enqueue);
        # no in-place transition, no enqueue, old key orphaned for a future GC (AC-9).
        return None

    raise ValueError(f"unhandled recompute trigger: {trigger!r}")  # pragma: no cover


def recompute_cost_only_bulk(
    store: EstimateStore,
    keys: Iterable[tuple[str, str]],
    *,
    price_per_gram: float,
) -> list[EstimateRecord | None]:
    """Apply :func:`recompute_cost_only` over a caller-supplied key set (AC-6, bulk arithmetic).

    The *which-keys* decision is the caller's (Story 32.5 maps a Spoolman filament → the affected
    bundles); this supplies the iteration mechanism + the per-key correctness, NOT the event
    source. No enqueue on any key (it is the cheap arithmetic path). Emits the COUNT touched so a
    bulk recompute is observable and never silently truncated (NFR20-OBS-1).
    """
    results = [
        recompute_cost_only(store, stl_hash, bundle_hash, price_per_gram=price_per_gram)
        for stl_hash, bundle_hash in keys
    ]
    _emit_bulk(count=len(results), recompute_path="arithmetic")
    return results


async def invalidate_bulk(
    store: EstimateStore,
    arq_pool: Any,
    *,
    trigger: RecomputeTrigger,
    keys: Iterable[tuple[str, ...]],
    price_per_gram: float | None = None,
) -> list[EstimateRecord | None]:
    """Run :func:`invalidate` over a caller-supplied key set (AC-6 — Orca-upgrade / re-tune).

    Per-key dedupe still holds (each key's enqueue rides its own ``_job_id``). The caller owns
    the key set (an Orca-upgrade ops trigger supplies "all" via
    :meth:`EstimateStore.iter_all_estimates`; a bundle re-tune supplies the sibling set via
    :meth:`EstimateStore.iter_stl_estimates`). Emits the COUNT touched (NFR20-OBS-1 — never
    silently truncated).

    Each key is either a 2-tuple ``(stl_hash, bundle_hash)`` — the in-place / unchanged-hash case
    (the old key is also the re-slice target) — or a 3-tuple ``(stl_hash, old_bundle_hash,
    new_bundle_hash)`` for a bundle-CHANGING trigger, so the old record is marked stale while the
    recompute is enqueued for the corresponding new key (the per-record old→new contract of
    :func:`invalidate`, applied across the set).
    """
    results: list[EstimateRecord | None] = []
    for key in keys:
        if len(key) == 3:
            stl_hash, bundle_hash, new_bundle_hash = key
        else:
            stl_hash, bundle_hash = key
            new_bundle_hash = None
        results.append(
            await invalidate(
                store,
                arq_pool,
                trigger=trigger,
                stl_hash=stl_hash,
                bundle_hash=bundle_hash,
                new_bundle_hash=new_bundle_hash,
                price_per_gram=price_per_gram,
            )
        )
    _emit_bulk(count=len(results), trigger=trigger)
    return results


# --- Observability (NFR20-OBS-1, AC-8) ----------------------------------------
#
# One structured line per transition / recompute, carrying the hashes + trigger + resulting
# estimate_status. The cost-only path additionally tags the arithmetic path so a dashboard can
# confirm cost ticks never hit the slicer queue (the R1 guard is observable). NO g-code (there
# is none in the cost-only path) and NO full EstimateRecord dump — only hashes/status/trigger/
# count cross into logs. Mirrors the Story 32.3 _emit_estimate_persist shape.


def _emit_recompute(
    record: EstimateRecord,
    *,
    trigger: RecomputeTrigger,
    recompute_path: str,
) -> None:
    logger.info(
        "slicer.recompute complete",
        extra={
            "labels.stl_hash": record.stl_hash,
            "labels.bundle_hash": record.bundle_hash,
            "labels.trigger": trigger.value,
            "labels.estimate_status": record.status.value,
            "labels.recompute_path": recompute_path,
        },
    )


def _emit_invalidate(
    stl_hash: str,
    *,
    old_bundle_hash: str,
    new_bundle_hash: str,
    trigger: RecomputeTrigger,
    record: EstimateRecord | None,
) -> None:
    # Carry BOTH hashes so a dashboard can see the old (now-stale) key and the new re-slice
    # target distinctly — never served as fresh, the recompute targets the new key (R9 / AC-5).
    extra: dict[str, Any] = {
        "labels.stl_hash": stl_hash,
        "labels.old_bundle_hash": old_bundle_hash,
        "labels.new_bundle_hash": new_bundle_hash,
        "labels.trigger": trigger.value,
        "labels.recompute_path": "reslice",
    }
    if record is not None:
        extra["labels.estimate_status"] = record.status.value
    logger.info("slicer.invalidate complete", extra=extra)
    sentry_sdk.add_breadcrumb(
        category="slicer",
        level="info",
        message="estimate invalidated (re-slice enqueued)",
        data={
            "stl_hash": stl_hash,
            "old_bundle_hash": old_bundle_hash,
            "new_bundle_hash": new_bundle_hash,
            "trigger": trigger.value,
        },
    )


def _emit_bulk(
    *,
    count: int,
    trigger: RecomputeTrigger | None = None,
    recompute_path: str | None = None,
) -> None:
    extra: dict[str, Any] = {"labels.count": count}
    if trigger is not None:
        extra["labels.trigger"] = trigger.value
    if recompute_path is not None:
        extra["labels.recompute_path"] = recompute_path
    logger.info("slicer.recompute bulk", extra=extra)
