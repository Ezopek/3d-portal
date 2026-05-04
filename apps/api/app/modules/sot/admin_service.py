"""Write-side service functions for Model admin operations.

Each function owns its own transaction (commit) and writes an audit_log
row inside the same tx for atomicity. Callers receive the mutated Model
row; they are responsible for building the full response via
`get_model_detail`.

Audit log entries are inserted as direct AuditLog rows (not via
`record_event`) so they share the same session/tx as the mutation.
"""

import datetime
import hashlib
import json
import mimetypes
import os
import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.db.models import (
    AuditLog,
    Category,
    Model,
    ModelExternalLink,
    ModelFile,
    ModelFileKind,
    ModelNote,
    ModelPrint,
    ModelTag,
    Tag,
)
from app.modules.sot.admin_schemas import (
    CategoryCreate,
    CategoryPatch,
    ExternalLinkCreate,
    ExternalLinkPatch,
    ModelCreate,
    ModelFilePatch,
    ModelPatch,
    NoteCreate,
    NotePatch,
    PrintCreate,
    PrintPatch,
    TagCreate,
    TagMerge,
    TagPatch,
    TagsReplace,
)

_MAX_FILE_BYTES = 500 * 1024 * 1024  # 500 MB

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    """Convert *text* to a URL-safe slug.

    Non-ASCII / punctuation chars are replaced by hyphens. If the result is
    empty (e.g. all CJK input) we fall back to ``model-<short_uuid>``.
    """
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    if not slug:
        slug = f"model-{uuid.uuid4().hex[:8]}"
    return slug


def _unique_slug(session: Session, base: str) -> str:
    """Return *base* if not taken, else ``base-<short_uuid>``."""
    existing = session.exec(select(Model.slug).where(Model.slug == base)).first()
    if existing is None:
        return base
    return f"{base}-{uuid.uuid4().hex[:8]}"


def _audit(
    session: Session,
    *,
    action: str,
    entity_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    session.add(
        AuditLog(
            action=action,
            entity_type="model",
            entity_id=entity_id,
            actor_user_id=actor_user_id,
            before_json=json.dumps(before, default=str) if before is not None else None,
            after_json=json.dumps(after, default=str) if after is not None else None,
        )
    )


def _audit_entity(
    session: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    """Generic audit helper that accepts explicit entity_type."""
    session.add(
        AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_user_id=actor_user_id,
            before_json=json.dumps(before, default=str) if before is not None else None,
            after_json=json.dumps(after, default=str) if after is not None else None,
        )
    )


def _model_snapshot(m: Model) -> dict:
    """Key fields for audit before/after snapshots."""
    return {
        "name_en": m.name_en,
        "name_pl": m.name_pl,
        "slug": m.slug,
        "legacy_id": m.legacy_id,
        "category_id": str(m.category_id),
        "source": str(m.source),
        "status": str(m.status),
        "rating": m.rating,
        "thumbnail_file_id": str(m.thumbnail_file_id) if m.thumbnail_file_id else None,
        "deleted_at": m.deleted_at.isoformat() if m.deleted_at else None,
    }


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


def create_model(
    session: Session,
    *,
    payload: ModelCreate,
    actor_user_id: uuid.UUID,
) -> Model:
    """Create a new Model row.

    Raises:
        ValueError("category not found") — category_id absent in DB.
        ValueError("slug_conflict") — provided slug already taken.
    """
    # Validate category
    cat = session.exec(select(Category).where(Category.id == payload.category_id)).first()
    if cat is None:
        raise ValueError("category not found")

    # Resolve slug
    if payload.slug is not None:
        slug = payload.slug
        collision = session.exec(select(Model.slug).where(Model.slug == slug)).first()
        if collision is not None:
            raise ValueError("slug_conflict")
    else:
        base = _slugify(payload.name_en)
        slug = _unique_slug(session, base)

    now = datetime.datetime.now(datetime.UTC)
    today = now.date()

    m = Model(
        slug=slug,
        name_en=payload.name_en,
        name_pl=payload.name_pl,
        category_id=payload.category_id,
        source=payload.source,
        status=payload.status,
        rating=payload.rating,
        date_added=today,
        created_at=now,
        updated_at=now,
    )
    session.add(m)
    session.flush()  # populate m.id

    _audit(
        session,
        action="model.create",
        entity_id=m.id,
        actor_user_id=actor_user_id,
        after=_model_snapshot(m),
    )

    session.commit()
    session.refresh(m)
    return m


def update_model(
    session: Session,
    *,
    model: Model,
    patch: ModelPatch,
    actor_user_id: uuid.UUID,
) -> Model:
    """Apply a partial update to *model*.

    Raises:
        ValueError("category not found") — category_id absent in DB.
        ValueError("slug_conflict") — new slug already taken by another model.
    """
    before = _model_snapshot(model)

    data = patch.model_dump(exclude_unset=True)

    if "category_id" in data and data["category_id"] is not None:
        cat = session.exec(select(Category).where(Category.id == data["category_id"])).first()
        if cat is None:
            raise ValueError("category not found")

    if "slug" in data and data["slug"] is not None:
        new_slug = data["slug"]
        collision = session.exec(
            select(Model.slug).where(Model.slug == new_slug, Model.id != model.id)
        ).first()
        if collision is not None:
            raise ValueError("slug_conflict")

    for field, value in data.items():
        setattr(model, field, value)

    model.updated_at = datetime.datetime.now(datetime.UTC)

    after = _model_snapshot(model)

    # Only record changed fields in audit
    changed_before = {k: v for k, v in before.items() if after.get(k) != v}
    changed_after = {k: after[k] for k in changed_before}

    session.add(model)
    session.flush()

    _audit(
        session,
        action="model.update",
        entity_id=model.id,
        actor_user_id=actor_user_id,
        before=changed_before if changed_before else before,
        after=changed_after if changed_after else after,
    )

    session.commit()
    session.refresh(model)
    return model


def restore_model(
    session: Session,
    *,
    model_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> Model:
    """Clear deleted_at on a model.

    404 if not found (regardless of deleted_at state — we use include_deleted
    on the lookup so we can restore soft-deleted models).
    Idempotent: already-active model returns 200.
    """
    m = session.exec(select(Model).where(Model.id == model_id)).first()
    if m is None:
        raise LookupError("model not found")

    before = {"deleted_at": m.deleted_at.isoformat() if m.deleted_at else None}
    m.deleted_at = None
    m.updated_at = datetime.datetime.now(datetime.UTC)
    session.add(m)
    session.flush()

    _audit(
        session,
        action="model.restore",
        entity_id=m.id,
        actor_user_id=actor_user_id,
        before=before,
        after={"deleted_at": None},
    )

    session.commit()
    session.refresh(m)
    return m


def soft_delete_model(
    session: Session,
    *,
    model_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> Model:
    """Set deleted_at = now().  404 if not found.  Idempotent."""
    m = session.exec(select(Model).where(Model.id == model_id)).first()
    if m is None:
        raise LookupError("model not found")

    before = {"deleted_at": m.deleted_at.isoformat() if m.deleted_at else None}
    now = datetime.datetime.now(datetime.UTC)
    if m.deleted_at is None:
        m.deleted_at = now
        m.updated_at = now
    after_ts = m.deleted_at.isoformat()

    session.add(m)
    session.flush()

    _audit(
        session,
        action="model.delete",
        entity_id=m.id,
        actor_user_id=actor_user_id,
        before=before,
        after={"deleted_at": after_ts},
    )

    session.commit()
    session.refresh(m)
    return m


def hard_delete_model(
    session: Session,
    *,
    model_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    content_dir: Path,
) -> None:
    """Permanently delete a model row and its related rows (DB cascade).

    Steps:
    1. Collect ModelFile storage_paths (needed before cascade removes rows).
    2. Write audit_log row with a full snapshot.
    3. Delete Model row (DB CASCADE removes model_file, model_tag,
       model_print, model_note, model_external_link rows).
    4. Commit.
    5. Remove binary files from disk.

    Worst case: if Python crashes between commit (step 4) and disk cleanup
    (step 5), files remain on disk but DB rows are gone. These orphans can
    be garbage-collected by a separate sweep script. This is acceptable for
    v1.
    """
    m = session.exec(select(Model).where(Model.id == model_id)).first()
    if m is None:
        raise LookupError("model not found")

    # Collect storage paths before cascade removes model_file rows
    files = session.exec(select(ModelFile).where(ModelFile.model_id == model_id)).all()
    storage_paths = [f.storage_path for f in files]

    # Count related rows for the snapshot
    from sqlmodel import func

    from app.core.db.models import ModelExternalLink, ModelNote, ModelPrint, ModelTag

    tag_count = session.exec(
        select(func.count()).select_from(
            select(ModelTag).where(ModelTag.model_id == model_id).subquery()
        )
    ).one()
    note_count = session.exec(
        select(func.count()).select_from(
            select(ModelNote).where(ModelNote.model_id == model_id).subquery()
        )
    ).one()
    print_count = session.exec(
        select(func.count()).select_from(
            select(ModelPrint).where(ModelPrint.model_id == model_id).subquery()
        )
    ).one()
    link_count = session.exec(
        select(func.count()).select_from(
            select(ModelExternalLink).where(ModelExternalLink.model_id == model_id).subquery()
        )
    ).one()

    snapshot = {
        **_model_snapshot(m),
        "file_count": len(storage_paths),
        "tag_count": tag_count,
        "note_count": note_count,
        "print_count": print_count,
        "link_count": link_count,
    }

    # Write audit log BEFORE cascade (entity_id still valid for forensics)
    _audit(
        session,
        action="model.hard_delete",
        entity_id=m.id,
        actor_user_id=actor_user_id,
        before=snapshot,
        after=None,
    )

    session.delete(m)
    session.commit()

    # Disk cleanup after successful commit — see docstring for failure mode
    base = content_dir.resolve()
    for sp in storage_paths:
        full = (base / sp).resolve()
        if full.is_file():
            full.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Internal helpers for model_file audit
# ---------------------------------------------------------------------------


def _audit_file(
    session: Session,
    *,
    action: str,
    entity_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    session.add(
        AuditLog(
            action=action,
            entity_type="model_file",
            entity_id=entity_id,
            actor_user_id=actor_user_id,
            before_json=json.dumps(before, default=str) if before is not None else None,
            after_json=json.dumps(after, default=str) if after is not None else None,
        )
    )


def _file_snapshot(f: ModelFile) -> dict:
    return {
        "kind": str(f.kind),
        "original_name": f.original_name,
        "sha256_prefix": f.sha256[:16],
        "size_bytes": f.size_bytes,
        "storage_path": f.storage_path,
    }


# ---------------------------------------------------------------------------
# Async helper for atomic file write
# ---------------------------------------------------------------------------


async def _write_atomic(
    upload: UploadFile,
    dst_dir: Path,
    file_uuid: uuid.UUID,
    ext: str,
) -> tuple[Path, Path, str, int]:
    """Stream *upload* to a tmp file, returning (tmp_path, final_path, sha256_hex, size_bytes).

    Raises HTTPException 413 if content exceeds _MAX_FILE_BYTES.
    """
    dst_dir.mkdir(parents=True, exist_ok=True)
    tmp = dst_dir / f".tmp.{file_uuid}{ext}"
    final = dst_dir / f"{file_uuid}{ext}"
    h = hashlib.sha256()
    size = 0
    with tmp.open("wb") as fp:
        while True:
            chunk = await upload.read(64 * 1024)
            if not chunk:
                break
            fp.write(chunk)
            h.update(chunk)
            size += len(chunk)
            if size > _MAX_FILE_BYTES:
                tmp.unlink(missing_ok=True)
                raise HTTPException(413, "File exceeds 500 MB")
        fp.flush()
        os.fsync(fp.fileno())
    return tmp, final, h.hexdigest(), size


# ---------------------------------------------------------------------------
# ModelFile service functions
# ---------------------------------------------------------------------------


async def upload_model_file(
    session: Session,
    *,
    model_id: uuid.UUID,
    kind: ModelFileKind,
    upload: UploadFile,
    actor_user_id: uuid.UUID,
    content_dir: Path,
) -> tuple[ModelFile, bool]:
    """Upload a binary file and create a ModelFile row.

    Returns (file_row, was_existing) where was_existing=True means the same
    content+kind already existed (sha256-based dedup) and the existing row
    was returned instead of creating a new one.

    Raises:
        HTTPException(404) — model not found or soft-deleted.
        HTTPException(413) — file exceeds 500 MB.
    """
    # Validate model exists and is not soft-deleted
    m = session.exec(select(Model).where(Model.id == model_id, Model.deleted_at.is_(None))).first()
    if m is None:
        raise HTTPException(404, "model not found")

    file_uuid = uuid.uuid4()

    # Sanitize extension
    original_name = upload.filename or "upload"
    raw_ext = Path(original_name).suffix.lower()
    # Keep only alphanumeric extensions
    ext = "." + "".join(c for c in raw_ext.lstrip(".") if c.isalnum()) if raw_ext else ""

    dst_dir = content_dir / "models" / str(model_id) / "files"
    tmp_path, final_path, sha256, size_bytes = await _write_atomic(upload, dst_dir, file_uuid, ext)

    # Derive mime type
    mime_type = mimetypes.guess_type(original_name)[0] or "application/octet-stream"
    if kind == ModelFileKind.stl:
        mime_type = "model/stl"

    dst_rel = f"models/{model_id}/files/{file_uuid}{ext}"

    file_row = ModelFile(
        model_id=model_id,
        kind=kind,
        original_name=original_name,
        storage_path=dst_rel,
        sha256=sha256,
        size_bytes=size_bytes,
        mime_type=mime_type,
    )

    try:
        session.add(file_row)
        session.flush()  # populate file_row.id before audit; may raise IntegrityError

        _audit_file(
            session,
            action="model_file.upload",
            entity_id=file_row.id,
            actor_user_id=actor_user_id,
            after={
                "kind": str(kind),
                "original_name": original_name,
                "sha256_prefix": sha256[:16],
                "size_bytes": size_bytes,
            },
        )

        session.commit()
    except IntegrityError:
        session.rollback()
        # Clean up the tmp file — no DB row was created
        tmp_path.unlink(missing_ok=True)
        # Look up the existing row by natural key
        existing = session.exec(
            select(ModelFile).where(
                ModelFile.model_id == model_id,
                ModelFile.sha256 == sha256,
                ModelFile.kind == kind,
            )
        ).first()
        if existing is None:
            # Shouldn't happen — some other integrity violation
            raise HTTPException(409, "file conflict: duplicate or constraint violation") from None
        return existing, True

    session.refresh(file_row)
    # Rename tmp → final (outside tx; orphan file on crash cleaned by GC sweep)
    tmp_path.rename(final_path)

    return file_row, False


def update_model_file(
    session: Session,
    *,
    model_id: uuid.UUID,
    file_id: uuid.UUID,
    patch: ModelFilePatch,
    actor_user_id: uuid.UUID,
) -> ModelFile:
    """Apply a partial update to a ModelFile row.

    Raises:
        LookupError("file not found") — file_id absent or belongs to different model.
        ValueError("kind_conflict") — changing kind would violate UNIQUE (model_id, sha256, kind).
    """
    f = session.exec(
        select(ModelFile).where(ModelFile.id == file_id, ModelFile.model_id == model_id)
    ).first()
    if f is None:
        raise LookupError("file not found")

    before = _file_snapshot(f)
    data = patch.model_dump(exclude_unset=True)

    if "kind" in data and data["kind"] is not None and data["kind"] != f.kind:
        # Check for UNIQUE collision before applying the change
        collision = session.exec(
            select(ModelFile).where(
                ModelFile.model_id == model_id,
                ModelFile.sha256 == f.sha256,
                ModelFile.kind == data["kind"],
                ModelFile.id != file_id,
            )
        ).first()
        if collision is not None:
            raise ValueError("kind_conflict")

    for field, value in data.items():
        setattr(f, field, value)

    after = _file_snapshot(f)
    changed_before = {k: v for k, v in before.items() if after.get(k) != v}
    changed_after = {k: after[k] for k in changed_before}

    session.add(f)
    session.flush()

    _audit_file(
        session,
        action="model_file.update",
        entity_id=f.id,
        actor_user_id=actor_user_id,
        before=changed_before if changed_before else before,
        after=changed_after if changed_after else after,
    )

    session.commit()
    session.refresh(f)
    return f


def delete_model_file(
    session: Session,
    *,
    model_id: uuid.UUID,
    file_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    content_dir: Path,
) -> None:
    """Delete a ModelFile row and its binary from disk.

    Ordering: read storage_path → audit → DELETE row → commit → unlink disk file.
    If unlink fails, the binary is an orphan (cleaned by GC sweep).

    Raises:
        LookupError("file not found") — file_id absent or belongs to different model.
    """
    f = session.exec(
        select(ModelFile).where(ModelFile.id == file_id, ModelFile.model_id == model_id)
    ).first()
    if f is None:
        raise LookupError("file not found")

    storage_path = f.storage_path
    snapshot = _file_snapshot(f)

    _audit_file(
        session,
        action="model_file.delete",
        entity_id=f.id,
        actor_user_id=actor_user_id,
        before=snapshot,
        after=None,
    )

    session.delete(f)
    session.commit()

    # Disk cleanup after commit — orphan on crash is acceptable (GC sweep)
    full_path = (content_dir / storage_path).resolve()
    if full_path.is_file():
        full_path.unlink(missing_ok=True)


def set_thumbnail(
    session: Session,
    *,
    model_id: uuid.UUID,
    file_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> Model:
    """Set thumbnail_file_id on a model.

    Raises:
        LookupError("model not found") — model absent or soft-deleted.
        ValueError("file not found") — ModelFile row absent.
        ValueError("file belongs to different model") — cross-model mismatch.
    """
    m = session.exec(select(Model).where(Model.id == model_id, Model.deleted_at.is_(None))).first()
    if m is None:
        raise LookupError("model not found")

    f = session.exec(select(ModelFile).where(ModelFile.id == file_id)).first()
    if f is None:
        raise ValueError("file not found")
    if f.model_id != model_id:
        raise ValueError("file belongs to different model")

    before = {"thumbnail_file_id": str(m.thumbnail_file_id) if m.thumbnail_file_id else None}
    m.thumbnail_file_id = file_id
    m.updated_at = datetime.datetime.now(datetime.UTC)
    session.add(m)
    session.flush()

    _audit(
        session,
        action="model.update",
        entity_id=m.id,
        actor_user_id=actor_user_id,
        before=before,
        after={"thumbnail_file_id": str(file_id)},
    )

    session.commit()
    session.refresh(m)
    return m


# ---------------------------------------------------------------------------
# Tags M2M helpers
# ---------------------------------------------------------------------------


def _get_model_active(session: Session, model_id: uuid.UUID) -> Model:
    """Return active Model or raise LookupError."""
    m = session.exec(select(Model).where(Model.id == model_id, Model.deleted_at.is_(None))).first()
    if m is None:
        raise LookupError("model not found")
    return m


def _model_tag_ids(session: Session, model_id: uuid.UUID) -> list[uuid.UUID]:
    rows = session.exec(select(ModelTag).where(ModelTag.model_id == model_id)).all()
    return [r.tag_id for r in rows]


# ---------------------------------------------------------------------------
# Tags M2M
# ---------------------------------------------------------------------------


def replace_model_tags(
    session: Session,
    *,
    model_id: uuid.UUID,
    payload: TagsReplace,
    actor_user_id: uuid.UUID,
) -> list[Tag]:
    """Replace ALL tags for model with the provided set.

    Raises:
        LookupError("model not found") — model absent or soft-deleted.
        ValueError("tag not found: <id>") — any tag_id absent in DB.
    """
    _get_model_active(session, model_id)

    # Validate all tag ids exist
    for tid in payload.tag_ids:
        if session.get(Tag, tid) is None:
            raise ValueError(f"tag not found: {tid}")

    before_ids = _model_tag_ids(session, model_id)

    # Remove all existing
    existing_rows = session.exec(select(ModelTag).where(ModelTag.model_id == model_id)).all()
    for row in existing_rows:
        session.delete(row)
    session.flush()

    # Add new set
    for tid in payload.tag_ids:
        session.add(ModelTag(model_id=model_id, tag_id=tid))
    session.flush()

    after_ids = list(payload.tag_ids)

    _audit_entity(
        session,
        action="model.update",
        entity_type="model",
        entity_id=model_id,
        actor_user_id=actor_user_id,
        before={"tag_ids": [str(t) for t in before_ids]},
        after={"tag_ids": [str(t) for t in after_ids]},
    )

    session.commit()

    tags = (
        session.exec(select(Tag).where(Tag.id.in_(after_ids))).all()  # type: ignore[arg-type]
        if after_ids
        else []
    )
    return list(tags)


def add_model_tag(
    session: Session,
    *,
    model_id: uuid.UUID,
    tag_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> list[Tag]:
    """Add one tag to model. Idempotent — 200 if already attached.

    Raises:
        LookupError("model not found") — model absent or soft-deleted.
        LookupError("tag not found") — tag absent in DB.
    """
    _get_model_active(session, model_id)

    if session.get(Tag, tag_id) is None:
        raise LookupError("tag not found")

    existing = session.exec(
        select(ModelTag).where(ModelTag.model_id == model_id, ModelTag.tag_id == tag_id)
    ).first()

    if existing is None:
        session.add(ModelTag(model_id=model_id, tag_id=tag_id))
        session.flush()

        _audit_entity(
            session,
            action="model_tag.add",
            entity_type="model",
            entity_id=model_id,
            actor_user_id=actor_user_id,
            after={"added_tag_id": str(tag_id)},
        )
        session.commit()

    tag_ids = _model_tag_ids(session, model_id)
    if tag_ids:
        return list(session.exec(select(Tag).where(Tag.id.in_(tag_ids))).all())  # type: ignore[arg-type]
    return []


def remove_model_tag(
    session: Session,
    *,
    model_id: uuid.UUID,
    tag_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> None:
    """Remove one tag from model. Idempotent — 204 even if not attached.

    Raises:
        LookupError("model not found") — model absent or soft-deleted.
    """
    _get_model_active(session, model_id)

    row = session.exec(
        select(ModelTag).where(ModelTag.model_id == model_id, ModelTag.tag_id == tag_id)
    ).first()

    if row is not None:
        session.delete(row)
        session.flush()

        _audit_entity(
            session,
            action="model_tag.remove",
            entity_type="model",
            entity_id=model_id,
            actor_user_id=actor_user_id,
            after={"removed_tag_id": str(tag_id)},
        )
        session.commit()


# ---------------------------------------------------------------------------
# Tags global
# ---------------------------------------------------------------------------


def create_tag(
    session: Session,
    *,
    payload: TagCreate,
    actor_user_id: uuid.UUID,
) -> Tag:
    """Create a new global Tag.

    Raises:
        ValueError("slug_conflict") — slug already in use.
    """
    collision = session.exec(select(Tag).where(Tag.slug == payload.slug)).first()
    if collision is not None:
        raise ValueError("slug_conflict")

    now = datetime.datetime.now(datetime.UTC)
    tag = Tag(
        slug=payload.slug,
        name_en=payload.name_en,
        name_pl=payload.name_pl,
        created_at=now,
        updated_at=now,
    )
    session.add(tag)
    session.flush()

    _audit_entity(
        session,
        action="tag.create",
        entity_type="tag",
        entity_id=tag.id,
        actor_user_id=actor_user_id,
        after={"slug": tag.slug, "name_en": tag.name_en, "name_pl": tag.name_pl},
    )

    session.commit()
    session.refresh(tag)
    return tag


def update_tag(
    session: Session,
    *,
    tag_id: uuid.UUID,
    patch: TagPatch,
    actor_user_id: uuid.UUID,
) -> Tag:
    """Partially update a global Tag.

    Raises:
        LookupError("tag not found")
        ValueError("slug_conflict")
    """
    tag = session.get(Tag, tag_id)
    if tag is None:
        raise LookupError("tag not found")

    before = {"slug": tag.slug, "name_en": tag.name_en, "name_pl": tag.name_pl}
    data = patch.model_dump(exclude_unset=True)

    if "slug" in data and data["slug"] is not None and data["slug"] != tag.slug:
        collision = session.exec(
            select(Tag).where(Tag.slug == data["slug"], Tag.id != tag_id)
        ).first()
        if collision is not None:
            raise ValueError("slug_conflict")

    for field, value in data.items():
        setattr(tag, field, value)

    tag.updated_at = datetime.datetime.now(datetime.UTC)
    after = {"slug": tag.slug, "name_en": tag.name_en, "name_pl": tag.name_pl}

    session.add(tag)
    session.flush()

    _audit_entity(
        session,
        action="tag.update",
        entity_type="tag",
        entity_id=tag.id,
        actor_user_id=actor_user_id,
        before=before,
        after=after,
    )

    session.commit()
    session.refresh(tag)
    return tag


def delete_tag(
    session: Session,
    *,
    tag_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> None:
    """Delete a global Tag. RESTRICT: 409 if any ModelTag references this tag.

    Raises:
        LookupError("tag not found")
        ValueError("tag_in_use")
    """
    tag = session.get(Tag, tag_id)
    if tag is None:
        raise LookupError("tag not found")

    before = {"slug": tag.slug, "name_en": tag.name_en}

    _audit_entity(
        session,
        action="tag.delete",
        entity_type="tag",
        entity_id=tag.id,
        actor_user_id=actor_user_id,
        before=before,
    )

    try:
        session.delete(tag)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ValueError("tag_in_use") from exc


def merge_tags(
    session: Session,
    *,
    payload: TagMerge,
    actor_user_id: uuid.UUID,
) -> Tag:
    """Merge from_id into to_id. Rewires ModelTag rows; deletes from-tag.

    Handles duplicate ModelTag collisions at the merge boundary.

    Raises:
        LookupError("from tag not found")
        LookupError("to tag not found")
    """
    from_tag = session.get(Tag, payload.from_id)
    if from_tag is None:
        raise LookupError("from tag not found")

    to_tag = session.get(Tag, payload.to_id)
    if to_tag is None:
        raise LookupError("to tag not found")

    # Find all model_tag rows referencing from_tag
    from_rows = session.exec(
        select(ModelTag).where(ModelTag.tag_id == payload.from_id)
    ).all()

    rewired = 0
    for row in from_rows:
        # Check if model already has to_tag — if so, just delete the from row
        to_exists = session.exec(
            select(ModelTag).where(
                ModelTag.model_id == row.model_id,
                ModelTag.tag_id == payload.to_id,
            )
        ).first()
        if to_exists is not None:
            session.delete(row)
        else:
            session.delete(row)
            session.flush()
            session.add(ModelTag(model_id=row.model_id, tag_id=payload.to_id))
            rewired += 1
    session.flush()

    # Delete the from-tag
    session.delete(from_tag)
    session.flush()

    _audit_entity(
        session,
        action="tag.merge",
        entity_type="tag",
        entity_id=payload.to_id,
        actor_user_id=actor_user_id,
        after={"merged_from": str(payload.from_id), "rewired_models": rewired},
    )

    session.commit()
    session.refresh(to_tag)
    return to_tag


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


def _would_cycle(session: Session, category_id: uuid.UUID, new_parent_id: uuid.UUID | None) -> bool:
    if new_parent_id is None:
        return False
    if new_parent_id == category_id:
        return True
    visited: set[uuid.UUID] = {category_id}
    cur: uuid.UUID | None = new_parent_id
    while cur is not None:
        if cur in visited:
            return True
        visited.add(cur)
        parent = session.exec(
            select(Category.parent_id).where(Category.id == cur)
        ).first()
        cur = parent
    return False


def create_category(
    session: Session,
    *,
    payload: CategoryCreate,
    actor_user_id: uuid.UUID,
) -> Category:
    """Create a new Category.

    Raises:
        ValueError("parent not found") — parent_id given but absent.
        ValueError("slug_conflict") — (parent_id, slug) collision.
    """
    if payload.parent_id is not None and session.get(Category, payload.parent_id) is None:
        raise ValueError("parent not found")

    now = datetime.datetime.now(datetime.UTC)
    cat = Category(
        parent_id=payload.parent_id,
        slug=payload.slug,
        name_en=payload.name_en,
        name_pl=payload.name_pl,
        created_at=now,
        updated_at=now,
    )
    session.add(cat)

    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise ValueError("slug_conflict") from exc

    _audit_entity(
        session,
        action="category.create",
        entity_type="category",
        entity_id=cat.id,
        actor_user_id=actor_user_id,
        after={
            "parent_id": str(cat.parent_id) if cat.parent_id else None,
            "slug": cat.slug,
            "name_en": cat.name_en,
        },
    )

    session.commit()
    session.refresh(cat)
    return cat


def update_category(
    session: Session,
    *,
    category_id: uuid.UUID,
    patch: CategoryPatch,
    actor_user_id: uuid.UUID,
) -> Category:
    """Partially update a Category.

    Raises:
        LookupError("category not found")
        ValueError("parent not found") — new parent_id absent.
        ValueError("cycle") — new parent_id would create a cycle.
        ValueError("slug_conflict")
    """
    cat = session.get(Category, category_id)
    if cat is None:
        raise LookupError("category not found")

    before = {
        "parent_id": str(cat.parent_id) if cat.parent_id else None,
        "slug": cat.slug,
        "name_en": cat.name_en,
        "name_pl": cat.name_pl,
    }

    data = patch.model_dump(exclude_unset=True)

    # Only check parent_id if it was explicitly provided in the payload
    if "parent_id" in data:
        new_parent_id = data["parent_id"]
        if new_parent_id is not None:
            if session.get(Category, new_parent_id) is None:
                raise ValueError("parent not found")
            if _would_cycle(session, category_id, new_parent_id):
                raise ValueError("cycle")
        cat.parent_id = new_parent_id

    for field, value in data.items():
        if field == "parent_id":
            continue  # already handled
        setattr(cat, field, value)

    cat.updated_at = datetime.datetime.now(datetime.UTC)
    after = {
        "parent_id": str(cat.parent_id) if cat.parent_id else None,
        "slug": cat.slug,
        "name_en": cat.name_en,
        "name_pl": cat.name_pl,
    }

    session.add(cat)

    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise ValueError("slug_conflict") from exc

    _audit_entity(
        session,
        action="category.update",
        entity_type="category",
        entity_id=cat.id,
        actor_user_id=actor_user_id,
        before=before,
        after=after,
    )

    session.commit()
    session.refresh(cat)
    return cat


def delete_category(
    session: Session,
    *,
    category_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> None:
    """Delete a Category. RESTRICT if models or child categories reference it.

    Raises:
        LookupError("category not found")
        ValueError("category_in_use")
    """
    cat = session.get(Category, category_id)
    if cat is None:
        raise LookupError("category not found")

    before = {"slug": cat.slug, "name_en": cat.name_en}

    _audit_entity(
        session,
        action="category.delete",
        entity_type="category",
        entity_id=cat.id,
        actor_user_id=actor_user_id,
        before=before,
    )

    try:
        session.delete(cat)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ValueError("category_in_use") from exc


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


def create_note(
    session: Session,
    *,
    model_id: uuid.UUID,
    payload: NoteCreate,
    actor_user_id: uuid.UUID,
) -> ModelNote:
    """Create a ModelNote. author_id set to actor_user_id.

    Raises:
        LookupError("model not found")
    """
    _get_model_active(session, model_id)

    now = datetime.datetime.now(datetime.UTC)
    note = ModelNote(
        model_id=model_id,
        kind=payload.kind,
        body=payload.body,
        author_id=actor_user_id,
        created_at=now,
        updated_at=now,
    )
    session.add(note)
    session.flush()

    _audit_entity(
        session,
        action="model_note.create",
        entity_type="model_note",
        entity_id=note.id,
        actor_user_id=actor_user_id,
        after={"model_id": str(model_id), "kind": str(payload.kind)},
    )

    session.commit()
    session.refresh(note)
    return note


def update_note(
    session: Session,
    *,
    note_id: uuid.UUID,
    patch: NotePatch,
    actor_user_id: uuid.UUID,
) -> ModelNote:
    """Partially update a ModelNote.

    Raises:
        LookupError("note not found")
    """
    note = session.get(ModelNote, note_id)
    if note is None:
        raise LookupError("note not found")

    before = {"kind": str(note.kind), "body": note.body}
    data = patch.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(note, field, value)

    note.updated_at = datetime.datetime.now(datetime.UTC)
    after = {"kind": str(note.kind), "body": note.body}

    session.add(note)
    session.flush()

    _audit_entity(
        session,
        action="model_note.update",
        entity_type="model_note",
        entity_id=note.id,
        actor_user_id=actor_user_id,
        before=before,
        after=after,
    )

    session.commit()
    session.refresh(note)
    return note


def delete_note(
    session: Session,
    *,
    note_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> None:
    """Delete a ModelNote.

    Raises:
        LookupError("note not found")
    """
    note = session.get(ModelNote, note_id)
    if note is None:
        raise LookupError("note not found")

    before = {"model_id": str(note.model_id), "kind": str(note.kind)}

    _audit_entity(
        session,
        action="model_note.delete",
        entity_type="model_note",
        entity_id=note.id,
        actor_user_id=actor_user_id,
        before=before,
    )

    session.delete(note)
    session.commit()


# ---------------------------------------------------------------------------
# Prints
# ---------------------------------------------------------------------------


def create_print(
    session: Session,
    *,
    model_id: uuid.UUID,
    payload: PrintCreate,
    actor_user_id: uuid.UUID,
) -> ModelPrint:
    """Create a ModelPrint.

    Raises:
        LookupError("model not found")
        ValueError("photo_file cross-model") — photo_file_id belongs to different model.
    """
    _get_model_active(session, model_id)

    if payload.photo_file_id is not None:
        pf = session.get(ModelFile, payload.photo_file_id)
        if pf is None or pf.model_id != model_id:
            raise ValueError("photo_file cross-model")

    now = datetime.datetime.now(datetime.UTC)
    pr = ModelPrint(
        model_id=model_id,
        printed_at=payload.printed_at,
        note=payload.note,
        photo_file_id=payload.photo_file_id,
        created_at=now,
        updated_at=now,
    )
    session.add(pr)
    session.flush()

    _audit_entity(
        session,
        action="model_print.create",
        entity_type="model_print",
        entity_id=pr.id,
        actor_user_id=actor_user_id,
        after={
            "model_id": str(model_id),
            "printed_at": str(payload.printed_at) if payload.printed_at else None,
        },
    )

    session.commit()
    session.refresh(pr)
    return pr


def update_print(
    session: Session,
    *,
    print_id: uuid.UUID,
    patch: PrintPatch,
    actor_user_id: uuid.UUID,
) -> ModelPrint:
    """Partially update a ModelPrint.

    Raises:
        LookupError("print not found")
        ValueError("photo_file cross-model") — new photo_file_id cross-model.
    """
    pr = session.get(ModelPrint, print_id)
    if pr is None:
        raise LookupError("print not found")

    before = {
        "printed_at": str(pr.printed_at) if pr.printed_at else None,
        "note": pr.note,
        "photo_file_id": str(pr.photo_file_id) if pr.photo_file_id else None,
    }

    data = patch.model_dump(exclude_unset=True)

    if "photo_file_id" in data and data["photo_file_id"] is not None:
        pf = session.get(ModelFile, data["photo_file_id"])
        if pf is None or pf.model_id != pr.model_id:
            raise ValueError("photo_file cross-model")

    for field, value in data.items():
        setattr(pr, field, value)

    pr.updated_at = datetime.datetime.now(datetime.UTC)
    after = {
        "printed_at": str(pr.printed_at) if pr.printed_at else None,
        "note": pr.note,
        "photo_file_id": str(pr.photo_file_id) if pr.photo_file_id else None,
    }

    session.add(pr)
    session.flush()

    _audit_entity(
        session,
        action="model_print.update",
        entity_type="model_print",
        entity_id=pr.id,
        actor_user_id=actor_user_id,
        before=before,
        after=after,
    )

    session.commit()
    session.refresh(pr)
    return pr


def delete_print(
    session: Session,
    *,
    print_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> None:
    """Delete a ModelPrint.

    Raises:
        LookupError("print not found")
    """
    pr = session.get(ModelPrint, print_id)
    if pr is None:
        raise LookupError("print not found")

    before = {"model_id": str(pr.model_id)}

    _audit_entity(
        session,
        action="model_print.delete",
        entity_type="model_print",
        entity_id=pr.id,
        actor_user_id=actor_user_id,
        before=before,
    )

    session.delete(pr)
    session.commit()


# ---------------------------------------------------------------------------
# External links
# ---------------------------------------------------------------------------


def create_external_link(
    session: Session,
    *,
    model_id: uuid.UUID,
    payload: ExternalLinkCreate,
    actor_user_id: uuid.UUID,
) -> ModelExternalLink:
    """Create a ModelExternalLink.

    Raises:
        LookupError("model not found")
        ValueError("source_conflict") — (model_id, source) collision.
    """
    _get_model_active(session, model_id)

    now = datetime.datetime.now(datetime.UTC)
    link = ModelExternalLink(
        model_id=model_id,
        source=payload.source,
        external_id=payload.external_id,
        url=payload.url,
        created_at=now,
        updated_at=now,
    )
    session.add(link)

    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise ValueError("source_conflict") from exc

    _audit_entity(
        session,
        action="model_external_link.create",
        entity_type="model_external_link",
        entity_id=link.id,
        actor_user_id=actor_user_id,
        after={"model_id": str(model_id), "source": str(payload.source), "url": payload.url},
    )

    session.commit()
    session.refresh(link)
    return link


def update_external_link(
    session: Session,
    *,
    link_id: uuid.UUID,
    patch: ExternalLinkPatch,
    actor_user_id: uuid.UUID,
) -> ModelExternalLink:
    """Partially update a ModelExternalLink.

    Raises:
        LookupError("link not found")
        ValueError("source_conflict")
    """
    link = session.get(ModelExternalLink, link_id)
    if link is None:
        raise LookupError("link not found")

    before = {"source": str(link.source), "url": link.url, "external_id": link.external_id}
    data = patch.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(link, field, value)

    link.updated_at = datetime.datetime.now(datetime.UTC)
    after = {"source": str(link.source), "url": link.url, "external_id": link.external_id}

    session.add(link)

    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise ValueError("source_conflict") from exc

    _audit_entity(
        session,
        action="model_external_link.update",
        entity_type="model_external_link",
        entity_id=link.id,
        actor_user_id=actor_user_id,
        before=before,
        after=after,
    )

    session.commit()
    session.refresh(link)
    return link


def delete_external_link(
    session: Session,
    *,
    link_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> None:
    """Delete a ModelExternalLink.

    Raises:
        LookupError("link not found")
    """
    link = session.get(ModelExternalLink, link_id)
    if link is None:
        raise LookupError("link not found")

    before = {"model_id": str(link.model_id), "source": str(link.source)}

    _audit_entity(
        session,
        action="model_external_link.delete",
        entity_type="model_external_link",
        entity_id=link.id,
        actor_user_id=actor_user_id,
        before=before,
    )

    session.delete(link)
    session.commit()
