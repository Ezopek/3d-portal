"""Tests for ``scripts.backfill_iso_thumbnail``."""

from __future__ import annotations

import uuid
from pathlib import Path

from sqlmodel import Session

from app.core.db.models import Category, Model, ModelFile, ModelFileKind
from app.core.db.session import create_engine_for_url, init_schema
from scripts.backfill_iso_thumbnail import run


def _engine(tmp_path: Path):
    eng = create_engine_for_url(f"sqlite:///{tmp_path / 'iso.db'}")
    init_schema(eng)
    return eng


def _seed(session: Session, *, slug: str) -> uuid.UUID:
    cat = Category(slug=f"c-{uuid.uuid4().hex[:6]}", name_en="c")
    session.add(cat)
    session.commit()
    session.refresh(cat)
    m = Model(slug=slug, name_en=slug, category_id=cat.id)
    session.add(m)
    session.commit()
    session.refresh(m)
    return m.id


def _add_file(session, model_id, name, kind=ModelFileKind.image) -> uuid.UUID:
    f = ModelFile(
        model_id=model_id,
        kind=kind,
        original_name=name,
        storage_path=f"models/{model_id}/files/{uuid.uuid4()}.png",
        sha256=uuid.uuid4().hex,
        size_bytes=1,
        mime_type="image/png",
    )
    session.add(f)
    session.commit()
    session.refresh(f)
    return f.id


def test_backfill_points_thumbnail_at_iso_when_only_renders(tmp_path):
    engine = _engine(tmp_path)
    with Session(engine) as s:
        mid = _seed(s, slug="renders-only")
        front_id = _add_file(s, mid, "front-render.png")
        iso_id = _add_file(s, mid, "iso-render.png")
        # Pretend the previous backfill picked front as thumbnail.
        m = s.get(Model, mid)
        m.thumbnail_file_id = front_id
        s.add(m)
        s.commit()

    stats = run(engine, dry_run=False)
    assert stats.updated == 1

    with Session(engine) as s:
        m = s.get(Model, mid)
        assert m.thumbnail_file_id == iso_id


def test_backfill_skips_models_with_user_photos(tmp_path):
    engine = _engine(tmp_path)
    with Session(engine) as s:
        mid = _seed(s, slug="has-photos")
        photo_id = _add_file(s, mid, "PXL_20260101.jpg")
        _add_file(s, mid, "iso-render.png")
        m = s.get(Model, mid)
        m.thumbnail_file_id = photo_id
        s.add(m)
        s.commit()

    stats = run(engine, dry_run=False)
    assert stats.has_user_photos == 1
    assert stats.updated == 0

    with Session(engine) as s:
        m = s.get(Model, mid)
        assert m.thumbnail_file_id == photo_id


def test_backfill_skips_when_iso_render_missing(tmp_path):
    engine = _engine(tmp_path)
    with Session(engine) as s:
        _seed(s, slug="no-iso")

    stats = run(engine, dry_run=False)
    assert stats.no_iso_render == 1
    assert stats.updated == 0


def test_backfill_idempotent_when_already_iso(tmp_path):
    engine = _engine(tmp_path)
    with Session(engine) as s:
        mid = _seed(s, slug="already-iso")
        iso_id = _add_file(s, mid, "iso-render.png")
        m = s.get(Model, mid)
        m.thumbnail_file_id = iso_id
        s.add(m)
        s.commit()

    stats = run(engine, dry_run=False)
    assert stats.already_iso == 1
    assert stats.updated == 0


def test_dry_run_does_not_mutate(tmp_path):
    engine = _engine(tmp_path)
    with Session(engine) as s:
        mid = _seed(s, slug="dry")
        front_id = _add_file(s, mid, "front-render.png")
        _add_file(s, mid, "iso-render.png")
        m = s.get(Model, mid)
        m.thumbnail_file_id = front_id
        s.add(m)
        s.commit()

    stats = run(engine, dry_run=True)
    assert stats.updated == 1
    with Session(engine) as s:
        m = s.get(Model, mid)
        assert m.thumbnail_file_id == front_id
