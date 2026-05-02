"""Tests for scan_catalog."""
from pathlib import Path

from migrate_catalog_3mf import (
    scan_catalog,
    WrapInFolder,
    MoveDir,
    Convert3mf,
    Archive3mf,
    DeleteFile,
    RemoveEmptyDir,
)


def _make_synthetic_catalog(root: Path) -> Path:
    """Build a tiny realistic catalog under root.

    decorum/
        BunBowl.stl                            (loose; gets wrapped)
        Stria Paper Holder/
            stria paper.3mf                    (no sibling stl; convert + archive)
            prints/2026-01-01.jpg              (must NOT be touched)
        Marshmallow table/
            table.3mf                          (sibling stl exists; archive only)
            Top.stl
    praktyczne/                                (empty top-level)
    wlasne modele/
        mosfet_hw-700_case/
            Base.step
        podstawka.FCStd
        test_spiecia.3mf
    """
    (root / "decorum").mkdir(parents=True)
    (root / "decorum" / "BunBowl.stl").write_text("dummy")
    (root / "decorum" / "Stria Paper Holder").mkdir()
    (root / "decorum" / "Stria Paper Holder" / "stria paper.3mf").write_text("dummy")
    (root / "decorum" / "Stria Paper Holder" / "prints").mkdir()
    (root / "decorum" / "Stria Paper Holder" / "prints" / "2026-01-01.jpg").write_text("img")
    (root / "decorum" / "Marshmallow table").mkdir()
    (root / "decorum" / "Marshmallow table" / "table.3mf").write_text("dummy")
    (root / "decorum" / "Marshmallow table" / "Top.stl").write_text("dummy")

    (root / "praktyczne").mkdir()

    (root / "wlasne modele").mkdir()
    (root / "wlasne modele" / "mosfet_hw-700_case").mkdir()
    (root / "wlasne modele" / "mosfet_hw-700_case" / "Base.step").write_text("dummy")
    (root / "wlasne modele" / "podstawka.FCStd").write_text("dummy")
    (root / "wlasne modele" / "test_spiecia.3mf").write_text("dummy")

    return root


def test_loose_stl_at_category_root_emits_wrap(tmp_path):
    _make_synthetic_catalog(tmp_path)
    actions = scan_catalog(tmp_path)

    wraps = [a for a in actions if isinstance(a, WrapInFolder)]
    assert any(
        a.file == tmp_path / "decorum" / "BunBowl.stl"
        and a.folder == tmp_path / "decorum" / "BunBowl"
        for a in wraps
    )


def test_3mf_without_sibling_stl_emits_convert_then_archive(tmp_path):
    _make_synthetic_catalog(tmp_path)
    actions = scan_catalog(tmp_path)

    src = tmp_path / "decorum" / "Stria Paper Holder" / "stria paper.3mf"
    converts = [a for a in actions if isinstance(a, Convert3mf) and a.src == src]
    archives = [a for a in actions if isinstance(a, Archive3mf) and a.src == src]
    assert len(converts) == 1
    assert len(archives) == 1
    expected_archive = (
        tmp_path
        / "_archive"
        / "3mf-originals"
        / "decorum"
        / "Stria Paper Holder"
        / "stria paper.3mf"
    )
    assert archives[0].dst == expected_archive

    assert actions.index(converts[0]) < actions.index(archives[0])


def test_3mf_with_sibling_stl_emits_archive_only(tmp_path):
    _make_synthetic_catalog(tmp_path)
    actions = scan_catalog(tmp_path)

    src = tmp_path / "decorum" / "Marshmallow table" / "table.3mf"
    converts = [a for a in actions if isinstance(a, Convert3mf) and a.src == src]
    archives = [a for a in actions if isinstance(a, Archive3mf) and a.src == src]
    assert converts == []
    assert len(archives) == 1


def test_prints_subdir_is_ignored(tmp_path):
    _make_synthetic_catalog(tmp_path)
    actions = scan_catalog(tmp_path)
    for a in actions:
        if hasattr(a, "src"):
            assert "prints" not in a.src.parts
        if hasattr(a, "file"):
            assert "prints" not in a.file.parts


def test_mosfet_emits_move_to_narzedzia(tmp_path):
    _make_synthetic_catalog(tmp_path)
    actions = scan_catalog(tmp_path)
    moves = [a for a in actions if isinstance(a, MoveDir)]
    assert len(moves) == 1
    assert moves[0].src == tmp_path / "wlasne modele" / "mosfet_hw-700_case"
    assert moves[0].dst == tmp_path / "narzedzia" / "mosfet_hw-700_case"


def test_wlasne_modele_other_files_get_deleted(tmp_path):
    _make_synthetic_catalog(tmp_path)
    actions = scan_catalog(tmp_path)
    deletes = [a for a in actions if isinstance(a, DeleteFile)]
    deleted_names = {a.path.name for a in deletes}
    assert "podstawka.FCStd" in deleted_names
    assert "test_spiecia.3mf" in deleted_names


def test_wlasne_modele_dir_removal_emitted_last(tmp_path):
    _make_synthetic_catalog(tmp_path)
    actions = scan_catalog(tmp_path)
    rmd = [a for a in actions if isinstance(a, RemoveEmptyDir)]
    assert len(rmd) == 1
    assert rmd[0].path == tmp_path / "wlasne modele"
    rmd_idx = actions.index(rmd[0])
    for i, a in enumerate(actions):
        if i == rmd_idx:
            continue
        if hasattr(a, "path") and "wlasne modele" in a.path.parts:
            assert i < rmd_idx
        if hasattr(a, "src") and "wlasne modele" in a.src.parts:
            assert i < rmd_idx


def test_loose_3mf_at_category_root_wraps_then_converts_then_archives(tmp_path):
    """Edge case: 3mf directly under category dir."""
    (tmp_path / "decorum").mkdir(parents=True)
    (tmp_path / "decorum" / "loose.3mf").write_text("dummy")
    actions = scan_catalog(tmp_path)
    wrap = next(a for a in actions if isinstance(a, WrapInFolder))
    convert = next(a for a in actions if isinstance(a, Convert3mf))
    archive = next(a for a in actions if isinstance(a, Archive3mf))
    assert wrap.file == tmp_path / "decorum" / "loose.3mf"
    assert wrap.folder == tmp_path / "decorum" / "loose"
    assert convert.src == tmp_path / "decorum" / "loose" / "loose.3mf"
    assert archive.src == tmp_path / "decorum" / "loose" / "loose.3mf"


def test_archive_dir_inside_a_model_folder_is_ignored(tmp_path):
    """Robustness: a leftover _archive/ inside a model folder must not recurse."""
    (tmp_path / "decorum" / "weird" / "_archive" / "junk").mkdir(parents=True)
    (tmp_path / "decorum" / "weird" / "_archive" / "junk" / "old.3mf").write_text("x")
    actions = scan_catalog(tmp_path)
    for a in actions:
        if hasattr(a, "src"):
            assert "_archive" not in a.src.parts
