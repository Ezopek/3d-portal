"""End-to-end test: synthetic catalog → --apply → assert final state."""
import json
from pathlib import Path

import trimesh

from migrate_catalog_3mf import main


def _index_entry(eid: str, path: str, category: str, **kwargs) -> dict:
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


def _make_real_catalog(root: Path, make_sphere, make_cube) -> None:
    (root / "_index").mkdir(parents=True)
    index = [
        _index_entry("001", "decorum/BunBowl.stl", "decorations"),
        _index_entry("002", "decorum/Stria Paper Holder", "decorations"),
        _index_entry("100", "wlasne modele/mosfet_hw-700_case", "own_models"),
        _index_entry(
            "101",
            "wlasne modele/podstawka_laptop_latitude_5450.FCStd",
            "own_models",
        ),
        _index_entry("102", "wlasne modele/test_spiecia.FCStd", "own_models"),
    ]
    (root / "_index" / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    (root / "decorum").mkdir()
    sphere = make_sphere()
    sphere.export(str(root / "decorum" / "BunBowl.stl"), file_type="stl")

    (root / "decorum" / "Stria Paper Holder").mkdir()
    src_3mf = root / "decorum" / "Stria Paper Holder" / "stria paper.3mf"
    scene = trimesh.Scene()
    scene.add_geometry(make_sphere(radius=12.0), geom_name="body")
    scene.add_geometry(make_cube(extents=(3.0, 3.0, 3.0)), geom_name="pin")
    scene.export(str(src_3mf), file_type="3mf")

    (root / "wlasne modele" / "mosfet_hw-700_case").mkdir(parents=True)
    (root / "wlasne modele" / "mosfet_hw-700_case" / "Base.step").write_text(
        "dummy"
    )
    (root / "wlasne modele" / "podstawka_laptop_latitude_5450.FCStd").write_text("d")
    (root / "wlasne modele" / "test_spiecia.FCStd").write_text("d")
    (root / "wlasne modele" / "test_spiecia.3mf").write_text("d")

    (root / "narzedzia").mkdir()


def test_end_to_end_dry_run_then_apply(tmp_path, make_sphere, make_cube, capsys):
    _make_real_catalog(tmp_path, make_sphere, make_cube)
    report_dir = tmp_path / "_reports"

    rc = main(
        [
            "--catalog-root",
            str(tmp_path),
            "--dry-run",
            "--report-dir",
            str(report_dir),
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    assert "## Wraps" in captured.out
    assert (tmp_path / "decorum" / "BunBowl.stl").exists()
    assert not (tmp_path / "decorum" / "BunBowl").exists()

    rc = main(
        [
            "--catalog-root",
            str(tmp_path),
            "--apply",
            "--report-dir",
            str(report_dir),
        ]
    )
    assert rc == 0

    # Wraps:
    assert (tmp_path / "decorum" / "BunBowl" / "BunBowl.stl").exists()
    assert not (tmp_path / "decorum" / "BunBowl.stl").exists()

    # Conversions:
    spaper_dir = tmp_path / "decorum" / "Stria Paper Holder"
    stls = sorted(p.name for p in spaper_dir.glob("*.stl"))
    assert stls == ["stria paper_01.stl", "stria paper_02.stl"]
    assert not (spaper_dir / "stria paper.3mf").exists()
    assert (
        tmp_path
        / "_archive"
        / "3mf-originals"
        / "decorum"
        / "Stria Paper Holder"
        / "stria paper.3mf"
    ).exists()

    # Mosfet move:
    assert (
        tmp_path / "narzedzia" / "mosfet_hw-700_case" / "Base.step"
    ).exists()
    assert not (tmp_path / "wlasne modele").exists()

    # Index updated:
    new_index = json.loads(
        (tmp_path / "_index" / "index.json").read_text(encoding="utf-8")
    )
    by_id = {e["id"]: e for e in new_index}
    assert by_id["001"]["path"] == "decorum/BunBowl"
    assert by_id["100"]["path"] == "narzedzia/mosfet_hw-700_case"
    assert by_id["100"]["category"] == "tools"
    assert "101" not in by_id
    assert "102" not in by_id

    reports = list(report_dir.glob("*-3mf-to-stl-migration.md"))
    assert len(reports) == 1

    rc2 = main(
        [
            "--catalog-root",
            str(tmp_path),
            "--apply",
            "--report-dir",
            str(report_dir),
        ]
    )
    assert rc2 == 0
    new_index_2 = json.loads(
        (tmp_path / "_index" / "index.json").read_text(encoding="utf-8")
    )
    assert new_index_2 == new_index
