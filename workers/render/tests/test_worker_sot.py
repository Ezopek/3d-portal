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

        files = list(s.exec(select(ModelFile).where(ModelFile.kind == ModelFileKind.image)).all())
        names = {f.original_name for f in files}
        assert names == {"iso-render.png", "front-render.png", "side-render.png", "top-render.png"}
        m = s.exec(select(Model).where(Model.slug == "t")).one()
        # Thumbnail set to iso
        iso = next(f for f in files if f.original_name == "iso-render.png")
        assert m.thumbnail_file_id == iso.id

    # Status flow: running then done
    redis.set.assert_any_await("render:status:" + model_id, b"running", ex=60 * 60)
    redis.set.assert_any_await("render:status:" + model_id, b"done", ex=60 * 60)


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
        files = list(s.exec(select(ModelFile).where(ModelFile.kind == ModelFileKind.image)).all())
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

    model_id, _a_id, _b_id = _seed_two_stls(engine, content_dir, flags=(False, False))

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


# ---------------------------------------------------------------------------
# Story 23.2 (TB-034) — STL preview source-tracking + lock release
# ---------------------------------------------------------------------------


def _seed_model_with_stl(engine, content_dir: Path, *, sha256: str) -> tuple[str, str]:
    """Seed (model, single STL) — returns (model_id_str, stl_file_id_str).

    The on-disk STL file is a minimal valid ASCII solid; the row's
    ``sha256`` column is whatever the caller supplied (lets the test
    control the sha8 suffix used by the worker's source-tracking).
    """
    from app.core.db.models import Category, Model, ModelFile, ModelFileKind

    valid_stl = (
        "solid t\nfacet normal 0 0 1\nouter loop\n"
        "vertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\n"
        "endloop\nendfacet\nendsolid t\n"
    )
    with Session(engine) as s:
        cat = Category(slug=f"sf-{uuid.uuid4().hex[:6]}", name_en="sf")
        s.add(cat)
        s.commit()
        s.refresh(cat)
        m = Model(slug=f"sf-{uuid.uuid4().hex[:6]}", name_en="sf", category_id=cat.id)
        s.add(m)
        s.commit()
        s.refresh(m)
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
                original_name="thing.stl",
                storage_path=rel,
                sha256=sha256,
                size_bytes=10,
                mime_type="model/stl",
            )
        )
        s.commit()
        return str(m.id), str(stl_uuid)


def _fake_render_views_factory(label: str = "fake"):
    """Return a (captured_paths, render_views_fn) tuple — render_views_fn
    writes 4 dummy PNGs into the supplied output_dir.

    ``label`` is folded into each PNG's bytes so callers exercising the
    same model across multiple render passes (e.g. STL-replace) produce
    DIFFERENT preview sha256s and don't trip the
    ``(model_id, sha256, kind)`` unique constraint on ``ModelFile``.
    Production renders inherently differ across STL geometries, so this
    is a test-fixture concern only.
    """
    captured: dict[str, list[Path]] = {}

    def fake_render_views(*, stl_paths, output_dir, size):
        captured["paths"] = list(stl_paths)
        from render.trimesh_render import VIEW_NAMES

        for view in VIEW_NAMES:
            (Path(output_dir) / f"{view}.png").write_bytes(f"{label}-{view}".encode())
        return {v: Path(output_dir) / f"{v}.png" for v in VIEW_NAMES}

    return captured, fake_render_views


def test_render_stl_previews_stamps_sha8_into_original_name(tmp_db_engine):
    """SOURCE-TRACK (AC1): the 4 new stl_preview rows MUST encode the
    source STL's sha8 in ``original_name`` (e.g. ``iso-aaaaaaaa.png``)
    so the dispatch + list queries can scope to the current geometry."""
    engine, tmp_root = tmp_db_engine
    content_dir = tmp_root / "content"
    content_dir.mkdir()

    sha256_a = "a" * 64
    _model_id, stl_id = _seed_model_with_stl(engine, content_dir, sha256=sha256_a)

    redis = MagicMock()
    redis.set = AsyncMock(return_value=None)
    redis.delete = AsyncMock(return_value=None)
    _captured, fake_render_views = _fake_render_views_factory()

    with patch("render.worker.render_views", fake_render_views):
        from render.worker import render_stl_previews

        ctx = {
            "redis": redis,
            "engine": engine,
            "content_dir": content_dir,
            "image_size": 256,
        }
        result = asyncio.run(render_stl_previews(ctx, stl_id))

    assert result["status"] == "done", result
    from app.core.db.models import ModelFile, ModelFileKind

    with Session(engine) as s:
        previews = list(
            s.exec(select(ModelFile).where(ModelFile.kind == ModelFileKind.stl_preview)).all()
        )
        names = sorted(p.original_name for p in previews)
        assert names == [
            "front-aaaaaaaa.png",
            "iso-aaaaaaaa.png",
            "side-aaaaaaaa.png",
            "top-aaaaaaaa.png",
        ], names

    # AC6 — lock release runs in ``finally`` on done path.
    redis.delete.assert_awaited_with(f"share:stl_preview_lock:{stl_id}")


def test_render_stl_previews_renders_new_set_after_stl_replace(tmp_db_engine):
    """SHA-MISMATCH (AC2 / AC8): when the source STL changes (operator
    swap → new sha256), the worker MUST render a fresh 4-view set even
    though 4 stl_preview rows for the prior geometry still exist. The
    idempotency count guard honors the sha8 LIKE filter so orphan rows
    do NOT mask the new render.

    Post-state: 4 OLD rows (sha8 = "aaaaaaaa") + 4 NEW rows
    (sha8 = "bbbbbbbb") = 8 stl_preview rows total in DB.
    """
    engine, tmp_root = tmp_db_engine
    content_dir = tmp_root / "content"
    content_dir.mkdir()

    sha256_a = "a" * 64  # sha8 == "aaaaaaaa"
    sha256_b = "b" * 64  # sha8 == "bbbbbbbb"
    model_id, stl_a_id = _seed_model_with_stl(engine, content_dir, sha256=sha256_a)

    redis = MagicMock()
    redis.set = AsyncMock(return_value=None)
    redis.delete = AsyncMock(return_value=None)
    _captured_old, fake_render_views_old = _fake_render_views_factory(label="old")

    # First render: populates 4 OLD previews stamped with sha8_a.
    with patch("render.worker.render_views", fake_render_views_old):
        from render.worker import render_stl_previews

        ctx = {
            "redis": redis,
            "engine": engine,
            "content_dir": content_dir,
            "image_size": 256,
        }
        first = asyncio.run(render_stl_previews(ctx, stl_a_id))
    assert first["status"] == "done", first

    # Replace the STL: delete the old row + insert a new one with sha256_b
    # under the same model. Mirrors the operator delete-and-reupload flow.
    from app.core.db.models import Model, ModelFile, ModelFileKind

    with Session(engine) as s:
        model = s.exec(select(Model).where(Model.id == uuid.UUID(model_id))).one()
        old_stl_row = s.exec(
            select(ModelFile)
            .where(ModelFile.model_id == model.id)
            .where(ModelFile.kind == ModelFileKind.stl)
        ).one()
        s.delete(old_stl_row)
        s.commit()

        new_stl_uuid = uuid.uuid4()
        rel = f"models/{model.id}/files/{new_stl_uuid}.stl"
        dst = content_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(
            "solid t\nfacet normal 0 0 1\nouter loop\n"
            "vertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\n"
            "endloop\nendfacet\nendsolid t\n"
        )
        s.add(
            ModelFile(
                id=new_stl_uuid,
                model_id=model.id,
                kind=ModelFileKind.stl,
                original_name="replacement.stl",
                storage_path=rel,
                sha256=sha256_b,
                size_bytes=10,
                mime_type="model/stl",
            )
        )
        s.commit()
        new_stl_id = str(new_stl_uuid)

    # Second render: 4 OLD previews exist but stamped with sha8_a, so the
    # sha8-filtered idempotency count for sha8_b is 0 → render proceeds.
    # Use a DIFFERENT label so the new previews' bytes hash to different
    # sha256s than the OLD ones (the ModelFile unique constraint covers
    # ``(model_id, sha256, kind)``).
    _captured_new, fake_render_views_new = _fake_render_views_factory(label="new")
    with patch("render.worker.render_views", fake_render_views_new):
        from render.worker import render_stl_previews

        ctx = {
            "redis": redis,
            "engine": engine,
            "content_dir": content_dir,
            "image_size": 256,
        }
        second = asyncio.run(render_stl_previews(ctx, new_stl_id))
    assert second["status"] == "done", second

    # Post-state: 4 OLD + 4 NEW = 8 stl_preview rows total in DB; the
    # share-list query (apps/api/app/modules/share/router.py) is what
    # filters them down to the CURRENT STL's 4 — covered in
    # apps/api/tests/test_stl_preview_single_flight.py::
    # test_share_list_filters_to_current_stl_sha8_only.
    with Session(engine) as s:
        all_previews = list(
            s.exec(select(ModelFile).where(ModelFile.kind == ModelFileKind.stl_preview)).all()
        )
        assert len(all_previews) == 8, [p.original_name for p in all_previews]
        old_names = sorted(p.original_name for p in all_previews if "aaaaaaaa" in p.original_name)
        new_names = sorted(p.original_name for p in all_previews if "bbbbbbbb" in p.original_name)
        assert len(old_names) == 4 and len(new_names) == 4, (old_names, new_names)


def test_render_stl_previews_skips_when_current_sha8_set_complete(tmp_db_engine):
    """SOURCE-TRACK-SKIP (AC2): when 4 previews already exist WITH the
    current sha8 stamp, the idempotency check skips render."""
    engine, tmp_root = tmp_db_engine
    content_dir = tmp_root / "content"
    content_dir.mkdir()

    sha256_a = "a" * 64
    _model_id, stl_id = _seed_model_with_stl(engine, content_dir, sha256=sha256_a)

    redis = MagicMock()
    redis.set = AsyncMock(return_value=None)
    redis.delete = AsyncMock(return_value=None)
    _captured, fake_render_views = _fake_render_views_factory()

    # First call populates 4 previews with sha8_a stamp.
    with patch("render.worker.render_views", fake_render_views):
        from render.worker import render_stl_previews

        ctx = {
            "redis": redis,
            "engine": engine,
            "content_dir": content_dir,
            "image_size": 256,
        }
        asyncio.run(render_stl_previews(ctx, stl_id))

    # Second call: completion gate triggers skip path.
    redis.delete.reset_mock()
    with patch("render.worker.render_views", fake_render_views):
        from render.worker import render_stl_previews

        result = asyncio.run(render_stl_previews(ctx, stl_id))
    assert result["status"] == "skipped", result
    # AC6 — lock release runs even on skip path (it's in ``finally``).
    redis.delete.assert_awaited_with(f"share:stl_preview_lock:{stl_id}")


def test_render_stl_previews_releases_lock_on_failure(tmp_db_engine):
    """LOCK-RELEASE-FAIL (AC6): the lock-delete in the ``finally`` block
    runs even when the worker fails (e.g. missing STL file on disk).
    """
    engine, tmp_root = tmp_db_engine
    content_dir = tmp_root / "content"
    content_dir.mkdir()

    sha256_a = "a" * 64
    _model_id, stl_id = _seed_model_with_stl(engine, content_dir, sha256=sha256_a)

    # Delete the on-disk STL so the worker hits the "STL missing on disk"
    # failure path. The DB row stays — the worker returns
    # ``{"status": "failed"}`` and the finally block MUST still delete
    # the lock key.
    from app.core.db.models import ModelFile, ModelFileKind

    with Session(engine) as s:
        row = s.exec(
            select(ModelFile)
            .where(ModelFile.id == uuid.UUID(stl_id))
            .where(ModelFile.kind == ModelFileKind.stl)
        ).one()
        (content_dir / row.storage_path).unlink()

    redis = MagicMock()
    redis.set = AsyncMock(return_value=None)
    redis.delete = AsyncMock(return_value=None)

    from render.worker import render_stl_previews

    ctx = {
        "redis": redis,
        "engine": engine,
        "content_dir": content_dir,
        "image_size": 256,
    }
    result = asyncio.run(render_stl_previews(ctx, stl_id))
    assert result["status"] == "failed", result
    redis.delete.assert_awaited_with(f"share:stl_preview_lock:{stl_id}")


# ---------------------------------------------------------------------------
# Story 23.2 round-2 (Codex P1) — legacy stl_preview row migration
# ---------------------------------------------------------------------------


def _compute_png_sha256(bytes_payload: bytes) -> str:
    import hashlib as _hashlib

    return _hashlib.sha256(bytes_payload).hexdigest()


@pytest.mark.parametrize(
    "collide",
    [
        pytest.param(False, id="distinct-sha256"),
        pytest.param(True, id="colliding-sha256"),
    ],
)
def test_render_stl_previews_purges_legacy_rows_before_render(tmp_db_engine, collide):
    """LEGACY-MIGRATION (Codex P1): pre-Story-23.2 ``stl_preview`` rows
    (named ``iso.png`` / ``front.png`` / ``side.png`` / ``top.png`` with
    no sha8 stamp) MUST be deleted — both DB row and on-disk file —
    before the sha8-stamped re-render runs.

    Two failure modes the purge protects against:

    1. ``(model_id, sha256, kind)`` unique constraint: identical PNG
       bytes (same STL geometry, deterministic renderer) → identical
       sha256 → INSERT collides → commit rolls back → share recipient
       gets zero previews + retries keep failing. Covered by the
       ``colliding-sha256`` parameter — legacy rows pre-seeded with the
       SAME sha256 the fake renderer will produce.
    2. Hidden previews: legacy rows survive in DB but are filtered out
       by the resolve_share sha8 LIKE filter → orphan rows linger,
       confusing operators and inflating storage. Covered by the
       ``distinct-sha256`` parameter.
    """
    engine, tmp_root = tmp_db_engine
    content_dir = tmp_root / "content"
    content_dir.mkdir()

    sha256_a = "a" * 64  # current STL sha8 == "aaaaaaaa"
    model_id_str, stl_id = _seed_model_with_stl(engine, content_dir, sha256=sha256_a)
    model_uuid = uuid.UUID(model_id_str)

    from app.core.db.models import ModelFile, ModelFileKind

    # In the ``colliding-sha256`` parameter, write the SAME PNG bytes
    # the fake renderer will produce ("collide-<view>") and compute the
    # matching sha256 — so the legacy rows occupy the
    # ``(model_id, sha256, kind=stl_preview)`` slot that the fresh
    # render WILL try to claim. Without the purge, the new INSERT
    # hits the unique constraint.
    legacy_files: list[Path] = []
    legacy_ids: list[uuid.UUID] = []
    label = "collide" if collide else "post-migration"
    with Session(engine) as s:
        for view in ("iso", "front", "side", "top"):
            legacy_uuid = uuid.uuid4()
            rel = f"models/{model_uuid}/stl_previews/{legacy_uuid}.png"
            dst = content_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            payload = f"{label}-{view}".encode()
            dst.write_bytes(payload)
            legacy_files.append(dst)
            row = ModelFile(
                id=legacy_uuid,
                model_id=model_uuid,
                kind=ModelFileKind.stl_preview,
                original_name=f"{view}.png",  # bare name, no sha8 — LEGACY
                storage_path=rel,
                sha256=(
                    _compute_png_sha256(payload)
                    if collide
                    else f"legacy-{view}-sha256-{legacy_uuid.hex}"
                ),
                size_bytes=len(payload),
                mime_type="image/png",
                position=None,
            )
            s.add(row)
            legacy_ids.append(legacy_uuid)
        s.commit()

    redis = MagicMock()
    redis.set = AsyncMock(return_value=None)
    redis.delete = AsyncMock(return_value=None)
    redis.eval = AsyncMock(return_value=1)
    _captured, fake_render_views = _fake_render_views_factory(label=label)

    with patch("render.worker.render_views", fake_render_views):
        from render.worker import render_stl_previews

        ctx = {
            "redis": redis,
            "engine": engine,
            "content_dir": content_dir,
            "image_size": 256,
        }
        result = asyncio.run(render_stl_previews(ctx, stl_id))
    assert result["status"] == "done", result

    # Assert: legacy DB rows deleted; legacy files unlinked; 4 new
    # sha8-stamped rows present.
    with Session(engine) as s:
        previews = list(
            s.exec(select(ModelFile).where(ModelFile.kind == ModelFileKind.stl_preview)).all()
        )
        names = sorted(p.original_name for p in previews)
        assert names == [
            "front-aaaaaaaa.png",
            "iso-aaaaaaaa.png",
            "side-aaaaaaaa.png",
            "top-aaaaaaaa.png",
        ], names
        for legacy_id in legacy_ids:
            assert not any(p.id == legacy_id for p in previews), (
                f"legacy row {legacy_id} survived purge"
            )
    for f in legacy_files:
        assert not f.exists(), f"legacy file {f} survived disk-unlink"


# ---------------------------------------------------------------------------
# Story 23.2 round-2 (Codex P2#2) — lock owner-token race
# ---------------------------------------------------------------------------


def test_render_stl_previews_lock_release_does_not_stomp_newer_token(tmp_db_engine):
    """LOCK-OWNER-TOKEN (Codex P2#2): worker's ``finally`` block MUST
    use Lua check-and-delete so a stale older worker (whose lock TTL
    expired and a NEWER dispatch has since acquired a fresh lock) does
    NOT stomp the newer lock on exit.

    Simulates the race:
      t0  request A enqueues job J_A, acquires lock with token "old"
      t1  job J_A sits in arq queue past 300s TTL → lock expires
      t2  request B enqueues job J_B, acquires fresh lock with token "new"
      t3  worker J_A finally runs → MUST NOT delete the "new" lock

    Uses ``fakeredis.aioredis`` so the EVAL semantics match Redis
    server behavior (script atomicity + ARGV/KEYS bindings).
    """
    import fakeredis.aioredis

    engine, tmp_root = tmp_db_engine
    content_dir = tmp_root / "content"
    content_dir.mkdir()

    sha256_a = "a" * 64
    _model_id, stl_id = _seed_model_with_stl(engine, content_dir, sha256=sha256_a)
    lock_key = f"share:stl_preview_lock:{stl_id}"

    _captured, fake_render_views = _fake_render_views_factory()

    async def scenario() -> tuple[dict[str, str], bytes | None]:
        # FakeRedis client + render call MUST share one event loop to
        # avoid "Queue bound to a different event loop" errors.
        fake_redis = fakeredis.aioredis.FakeRedis()
        await fake_redis.set(lock_key, "new", ex=300)
        with patch("render.worker.render_views", fake_render_views):
            from render.worker import render_stl_previews

            ctx = {
                "redis": fake_redis,
                "engine": engine,
                "content_dir": content_dir,
                "image_size": 256,
            }
            # Older worker invoked with the OLDER token. Its lock has long
            # since expired and a newer dispatch has installed "new".
            r = await render_stl_previews(ctx, stl_id, "old")
        survivor = await fake_redis.get(lock_key)
        return r, survivor

    result, surviving = asyncio.run(scenario())
    assert result["status"] == "done", result
    # The NEWER lock MUST survive — older worker's Lua EVAL only deletes
    # the key if its value still equals "old", which it doesn't.
    assert surviving == b"new", (
        f"older worker stomped the newer lock; got {surviving!r}, expected b'new'"
    )


def test_render_stl_previews_lock_release_clears_matching_token(tmp_db_engine):
    """LOCK-OWNER-TOKEN-HAPPY: when worker's token matches the stored
    lock value (no race), the Lua check-and-delete clears the key so a
    subsequent dispatcher can re-acquire immediately.
    """
    import fakeredis.aioredis

    engine, tmp_root = tmp_db_engine
    content_dir = tmp_root / "content"
    content_dir.mkdir()

    sha256_a = "a" * 64
    _model_id, stl_id = _seed_model_with_stl(engine, content_dir, sha256=sha256_a)
    lock_key = f"share:stl_preview_lock:{stl_id}"

    _captured, fake_render_views = _fake_render_views_factory()

    async def scenario() -> tuple[dict[str, str], bytes | None]:
        fake_redis = fakeredis.aioredis.FakeRedis()
        await fake_redis.set(lock_key, "mine", ex=300)
        with patch("render.worker.render_views", fake_render_views):
            from render.worker import render_stl_previews

            ctx = {
                "redis": fake_redis,
                "engine": engine,
                "content_dir": content_dir,
                "image_size": 256,
            }
            r = await render_stl_previews(ctx, stl_id, "mine")
        survivor = await fake_redis.get(lock_key)
        return r, survivor

    result, surviving = asyncio.run(scenario())
    assert result["status"] == "done", result
    assert surviving is None, "matching-token release should clear the lock"


def test_render_stl_previews_legacy_token_falls_back_to_unconditional_delete(tmp_db_engine):
    """LOCK-OWNER-TOKEN-BACKCOMPAT: when ``lock_token == ""`` (legacy
    invocation, no token to check), the worker falls back to
    unconditional delete to preserve pre-round-2 semantics. Protects
    any in-flight arq job that was enqueued before the round-2
    signature change rolled out.
    """
    import fakeredis.aioredis

    engine, tmp_root = tmp_db_engine
    content_dir = tmp_root / "content"
    content_dir.mkdir()

    sha256_a = "a" * 64
    _model_id, stl_id = _seed_model_with_stl(engine, content_dir, sha256=sha256_a)
    lock_key = f"share:stl_preview_lock:{stl_id}"

    _captured, fake_render_views = _fake_render_views_factory()

    async def scenario() -> tuple[dict[str, str], bytes | None]:
        fake_redis = fakeredis.aioredis.FakeRedis()
        await fake_redis.set(lock_key, "whatever", ex=300)
        with patch("render.worker.render_views", fake_render_views):
            from render.worker import render_stl_previews

            ctx = {
                "redis": fake_redis,
                "engine": engine,
                "content_dir": content_dir,
                "image_size": 256,
            }
            # No third positional arg → default "" → unconditional delete path.
            r = await render_stl_previews(ctx, stl_id)
        survivor = await fake_redis.get(lock_key)
        return r, survivor

    result, surviving = asyncio.run(scenario())
    assert result["status"] == "done", result
    assert surviving is None, "legacy-token path should unconditionally delete"
