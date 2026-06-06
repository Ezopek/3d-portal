"""PROFILE-OFFER-1 (T2) — offer storage layer tests (AC-5, AC-6, AC-7, AC-10).

Real file I/O in a tmp ``offers/`` subtree: server-minted path-safe ``offer_id``, the
single-SoT layout disjoint from the grid/library trees, the reused atomic single-file publish
(byte-identical tree on injected failure, no temp leftover, operator-friendly metadata),
delete idempotency, and the read-time revalidation that flips an offer to ``invalid`` after a
referenced block is removed.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import pytest

from app.modules.slicer import import_service
from app.modules.slicer.profile_library import derive_block_id, store_block
from app.modules.slicer.profile_offer import (
    REASON_UNKNOWN_BLOCK,
    ProfileChain,
    build_offer_record,
    delete_offer,
    is_valid_offer_id,
    list_offers,
    mint_offer_id,
    offer_path,
    offers_root,
    read_offer,
    revalidate_offers,
    store_offer,
)

ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-0000000000aa")


def _store_block(root: Path, profile_type: str, name: str, **extra: object) -> str:
    block_id = derive_block_id(profile_type, name)  # type: ignore[arg-type]
    manifest = {
        "manifest_version": "1",
        "block_id": block_id,
        "profile_type": profile_type,
        "name": name,
        "source": "user",
        "is_system": False,
        "inherit": None,
        "inherit_chain": [],
        "settings_id": None,
        "material_type": extra.get("material_type"),
        "compatible_printers": extra.get("compatible_printers", []),
        "validation_state": "usable",
        "reasons": [],
        "portal_label": None,
        "imported_at": "2026-06-06T00:00:00+00:00",
        "imported_by": str(ADMIN_ID),
        "original_filename": "p.json",
    }
    store_block(
        root, profile_type=profile_type, block_id=block_id, body={"name": name}, manifest=manifest
    )  # type: ignore[arg-type]
    return block_id


def _usable_chain(root: Path) -> ProfileChain:
    return ProfileChain(
        machine_block_id=_store_block(root, "machine", "K1 Max"),
        process_block_id=_store_block(root, "process", "0.20 Standard"),
        filament_block_id=_store_block(root, "filament", "Rosa PLA", material_type="PLA"),
    )


def _record(
    root: Path,
    *,
    offer_id: str | None = None,
    chain: ProfileChain | None = None,
    label: str = "Offer",
    visibility: str = "hidden",
    is_default: bool = False,
    categories: list[str] | None = None,
    created_at: str = "2026-06-06T00:00:00+00:00",
) -> dict:
    return build_offer_record(
        offer_id=offer_id or mint_offer_id(),
        label=label,
        description=None,
        chain=chain or _usable_chain(root),
        visibility=visibility,  # type: ignore[arg-type]
        is_default=is_default,
        compatible_material_categories=categories or ["PLA"],
        validation_state="usable",
        reasons=[],
        created_at=created_at,
        created_by=ADMIN_ID,
        updated_at=created_at,
    )


# === AC-6: server-minted path-safe offer_id ===================================


def test_offer_id_is_32_char_hex_and_unique() -> None:
    a = mint_offer_id()
    b = mint_offer_id()
    assert is_valid_offer_id(a) and len(a) == 32
    assert a != b  # minted, not derived — distinct each time


@pytest.mark.parametrize(
    "bad", ["", "../etc", "g" * 32, "ABCDEF0123456789abcdef0123456789", "short", "/" * 32]
)
def test_invalid_offer_ids_rejected(bad: str) -> None:
    assert is_valid_offer_id(bad) is False


def test_offer_path_layout_is_disjoint_from_grid_and_library(tmp_path: Path) -> None:
    oid = mint_offer_id()
    p = offer_path(tmp_path, oid)
    assert p == tmp_path / "offers" / f"{oid}.json"
    assert "intents" not in p.parts
    assert "system" not in p.parts
    assert "library" not in p.parts


# === AC-7: atomic store + metadata preservation ===============================


def test_store_writes_sidecar(tmp_path: Path) -> None:
    record = _record(tmp_path, label="My Offer")
    path = store_offer(tmp_path, record)
    assert path.exists()
    assert json.loads(path.read_text())["label"] == "My Offer"
    assert read_offer(tmp_path, record["offer_id"])["label"] == "My Offer"


def test_store_rejects_invalid_offer_id(tmp_path: Path) -> None:
    record = _record(tmp_path)
    record["offer_id"] = "../escape"
    with pytest.raises(ValueError, match="invalid offer_id"):
        store_offer(tmp_path, record)


def test_fresh_offers_subtree_inherits_operator_friendly_metadata(tmp_path: Path) -> None:
    # Regression for the live RW-mount smoke: a fresh offers/ subtree must not be created as
    # root-owned/executable files. In tmpfs we assert the mode half; production root preserves
    # uid/gid via the shared _stage_temp metadata source.
    tmp_path.chmod(0o775)
    old_umask = os.umask(0o022)
    try:
        record = _record(tmp_path)
        path = store_offer(tmp_path, record)
    finally:
        os.umask(old_umask)
    assert (offers_root(tmp_path).stat().st_mode & 0o777) == 0o775
    assert (path.stat().st_mode & 0o777) == 0o664


def test_store_upsert_overwrites_in_place(tmp_path: Path) -> None:
    chain = _usable_chain(tmp_path)
    oid = mint_offer_id()
    store_offer(tmp_path, _record(tmp_path, offer_id=oid, chain=chain, label="v1"))
    store_offer(tmp_path, _record(tmp_path, offer_id=oid, chain=chain, label="v2"))
    assert len(list((offers_root(tmp_path)).glob("*.json"))) == 1  # one file, overwritten
    assert read_offer(tmp_path, oid)["label"] == "v2"


def test_store_rolls_back_byte_identical_on_rename_failure(tmp_path: Path, monkeypatch) -> None:
    chain = _usable_chain(tmp_path)
    before = {
        p.relative_to(tmp_path).as_posix(): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }

    def boom_rename(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(import_service.os, "rename", boom_rename)
    with pytest.raises(OSError, match="disk full"):
        store_offer(tmp_path, _record(tmp_path, chain=chain))

    after = {
        p.relative_to(tmp_path).as_posix(): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    assert after == before  # nothing published
    assert not list(tmp_path.rglob(".*tmp*"))  # no temp leftover


# === AC-10: list / read / delete + read-time revalidation =====================


def test_list_empty_tree_is_empty(tmp_path: Path) -> None:
    assert list_offers(tmp_path) == []


def test_list_deterministic_order_by_created_at(tmp_path: Path) -> None:
    chain = _usable_chain(tmp_path)
    store_offer(
        tmp_path, _record(tmp_path, chain=chain, label="B", created_at="2026-06-06T02:00:00+00:00")
    )
    store_offer(
        tmp_path, _record(tmp_path, chain=chain, label="A", created_at="2026-06-06T01:00:00+00:00")
    )
    labels = [s["label"] for s in list_offers(tmp_path)]
    assert labels == ["A", "B"]


def test_read_absent_offer_is_none(tmp_path: Path) -> None:
    assert read_offer(tmp_path, mint_offer_id()) is None


def test_read_invalid_offer_id_is_none(tmp_path: Path) -> None:
    assert read_offer(tmp_path, "../escape") is None


def test_delete_removes_sidecar_then_404(tmp_path: Path) -> None:
    record = _record(tmp_path)
    store_offer(tmp_path, record)
    assert delete_offer(tmp_path, record["offer_id"]) is True
    assert read_offer(tmp_path, record["offer_id"]) is None
    # Re-delete is idempotent-safe False (the endpoint maps to 404, never 500).
    assert delete_offer(tmp_path, record["offer_id"]) is False


def test_delete_invalid_offer_id_is_false(tmp_path: Path) -> None:
    assert delete_offer(tmp_path, "../escape") is False


def test_delete_does_not_touch_referenced_blocks(tmp_path: Path) -> None:
    chain = _usable_chain(tmp_path)
    record = _record(tmp_path, chain=chain)
    store_offer(tmp_path, record)
    delete_offer(tmp_path, record["offer_id"])
    # The referenced library blocks survive — offers reference, they do not own.
    from app.modules.slicer.profile_library import read_block

    assert read_block(tmp_path, chain.machine_block_id) is not None
    assert read_block(tmp_path, chain.process_block_id) is not None
    assert read_block(tmp_path, chain.filament_block_id) is not None


def test_list_revalidation_flips_to_invalid_after_block_removed(tmp_path: Path) -> None:
    chain = _usable_chain(tmp_path)
    record = _record(tmp_path, chain=chain)
    store_offer(tmp_path, record)
    # Stored snapshot says usable.
    [resolved_before] = revalidate_offers(tmp_path, list_offers(tmp_path))
    assert resolved_before.state == "usable"

    # Delete a referenced block — the next revalidation must NOT serve the stale usable.
    from app.modules.slicer.profile_library import delete_block

    assert delete_block(tmp_path, chain.process_block_id) is True
    [resolved_after] = revalidate_offers(tmp_path, list_offers(tmp_path))
    assert resolved_after.state == "invalid"
    assert REASON_UNKNOWN_BLOCK in resolved_after.reasons
    # The offer sidecar itself is NOT eagerly deleted — it remains, flagged.
    assert read_offer(tmp_path, record["offer_id"]) is not None


def test_duplicate_default_computed_across_offer_set(tmp_path: Path) -> None:
    chain = _usable_chain(tmp_path)
    store_offer(
        tmp_path,
        _record(tmp_path, chain=chain, visibility="visible", is_default=True, categories=["PLA"]),
    )
    store_offer(
        tmp_path,
        _record(tmp_path, chain=chain, visibility="visible", is_default=True, categories=["PLA"]),
    )
    states = [r.state for r in revalidate_offers(tmp_path, list_offers(tmp_path))]
    # Both visible defaults for PLA are flagged requires_attention.
    assert states == ["requires_attention", "requires_attention"]
