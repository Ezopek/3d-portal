"""PROFILE-PUBLISH-1 — offer publish-state sidecar tests."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from app.modules.slicer import import_service
from app.modules.slicer.profile_offer import (
    ProfileChain,
    build_offer_record,
    offer_path,
    store_offer,
)
from app.modules.slicer.profile_publish import (
    PUBLISH_STATE_PUBLISHED,
    PUBLISH_STATE_UNPUBLISHED,
    apply_published_state,
    apply_unpublished_state,
    publish_state_of,
    store_publish_state,
)

ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-0000000000aa")


def _record() -> dict:
    return build_offer_record(
        offer_id="1" * 32,
        label="Standard",
        description=None,
        chain=ProfileChain(
            machine_block_id="2" * 32,
            process_block_id="3" * 32,
            filament_block_id="4" * 32,
        ),
        visibility="visible",
        is_default=False,
        compatible_material_categories=["TPU"],
        validation_state="usable",
        reasons=[],
        created_at="2026-06-06T00:00:00+00:00",
        created_by=ADMIN_ID,
        updated_at="2026-06-06T00:00:00+00:00",
    )


def test_v1_offer_sidecar_reads_forward_as_unpublished() -> None:
    sidecar = _record()
    sidecar.pop("publish_state", None)
    sidecar.pop("published_bundle_hash", None)
    sidecar["offer_manifest_version"] = "1"

    state = publish_state_of(sidecar)

    assert state.publish_state == PUBLISH_STATE_UNPUBLISHED
    assert state.published_bundle_hash is None
    assert state.published_at is None


def test_apply_published_state_is_additive_v2_and_leak_fenced() -> None:
    sidecar = _record()

    updated = apply_published_state(
        sidecar,
        bundle_hash="a" * 64,
        published_at="2026-06-06T01:02:03+00:00",
        published_by=ADMIN_ID,
        source_snapshot_ref="b" * 64,
        stl_hash="c" * 64,
    )

    assert updated["offer_manifest_version"] == "2"
    assert updated["publish_state"] == PUBLISH_STATE_PUBLISHED
    assert updated["published_bundle_hash"] == "a" * 64
    assert updated["published_by"] == str(ADMIN_ID)
    assert updated["source_snapshot_ref"] == "b" * 64
    assert updated["published_stl_hash"] == "c" * 64
    serialized = json.dumps(updated)
    assert "gcode" not in serialized
    assert "/mnt/" not in serialized
    assert "nozzle_temperature" not in serialized


def test_apply_unpublished_state_clears_active_publish_refs() -> None:
    published = apply_published_state(
        _record(),
        bundle_hash="a" * 64,
        published_at="2026-06-06T01:02:03+00:00",
        published_by=ADMIN_ID,
        source_snapshot_ref="b" * 64,
        stl_hash="c" * 64,
    )

    unpublished = apply_unpublished_state(published)

    assert unpublished["offer_manifest_version"] == "2"
    assert unpublished["publish_state"] == PUBLISH_STATE_UNPUBLISHED
    assert unpublished["published_bundle_hash"] is None
    assert unpublished["published_at"] is None
    assert unpublished["published_by"] is None
    assert unpublished["source_snapshot_ref"] is None
    assert unpublished["published_stl_hash"] is None


def test_store_publish_state_rolls_back_byte_identical_on_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = _record()
    store_offer(tmp_path, original)
    before = offer_path(tmp_path, original["offer_id"]).read_bytes()
    updated = apply_published_state(
        original,
        bundle_hash="a" * 64,
        published_at="2026-06-06T01:02:03+00:00",
        published_by=ADMIN_ID,
        source_snapshot_ref="b" * 64,
        stl_hash="c" * 64,
    )

    def boom_rename(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(import_service.os, "rename", boom_rename)
    with pytest.raises(OSError, match="disk full"):
        store_publish_state(tmp_path, updated)

    assert offer_path(tmp_path, original["offer_id"]).read_bytes() == before
    assert not list(tmp_path.rglob(".*tmp*"))
