"""Bounded default-matrix enumeration + resolution helpers (Story 35.6).

This module implements the default-matrix backfill pipeline:

1. :func:`enumerate_matrix_cells` — pure function; builds the cross-product of
   published offers x enabled material_defaults (G-BACKFILL-OPT-IN: filament_overrides
   are NEVER enumerated here; they are opt-in only via ``--include-overrides`` flag).
2. :func:`resolve_matrix_cells` — resolves each cell to a bundle_hash via
   ``resolve_chain``; a failure classifies as ``resolve_failed`` and is logged.
3. :func:`load_active_matrix` — convenience wrapper that lists all offers, loads the
   policy, enumerates, and resolves in one call.
4. :func:`enqueue_matrix_for_all_stls` — shared helper used by both the script and the
   event-driven hooks: walks all catalog ``kind=stl`` ModelFile rows, applies freshness
   pre-checks, and idempotently enqueues ``(stl_hash, bundle_hash)`` pairs.

FR23-BACKFILL-1 / NFR23-QUEUE-BOUND-1.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.modules.slicer.profile_offer import chain_of, list_offers, read_offer
from app.modules.slicer.profile_policy import (
    EstimateProfileSource,
    ProfilePolicy,
    ProfilePolicyStore,
    ProfileSelection,
)
from app.modules.slicer.profile_publish import PUBLISH_STATE_PUBLISHED, publish_state_of
from app.modules.slicer.resolver import VendoredProfileSource, resolve_chain

_LOG = logging.getLogger("app.modules.slicer.matrix_backfill")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MatrixCell:
    """One (offer, material) pair from the default matrix.

    Never contains filament_overrides entries — those are opt-in only (G-BACKFILL-OPT-IN).
    """

    offer_id: str
    offer_label: str
    material: str  # normalized (uppercase from policy key)
    orca_profile_ref: str  # from policy.material_defaults[material].orca_filament_profile_ref


@dataclass(frozen=True)
class ResolvedMatrixCell:
    """Result of resolving one :class:`MatrixCell` to a concrete bundle."""

    cell: MatrixCell
    bundle_hash: str | None
    profile_selection: ProfileSelection | None
    resolve_failed: bool = False


# ---------------------------------------------------------------------------
# Pure enumeration (AC-2, AC-3 — no I/O)
# ---------------------------------------------------------------------------


def enumerate_matrix_cells(
    offers: list[dict],
    policy: ProfilePolicy,
    *,
    material_filter: str | None = None,
) -> list[MatrixCell]:
    """Return one :class:`MatrixCell` per (published offer, enabled material_default) pair.

    Pure function — no I/O.  Filament overrides are deliberately excluded
    (G-BACKFILL-OPT-IN: only the operator-supervised script with ``--include-overrides``
    touches those).

    When ``material_filter`` is provided (Story 35.6 fix), only that material key
    is enumerated (used by the material-default hook to prevent queue explosions).
    """
    cells: list[MatrixCell] = []
    for sidecar in offers:
        if publish_state_of(sidecar).publish_state != PUBLISH_STATE_PUBLISHED:
            continue
        offer_id = sidecar.get("offer_id", "")
        offer_label = sidecar.get("label", offer_id)
        compatible = set(sidecar.get("compatible_material_categories") or [])

        # filter to the requested material only, or all enabled ones
        target_keys = (
            [material_filter] if material_filter else list(policy.material_defaults.keys())
        )

        for material_key in target_keys:
            if not material_key:
                continue
            default = policy.material_defaults.get(material_key)
            if not default or not default.enabled:
                continue
            if material_key not in compatible:
                continue
            cells.append(
                MatrixCell(
                    offer_id=offer_id,
                    offer_label=offer_label,
                    material=material_key,
                    orca_profile_ref=default.orca_filament_profile_ref,
                )
            )
    return cells


def enumerate_offer_cells(
    offers: list[dict], *, visible_only: bool, offer_id: str | None = None
) -> list[ResolvedMatrixCell]:
    """Return one resolved backfill cell per eligible published offer.

    This is the offer-SoT counterpart to :func:`enumerate_matrix_cells`: it is pure, performs
    no policy/material-default reads, and never resolves profile chains. The bundle hash is the
    already-published ``published_bundle_hash`` stored on the offer sidecar.
    """
    cells: list[ResolvedMatrixCell] = []
    for sidecar in offers:
        current_offer_id = sidecar.get("offer_id", "")
        if offer_id is not None and current_offer_id != offer_id:
            continue
        publish_state = publish_state_of(sidecar)
        bundle_hash = publish_state.published_bundle_hash
        if publish_state.publish_state != PUBLISH_STATE_PUBLISHED:
            continue
        if not bundle_hash:
            continue
        if sidecar.get("validation_state") == "invalid":
            continue
        if visible_only and sidecar.get("visibility") != "visible":
            continue
        cells.append(
            ResolvedMatrixCell(
                cell=MatrixCell(
                    offer_id=current_offer_id,
                    offer_label=sidecar.get("label", current_offer_id),
                    material="",
                    orca_profile_ref="",
                ),
                bundle_hash=bundle_hash,
                profile_selection=None,
                resolve_failed=False,
            )
        )
    return cells


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def resolve_matrix_cells(
    cells: list[MatrixCell],
    *,
    source: VendoredProfileSource,
    store: Any,
    orca_version: str,
    validator: Any,
    offers_map: dict[str, dict] | None = None,
    _resolve_chain_fn: Callable[..., Any] = resolve_chain,
    _read_offer_fn: Callable[[Any, str], dict | None] = read_offer,
) -> list[ResolvedMatrixCell]:
    """Resolve each :class:`MatrixCell` to a bundle_hash via ``resolve_chain``.

    A classified failure on one cell does NOT stop the others.  Failures are
    logged at WARNING level with structured keys (AC-14).

    ``offers_map`` (Story 35.6 fix) allows reusing pre-loaded sidecars to avoid
    redundant reads.

    ``_resolve_chain_fn`` and ``_read_offer_fn`` are seams for testing.
    """
    from app.modules.slicer.models import ResolveSuccess

    results: list[ResolvedMatrixCell] = []
    for cell in cells:
        sidecar = (
            offers_map.get(cell.offer_id)
            if offers_map is not None
            else _read_offer_fn(source.root, cell.offer_id)
        )
        if sidecar is None:
            _LOG.warning(
                "slicer.matrix_backfill.resolve_failed",
                extra={
                    "labels.offer_id": cell.offer_id,
                    "labels.material": cell.material,
                    "labels.reason": "offer_not_found",
                },
            )
            results.append(
                ResolvedMatrixCell(
                    cell=cell, bundle_hash=None, profile_selection=None, resolve_failed=True
                )
            )
            continue

        chain = chain_of(sidecar)
        profile_selection = ProfileSelection(
            source=EstimateProfileSource.default_material_profile,
            orca_filament_profile_ref=cell.orca_profile_ref,
            selected_material=cell.material,
        )

        outcome = _resolve_chain_fn(
            chain,
            source=source,
            store=store,
            orca_version=orca_version,
            validator=validator,
            material_class=cell.material,
            profile_selection=profile_selection,
        )

        if isinstance(outcome, ResolveSuccess):
            results.append(
                ResolvedMatrixCell(
                    cell=cell,
                    bundle_hash=outcome.bundle.bundle_hash,
                    profile_selection=profile_selection,
                    resolve_failed=False,
                )
            )
        else:
            _LOG.warning(
                "slicer.matrix_backfill.resolve_failed",
                extra={
                    "labels.offer_id": cell.offer_id,
                    "labels.material": cell.material,
                    "labels.reason": outcome.reason.value,
                },
            )
            results.append(
                ResolvedMatrixCell(
                    cell=cell,
                    bundle_hash=None,
                    profile_selection=None,
                    resolve_failed=True,
                )
            )
    return results


# ---------------------------------------------------------------------------
# Convenience loader
# ---------------------------------------------------------------------------


def load_active_matrix(
    root: Path,
    policy_store: ProfilePolicyStore,
    source: VendoredProfileSource,
    store: Any,
    orca_version: str,
    validator: Any,
) -> list[ResolvedMatrixCell]:
    """Load all offers, enumerate, and resolve; return all cells (including failures).

    Callers (hooks, script) can filter on ``resolve_failed`` to count/log failures.
    """
    offers = list_offers(root)
    offers_map = {s.get("offer_id", ""): s for s in offers if s.get("offer_id")}
    policy = policy_store.load()
    cells = enumerate_matrix_cells(offers, policy)
    return resolve_matrix_cells(
        cells,
        source=source,
        store=store,
        orca_version=orca_version,
        validator=validator,
        offers_map=offers_map,
    )


# ---------------------------------------------------------------------------
# Shared enqueue helper (used by script and event-driven hooks)
# ---------------------------------------------------------------------------


async def enqueue_matrix_for_all_stls(
    resolved_cells: list[ResolvedMatrixCell],
    *,
    arq_pool: Any,
    stl_cache: Any,
    estimate_store: Any,
    content_dir: Path,
    db_session: Any,
) -> dict[str, int]:
    """Walk all catalog ``kind=stl`` ModelFile rows and enqueue fresh-check + enqueue.

    Returns summary counters: ``enqueued``, ``already_fresh``, ``missing_stl``, ``errors``.
    Used by both the backfill script and the event-driven hooks.
    """
    from sqlmodel import select

    from app.core.db.models import ModelFile, ModelFileKind
    from app.modules.slicer.enqueue import enqueue_slice_estimate
    from app.modules.slicer.models import EstimateStatus
    from app.modules.slicer.stl_cache import is_content_hash

    counters: dict[str, int] = {
        "enqueued": 0,
        "already_fresh": 0,
        "missing_stl": 0,
        "errors": 0,
    }

    active_cells = [rc for rc in resolved_cells if rc.bundle_hash is not None]
    if not active_cells:
        return counters

    rows = db_session.exec(select(ModelFile).where(ModelFile.kind == ModelFileKind.stl)).all()
    content_root = Path(content_dir).resolve()

    for row in rows:
        abs_path = (content_root / row.storage_path).resolve()
        try:
            abs_path.relative_to(content_root)
        except ValueError:
            counters["errors"] += 1
            continue
        if not abs_path.is_file():
            counters["missing_stl"] += len(active_cells)
            continue
        candidate_stl_hash = row.sha256
        if not is_content_hash(candidate_stl_hash):
            counters["errors"] += len(active_cells)
            continue
        for rc in active_cells:
            existing = estimate_store.read(candidate_stl_hash, rc.bundle_hash)
            if existing is not None and existing.status == EstimateStatus.fresh:
                counters["already_fresh"] += 1
                continue
            try:
                await enqueue_slice_estimate(
                    arq_pool,
                    source_stl=abs_path,
                    bundle_hash=rc.bundle_hash,
                    stl_cache=stl_cache,
                )
                counters["enqueued"] += 1
            except Exception:
                _LOG.exception(
                    "slicer.matrix_backfill.enqueue_error",
                    extra={
                        "labels.offer_id": rc.cell.offer_id,
                        "labels.material": rc.cell.material,
                    },
                )
                counters["errors"] += 1

    return counters
