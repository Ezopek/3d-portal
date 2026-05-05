import asyncio
import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlmodel import Session, select


# Set DATABASE_URL to a fresh tmp sqlite before importing app code
@pytest.fixture
def tmp_db_engine():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "portal.db"
        url = f"sqlite:///{db_path}"
        # Import models package first so all SQLModel table classes register
        # on SQLModel.metadata before init_schema runs create_all.
        import app.core.db.models  # noqa: F401
        from app.core.db.session import create_engine_for_url, init_schema

        engine = create_engine_for_url(url)
        init_schema(engine)
        yield engine, Path(tmp)


def test_render_model_inserts_4_modelfile_rows(tmp_db_engine):
    engine, tmp_root = tmp_db_engine
    content_dir = tmp_root / "content"
    content_dir.mkdir()

    # Seed: a model with one STL file. The STL bytes are minimal valid ASCII STL.
    from app.core.db.models import Category, Model, ModelFile, ModelFileKind

    with Session(engine) as s:
        cat = Category(slug="t", name_en="t")
        s.add(cat)
        s.commit()
        s.refresh(cat)
        m = Model(slug="t", name_en="t", category_id=cat.id)
        s.add(m)
        s.commit()
        s.refresh(m)
        stl_uuid = uuid.uuid4()
        storage_rel = f"models/{m.id}/files/{stl_uuid}.stl"
        dst = content_dir / storage_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        # Minimal valid ASCII STL (a triangle)
        dst.write_text(
            "solid t\nfacet normal 0 0 1\nouter loop\n"
            "vertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\n"
            "endloop\nendfacet\nendsolid t\n"
        )
        s.add(
            ModelFile(
                id=stl_uuid,
                model_id=m.id,
                kind=ModelFileKind.stl,
                original_name="t.stl",
                storage_path=storage_rel,
                sha256="x",
                size_bytes=10,
                mime_type="model/stl",
            )
        )
        s.commit()
        model_id = str(m.id)

    # Mock redis + render_views (don't actually run trimesh; produce 4 dummy PNGs)
    redis = MagicMock()
    redis.set = AsyncMock(return_value=None)

    def fake_render_views(*, stl_paths, output_dir, size):
        from render.trimesh_render import VIEW_NAMES

        for view in VIEW_NAMES:
            (Path(output_dir) / f"{view}.png").write_bytes(f"fake-png-{view}".encode())
        return {v: Path(output_dir) / f"{v}.png" for v in VIEW_NAMES}

    with patch("render.worker.render_views", fake_render_views):
        from render.worker import render_model

        ctx = {
            "redis": redis,
            "engine": engine,
            "content_dir": content_dir,
            "image_size": 256,
        }
        result = asyncio.run(render_model(ctx, model_id))

    assert result["status"] == "done"
    assert set(result["rendered_views"]) == {"front", "iso", "side", "top"}

    with Session(engine) as s:
        from app.core.db.models import Model, ModelFile, ModelFileKind

        files = list(
            s.exec(
                select(ModelFile)
                .where(ModelFile.kind == ModelFileKind.image)
            ).all()
        )
        names = {f.original_name for f in files}
        assert names == {"iso-render.png", "front-render.png", "side-render.png", "top-render.png"}
        m = s.exec(select(Model).where(Model.slug == "t")).one()
        # Thumbnail set to iso
        iso = next(f for f in files if f.original_name == "iso-render.png")
        assert m.thumbnail_file_id == iso.id

    # Status flow: running then done
    redis.set.assert_any_await(
        "render:status:" + model_id, b"running", ex=60 * 60
    )
    redis.set.assert_any_await(
        "render:status:" + model_id, b"done", ex=60 * 60
    )


def test_render_model_replaces_old_auto_renders(tmp_db_engine):
    engine, tmp_root = tmp_db_engine
    content_dir = tmp_root / "content"
    content_dir.mkdir()

    from app.core.db.models import Category, Model, ModelFile, ModelFileKind

    with Session(engine) as s:
        cat = Category(slug="r", name_en="r")
        s.add(cat)
        s.commit()
        s.refresh(cat)
        m = Model(slug="r", name_en="r", category_id=cat.id)
        s.add(m)
        s.commit()
        s.refresh(m)
        stl_uuid = uuid.uuid4()
        storage_rel = f"models/{m.id}/files/{stl_uuid}.stl"
        (content_dir / storage_rel).parent.mkdir(parents=True, exist_ok=True)
        (content_dir / storage_rel).write_text(
            "solid r\nfacet normal 0 0 1\nouter loop\n"
            "vertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\n"
            "endloop\nendfacet\nendsolid r\n"
        )
        s.add(
            ModelFile(
                id=stl_uuid,
                model_id=m.id,
                kind=ModelFileKind.stl,
                original_name="r.stl",
                storage_path=storage_rel,
                sha256="x",
                size_bytes=10,
                mime_type="model/stl",
            )
        )
        # Pre-seed an old auto-render
        old_uuid = uuid.uuid4()
        old_rel = f"models/{m.id}/files/{old_uuid}.png"
        (content_dir / old_rel).write_bytes(b"old-data")
        s.add(
            ModelFile(
                id=old_uuid,
                model_id=m.id,
                kind=ModelFileKind.image,
                original_name="iso-render.png",
                storage_path=old_rel,
                sha256="o",
                size_bytes=8,
                mime_type="image/png",
            )
        )
        s.commit()
        model_id = str(m.id)
        s.refresh(m)
        # Set thumbnail to the old auto-render
        m.thumbnail_file_id = old_uuid
        s.add(m)
        s.commit()

    redis = MagicMock()
    redis.set = AsyncMock(return_value=None)

    def fake_render_views(*, stl_paths, output_dir, size):
        from render.trimesh_render import VIEW_NAMES

        for view in VIEW_NAMES:
            (Path(output_dir) / f"{view}.png").write_bytes(f"new-data-{view}".encode())
        return {v: Path(output_dir) / f"{v}.png" for v in VIEW_NAMES}

    with patch("render.worker.render_views", fake_render_views):
        from render.worker import render_model

        ctx = {
            "redis": redis,
            "engine": engine,
            "content_dir": content_dir,
            "image_size": 256,
        }
        result = asyncio.run(render_model(ctx, model_id))

    assert result["status"] == "done"
    with Session(engine) as s:
        files = list(
            s.exec(
                select(ModelFile).where(ModelFile.kind == ModelFileKind.image)
            ).all()
        )
        # Old row gone, 4 new rows
        old_present = any(f.id == old_uuid for f in files)
        assert not old_present
        assert len(files) == 4
        m = s.exec(select(Model).where(Model.slug == "r")).one()
        # Thumbnail re-pointed to NEW iso
        new_iso = next(f for f in files if f.original_name == "iso-render.png")
        assert m.thumbnail_file_id == new_iso.id
    # Old PNG file removed from disk
    assert not (content_dir / old_rel).exists()


def _seed_two_stls(engine, content_dir, *, flags: tuple[bool, bool]):
    """Seed a model with two STL files; returns (model_id, file_a_id, file_b_id)."""
    from app.core.db.models import Category, Model, ModelFile, ModelFileKind

    valid_stl = (
        "solid t\nfacet normal 0 0 1\nouter loop\n"
        "vertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\n"
        "endloop\nendfacet\nendsolid t\n"
    )
    with Session(engine) as s:
        cat = Category(slug="x", name_en="x")
        s.add(cat)
        s.commit()
        s.refresh(cat)
        m = Model(slug="x", name_en="x", category_id=cat.id)
        s.add(m)
        s.commit()
        s.refresh(m)
        ids: list[uuid.UUID] = []
        for label, flag in zip(["a", "b"], flags, strict=True):
            stl_uuid = uuid.uuid4()
            rel = f"models/{m.id}/files/{stl_uuid}.stl"
            dst = content_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(valid_stl)
            s.add(
                ModelFile(
                    id=stl_uuid,
                    model_id=m.id,
                    kind=ModelFileKind.stl,
                    original_name=f"{label}.stl",
                    storage_path=rel,
                    sha256=f"x-{label}",
                    size_bytes=10,
                    mime_type="model/stl",
                    selected_for_render=flag,
                )
            )
            ids.append(stl_uuid)
        s.commit()
        return str(m.id), ids[0], ids[1]


def test_render_model_honors_selected_for_render(tmp_db_engine):
    """When selected_stl_file_ids is None the worker uses the persisted flag —
    the unselected STL must not feed into render_views."""
    engine, tmp_root = tmp_db_engine
    content_dir = tmp_root / "content"
    content_dir.mkdir()

    model_id, sel_id, unsel_id = _seed_two_stls(engine, content_dir, flags=(True, False))

    redis = MagicMock()
    redis.set = AsyncMock(return_value=None)
    captured: dict[str, list[Path]] = {}

    def fake_render_views(*, stl_paths, output_dir, size):
        captured["paths"] = list(stl_paths)
        from render.trimesh_render import VIEW_NAMES

        for view in VIEW_NAMES:
            (Path(output_dir) / f"{view}.png").write_bytes(f"fake-{view}".encode())
        return {v: Path(output_dir) / f"{v}.png" for v in VIEW_NAMES}

    with patch("render.worker.render_views", fake_render_views):
        from render.worker import render_model

        ctx = {"redis": redis, "engine": engine, "content_dir": content_dir, "image_size": 256}
        result = asyncio.run(render_model(ctx, model_id))

    assert result["status"] == "done"
    paths = captured["paths"]
    assert any(str(sel_id) in str(p) for p in paths), "selected STL must be rendered"
    assert not any(str(unsel_id) in str(p) for p in paths), "unselected STL must be skipped"


def test_render_model_falls_back_to_first_stl_when_none_selected(tmp_db_engine):
    """If admin cleared every flag, worker still renders the first STL alphabetically
    so a model with STL files never produces zero renders."""
    engine, tmp_root = tmp_db_engine
    content_dir = tmp_root / "content"
    content_dir.mkdir()

    model_id, a_id, b_id = _seed_two_stls(engine, content_dir, flags=(False, False))

    redis = MagicMock()
    redis.set = AsyncMock(return_value=None)
    captured: dict[str, list[Path]] = {}

    def fake_render_views(*, stl_paths, output_dir, size):
        captured["paths"] = list(stl_paths)
        from render.trimesh_render import VIEW_NAMES

        for view in VIEW_NAMES:
            (Path(output_dir) / f"{view}.png").write_bytes(f"fake-{view}".encode())
        return {v: Path(output_dir) / f"{v}.png" for v in VIEW_NAMES}

    with patch("render.worker.render_views", fake_render_views):
        from render.worker import render_model

        ctx = {"redis": redis, "engine": engine, "content_dir": content_dir, "image_size": 256}
        result = asyncio.run(render_model(ctx, model_id))

    assert result["status"] == "done"
    assert len(captured["paths"]) == 1, "fallback should render exactly one STL"
