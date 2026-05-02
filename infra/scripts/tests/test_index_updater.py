"""Tests for apply_index_updates."""
from pathlib import Path

from migrate_catalog_3mf import (
    apply_index_updates,
    WrapInFolder,
    MoveDir,
)


def _entry(eid, path, category="practical", **kwargs):
    return {
        "id": eid,
        "name_en": f"Model {eid}",
        "name_pl": f"Model {eid}",
        "path": path,
        "category": category,
        "subcategory": "",
        "tags": [],
        "source": "unknown",
        "printables_id": None,
        "thangs_id": None,
        "makerworld_id": None,
        "source_url": None,
        "rating": None,
        "status": "not_printed",
        "notes": "",
        "thumbnail": None,
        "date_added": "2026-04-01",
        "prints": [],
        **kwargs,
    }


def test_wrap_updates_path_for_loose_file_entry(tmp_path):
    catalog = tmp_path
    index = [_entry("001", "decorum/BunBowl.stl", category="decorations")]
    actions = [
        WrapInFolder(
            file=catalog / "decorum" / "BunBowl.stl",
            folder=catalog / "decorum" / "BunBowl",
        )
    ]
    new_index = apply_index_updates(index, actions, catalog)
    assert new_index[0]["path"] == "decorum/BunBowl"


def test_mosfet_move_updates_path_and_category(tmp_path):
    index = [
        _entry(
            "200",
            "wlasne modele/mosfet_hw-700_case",
            category="own_models",
            notes="FreeCAD source files (.FCStd) plus STEP export.",
        )
    ]
    actions = [
        MoveDir(
            src=tmp_path / "wlasne modele" / "mosfet_hw-700_case",
            dst=tmp_path / "narzedzia" / "mosfet_hw-700_case",
        )
    ]
    new_index = apply_index_updates(index, actions, tmp_path)
    assert new_index[0]["path"] == "narzedzia/mosfet_hw-700_case"
    assert new_index[0]["category"] == "tools"


def test_explicit_index_deletions_drop_two_fcstd_entries(tmp_path):
    index = [
        _entry("100", "wlasne modele/podstawka_laptop_latitude_5450.FCStd"),
        _entry("101", "wlasne modele/test_spiecia.FCStd"),
        _entry("002", "decorum/Other"),
    ]
    new_index = apply_index_updates(index, [], tmp_path)
    paths = {e["path"] for e in new_index}
    assert paths == {"decorum/Other"}


def test_paths_use_forward_slashes_on_all_platforms(tmp_path):
    index = [_entry("001", "decorum/BunBowl.stl")]
    actions = [
        WrapInFolder(
            file=tmp_path / "decorum" / "BunBowl.stl",
            folder=tmp_path / "decorum" / "BunBowl",
        )
    ]
    new_index = apply_index_updates(index, actions, tmp_path)
    assert "/" in new_index[0]["path"]
    assert "\\" not in new_index[0]["path"]


def test_unrelated_entries_pass_through_untouched(tmp_path):
    index = [_entry("050", "praktyczne/Hammer/hammer.stl")]
    actions = [
        WrapInFolder(
            file=tmp_path / "decorum" / "Other.stl",
            folder=tmp_path / "decorum" / "Other",
        )
    ]
    new_index = apply_index_updates(index, actions, tmp_path)
    assert new_index[0]["path"] == "praktyczne/Hammer/hammer.stl"
