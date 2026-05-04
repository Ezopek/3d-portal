"""Integration tests for scripts.migrate_from_index_json.

Each test gets its own isolated SQLite DB and temporary dst_root so they
don't interfere with each other or with the main test suite DB.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlmodel import Session, select

from app.core.db.models import (
    AuditLog,
    Category,
    ExternalSource,
    Model,
    ModelExternalLink,
    ModelFile,
    ModelFileKind,
    ModelNote,
    ModelPrint,
    ModelSource,
    NoteKind,
    Tag,
    User,
)
from app.core.db.session import create_engine_for_url, init_schema
from scripts.migrate_from_index_json import (
    MIGRATION_COMPLETE_FLAG,
    run,
    sha256_of_file,
    slugify,
)

# ---------------------------------------------------------------------------
# Paths to fixtures
# ---------------------------------------------------------------------------

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "migration"
INDEX_JSON = FIXTURE_DIR / "index.json"
SRC_ROOT = FIXTURE_DIR / "src"
SRC_3MF = FIXTURE_DIR / "3mf"


# ---------------------------------------------------------------------------
# Shared fixture builders
# ---------------------------------------------------------------------------


def _make_engine(tmp_path: Path):
    db = tmp_path / "test_migration.db"
    eng = create_engine_for_url(f"sqlite:///{db}")
    init_schema(eng)
    return eng


def _make_args(
    tmp_path: Path,
    *,
    dry_run: bool = False,
    force_rerun: bool = False,
    src_3mf: Path | None = SRC_3MF,
    dst_root: Path | None = None,
    report: Path | None = None,
) -> argparse.Namespace:
    if dst_root is None:
        dst_root = tmp_path / "dst"
        dst_root.mkdir(exist_ok=True)
    if report is None:
        report = tmp_path / "report.md"
    return argparse.Namespace(
        index=INDEX_JSON,
        src_root=SRC_ROOT,
        src_3mf=src_3mf,
        dst_root=dst_root,
        report=report,
        dry_run=dry_run,
        force_rerun=force_rerun,
    )


def _run_migration(tmp_path: Path, **kwargs) -> tuple[argparse.Namespace, object]:
    engine = _make_engine(tmp_path)
    args = _make_args(tmp_path, **kwargs)
    rc = run(args, engine=engine)
    return args, engine, rc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_happy_path(tmp_path):
    """Full migration: 2 models, correct field values, file count."""
    _args, engine, rc = _run_migration(tmp_path)
    assert rc == 0

    with Session(engine) as session:
        models = session.exec(select(Model)).all()
        assert len(models) == 2

        legacy_ids = {m.legacy_id for m in models}
        assert legacy_ids == {"001", "002"}

        dragon = session.exec(select(Model).where(Model.legacy_id == "001")).one()
        assert dragon.name_pl == "Smok przegubowy"
        assert dragon.name_en == "Articulated Dragon"

        holder = session.exec(select(Model).where(Model.legacy_id == "002")).one()
        assert holder.name_pl is None
        assert holder.name_en == "Holder"

        files = session.exec(select(ModelFile)).all()
        # dragon: dragon.stl, iso.png (image), original.3mf
        # holder: holder.stl, source.step, prints/first.jpg (print kind)
        assert len(files) >= 6


def test_idempotency(tmp_path):
    """Running migration twice yields same model count — no duplicates."""
    engine = _make_engine(tmp_path)
    args = _make_args(tmp_path)

    rc1 = run(args, engine=engine)
    assert rc1 == 0

    # Second run: flag exists, need force-rerun; reuse same dst
    args2 = _make_args(
        tmp_path,
        force_rerun=True,
        dst_root=args.dst_root,
        report=tmp_path / "report2.md",
    )

    rc2 = run(args2, engine=engine)
    assert rc2 == 0

    with Session(engine) as session:
        models = session.exec(select(Model)).all()
        assert len(models) == 2  # no duplicates


def test_tag_dedup(tmp_path):
    """Dragon tags [dragon, smok, articulated] → 2 distinct Tag rows."""
    _args, engine, rc = _run_migration(tmp_path)
    assert rc == 0

    with Session(engine) as session:
        # "smok" maps to "dragon" via PL_EN, so only "dragon" + "articulated" exist
        tags = session.exec(select(Tag)).all()
        tag_map = {t.slug: t for t in tags}

        assert "dragon" in tag_map
        assert "articulated" in tag_map
        # "smok" should NOT be a separate tag (it collapses into "dragon")
        assert "smok" not in tag_map
        # dragon tag should have name_pl set
        assert tag_map["dragon"].name_pl == "smok"


def test_sha256_consistency(tmp_path):
    """Every model_file.sha256 matches the on-disk file's hash."""
    args, engine, rc = _run_migration(tmp_path)
    assert rc == 0

    with Session(engine) as session:
        files = session.exec(select(ModelFile)).all()
        assert files  # sanity

        for mf in files:
            disk_path = args.dst_root / mf.storage_path
            assert disk_path.exists(), f"missing: {disk_path}"
            assert sha256_of_file(disk_path) == mf.sha256


def test_source_normalization(tmp_path):
    """Dragon → printables, Holder → unknown."""
    _args, engine, rc = _run_migration(tmp_path)
    assert rc == 0

    with Session(engine) as session:
        dragon = session.exec(select(Model).where(Model.legacy_id == "001")).one()
        holder = session.exec(select(Model).where(Model.legacy_id == "002")).one()

    assert dragon.source == ModelSource.printables
    assert holder.source == ModelSource.unknown


def test_dry_run_no_writes(tmp_path):
    """--dry-run mode inserts nothing into DB and copies no files."""
    args, engine, rc = _run_migration(tmp_path, dry_run=True)
    # dry-run always returns 0
    assert rc == 0

    with Session(engine) as session:
        models = session.exec(select(Model)).all()
        # Only the migration actor User may be created even in dry-run
        # (actually migration user is created before the loop, outside dry-run guard)
        # But no Model rows should exist
        assert len(models) == 0

        files = session.exec(select(ModelFile)).all()
        assert len(files) == 0

    # No files should be copied
    dst_files = list(args.dst_root.rglob("*"))
    # Only hidden test files are possible, but no model files
    model_files = [f for f in dst_files if f.is_file() and "models" in str(f)]
    assert model_files == []


def test_migration_complete_flag_blocks_rerun(tmp_path):
    """Existing flag file aborts a normal run."""
    engine = _make_engine(tmp_path)
    args = _make_args(tmp_path)

    rc1 = run(args, engine=engine)
    assert rc1 == 0
    flag = args.dst_root / MIGRATION_COMPLETE_FLAG
    assert flag.exists()

    # Second run without force-rerun should fail with rc=2
    args2 = _make_args(
        tmp_path,
        dst_root=args.dst_root,
        report=tmp_path / "report2.md",
    )
    rc2 = run(args2, engine=engine)
    assert rc2 == 2


def test_force_rerun_bypasses_flag(tmp_path):
    """--force-rerun allows migration even if flag exists."""
    engine = _make_engine(tmp_path)
    args = _make_args(tmp_path)
    rc1 = run(args, engine=engine)
    assert rc1 == 0

    args2 = _make_args(
        tmp_path,
        force_rerun=True,
        dst_root=args.dst_root,
        report=tmp_path / "report2.md",
    )
    rc2 = run(args2, engine=engine)
    assert rc2 == 0


def test_categories_created_with_hierarchy(tmp_path):
    """'decorations' is root; 'articulated-figures' is its child (slug is slugified)."""
    _args, engine, rc = _run_migration(tmp_path)
    assert rc == 0

    with Session(engine) as session:
        decorations = session.exec(select(Category).where(Category.slug == "decorations")).first()
        assert decorations is not None
        assert decorations.parent_id is None

        # "articulated_figures" → slugify → "articulated-figures"
        articulated = session.exec(
            select(Category).where(Category.slug == "articulated-figures")
        ).first()
        assert articulated is not None
        assert articulated.parent_id == decorations.id


def test_external_links_from_printables_id(tmp_path):
    """Dragon gets 1 external link: source=printables, id=12345."""
    _args, engine, rc = _run_migration(tmp_path)
    assert rc == 0

    with Session(engine) as session:
        dragon = session.exec(select(Model).where(Model.legacy_id == "001")).one()
        links = session.exec(
            select(ModelExternalLink).where(ModelExternalLink.model_id == dragon.id)
        ).all()

    assert len(links) == 1
    link = links[0]
    assert link.source == ExternalSource.printables
    assert link.external_id == "12345"
    assert "printables.com" in link.url


def test_notes_imported(tmp_path):
    """Dragon has 1 ModelNote with kind=description."""
    _args, engine, rc = _run_migration(tmp_path)
    assert rc == 0

    with Session(engine) as session:
        dragon = session.exec(select(Model).where(Model.legacy_id == "001")).one()
        notes = session.exec(select(ModelNote).where(ModelNote.model_id == dragon.id)).all()

    assert len(notes) == 1
    assert notes[0].kind == NoteKind.description
    assert notes[0].body == "great print"


def test_audit_log_entries_per_record(tmp_path):
    """At least 2 audit_log rows per model (1 model.create + N file uploads)."""
    _args, engine, rc = _run_migration(tmp_path)
    assert rc == 0

    with Session(engine) as session:
        # Migration user
        actor = session.exec(select(User).where(User.email == "migration@portal.local")).one()

        logs = session.exec(select(AuditLog).where(AuditLog.actor_user_id == actor.id)).all()

    # 2 models x (1 model.create + at least 1 file upload) = at least 4 rows
    assert len(logs) >= 4

    actions = {log.action for log in logs}
    assert "model.create" in actions
    assert "model_file.upload" in actions


def test_3mf_archive_imported(tmp_path):
    """Dragon has 1 ModelFile with kind=archive_3mf and name=original.3mf."""
    _args, engine, rc = _run_migration(tmp_path)
    assert rc == 0

    with Session(engine) as session:
        dragon = session.exec(select(Model).where(Model.legacy_id == "001")).one()
        tmf_files = session.exec(
            select(ModelFile).where(
                ModelFile.model_id == dragon.id,
                ModelFile.kind == ModelFileKind.archive_3mf,
            )
        ).all()

    assert len(tmf_files) == 1
    assert tmf_files[0].original_name == "original.3mf"


def test_prints_imported_even_when_photo_missing(tmp_path):
    """Dragon has 1 ModelPrint row, photo_file_id=None (missing.jpg absent)."""
    _args, engine, rc = _run_migration(tmp_path)
    assert rc == 0

    with Session(engine) as session:
        dragon = session.exec(select(Model).where(Model.legacy_id == "001")).one()
        prints = session.exec(select(ModelPrint).where(ModelPrint.model_id == dragon.id)).all()

    assert len(prints) == 1
    assert prints[0].photo_file_id is None
    assert prints[0].note == "first try"


def test_thumbnail_resolved(tmp_path):
    """Dragon.thumbnail_file_id points at the ModelFile for iso.png."""
    _args, engine, rc = _run_migration(tmp_path)
    assert rc == 0

    with Session(engine) as session:
        dragon = session.exec(select(Model).where(Model.legacy_id == "001")).one()
        assert dragon.thumbnail_file_id is not None

        thumb_file = session.exec(
            select(ModelFile).where(ModelFile.id == dragon.thumbnail_file_id)
        ).one()

    assert thumb_file.original_name == "iso.png"


# ---------------------------------------------------------------------------
# Unit-level helpers
# ---------------------------------------------------------------------------


def test_slugify_basic():
    assert slugify("Articulated Dragon") == "articulated-dragon"
    assert slugify("Hello World!") == "hello-world"
    assert slugify("--test--") == "test"
    assert slugify("some_thing_here") == "some-thing-here"
