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
