"""Tests for ``scripts.backfill_legacy_renders``.

Each test runs against an isolated SQLite DB and a tmp content/renders dir so
it cannot interfere with the shared session DB or with sibling tests.
"""

from __future__ import annotations

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
from scripts.backfill_legacy_renders import backfill_legacy_renders


def _make_engine(tmp_path: Path):
    db = tmp_path / "test_backfill_renders.db"
    eng = create_engine_for_url(f"sqlite:///{db}")
    init_schema(eng)
    return eng


def _seed_category(session: Session, slug: str = "cat-lr") -> Category:
    c = Category(slug=slug, name_en=slug)
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


def _seed_model(
    session: Session,
    *,
    slug: str,
    category_id: uuid.UUID,
    legacy_id: str | None,
) -> Model:
    m = Model(
        slug=slug,
        name_en=slug,
        category_id=category_id,
        legacy_id=legacy_id,
    )
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


# A 1x1 transparent PNG; exact bytes are unimportant — what matters is that the
# script can hash and copy them.
_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xfc\xff\xff?\x00\x05\xfe\x02\xfe\xa3\x06\xc0\xb1"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _write_render(renders_dir: Path, legacy_id: str, name: str = "iso.png") -> Path:
    target_dir = renders_dir / legacy_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / name
    target.write_bytes(_PNG_BYTES)
    return target


def test_backfill_imports_render_and_sets_thumbnail(tmp_path):
    engine = _make_engine(tmp_path)
    renders_dir = tmp_path / "renders"
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    with Session(engine) as s:
        cat = _seed_category(s)
        m = _seed_model(s, slug="m-with-render", category_id=cat.id, legacy_id="001")
        model_id = m.id

    _write_render(renders_dir, "001")

    stats = backfill_legacy_renders(
        engine,
        renders_dir=renders_dir,
        content_dir=content_dir,
    )
    assert stats.imported == 1
    assert stats.skipped == 0
    assert stats.no_render_found == 0

    with Session(engine) as s:
        refreshed = s.exec(select(Model).where(Model.id == model_id)).one()
        files = list(s.exec(select(ModelFile).where(ModelFile.model_id == model_id)).all())
        assert len(files) == 1
        f = files[0]
        assert f.kind == ModelFileKind.image
        assert f.original_name == "iso-render.png"
        assert f.position is None
        assert f.size_bytes == len(_PNG_BYTES)
        # File was written under content_dir at the storage_path
        assert (content_dir / f.storage_path).is_file()
        # Thumbnail was set to the new file
        assert refreshed.thumbnail_file_id == f.id

        audits = list(
            s.exec(select(AuditLog).where(AuditLog.action == "model.legacy_render.import")).all()
        )
        assert len(audits) == 1
        audit = audits[0]
        assert audit.entity_type == "model"
        assert audit.entity_id == model_id
        assert json.loads(audit.before_json) == {"thumbnail_file_id": None}
        after = json.loads(audit.after_json)
        assert after["model_file_id"] == str(f.id)
        assert after["thumbnail_file_id"] == str(f.id)
        assert after["storage_path"] == f.storage_path


def test_backfill_skips_models_with_no_render_dir(tmp_path):
    engine = _make_engine(tmp_path)
    renders_dir = tmp_path / "renders"
    renders_dir.mkdir()
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    with Session(engine) as s:
        cat = _seed_category(s)
        m = _seed_model(s, slug="m-no-render", category_id=cat.id, legacy_id="missing")
        model_id = m.id

    stats = backfill_legacy_renders(
        engine,
        renders_dir=renders_dir,
        content_dir=content_dir,
    )
    assert stats.imported == 0
    assert stats.skipped == 0
    assert stats.no_render_found == 1

    with Session(engine) as s:
        refreshed = s.exec(select(Model).where(Model.id == model_id)).one()
        assert refreshed.thumbnail_file_id is None
        files = list(s.exec(select(ModelFile).where(ModelFile.model_id == model_id)).all())
        assert files == []
        audits = list(
            s.exec(select(AuditLog).where(AuditLog.action == "model.legacy_render.import")).all()
        )
        assert audits == []


def test_backfill_is_idempotent_on_rerun(tmp_path):
    engine = _make_engine(tmp_path)
    renders_dir = tmp_path / "renders"
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    with Session(engine) as s:
        cat = _seed_category(s)
        _seed_model(s, slug="m-idem", category_id=cat.id, legacy_id="001")

    _write_render(renders_dir, "001")

    first = backfill_legacy_renders(engine, renders_dir=renders_dir, content_dir=content_dir)
    assert first.imported == 1

    second = backfill_legacy_renders(engine, renders_dir=renders_dir, content_dir=content_dir)
    assert second.imported == 0
    assert second.skipped == 1
    assert second.no_render_found == 0

    with Session(engine) as s:
        files = list(s.exec(select(ModelFile)).all())
        # Still exactly one file row — no duplicate import.
        assert len(files) == 1
        audits = list(
            s.exec(select(AuditLog).where(AuditLog.action == "model.legacy_render.import")).all()
        )
        # Exactly one audit entry from the first run; the second run added none.
        assert len(audits) == 1


def test_backfill_dry_run_does_not_mutate(tmp_path):
    engine = _make_engine(tmp_path)
    renders_dir = tmp_path / "renders"
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    with Session(engine) as s:
        cat = _seed_category(s)
        m = _seed_model(s, slug="m-dry", category_id=cat.id, legacy_id="001")
        model_id = m.id

    _write_render(renders_dir, "001")

    stats = backfill_legacy_renders(
        engine, renders_dir=renders_dir, content_dir=content_dir, dry_run=True
    )
    assert stats.imported == 1

    with Session(engine) as s:
        refreshed = s.exec(select(Model).where(Model.id == model_id)).one()
        assert refreshed.thumbnail_file_id is None
        files = list(s.exec(select(ModelFile).where(ModelFile.model_id == model_id)).all())
        assert files == []
        audits = list(
            s.exec(select(AuditLog).where(AuditLog.action == "model.legacy_render.import")).all()
        )
        assert audits == []
    # No file copied to content dir
    assert list(content_dir.rglob("*.png")) == []
