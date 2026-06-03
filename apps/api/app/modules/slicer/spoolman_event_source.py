"""SPOOL-EVT-1 — live Spoolman-change event source (the poll-diff trigger).

Closes the last deferred half of the Spoolman live-invalidation chain. Story 32.5 shipped
``apply_spoolman_filament_change`` (classify cost-only vs mapped-override + dispatch into the
Story 32.4 engine, given a single filament's old→new state plus a caller-supplied
``affected_keys`` set); SPOOL-PREQ-1 shipped the persisted reverse index +
``lookup_affected_keys`` (``spoolman_filament_ref → AffectedGroup[]``). This module is the
SOURCE that drives them from the Init 19 Spoolman poll: it diffs two successive snapshots by
the churn-stable ``spoolman_filament_ref`` and, for each *changed* ref, looks up the affected
estimate keys and dispatches one ``apply_spoolman_filament_change`` per pinning intent.

Boundaries (unchanged from the deferred note in ``deferred-work.md`` § SPOOL-EVT-1):

- **Pure app-side; NO second Spoolman read.** It consumes the two snapshots the existing
  Init 19 poll already fetched (handed in by ``SpoolsService`` via the
  ``SnapshotChangeHandler`` seam) — it never touches the Spoolman client or cache itself.
- No catalog→``stl_hash`` ingestion (EST-INGEST-1), no ``POST /api/estimates/recompute``
  (EST-RECOMPUTE-1), no UI. It only enumerates already-persisted estimate keys and feeds the
  existing 32.5 dispatch.

The diff is gated by :func:`classify_spoolman_delta` BEFORE the estimate-store scan, so a
no-op / irrelevant change (e.g. a color edit, or a byte-identical snapshot) costs only a dict
comparison — it never reaches ``lookup_affected_keys`` (which is O(all estimates)) and never
dispatches.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import Settings, get_settings
from app.modules.slicer.attribution_store import AttributionStore, lookup_affected_keys
from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.estimate_store import EstimateStore
from app.modules.slicer.overrides import spoolman_filament_ref
from app.modules.slicer.resolver import VendoredProfileSource
from app.modules.slicer.spoolman_invalidation import (
    apply_spoolman_filament_change,
    classify_spoolman_delta,
)
from app.modules.spools.models import SpoolmanFilament, SpoolmanSnapshot

logger = logging.getLogger(__name__)


def _filaments_by_ref(snapshot: SpoolmanSnapshot) -> dict[str, SpoolmanFilament]:
    # Keyed by the churn-stable vendor∥material∥name ref (the SAME key SPOOL-PREQ-1 indexes
    # by, so the diff key and the lookup key cannot diverge). A name/vendor/material edit
    # re-keys the ref → it surfaces as a removed ref + an added ref (no correlatable old→new
    # state) and is intentionally NOT dispatched; price / weight / filament.extra edits keep
    # the ref stable and are exactly what the diff catches.
    return {spoolman_filament_ref(f): f for f in snapshot.filaments}


class SpoolmanInvalidationHandler:
    """Diff two Spoolman snapshots and dispatch estimate invalidations (the event source).

    Implements the spools-side ``SnapshotChangeHandler`` protocol
    (``async handle(previous, current)``) so the Init 19 poll can invoke it WITHOUT importing
    the slicer module — keeping the spools→slicer dependency one-directional (the cron is the
    composition root that wires the two together).
    """

    def __init__(
        self,
        *,
        estimate_store: EstimateStore,
        attribution_store: AttributionStore,
        bundle_store: BundleStore,
        source: VendoredProfileSource,
        arq_pool: Any,
        orca_version: str,
    ) -> None:
        self._estimate_store = estimate_store
        self._attribution_store = attribution_store
        self._bundle_store = bundle_store
        self._source = source
        self._arq_pool = arq_pool
        self._orca_version = orca_version

    async def handle(self, previous: SpoolmanSnapshot, current: SpoolmanSnapshot) -> None:
        """Diff ``previous`` → ``current`` filaments by ref and dispatch per affected group."""
        old_by_ref = _filaments_by_ref(previous)
        new_by_ref = _filaments_by_ref(current)

        changed_refs = 0
        dispatched_groups = 0
        for ref, new_f in new_by_ref.items():
            old_f = old_by_ref.get(ref)
            if old_f is None:
                # Newly added filament ref — no prior resolve/estimate to invalidate.
                continue
            if classify_spoolman_delta(old_f, new_f) is None:
                # No-op or irrelevant change (color, no change at all) — never dispatch, and
                # never pay the O(all-estimates) lookup scan for an unchanged filament.
                continue
            changed_refs += 1
            groups = lookup_affected_keys(
                ref,
                attribution_store=self._attribution_store,
                estimate_store=self._estimate_store,
            )
            for group in groups:
                if not group.affected_keys:
                    # The pin is known but no estimate has been computed against this bundle
                    # yet — nothing to invalidate. Skip rather than dispatch an empty key set
                    # (which on the mapped path would waste a re-resolve for zero writes).
                    continue
                await apply_spoolman_filament_change(
                    self._estimate_store,
                    self._arq_pool,
                    intent=group.intent,
                    old=old_f,
                    new=new_f,
                    source=self._source,
                    bundle_store=self._bundle_store,
                    orca_version=self._orca_version,
                    affected_keys=group.affected_keys,
                )
                dispatched_groups += 1

        # One structured summary line per diff (the per-classification lines come from the
        # 32.5 dispatch). Carries only counts — NEVER any Spoolman field values (AC-8 parity).
        logger.info(
            "slicer.spoolman_poll_diff",
            extra={
                "event.action": "slicer.spoolman_poll_diff",
                "labels.external_service": "spoolman",
                "labels.changed_ref_count": changed_refs,
                "labels.dispatched_group_count": dispatched_groups,
            },
        )


def build_spoolman_invalidation_handler(
    arq_pool: Any, *, settings: Settings | None = None
) -> SpoolmanInvalidationHandler:
    """Construct the handler from settings (the cron composition root).

    Mirrors the slicer worker's settings-wiring (``worker.py:startup``): the estimate/bundle
    stores + vendored-profile source come from the same content-root settings, and the
    attribution store shares the bundle-store root (SPOOL-PREQ-1 owns its ``attribution/``
    subtree there). ``arq_pool`` is the live arq pool the cron enqueues re-slices on (the
    mapped-override path targets the dedicated slicer queue via the 32.4 engine).
    """
    settings = settings or get_settings()
    return SpoolmanInvalidationHandler(
        estimate_store=EstimateStore(settings.slicer_estimate_store_dir),
        attribution_store=AttributionStore(settings.slicer_bundle_store_dir),
        bundle_store=BundleStore(settings.slicer_bundle_store_dir),
        source=VendoredProfileSource(settings.slicer_vendored_profiles_dir),
        arq_pool=arq_pool,
        orca_version=settings.orca_version,
    )
