"""Tests for ``scripts.backfill_thumbnails``.

Each test runs against an isolated SQLite DB so it cannot interfere with the
shared session DB or with sibling tests.
"""

from __future__ import annotations

import datetime
import json
import uuid
from pathlib import Path

from sqlmodel import Session, select

from app.core.db.models import (
    AuditLog,
    Category,
    Model,
    ModelFile,
    ModelFileKind,
)
from app.core.db.session import create_engine_for_url, init_schema
from scripts.backfill_thumbnails import backfill_thumbnails


def _make_engine(tmp_path: Path):
    db = tmp_path / "test_backfill.db"
    eng = create_engine_for_url(f"sqlite:///{db}")
    init_schema(eng)
    return eng


def _seed_category(session: Session, slug: str = "cat-bf") -> Category:
    c = Category(slug=slug, name_en=slug)
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


def _seed_model(session: Session, *, slug: str, category_id: uuid.UUID) -> Model:
    m = Model(slug=slug, name_en=slug, category_id=category_id)
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


def _seed_file(
    session: Session,
    *,
    model_id: uuid.UUID,
    kind: ModelFileKind,
    name: str,
    sha: str,
    position: int | None = None,
    created_at: datetime.datetime | None = None,
) -> ModelFile:
    mf = ModelFile(
        model_id=model_id,
        kind=kind,
        original_name=name,
        storage_path=f"models/{model_id}/files/{name}-{sha[:8]}",
        sha256=sha,
        size_bytes=1,
        mime_type="application/octet-stream",
        position=position,
    )
    if created_at is not None:
        mf.created_at = created_at
    session.add(mf)
    session.commit()
    session.refresh(mf)
    return mf


def test_backfill_sets_thumbnail_to_earliest_image_or_print(tmp_path):
    engine = _make_engine(tmp_path)
    with Session(engine) as s:
        cat = _seed_category(s)
        m = _seed_model(s, slug="model-bf-1", category_id=cat.id)
        # Insert in deliberately scrambled order; the script must pick by
        # (position NULLS LAST, created_at) — i.e. position=0 wins.
        _seed_file(
            s,
            model_id=m.id,
            kind=ModelFileKind.image,
            name="late.png",
            sha="a" * 64,
            position=5,
            created_at=datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC),
        )
        first = _seed_file(
            s,
            model_id=m.id,
            kind=ModelFileKind.image,
            name="first.png",
            sha="b" * 64,
            position=0,
            created_at=datetime.datetime(2024, 1, 2, tzinfo=datetime.UTC),
        )
        # An STL must NOT be picked.
        _seed_file(
            s,
            model_id=m.id,
            kind=ModelFileKind.stl,
            name="part.stl",
            sha="c" * 64,
        )
        first_id = first.id
        model_id = m.id

    stats = backfill_thumbnails(engine)
    assert stats.backfilled == 1
    assert stats.already_set == 0
    assert stats.no_image == 0

    with Session(engine) as s:
        refreshed = s.exec(select(Model).where(Model.id == model_id)).one()
        assert refreshed.thumbnail_file_id == first_id

        audits = s.exec(select(AuditLog).where(AuditLog.action == "model.thumbnail.backfill")).all()
        assert len(audits) == 1
        audit = audits[0]
        assert audit.entity_type == "model"
        assert audit.entity_id == model_id
        assert json.loads(audit.before_json) == {"thumbnail_file_id": None}
        assert json.loads(audit.after_json) == {"thumbnail_file_id": str(first_id)}


def test_backfill_skips_models_that_already_have_thumbnail(tmp_path):
    engine = _make_engine(tmp_path)
    with Session(engine) as s:
        cat = _seed_category(s)
        m = _seed_model(s, slug="model-bf-already", category_id=cat.id)
        existing = _seed_file(
            s, model_id=m.id, kind=ModelFileKind.image, name="hero.png", sha="d" * 64
        )
        m.thumbnail_file_id = existing.id
        s.add(m)
        s.commit()
        # Add another candidate the script would otherwise pick.
        other = _seed_file(
            s,
            model_id=m.id,
            kind=ModelFileKind.image,
            name="other.png",
            sha="e" * 64,
            position=0,
        )
        existing_id = existing.id
        other_id = other.id
        model_id = m.id

    stats = backfill_thumbnails(engine)
    assert stats.backfilled == 0
    assert stats.already_set == 1
    assert stats.no_image == 0

    with Session(engine) as s:
        refreshed = s.exec(select(Model).where(Model.id == model_id)).one()
        assert refreshed.thumbnail_file_id == existing_id
        assert refreshed.thumbnail_file_id != other_id

        audits = s.exec(select(AuditLog).where(AuditLog.action == "model.thumbnail.backfill")).all()
        assert audits == []


def test_backfill_leaves_stl_only_models_untouched(tmp_path):
    engine = _make_engine(tmp_path)
    with Session(engine) as s:
        cat = _seed_category(s)
        m = _seed_model(s, slug="model-bf-stl-only", category_id=cat.id)
        _seed_file(s, model_id=m.id, kind=ModelFileKind.stl, name="part.stl", sha="f" * 64)
        _seed_file(
            s,
            model_id=m.id,
            kind=ModelFileKind.archive_3mf,
            name="bundle.3mf",
            sha="0" * 64,
        )
        model_id = m.id

    stats = backfill_thumbnails(engine)
    assert stats.backfilled == 0
    assert stats.already_set == 0
    assert stats.no_image == 1

    with Session(engine) as s:
        refreshed = s.exec(select(Model).where(Model.id == model_id)).one()
        assert refreshed.thumbnail_file_id is None
        audits = s.exec(select(AuditLog).where(AuditLog.action == "model.thumbnail.backfill")).all()
        assert audits == []


def test_backfill_dry_run_does_not_mutate(tmp_path):
    engine = _make_engine(tmp_path)
    with Session(engine) as s:
        cat = _seed_category(s)
        m = _seed_model(s, slug="model-bf-dry", category_id=cat.id)
        _seed_file(s, model_id=m.id, kind=ModelFileKind.image, name="x.png", sha="1" * 64)
        model_id = m.id

    stats = backfill_thumbnails(engine, dry_run=True)
    assert stats.backfilled == 1

    with Session(engine) as s:
        refreshed = s.exec(select(Model).where(Model.id == model_id)).one()
        assert refreshed.thumbnail_file_id is None
        audits = s.exec(select(AuditLog).where(AuditLog.action == "model.thumbnail.backfill")).all()
        assert audits == []
