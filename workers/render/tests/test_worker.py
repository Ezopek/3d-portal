import json
import shutil
from pathlib import Path

import fakeredis.aioredis
import pytest

from render.worker import render_model


@pytest.mark.asyncio
async def test_render_model_writes_renders_under_model_id(tmp_path):
    catalog = tmp_path / "catalog"
    renders = tmp_path / "renders"
    (catalog / "decorum/dragon").mkdir(parents=True)
    fixture = Path(__file__).parent / "fixtures" / "cube.stl"
    shutil.copy(fixture, catalog / "decorum/dragon/Dragon.stl")
    index = catalog / "_index"
    index.mkdir()
    (index / "index.json").write_text(
        json.dumps(
            [
                {
                    "id": "001",
                    "name_en": "Dragon",
                    "name_pl": "Smok",
                    "path": "decorum/dragon",
                    "category": "decorations",
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
                    "date_added": "2026-04-29",
                }
            ]
        )
    )

    fake = fakeredis.aioredis.FakeRedis()
    ctx = {
        "redis": fake,
        "catalog_dir": catalog,
        "renders_dir": renders,
        "image_size": 64,
    }

    result = await render_model(ctx, "001")
    assert result["status"] == "done"
    out_dir = renders / "001"
    assert (out_dir / "front.png").exists()
    assert (out_dir / "iso.png").exists()
    assert await fake.get("render:status:001") == b"done"


@pytest.mark.asyncio
async def test_render_model_finds_stl_with_uppercase_extension(tmp_path):
    catalog = tmp_path / "catalog"
    renders = tmp_path / "renders"
    (catalog / "decorum/dragon").mkdir(parents=True)
    fixture = Path(__file__).parent / "fixtures" / "cube.stl"
    shutil.copy(fixture, catalog / "decorum/dragon/Dragon.STL")
    index = catalog / "_index"
    index.mkdir()
    (index / "index.json").write_text(
        json.dumps(
            [
                {
                    "id": "001",
                    "name_en": "Dragon",
                    "name_pl": "Smok",
                    "path": "decorum/dragon",
                    "category": "decorations",
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
                    "date_added": "2026-04-29",
                }
            ]
        )
    )

    fake = fakeredis.aioredis.FakeRedis()
    ctx = {"redis": fake, "catalog_dir": catalog, "renders_dir": renders, "image_size": 64}

    result = await render_model(ctx, "001")
    assert result["status"] == "done"
    assert (renders / "001" / "iso.png").exists()


@pytest.mark.asyncio
async def test_render_model_marks_failed_on_missing_stl(tmp_path):
    catalog = tmp_path / "catalog"
    renders = tmp_path / "renders"
    (catalog / "decorum/dragon").mkdir(parents=True)
    index = catalog / "_index"
    index.mkdir()
    (index / "index.json").write_text(
        json.dumps(
            [
                {
                    "id": "001",
                    "name_en": "X",
                    "name_pl": "X",
                    "path": "decorum/dragon",
                    "category": "decorations",
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
                    "date_added": "2026-04-29",
                }
            ]
        )
    )

    fake = fakeredis.aioredis.FakeRedis()
    ctx = {"redis": fake, "catalog_dir": catalog, "renders_dir": renders, "image_size": 64}

    result = await render_model(ctx, "001")
    assert result["status"] == "failed"
    assert "no stl" in result["reason"].lower() or "stl" in result["reason"].lower()
    assert await fake.get("render:status:001") == b"failed"


@pytest.mark.asyncio
async def test_render_model_with_selected_paths_uses_them(tmp_path):
    catalog = tmp_path / "catalog"
    renders = tmp_path / "renders"
    model_dir = catalog / "decorum/multi"
    (model_dir / "files").mkdir(parents=True)
    fixture = Path(__file__).parent / "fixtures" / "cube.stl"
    shutil.copy(fixture, model_dir / "files" / "a.stl")
    shutil.copy(fixture, model_dir / "files" / "b.stl")
    shutil.copy(fixture, model_dir / "files" / "c.stl")

    index = catalog / "_index"
    index.mkdir()
    (index / "index.json").write_text(
        json.dumps(
            [
                {
                    "id": "002",
                    "name_en": "Multi",
                    "name_pl": "Multi",
                    "path": "decorum/multi",
                    "category": "decorations",
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
                    "date_added": "2026-05-03",
                }
            ]
        )
    )

    fake = fakeredis.aioredis.FakeRedis()
    ctx = {"redis": fake, "catalog_dir": catalog, "renders_dir": renders, "image_size": 64}

    result = await render_model(ctx, "002", selected_paths=["files/a.stl", "files/b.stl"])
    assert result["status"] == "done"
    assert (renders / "002" / "iso.png").exists()


@pytest.mark.asyncio
async def test_render_model_falls_back_when_all_selected_paths_missing(tmp_path):
    catalog = tmp_path / "catalog"
    renders = tmp_path / "renders"
    model_dir = catalog / "decorum/onefile"
    model_dir.mkdir(parents=True)
    fixture = Path(__file__).parent / "fixtures" / "cube.stl"
    shutil.copy(fixture, model_dir / "Only.stl")

    index = catalog / "_index"
    index.mkdir()
    (index / "index.json").write_text(
        json.dumps(
            [
                {
                    "id": "003",
                    "name_en": "One",
                    "name_pl": "Jeden",
                    "path": "decorum/onefile",
                    "category": "decorations",
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
                    "date_added": "2026-05-03",
                }
            ]
        )
    )

    fake = fakeredis.aioredis.FakeRedis()
    ctx = {"redis": fake, "catalog_dir": catalog, "renders_dir": renders, "image_size": 64}

    result = await render_model(ctx, "003", selected_paths=["files/gone.stl"])
    assert result["status"] == "done"
    assert (renders / "003" / "iso.png").exists()


@pytest.mark.asyncio
async def test_render_model_rejects_path_traversal_in_selection(tmp_path):
    catalog = tmp_path / "catalog"
    renders = tmp_path / "renders"
    model_dir = catalog / "decorum/safe"
    model_dir.mkdir(parents=True)
    fixture = Path(__file__).parent / "fixtures" / "cube.stl"
    shutil.copy(fixture, model_dir / "Safe.stl")

    index = catalog / "_index"
    index.mkdir()
    (index / "index.json").write_text(
        json.dumps(
            [
                {
                    "id": "004",
                    "name_en": "Safe",
                    "name_pl": "Safe",
                    "path": "decorum/safe",
                    "category": "decorations",
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
                    "date_added": "2026-05-03",
                }
            ]
        )
    )

    fake = fakeredis.aioredis.FakeRedis()
    ctx = {"redis": fake, "catalog_dir": catalog, "renders_dir": renders, "image_size": 64}

    result = await render_model(ctx, "004", selected_paths=["../escape.stl"])
    assert result["status"] == "done"
    assert (renders / "004" / "iso.png").exists()
