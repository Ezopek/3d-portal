"""Tests for matrix_backfill module — offer-driven path (Story 40.x).

Covers:
- enumerate_offer_cells pure-function contract
"""

from __future__ import annotations

from app.modules.slicer.matrix_backfill import (
    enumerate_offer_cells,
)
from app.modules.slicer.profile_publish import PUBLISH_STATE_PUBLISHED, PUBLISH_STATE_UNPUBLISHED

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _sidecar(
    offer_id: str,
    *,
    publish_state: str = PUBLISH_STATE_PUBLISHED,
    compatible: list[str] | None = None,
    label: str = "",
    machine_block_id: str = "mach",
    process_block_id: str = "proc",
    filament_block_id: str = "fil",
) -> dict:
    base: dict = {
        "offer_id": offer_id,
        "label": label or offer_id,
        "publish_state": publish_state,
        "compatible_material_categories": compatible if compatible is not None else ["PLA"],
        "machine_block_id": machine_block_id,
        "process_block_id": process_block_id,
        "filament_block_id": filament_block_id,
        "filament_overrides": {},
    }
    if publish_state == PUBLISH_STATE_PUBLISHED:
        # publish_state_of requires these fields to return "published"
        base["published_bundle_hash"] = "fake-bundle-hash"
        base["published_at"] = "2026-01-01T00:00:00+00:00"
    return base


# ---------------------------------------------------------------------------
# Tests: enumerate_offer_cells (Story 40.1 offer-SoT pure enumeration)
# ---------------------------------------------------------------------------


def _offer_sidecar(
    offer_id: str,
    *,
    publish_state: str = PUBLISH_STATE_PUBLISHED,
    bundle_hash: str | None = "a" * 64,
    validation_state: str = "usable",
    visibility: str = "visible",
) -> dict:
    sidecar = _sidecar(offer_id, publish_state=publish_state)
    sidecar["validation_state"] = validation_state
    sidecar["visibility"] = visibility
    if publish_state == PUBLISH_STATE_PUBLISHED:
        sidecar["published_bundle_hash"] = bundle_hash
    return sidecar


def test_enumerate_offer_cells_includes_published_visible_valid_hash():
    cells = enumerate_offer_cells([_offer_sidecar("offer-1")], visible_only=True)

    assert len(cells) == 1
    assert cells[0].cell.offer_id == "offer-1"
    assert cells[0].bundle_hash == "a" * 64
    assert cells[0].resolve_failed is False


def test_enumerate_offer_cells_skips_ineligible_offers():
    cells = enumerate_offer_cells(
        [
            _offer_sidecar("published"),
            _offer_sidecar("unpublished", publish_state=PUBLISH_STATE_UNPUBLISHED),
            _offer_sidecar("invalid", validation_state="invalid"),
            _offer_sidecar("hidden", visibility="hidden"),
            _offer_sidecar("missing-hash", bundle_hash=None),
        ],
        visible_only=True,
    )

    assert [cell.cell.offer_id for cell in cells] == ["published"]


def test_enumerate_offer_cells_visible_only_false_includes_hidden():
    cells = enumerate_offer_cells(
        [_offer_sidecar("hidden", visibility="hidden")], visible_only=False
    )

    assert [cell.cell.offer_id for cell in cells] == ["hidden"]


def test_enumerate_offer_cells_offer_id_scope():
    cells = enumerate_offer_cells(
        [_offer_sidecar("offer-1"), _offer_sidecar("offer-2", bundle_hash="b" * 64)],
        visible_only=True,
        offer_id="offer-2",
    )

    assert len(cells) == 1
    assert cells[0].cell.offer_id == "offer-2"
    assert cells[0].bundle_hash == "b" * 64
