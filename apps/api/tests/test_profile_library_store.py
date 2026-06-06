"""PROFILE-LIB-1 (T2) — block storage layer tests (atomic store / list / read / delete).

Exercises real file I/O in a tmp ``library/`` subtree: the 33.2-reused two-phase atomic
publish (byte-identical tree on injected failure, no temp leftover), server-derived path-safe
``block_id`` + upsert, list-reads-manifests-only, and delete idempotency.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import pytest

from app.modules.slicer import import_service, profile_library
from app.modules.slicer.profile_library import (
    block_path,
    delete_block,
    derive_block_id,
    is_valid_block_id,
    library_root,
    list_blocks,
    manifest_path,
    read_block,
    store_block,
)

ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-0000000000aa")


def _manifest(block_id: str, profile_type: str, name: str) -> dict:
    return {
        "manifest_version": "1",
        "block_id": block_id,
        "profile_type": profile_type,
        "name": name,
        "source": "user",
        "is_system": False,
        "inherit": None,
        "inherit_chain": [],
        "settings_id": None,
        "material_type": None,
        "compatible_printers": [],
        "validation_state": "usable",
        "reasons": [],
        "portal_label": None,
        "imported_at": "2026-06-06T00:00:00+00:00",
        "imported_by": str(ADMIN_ID),
        "original_filename": "p.json",
    }


def _store(root: Path, profile_type: str, name: str, *, body: dict | None = None) -> str:
    block_id = derive_block_id(profile_type, name)  # type: ignore[arg-type]
    store_block(
        root,
        profile_type=profile_type,  # type: ignore[arg-type]
        block_id=block_id,
        body=body or {"name": name, "from": "User"},
        manifest=_manifest(block_id, profile_type, name),
    )
    return block_id


# === AC-7: server-derived path-safe block_id ===================================


def test_block_id_is_deterministic_32_char_hex() -> None:
    block_id = derive_block_id("process", "AI 0.20mm TPU - FlowTech")
    assert is_valid_block_id(block_id)
    assert len(block_id) == 32
    # Stable on re-derivation of the same (type, name) — the upsert key.
    assert block_id == derive_block_id("process", "AI 0.20mm TPU - FlowTech")
    # Distinct type ⇒ distinct id (same name, different block).
    assert block_id != derive_block_id("filament", "AI 0.20mm TPU - FlowTech")


@pytest.mark.parametrize(
    "bad", ["", "../etc", "g" * 32, "ABCDEF0123456789abcdef0123456789", "short", "/" * 32]
)
def test_invalid_block_ids_rejected(bad: str) -> None:
    assert is_valid_block_id(bad) is False


def test_block_path_layout_is_disjoint_from_grid(tmp_path: Path) -> None:
    bid = derive_block_id("process", "x")
    p = block_path(tmp_path, "process", bid)
    assert p == tmp_path / "library" / "process" / f"{bid}.json"
    # Disjoint from the grid trees.
    assert "intents" not in p.parts
    assert "system" not in p.parts


# === AC-8: atomic store + metadata preservation ===============================


def test_store_writes_body_and_manifest(tmp_path: Path) -> None:
    bid = _store(tmp_path, "process", "P1")
    body_p = block_path(tmp_path, "process", bid)
    assert body_p.exists()
    assert manifest_path(body_p).exists()
    assert json.loads(body_p.read_text())["name"] == "P1"
    assert json.loads(manifest_path(body_p).read_text())["block_id"] == bid


def test_fresh_library_subtree_inherits_operator_friendly_metadata(tmp_path: Path) -> None:
    # Regression for live PROFILE-LIB-1 smoke: a fresh library/process subtree must not be
    # created as root-owned/executable files when the API container writes into the bind mount.
    # In tmpfs we can assert the mode half directly; production root also preserves uid/gid.
    tmp_path.chmod(0o775)
    old_umask = os.umask(0o022)
    try:
        bid = _store(tmp_path, "process", "Metadata", body={"name": "Metadata"})
    finally:
        os.umask(old_umask)
    body_p = block_path(tmp_path, "process", bid)
    sidecar_p = manifest_path(body_p)
    assert (library_root(tmp_path).stat().st_mode & 0o777) == 0o775
    assert (body_p.parent.stat().st_mode & 0o777) == 0o775
    assert (body_p.stat().st_mode & 0o777) == 0o664
    assert (sidecar_p.stat().st_mode & 0o777) == 0o664


def test_reimport_same_type_name_is_upsert_not_duplicate(tmp_path: Path) -> None:
    bid1 = _store(tmp_path, "process", "Same", body={"name": "Same", "v": 1})
    bid2 = _store(tmp_path, "process", "Same", body={"name": "Same", "v": 2})
    assert bid1 == bid2
    process_dir = library_root(tmp_path) / "process"
    assert len(list(process_dir.glob("*.json"))) == 2  # one body + one manifest, not four
    body_p = block_path(tmp_path, "process", bid1)
    assert json.loads(body_p.read_text())["v"] == 2  # overwritten in place


def test_store_rolls_back_byte_identical_on_manifest_commit_failure(
    tmp_path: Path, monkeypatch
) -> None:
    # Pre-seed an existing block so the upsert has a prior state to roll back to.
    bid = _store(tmp_path, "process", "Roll", body={"name": "Roll", "v": 1})
    body_p = block_path(tmp_path, "process", bid)
    before = {
        p.relative_to(tmp_path).as_posix(): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }

    calls = {"n": 0}
    real_rename = import_service.os.rename

    def flaky_rename(src, dst):
        calls["n"] += 1
        if calls["n"] == 2:  # fail on the SECOND rename (the manifest commit)
            raise OSError("disk full")
        return real_rename(src, dst)

    monkeypatch.setattr(import_service.os, "rename", flaky_rename)

    with pytest.raises(OSError, match="disk full"):
        store_block(
            tmp_path,
            profile_type="process",
            block_id=bid,
            body={"name": "Roll", "v": 2},
            manifest=_manifest(bid, "process", "Roll"),
        )

    after = {
        p.relative_to(tmp_path).as_posix(): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    assert after == before  # byte-identical: the in-place upsert rolled back
    assert json.loads(body_p.read_text())["v"] == 1  # prior body restored
    assert not list(tmp_path.rglob(".*tmp*"))  # no temp leftover


# === AC-10: list reads manifests only ==========================================


def test_list_empty_tree_is_empty(tmp_path: Path) -> None:
    assert list_blocks(tmp_path) == []


def test_list_deterministic_order_process_first(tmp_path: Path) -> None:
    _store(tmp_path, "machine", "M-z")
    _store(tmp_path, "filament", "F-b")
    _store(tmp_path, "process", "P-c")
    _store(tmp_path, "process", "P-a")
    ordered = [(m["profile_type"], m["name"]) for m in list_blocks(tmp_path)]
    assert ordered == [
        ("process", "P-a"),
        ("process", "P-c"),
        ("filament", "F-b"),
        ("machine", "M-z"),
    ]


def test_list_filtered_by_type(tmp_path: Path) -> None:
    _store(tmp_path, "process", "P1")
    _store(tmp_path, "filament", "F1")
    only = list_blocks(tmp_path, profile_type="filament")
    assert [m["name"] for m in only] == ["F1"]


def test_list_reads_only_manifests_not_bodies(tmp_path: Path, monkeypatch) -> None:
    # A corrupt BODY must not break the list — only manifests are read.
    bid = _store(tmp_path, "process", "P1")
    block_path(tmp_path, "process", bid).write_text("{ corrupt body not json")
    listed = list_blocks(tmp_path)
    assert [m["name"] for m in listed] == ["P1"]


# === AC-11 / AC-12: read + delete round-trip ===================================


def test_read_block_by_id(tmp_path: Path) -> None:
    bid = _store(tmp_path, "process", "P1")
    manifest = read_block(tmp_path, bid)
    assert manifest is not None
    assert manifest["block_id"] == bid
    assert manifest["name"] == "P1"


def test_read_absent_block_is_none(tmp_path: Path) -> None:
    assert read_block(tmp_path, derive_block_id("process", "ghost")) is None


def test_read_invalid_block_id_is_none(tmp_path: Path) -> None:
    assert read_block(tmp_path, "../escape") is None


def test_delete_removes_body_and_manifest(tmp_path: Path) -> None:
    bid = _store(tmp_path, "process", "P1")
    body_p = block_path(tmp_path, "process", bid)
    assert delete_block(tmp_path, bid) is True
    assert not body_p.exists()
    assert not manifest_path(body_p).exists()
    assert read_block(tmp_path, bid) is None


def test_delete_absent_is_false(tmp_path: Path) -> None:
    assert delete_block(tmp_path, derive_block_id("process", "ghost")) is False


def test_delete_invalid_block_id_is_false(tmp_path: Path) -> None:
    assert delete_block(tmp_path, "../escape") is False


# === AC-1: the engine is purely additive — it does NOT touch the grid ===========


def test_profile_library_engine_does_not_touch_the_grid_surfaces() -> None:
    """AC-1: the library engine never enters the resolve / grid / append-only-store paths.

    Mirrors the 33.2 AC-23 fence intent at the module level: the separate-block engine must be
    purely additive over the 33.1/33.2 compiled-intent projection — it must not call
    ``resolve()``, read/write the ``intents/`` grid layout, or touch the append-only
    bundle/snapshot store or ``compatibility.py`` (those stay byte-stable — NFR21-PROVENANCE-1).
    """
    src = Path(profile_library.__file__).read_text(encoding="utf-8")
    # Call-form tokens (with the opening paren) so descriptive docstring prose that NAMES the
    # grid surfaces does not trip the fence — only actual usage would.
    for forbidden in (
        "compute_bundle_hash(",
        "resolve_inheritance(",
        "write_bundle(",
        "write_snapshot(",
        "BundleStore(",
        "is_compatible(",
        ".intent_path(",
        "resolve_preset(",
    ):
        assert forbidden not in src, f"library engine unexpectedly calls grid symbol {forbidden!r}"
    # The only import_service reuse is the SAFE atomic-publish foundation (AC-8), nothing
    # that mutates the grid or append-only store.
    assert "from app.modules.slicer.import_service import" in src
