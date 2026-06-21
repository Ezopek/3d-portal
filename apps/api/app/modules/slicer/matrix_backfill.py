"""Offer-driven matrix enumeration + enqueue helpers.

This module implements the offer-SoT backfill pipeline:

1. :func:`enumerate_offer_cells` — pure function; builds one resolved cell per
   published, visible offer using the already-published ``published_bundle_hash``.
2. :func:`enqueue_matrix_for_all_stls` — shared helper used by both the script and the
   event-driven hooks: walks all catalog ``kind=stl`` ModelFile rows, applies freshness
   pre-checks, and idempotently enqueues ``(stl_hash, bundle_hash)`` pairs.

FR23-BACKFILL-1 / NFR23-QUEUE-BOUND-1.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.modules.slicer.profile_publish import PUBLISH_STATE_PUBLISHED, publish_state_of

_LOG = logging.getLogger("app.modules.slicer.matrix_backfill")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MatrixCell:
    """One offer cell from the backfill matrix."""

    offer_id: str
    offer_label: str
    material: str
    orca_profile_ref: str


@dataclass(frozen=True)
class ResolvedMatrixCell:
    """Result of resolving one :class:`MatrixCell` to a concrete bundle."""

    cell: MatrixCell
    bundle_hash: str | None
    resolve_failed: bool = False


# ---------------------------------------------------------------------------
# Pure enumeration (offer-SoT path — no I/O)
# ---------------------------------------------------------------------------


def enumerate_offer_cells(
    offers: list[dict], *, visible_only: bool, offer_id: str | None = None
) -> list[ResolvedMatrixCell]:
    """Return one resolved backfill cell per eligible published offer.

    Pure function — performs no policy/material-default reads and never resolves profile chains.
    The bundle hash is the already-published ``published_bundle_hash`` stored on the offer sidecar.
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
                resolve_failed=False,
            )
        )
    return cells


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
