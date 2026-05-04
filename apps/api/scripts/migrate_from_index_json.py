"""Idempotent migration script: import legacy file-based catalog into SoT entity tables.

Reads `_index/index.json`, walks the file system, and populates:
  Category, Tag, Model, ModelFile, ModelTag, ModelPrint,
  ModelExternalLink, ModelNote, AuditLog

Usage:
    python -m scripts.migrate_from_index_json \\
        --index    PATH \\
        --src-root PATH \\
        --src-3mf  PATH \\
        --dst-root PATH \\
        --report   PATH \\
        [--dry-run] \\
        [--force-rerun]
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import logging
import mimetypes
import os
import re
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.engine import Engine
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
    ModelStatus,
    ModelTag,
    NoteKind,
    Tag,
    User,
    UserRole,
)
from app.core.db.session import get_engine, init_schema
from scripts.tag_translations import PL_EN

logger = logging.getLogger(__name__)

MIGRATION_ACTOR_EMAIL = "migration@portal.local"
MIGRATION_COMPLETE_FLAG = "migration_complete.flag"

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
_SOURCE_EXTS = {".step", ".stp", ".obj", ".f3d", ".fcstd"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def slugify(s: str) -> str:
    """Lowercase, strip punctuation → dashes, collapse and strip dashes."""
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def sha256_of_file(path: Path, chunk: int = 65536) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def title_case_slug(slug: str) -> str:
    return " ".join(w.capitalize() for w in slug.replace("_", " ").split())


def normalize_source(s: str | None) -> ModelSource:
    if not s:
        return ModelSource.unknown
    s = s.lower().strip()
    if "printables" in s:
        return ModelSource.printables
    if "thangs" in s:
        return ModelSource.thangs
    if "makerworld" in s:
        return ModelSource.makerworld
    if "cults" in s:
        return ModelSource.cults3d
    if "thingiverse" in s:
        return ModelSource.thingiverse
    if s in {"own", "self"}:
        return ModelSource.own
    if s == "unknown":
        return ModelSource.unknown
    return ModelSource.other


def atomic_copy(src: Path, dst: Path) -> None:
    """Copy src → dst atomically via a .tmp sibling."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(f".tmp.{dst.name}")
    shutil.copyfile(src, tmp)
    # Flush to disk before rename
    with tmp.open("rb") as fh:
        os.fsync(fh.fileno())
    os.rename(tmp, dst)


def mime_for_path(p: Path) -> str:
    ext = p.suffix.lower()
    if ext == ".stl":
        return "model/stl"
    guessed, _ = mimetypes.guess_type(p.name)
    return guessed or "application/octet-stream"


def classify_file(path: Path) -> ModelFileKind | None:
    """Return file kind or None if the file should be skipped."""
    if path.name.startswith("."):
        return None
    ext = path.suffix.lower()
    parts_lower = {p.lower() for p in path.parts}
    if ext == ".stl":
        return ModelFileKind.stl
    if ext == ".3mf":
        return ModelFileKind.archive_3mf
    if ext in _SOURCE_EXTS:
        return ModelFileKind.source
    # 'prints' parent → print
    if any("prints" in p for p in parts_lower):
        return ModelFileKind.print
    # images dir or image ext → image
    if any("images" in p for p in parts_lower) or ext in _IMAGE_EXTS:
        return ModelFileKind.image
    return None


# ---------------------------------------------------------------------------
# DB helpers — all within an existing session
# ---------------------------------------------------------------------------


def get_or_create_category(
    session: Session,
    slug: str,
    name_en: str,
    parent_id: uuid.UUID | None = None,
) -> Category:
    stmt = select(Category).where(
        Category.slug == slug,
        Category.parent_id == parent_id,
    )
    existing = session.exec(stmt).first()
    if existing:
        return existing
    cat = Category(slug=slug, name_en=name_en, parent_id=parent_id)
    session.add(cat)
    session.flush()  # get id without full commit
    return cat


def get_or_create_tag(session: Session, slug_en: str, name_pl: str | None) -> Tag:
    existing = session.exec(select(Tag).where(Tag.slug == slug_en)).first()
    if existing:
        # Backfill name_pl if we now have it and didn't before
        if name_pl and existing.name_pl is None:
            existing.name_pl = name_pl
            session.add(existing)
            session.flush()
        return existing
    tag = Tag(slug=slug_en, name_en=slug_en, name_pl=name_pl)
    session.add(tag)
    session.flush()
    return tag


def get_or_create_migration_user(session: Session) -> User:
    existing = session.exec(select(User).where(User.email == MIGRATION_ACTOR_EMAIL)).first()
    if existing:
        return existing
    u = User(
        email=MIGRATION_ACTOR_EMAIL,
        display_name="Migration",
        role=UserRole.admin,
        password_hash="*",
    )
    session.add(u)
    session.flush()
    return u


def unique_slug_for_model(
    session: Session, name_en: str, legacy_id: str, seen_slugs: set[str]
) -> str:
    base = slugify(name_en)
    # check DB collision
    existing = session.exec(select(Model).where(Model.slug == base)).first()
    if existing is None and base not in seen_slugs:
        seen_slugs.add(base)
        return base
    # fallback: suffix with legacy_id
    candidate = f"{base}-{slugify(legacy_id)}"
    seen_slugs.add(candidate)
    return candidate


def make_audit(
    actor_id: uuid.UUID,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    after: dict[str, Any] | None,
    request_id: str,
) -> AuditLog:
    return AuditLog(
        actor_user_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        after_json=json.dumps(after) if after is not None else None,
        request_id=request_id,
    )


# ---------------------------------------------------------------------------
# Per-model import
# ---------------------------------------------------------------------------


class ModelStats:
    def __init__(self) -> None:
        self.imported: list[str] = []
        self.skipped: list[tuple[str, str]] = []  # (id, reason)
        self.file_counts: dict[str, int] = {}
        self.skipped_files: list[tuple[str, str]] = []  # (path, reason)
        self.tags_en_only = 0
        self.tags_en_pl = 0
        self.categories_created: set[str] = set()

    def inc_file(self, kind: str) -> None:
        self.file_counts[kind] = self.file_counts.get(kind, 0) + 1


def import_record(
    session: Session,
    record: dict[str, Any],
    src_root: Path,
    src_3mf: Path | None,
    dst_root: Path,
    actor_id: uuid.UUID,
    request_id: str,
    seen_slugs: set[str],
    stats: ModelStats,
    dry_run: bool,
) -> None:
    rid = str(record["id"])

    # Idempotency check
    existing = session.exec(select(Model).where(Model.legacy_id == rid)).first()
    if existing is not None:
        stats.skipped.append((rid, "already imported"))
        logger.info("skipped model %s: already imported", rid)
        return

    name_en: str = record["name_en"]
    name_pl: str | None = record.get("name_pl") or None

    # ---- Categories ----
    cat_slug = slugify(record["category"])
    cat_name_en = title_case_slug(cat_slug)
    root_cat = get_or_create_category(session, cat_slug, cat_name_en, parent_id=None)
    if root_cat.id not in {c for c in [root_cat.id]}:
        stats.categories_created.add(cat_slug)

    sub_slug = record.get("subcategory")
    if sub_slug:
        sub_slug = slugify(sub_slug)
        sub_name_en = title_case_slug(sub_slug)
        sub_cat = get_or_create_category(session, sub_slug, sub_name_en, parent_id=root_cat.id)
        category_id = sub_cat.id
    else:
        category_id = root_cat.id

    # ---- Tags ----
    tag_ids: list[uuid.UUID] = []
    for raw_tag in record.get("tags") or []:
        raw_tag = raw_tag.lower().strip()
        if not raw_tag:
            continue
        if raw_tag in PL_EN:
            canonical_en = PL_EN[raw_tag]
            pl_form: str | None = raw_tag
        else:
            canonical_en = raw_tag
            pl_form = None
        tag = get_or_create_tag(session, canonical_en, pl_form)
        if tag.id not in tag_ids:
            tag_ids.append(tag.id)
        if pl_form:
            stats.tags_en_pl += 1
        else:
            stats.tags_en_only += 1

    # ---- Slug ----
    model_slug = unique_slug_for_model(session, name_en, rid, seen_slugs)

    # ---- Model insert ----
    status_raw = record.get("status") or "not_printed"
    try:
        model_status = ModelStatus(status_raw)
    except ValueError:
        model_status = ModelStatus.not_printed

    rating_val: float | None = record.get("rating")
    if rating_val is not None:
        rating_val = float(rating_val)

    date_added_raw = record.get("date_added")
    if date_added_raw:
        date_added = datetime.date.fromisoformat(date_added_raw)
    else:
        date_added = datetime.datetime.now(datetime.UTC).date()

    model_id = uuid.uuid4()
    model = Model(
        id=model_id,
        legacy_id=rid,
        slug=model_slug,
        name_en=name_en,
        name_pl=name_pl,
        category_id=category_id,
        source=normalize_source(record.get("source")),
        status=model_status,
        rating=rating_val,
        date_added=date_added,
        thumbnail_file_id=None,
    )
    session.add(model)
    session.flush()  # ensure model.id is set

    # ---- ModelTag rows ----
    for tid in tag_ids:
        mt = ModelTag(model_id=model.id, tag_id=tid)
        session.add(mt)
    session.flush()

    # ---- Walk model directory ----
    model_src_dir = src_root / record["path"]
    imported_files: list[ModelFile] = []  # for audit

    if model_src_dir.is_dir():
        for file_path in sorted(model_src_dir.rglob("*")):
            if not file_path.is_file():
                continue
            if file_path.name.startswith("."):
                continue
            kind = classify_file(file_path)
            if kind is None:
                reason = f"unrecognized extension {file_path.suffix!r}"
                stats.skipped_files.append((str(file_path), reason))
                logger.info("skipping file %s: %s", file_path, reason)
                continue

            sha = sha256_of_file(file_path)

            # Check sha/kind dup
            dup = session.exec(
                select(ModelFile).where(
                    ModelFile.model_id == model.id,
                    ModelFile.sha256 == sha,
                    ModelFile.kind == kind,
                )
            ).first()
            if dup is not None:
                stats.skipped_files.append((str(file_path), "sha256+kind duplicate"))
                logger.info("skipping file %s: sha256+kind duplicate", file_path)
                continue

            file_id = uuid.uuid4()
            ext = file_path.suffix.lower()
            rel_storage = f"models/{model.id}/files/{file_id}{ext}"
            dst_file = dst_root / rel_storage

            if not dry_run:
                atomic_copy(file_path, dst_file)

            mf = ModelFile(
                id=file_id,
                model_id=model.id,
                kind=kind,
                original_name=file_path.name,
                storage_path=rel_storage,
                sha256=sha,
                size_bytes=file_path.stat().st_size,
                mime_type=mime_for_path(file_path),
            )
            session.add(mf)
            session.flush()
            imported_files.append(mf)
            stats.inc_file(kind.value)
    else:
        logger.warning("model directory not found: %s", model_src_dir)

    # ---- 3MF originals ----
    if src_3mf is not None and src_3mf.is_dir():
        tmf_dir = src_3mf / record["path"]
        if tmf_dir.is_dir():
            for file_path in sorted(tmf_dir.rglob("*.3mf")):
                if not file_path.is_file():
                    continue
                sha = sha256_of_file(file_path)
                dup = session.exec(
                    select(ModelFile).where(
                        ModelFile.model_id == model.id,
                        ModelFile.sha256 == sha,
                        ModelFile.kind == ModelFileKind.archive_3mf,
                    )
                ).first()
                if dup is not None:
                    stats.skipped_files.append((str(file_path), "sha256+kind duplicate (3mf)"))
                    continue

                file_id = uuid.uuid4()
                rel_storage = f"models/{model.id}/files/{file_id}.3mf"
                dst_file = dst_root / rel_storage

                if not dry_run:
                    atomic_copy(file_path, dst_file)

                mf = ModelFile(
                    id=file_id,
                    model_id=model.id,
                    kind=ModelFileKind.archive_3mf,
                    original_name=file_path.name,
                    storage_path=rel_storage,
                    sha256=sha,
                    size_bytes=file_path.stat().st_size,
                    mime_type="model/3mf",
                )
                session.add(mf)
                session.flush()
                imported_files.append(mf)
                stats.inc_file(ModelFileKind.archive_3mf.value)

    # ---- Thumbnail ----
    thumb_name = record.get("thumbnail")
    if thumb_name:
        thumb_name_lower = thumb_name.lower()
        # Find among all files just inserted for this model
        all_model_files = session.exec(
            select(ModelFile).where(ModelFile.model_id == model.id)
        ).all()
        for mf in all_model_files:
            if mf.original_name.lower() == thumb_name_lower:
                model.thumbnail_file_id = mf.id
                session.add(model)
                session.flush()
                break

    # ---- Prints ----
    all_model_files_map: dict[str, ModelFile] = {}
    all_model_files = session.exec(select(ModelFile).where(ModelFile.model_id == model.id)).all()
    for mf in all_model_files:
        all_model_files_map[mf.original_name.lower()] = mf

    for print_entry in record.get("prints") or []:
        photo_file_id: uuid.UUID | None = None
        photo_path = print_entry.get("path")
        if photo_path:
            photo_name_lower = Path(photo_path).name.lower()
            photo_mf = all_model_files_map.get(photo_name_lower)
            if photo_mf:
                photo_file_id = photo_mf.id
            else:
                logger.info("print photo not found: %s for model %s", photo_path, rid)

        printed_at: datetime.date | None = None
        date_str = print_entry.get("date")
        if date_str:
            try:
                printed_at = datetime.date.fromisoformat(date_str)
            except ValueError:
                logger.warning("invalid date in print entry: %s", date_str)

        note_body: str | None = None
        notes_en = print_entry.get("notes_en")
        notes_pl = print_entry.get("notes_pl")
        notes_generic = print_entry.get("notes")
        if notes_en:
            note_body = notes_en
        elif notes_generic:
            note_body = notes_generic
        elif notes_pl:
            note_body = f"[PL] {notes_pl}"

        mp = ModelPrint(
            model_id=model.id,
            photo_file_id=photo_file_id,
            printed_at=printed_at,
            note=note_body,
        )
        session.add(mp)
    session.flush()

    # ---- External links ----
    def _add_link(source: ExternalSource, ext_id: str | None, url: str) -> None:
        dup = session.exec(
            select(ModelExternalLink).where(
                ModelExternalLink.model_id == model.id,
                ModelExternalLink.source == source,
            )
        ).first()
        if dup is not None:
            return
        session.add(
            ModelExternalLink(
                model_id=model.id,
                source=source,
                external_id=ext_id,
                url=url,
            )
        )

    printables_id = record.get("printables_id")
    thangs_id = record.get("thangs_id")
    makerworld_id = record.get("makerworld_id")
    source_url = record.get("source_url")

    if printables_id:
        _add_link(
            ExternalSource.printables,
            str(printables_id),
            f"https://printables.com/model/{printables_id}",
        )
    if thangs_id:
        _add_link(
            ExternalSource.thangs,
            str(thangs_id),
            f"https://thangs.com/m/{thangs_id}",
        )
    if makerworld_id:
        _add_link(
            ExternalSource.makerworld,
            str(makerworld_id),
            f"https://makerworld.com/en/models/{makerworld_id}",
        )
    if source_url:
        _add_link(ExternalSource.other, None, source_url)
    session.flush()

    # ---- Notes ----
    notes_body = (record.get("notes") or "").strip()
    if notes_body:
        mn = ModelNote(
            model_id=model.id,
            kind=NoteKind.description,
            body=notes_body,
            author_id=actor_id,
        )
        session.add(mn)
        session.flush()

    # ---- Audit log ----
    session.add(
        make_audit(
            actor_id,
            "model.create",
            "model",
            model.id,
            {"legacy_id": rid, "name_en": name_en, "slug": model_slug},
            request_id,
        )
    )
    for mf in imported_files:
        session.add(
            make_audit(
                actor_id,
                "model_file.upload",
                "model",
                model.id,
                {
                    "kind": mf.kind.value,
                    "original_name": mf.original_name,
                    "sha256": mf.sha256[:16],
                },
                request_id,
            )
        )
    session.flush()

    stats.imported.append(rid)
    logger.info("imported model %s (%s)", rid, name_en)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def verify(engine: Engine, dst_root: Path, stats: ModelStats, expected_count: int) -> list[str]:
    """Post-migration verification. Returns list of error messages."""
    errors: list[str] = []

    with Session(engine) as session:
        models = session.exec(select(Model)).all()
        actual_count = len(models)
        if actual_count != expected_count:
            errors.append(f"model count mismatch: expected {expected_count}, got {actual_count}")

        # STL check
        for m in models:
            stl_files = session.exec(
                select(ModelFile).where(
                    ModelFile.model_id == m.id,
                    ModelFile.kind == ModelFileKind.stl,
                )
            ).all()
            if not stl_files:
                logger.warning("model %s (%s) has no STL file", m.legacy_id, m.name_en)

        # Orphan check
        orphans = session.exec(
            select(ModelFile).where(~ModelFile.model_id.in_(select(Model.id)))
        ).all()
        if orphans:
            errors.append(f"found {len(orphans)} orphaned model_file rows")

        # SHA256 spot check (up to 5)
        all_files = session.exec(select(ModelFile)).all()
        import random

        sample = random.sample(all_files, min(5, len(all_files)))
        for mf in sample:
            dst_file = dst_root / mf.storage_path
            if not dst_file.exists():
                errors.append(f"file missing on disk: {mf.storage_path}")
                continue
            actual_sha = sha256_of_file(dst_file)
            if actual_sha != mf.sha256:
                errors.append(
                    f"sha256 mismatch for {mf.storage_path}: "
                    f"db={mf.sha256[:16]} disk={actual_sha[:16]}"
                )

    return errors


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def build_report(
    stats: ModelStats,
    errors: list[str],
    duration_s: float,
    free_before: int,
    free_after: int,
    dry_run: bool,
    now: datetime.datetime,
) -> str:
    status = "dry-run" if dry_run else ("success" if not errors else "failed")
    lines: list[str] = [
        f"# Migration Report — {now.strftime('%Y-%m-%d')}",
        "",
        f"**Status:** {status}",
        f"**Duration:** {duration_s:.1f}s",
        f"**Timestamp:** {now.isoformat()}",
        "",
        "## Models",
        f"- Imported: {len(stats.imported)}",
        f"- Skipped: {len(stats.skipped)}",
        "",
    ]
    if stats.skipped:
        lines.append("### Skipped models")
        for sid, reason in stats.skipped:
            lines.append(f"- `{sid}`: {reason}")
        lines.append("")

    lines += [
        "## Files",
        f"- By kind: {stats.file_counts}",
        f"- Skipped: {len(stats.skipped_files)}",
        "",
    ]
    if stats.skipped_files:
        lines.append("### Skipped files")
        for fp, reason in stats.skipped_files[:20]:
            lines.append(f"- `{fp}`: {reason}")
        if len(stats.skipped_files) > 20:
            lines.append(f"  _(and {len(stats.skipped_files) - 20} more)_")
        lines.append("")

    lines += [
        "## Tags",
        f"- EN-only tags: {stats.tags_en_only}",
        f"- EN+PL aliased tags: {stats.tags_en_pl}",
        f"- PL_EN map size: {len(PL_EN)}",
        "",
        "## Categories created",
    ]
    for slug in sorted(stats.categories_created):
        lines.append(f"- `{slug}`")
    lines.append("")

    lines += [
        "## Storage",
        f"- Free space before: {free_before // (1024**2)} MiB",
        f"- Free space after: {free_after // (1024**2)} MiB",
        "",
    ]

    if errors:
        lines.append("## Errors")
        for err in errors:
            lines.append(f"- {err}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run(args: argparse.Namespace, *, engine: Engine | None = None) -> int:
    """Execute the migration. Returns exit code (0 = success)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    dry_run: bool = args.dry_run
    index_path: Path = Path(args.index)
    src_root: Path = Path(args.src_root)
    src_3mf_path: Path | None = Path(args.src_3mf) if args.src_3mf else None
    dst_root: Path = Path(args.dst_root)
    report_path: Path = Path(args.report)
    force_rerun: bool = getattr(args, "force_rerun", False)

    t_start = datetime.datetime.now(datetime.UTC)

    # ---- Pre-flight checks ----
    if engine is None:
        engine = get_engine()

    if not index_path.is_file():
        logger.error("index file not found: %s", index_path)
        return 2

    records: list[dict[str, Any]] = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        logger.error("index.json must be a JSON array")
        return 2

    if not src_root.is_dir():
        logger.error("src-root not found: %s", src_root)
        return 2

    if src_3mf_path and not src_3mf_path.is_dir():
        logger.info("src-3mf not found (%s) — 3MF originals will be skipped", src_3mf_path)
        src_3mf_path = None

    if not dst_root.is_dir():
        logger.error("dst-root not found: %s", dst_root)
        return 2

    # Try to write a test file to check writability
    test_write = dst_root / ".migration_write_test"
    try:
        test_write.write_bytes(b"")
        test_write.unlink()
    except OSError as exc:
        logger.error("dst-root not writable: %s", exc)
        return 2

    flag_path = dst_root / MIGRATION_COMPLETE_FLAG
    if flag_path.exists() and not force_rerun and not dry_run:
        logger.error("Migration complete flag found at %s. Use --force-rerun to re-run.", flag_path)
        return 2

    # ---- Init schema (idempotent, safe) ----
    init_schema(engine)

    # Free space before
    free_before = shutil.disk_usage(dst_root).free

    # ---- Migration actor ----
    stats = ModelStats()
    seen_slugs: set[str] = set()

    with Session(engine) as session:
        actor = get_or_create_migration_user(session)
        session.commit()
        session.refresh(actor)
        actor_id = actor.id

    ts_iso = t_start.isoformat()
    request_id = f"migration-batch-{ts_iso}"

    # ---- Per-model loop ----
    for record in records:
        try:
            with Session(engine) as session:
                import_record(
                    session=session,
                    record=record,
                    src_root=src_root,
                    src_3mf=src_3mf_path,
                    dst_root=dst_root,
                    actor_id=actor_id,
                    request_id=request_id,
                    seen_slugs=seen_slugs,
                    stats=stats,
                    dry_run=dry_run,
                )
                if not dry_run:
                    session.commit()
        except Exception:
            logger.exception("failed to import record %s", record.get("id"))
            stats.skipped.append((str(record.get("id", "?")), "exception during import"))

    # ---- Verification ----
    errors: list[str] = []
    if not dry_run:
        errors = verify(engine, dst_root, stats, len(records))
    else:
        logger.info("dry-run: skipping verification")

    # ---- Report ----
    free_after = shutil.disk_usage(dst_root).free
    t_end = datetime.datetime.now(datetime.UTC)
    duration = (t_end - t_start).total_seconds()

    report_text = build_report(
        stats=stats,
        errors=errors,
        duration_s=duration,
        free_before=free_before,
        free_after=free_after,
        dry_run=dry_run,
        now=t_end,
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    logger.info("Report written to %s", report_path)

    if not dry_run and not errors:
        flag_path.write_text(t_end.isoformat(), encoding="utf-8")
        logger.info("Migration complete. Flag written to %s", flag_path)

    return 0 if (dry_run or not errors) else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--index", type=Path, required=True, help="Path to index.json")
    p.add_argument("--src-root", type=Path, required=True, help="Source file tree root")
    p.add_argument("--src-3mf", type=Path, default=None, help="Optional 3MF originals root")
    p.add_argument("--dst-root", type=Path, required=True, help="Destination storage root")
    p.add_argument(
        "--report",
        type=Path,
        default=Path(f"docs/migration/report-{datetime.date.today()}.md"),
        help="Path for markdown report",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse + report; no DB writes or file copies",
    )
    p.add_argument(
        "--force-rerun",
        action="store_true",
        help="Run even if migration_complete.flag exists",
    )
    args = p.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
