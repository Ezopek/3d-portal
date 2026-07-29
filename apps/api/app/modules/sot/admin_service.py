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
from typing import Any, NoReturn

from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.audit import record_event
from app.core.db.models import (
    AuditLog,
    BrowseCategory,
    Model,
    ModelBrowseCategory,
    ModelExternalLink,
    ModelFile,
    ModelFileKind,
    ModelNote,
    ModelPrint,
    ModelTag,
    NoteKind,
    Tag,
    TagGroup,
)
from app.core.db.session import get_engine
from app.modules.sot.admin_schemas import (
    BrowseCategoryCreate,
    BrowseCategoryPatch,
    ExternalLinkCreate,
    ExternalLinkPatch,
    ModelCategoriesReplace,
    ModelCreate,
    ModelFilePatch,
    ModelPatch,
    NoteCreate,
    NotePatch,
    PrintCreate,
    PrintPatch,
    TagCreate,
    TagGroupCreate,
    TagGroupPatch,
    TagMerge,
    TagPatch,
    TagsReplace,
)
from app.modules.sot.schemas import BrowseCategoryAdminRead
from app.modules.sot.service import _browse_category_model_counts

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


def _tag_snapshot(tag: Tag) -> dict:
    """Full bounded before/after snapshot for a `tag.*` audit row (Story 42.4).

    Always carries the two facet-membership fields so the move surface (D-MOVE-1)
    is auditable; UUIDs/strings/ints only — no PII (D-AUDIT-2)."""
    return {
        "slug": tag.slug,
        "name_en": tag.name_en,
        "name_pl": tag.name_pl,
        "group_id": str(tag.group_id) if tag.group_id is not None else None,
        "group_position": tag.group_position,
    }


def _model_snapshot(m: Model) -> dict:
    """Key fields for audit before/after snapshots."""
    return {
        "name_en": m.name_en,
        "name_pl": m.name_pl,
        "slug": m.slug,
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
        ValueError("slug_conflict") — provided slug already taken.
    """
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
        ValueError("slug_conflict") — new slug already taken by another model.
    """
    before = _model_snapshot(model)

    data = patch.model_dump(exclude_unset=True)

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
        # P3-1 fix-up on Codex review aa6a8eb: also remove the Story 13.2
        # thumbnail sidecar (<storage_path>.thumb.webp); it has no ModelFile
        # row, so the cascade above can't reach it. Story 22.1 / Decision W
        # adds the same cleanup for the gallery-tier sidecar.
        thumb = full.with_name(full.name + ".thumb.webp")
        thumb.unlink(missing_ok=True)
        gallery = full.with_name(full.name + ".gallery.webp")
        gallery.unlink(missing_ok=True)


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
        "selected_for_render": f.selected_for_render,
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

    # First STL on a model auto-selects for renders so worker still has
    # something to render after a single upload. Subsequent STL uploads stay
    # unselected — admin opts them in explicitly via the FilesTab checkbox.
    selected_for_render = False
    if kind == ModelFileKind.stl:
        already_selected = session.exec(
            select(ModelFile.id).where(
                ModelFile.model_id == model_id,
                ModelFile.kind == ModelFileKind.stl,
                ModelFile.selected_for_render.is_(True),
            )
        ).first()
        if already_selected is None:
            selected_for_render = True

    file_row = ModelFile(
        model_id=model_id,
        kind=kind,
        original_name=original_name,
        storage_path=dst_rel,
        sha256=sha256,
        size_bytes=size_bytes,
        mime_type=mime_type,
        selected_for_render=selected_for_render,
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

    if "selected_for_render" in data and data["selected_for_render"] is not None:
        # The flag is meaningful only for STL files — worker filters STL by it.
        # Reject the toggle on anything else so admin UIs don't silently set
        # the bit on photos / sources where it would never be honored.
        target_kind = data.get("kind") or f.kind
        if target_kind != ModelFileKind.stl:
            raise ValueError("selected_for_render_only_on_stl")

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
    # P3-1 fix-up on Codex review aa6a8eb: also remove the Story 13.2 thumbnail
    # sidecar (<storage_path>.thumb.webp), which is NOT represented by a
    # ModelFile row and would otherwise leak on every normal delete. Story
    # 22.1 / Decision W extends the same cleanup to the gallery-tier sidecar.
    thumb_path = full_path.with_name(full_path.name + ".thumb.webp")
    thumb_path.unlink(missing_ok=True)
    gallery_path = full_path.with_name(full_path.name + ".gallery.webp")
    gallery_path.unlink(missing_ok=True)


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

    before = _tag_snapshot(tag)
    data = patch.model_dump(exclude_unset=True)

    if "slug" in data and data["slug"] is not None and data["slug"] != tag.slug:
        collision = session.exec(
            select(Tag).where(Tag.slug == data["slug"], Tag.id != tag_id)
        ).first()
        if collision is not None:
            raise ValueError("slug_conflict")

    # Story 42.4 (D-MOVE-1) — validate a non-null move target group. A null
    # group_id is intentional (groupless); an explicit null group_position was
    # already rejected as 422 at the schema layer.
    if data.get("group_id") is not None and session.get(TagGroup, data["group_id"]) is None:
        raise ValueError("tag group not found")

    for field, value in data.items():
        setattr(tag, field, value)

    tag.updated_at = datetime.datetime.now(datetime.UTC)
    after = _tag_snapshot(tag)

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
    from_rows = session.exec(select(ModelTag).where(ModelTag.tag_id == payload.from_id)).all()

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
# Tag groups (Story 42.4 — admin governance)
# ---------------------------------------------------------------------------


def _tag_group_snapshot(tg: TagGroup) -> dict:
    """Full bounded before/after snapshot for a `tag_group.*` audit row."""
    return {
        "slug": tg.slug,
        "name_en": tg.name_en,
        "name_pl": tg.name_pl,
        "position": tg.position,
    }


def create_tag_group(
    session: Session,
    *,
    payload: TagGroupCreate,
    actor_user_id: uuid.UUID,
) -> TagGroup:
    """Create a new TagGroup.

    Raises:
        ValueError("slug_conflict") — slug already in use (uq_tag_group_slug).
    """
    now = datetime.datetime.now(datetime.UTC)
    tg = TagGroup(
        slug=payload.slug,
        name_en=payload.name_en,
        name_pl=payload.name_pl,
        position=payload.position,
        created_at=now,
        updated_at=now,
    )
    session.add(tg)

    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise ValueError("slug_conflict") from exc

    _audit_entity(
        session,
        action="tag_group.create",
        entity_type="tag_group",
        entity_id=tg.id,
        actor_user_id=actor_user_id,
        after=_tag_group_snapshot(tg),
    )

    session.commit()
    session.refresh(tg)
    return tg


def update_tag_group(
    session: Session,
    *,
    group_id: uuid.UUID,
    patch: TagGroupPatch,
    actor_user_id: uuid.UUID,
) -> TagGroup:
    """Partially update a TagGroup.

    Explicit null on the NOT NULL fields (slug/name_en/position) is rejected as
    422 at the schema layer (D-NULLSEM-1), so it never reaches `setattr` here;
    the only remaining IntegrityError path is a genuine slug race → 409. An
    empty patch is a no-op that still writes one `tag_group.update` row with
    before == after (unconditional audit).

    Raises:
        LookupError("tag group not found")
        ValueError("slug_conflict")
    """
    tg = session.get(TagGroup, group_id)
    if tg is None:
        raise LookupError("tag group not found")

    before = _tag_group_snapshot(tg)
    data = patch.model_dump(exclude_unset=True)

    for field, value in data.items():
        setattr(tg, field, value)

    tg.updated_at = datetime.datetime.now(datetime.UTC)
    after = _tag_group_snapshot(tg)

    session.add(tg)

    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise ValueError("slug_conflict") from exc

    _audit_entity(
        session,
        action="tag_group.update",
        entity_type="tag_group",
        entity_id=tg.id,
        actor_user_id=actor_user_id,
        before=before,
        after=after,
    )

    session.commit()
    session.refresh(tg)
    return tg


def delete_tag_group(
    session: Session,
    *,
    group_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> None:
    """Delete a TagGroup. Member tags survive as groupless via the FK
    `ON DELETE SET NULL` (Decision AU / D-SETNULL-1) — no per-tag update, no
    ORM cascade, no 409 in-use path. Member ids are read first for the audit
    snapshot.

    Raises:
        LookupError("tag group not found")
    """
    tg = session.get(TagGroup, group_id)
    if tg is None:
        raise LookupError("tag group not found")

    member_ids = list(session.exec(select(Tag.id).where(Tag.group_id == group_id)).all())

    _audit_entity(
        session,
        action="tag_group.delete",
        entity_type="tag_group",
        entity_id=tg.id,
        actor_user_id=actor_user_id,
        before={
            "slug": tg.slug,
            "name_en": tg.name_en,
            "detached_tag_ids": [str(i) for i in member_ids],
            "detached_tag_count": len(member_ids),
        },
    )

    session.delete(tg)
    session.commit()  # FK ON DELETE SET NULL nulls member tags' group_id


# ---------------------------------------------------------------------------
# Browse categories (Story 49.5 — admin governance)
# ---------------------------------------------------------------------------


def _browse_category_snapshot(cat: BrowseCategory) -> dict:
    """Full bounded before/after snapshot for a `browse_category.*` audit row.

    UUIDs / strings / ints / nulls only — no PII, no unbounded growth
    (D-AUDIT-2). The one intentionally-unbounded field, `detached_model_ids`,
    is added by `delete_browse_category` alone and always paired with a count.
    """
    return {
        "slug": cat.slug,
        "name_en": cat.name_en,
        "name_pl": cat.name_pl,
        "description_en": cat.description_en,
        "description_pl": cat.description_pl,
        "inclusion_criterion": cat.inclusion_criterion,
        "position": cat.position,
        "parent_id": str(cat.parent_id) if cat.parent_id is not None else None,
    }


def browse_category_model_count(session: Session, category_id: uuid.UUID) -> int:
    """Live-model assignment count for ONE category.

    Scoped sibling of the read-side `_browse_category_model_counts` aggregate
    and deliberately not a reuse of it: the admin write response needs exactly
    one category's count, not a whole-table GROUP BY. Same semantics though —
    soft-deleted models do not count.
    """
    rows = session.exec(
        select(ModelBrowseCategory.model_id)
        .join(Model, Model.id == ModelBrowseCategory.model_id)
        .where(
            ModelBrowseCategory.category_id == category_id,
            Model.deleted_at.is_(None),
        )
    ).all()
    return len(rows)


def _browse_category_children(session: Session, category_id: uuid.UUID) -> list[uuid.UUID]:
    rows = session.exec(
        select(BrowseCategory.id).where(BrowseCategory.parent_id == category_id)
    ).all()
    return list(rows)


def _browse_category_assignments(
    session: Session, category_id: uuid.UUID
) -> list[ModelBrowseCategory]:
    rows = session.exec(
        select(ModelBrowseCategory).where(ModelBrowseCategory.category_id == category_id)
    ).all()
    return list(rows)


def _validate_browse_category_ids(session: Session, category_ids: list[uuid.UUID]) -> None:
    """Every id in a replace-set payload must resolve to a real BrowseCategory.

    Extracted so the commit-time safety net can re-derive the same cause after a
    rollback, exactly as `delete_browse_category` re-derives its two conflict
    sources — one definition, used both proactively and reactively.

    Raises:
        ValueError("category not found: <id>")
    """
    for cid in category_ids:
        if session.get(BrowseCategory, cid) is None:
            raise ValueError(f"category not found: {cid}")


def _raise_model_categories_commit_error(
    session: Session,
    exc: IntegrityError,
    *,
    model_id: uuid.UUID,
    category_ids: list[uuid.UUID],
) -> NoReturn:
    """Re-derive WHICH referenced row vanished during a replace-set write.

    `ModelBrowseCategory` carries two `ondelete="RESTRICT"` FKs, so a model or a
    category deleted between validation and the flush/COMMIT fires an
    IntegrityError that the route would otherwise leak as a 500 — while its
    description promises a 404 for exactly those causes. Both are re-checked
    once the rollback has left a usable session, mapping onto the SAME
    LookupError/ValueError semantics the proactive checks already raise.

    Anything else is re-raised unchanged: a duplicate payload is already a 400
    before this point, and inventing a 404 for an unrelated integrity failure
    would be a confident wrong answer.

    Always raises.
    """
    session.rollback()
    _get_model_active(session, model_id)
    _validate_browse_category_ids(session, category_ids)
    raise exc


def _raise_browse_category_flush_error(
    session: Session,
    exc: IntegrityError,
    parent_id: uuid.UUID | None,
) -> NoReturn:
    """Re-derive WHICH constraint an INSERT/UPDATE flush violated, after rollback.

    `BrowseCategory` carries two of them — `uq_browse_category_slug` and the
    `parent_id` self-FK — and SQLite's message names neither reliably. A blanket
    `slug_conflict` would blame a provably-unique slug whenever the parent
    vanished between validation and flush, and retrying with a new slug would
    never help. So the parent is simply re-checked once the rollback has left a
    usable session; everything else stays the shipped slug conflict.

    Always raises.
    """
    session.rollback()
    if parent_id is not None and session.get(BrowseCategory, parent_id) is None:
        raise LookupError("parent not found") from exc
    raise ValueError("slug_conflict") from exc


def _validate_parent_is_root(session: Session, parent_id: uuid.UUID) -> None:
    """FR26-CAT-4 depth-2 ceiling, target side.

    Raises:
        LookupError("parent not found") — no such category.
        ValueError("parent_not_root") — the target parent is itself a child, so
            attaching under it would create a depth-3 grandchild.
    """
    parent = session.get(BrowseCategory, parent_id)
    if parent is None:
        raise LookupError("parent not found")
    if parent.parent_id is not None:
        raise ValueError("parent_not_root")


def create_browse_category(
    session: Session,
    *,
    payload: BrowseCategoryCreate,
    actor_user_id: uuid.UUID,
) -> BrowseCategory:
    """Create a new BrowseCategory.

    Parent validation runs BEFORE the insert so an unknown or non-root parent
    is a clean 404/422 rather than a raw IntegrityError.

    Raises:
        LookupError("parent not found")
        ValueError("parent_not_root")
        ValueError("slug_conflict") — uq_browse_category_slug.
    """
    if payload.parent_id is not None:
        _validate_parent_is_root(session, payload.parent_id)

    now = datetime.datetime.now(datetime.UTC)
    cat = BrowseCategory(
        slug=payload.slug,
        name_en=payload.name_en,
        name_pl=payload.name_pl,
        description_en=payload.description_en,
        description_pl=payload.description_pl,
        inclusion_criterion=payload.inclusion_criterion,
        position=payload.position,
        parent_id=payload.parent_id,
        created_at=now,
        updated_at=now,
    )
    session.add(cat)

    try:
        session.flush()
    except IntegrityError as exc:
        _raise_browse_category_flush_error(session, exc, payload.parent_id)

    _audit_entity(
        session,
        action="browse_category.create",
        entity_type="browse_category",
        entity_id=cat.id,
        actor_user_id=actor_user_id,
        after=_browse_category_snapshot(cat),
    )

    session.commit()
    session.refresh(cat)
    return cat


def update_browse_category(
    session: Session,
    *,
    category_id: uuid.UUID,
    patch: BrowseCategoryPatch,
    actor_user_id: uuid.UUID,
) -> BrowseCategory:
    """Partially update a BrowseCategory (rename / reorder / reparent).

    Explicit null on the NOT NULL fields (slug/name_en/position) is rejected as
    422 at the schema layer (D-NULLSEM-1), so it never reaches `setattr` here.
    An empty patch is a no-op that still writes one `browse_category.update`
    row with before == after (unconditional audit).

    Reparenting runs THREE independent checks, in this order, and only when
    `parent_id` is being set to a non-null value — clearing it to null can
    never increase any depth and is always allowed:

      1. self-cycle — a category may not be its own parent;
      2. target side — the new parent must itself be a root (depth-2 ceiling);
      3. source side — a category that currently HAS children may not move
         under any parent, because that would push those children to depth 3.

    Raises:
        LookupError("category not found")
        LookupError("parent not found")
        ValueError("self_cycle" | "parent_not_root" | "reparent_exceeds_depth")
        ValueError("slug_conflict")
    """
    cat = session.get(BrowseCategory, category_id)
    if cat is None:
        raise LookupError("category not found")

    before = _browse_category_snapshot(cat)
    data = patch.model_dump(exclude_unset=True)

    if data.get("parent_id") is not None:
        new_parent_id = data["parent_id"]
        if new_parent_id == category_id:
            raise ValueError("self_cycle")
        _validate_parent_is_root(session, new_parent_id)
        if _browse_category_children(session, category_id):
            raise ValueError("reparent_exceeds_depth")

    for field, value in data.items():
        setattr(cat, field, value)

    cat.updated_at = datetime.datetime.now(datetime.UTC)
    after = _browse_category_snapshot(cat)

    session.add(cat)

    try:
        session.flush()
    except IntegrityError as exc:
        _raise_browse_category_flush_error(session, exc, data.get("parent_id"))

    _audit_entity(
        session,
        action="browse_category.update",
        entity_type="browse_category",
        entity_id=cat.id,
        actor_user_id=actor_user_id,
        before=before,
        after=after,
    )

    session.commit()
    session.refresh(cat)
    return cat


def delete_browse_category(
    session: Session,
    *,
    category_id: uuid.UUID,
    detach: bool,
    actor_user_id: uuid.UUID,
) -> None:
    """Delete a BrowseCategory. TWO independent conflict sources, checked in a
    fixed order, both defending a real `ondelete="RESTRICT"` FK:

      1. CHILD CATEGORIES — checked FIRST and UNCONDITIONALLY, before `detach`
         is even consulted. `BrowseCategory.parent_id` is RESTRICT, so a
         childful category cannot be deleted; `detach=true` is documented as
         MODEL-assignment detach only and deliberately does NOT reparent or
         cascade-delete children. Clearing a child's parent (`PATCH
         {"parent_id": null}`) or deleting the child is a separate prior
         request.
      2. MODEL ASSIGNMENTS — `ModelBrowseCategory.category_id` is RESTRICT too.
         409 unless the caller explicitly opts into `detach=true`, which then
         detaches and deletes in ONE transaction.

    Both conflicts are NORMALLY detected by a proactive pre-query rather than by
    catching an IntegrityError, because SQLite's message does not name which FK
    fired and the two 409s could not otherwise be told apart. The pre-queries
    cannot close the window between themselves and the COMMIT, though, so the
    commit carries a safety net that rolls back and RE-DERIVES the cause from
    the post-rollback state — children first, preserving the same precedence.
    That mirrors the ratified `delete_tag` rollback/mapping and guarantees a
    racing insert surfaces as the documented 409, never as an unhandled 500.
    Because the rollback also restores the assignments a `detach=true` request
    deleted, only rows the request had not already accounted for count as that
    racing insert — otherwise an unrelated integrity failure would be reported
    as a `category_in_use` the caller's own `detach=true` was meant to resolve.

    Model assignments are NOT filtered to live models: a row whose model is
    soft-deleted still blocks an ordinary delete, so a `restore_model` can find
    its category relationships intact. `model_count` counts only NON-deleted
    models (Decision AY) and may therefore truthfully read 0 while such a row
    protects the category; `detach=true` is the explicit destructive opt-in.

    Raises:
        LookupError("category not found")
        ValueError("category_has_children")
        ValueError("category_in_use")
    """
    cat = session.get(BrowseCategory, category_id)
    if cat is None:
        raise LookupError("category not found")

    if _browse_category_children(session, category_id):
        raise ValueError("category_has_children")

    assignment_rows = _browse_category_assignments(session, category_id)
    if assignment_rows and not detach:
        raise ValueError("category_in_use")

    before = _browse_category_snapshot(cat)
    detached_ids: list[uuid.UUID] = []
    if assignment_rows:
        # The one intentionally-unbounded audit field (epic:42 `detached_tag_ids`
        # precedent), ALWAYS paired with a count so a reader never has to count
        # array elements to know the scale. Absent entirely when nothing was
        # detached — `detach=true` never fabricates a detach record.
        detached_ids = [row.model_id for row in assignment_rows]
        before["detached_model_ids"] = [str(m) for m in detached_ids]
        before["detached_model_count"] = len(detached_ids)
        for row in assignment_rows:
            session.delete(row)
        session.flush()

    _audit_entity(
        session,
        action="browse_category.delete",
        entity_type="browse_category",
        entity_id=cat.id,
        actor_user_id=actor_user_id,
        before=before,
    )

    try:
        session.delete(cat)
        session.commit()
    except IntegrityError as exc:
        # Safety net for the pre-query -> COMMIT window: a child or an
        # assignment inserted in between still fires the RESTRICT FK here. The
        # rollback discards the audit row too, so a losing race stays free of
        # side effects, exactly like the proactive 409s above.
        session.rollback()
        if _browse_category_children(session, category_id):
            raise ValueError("category_has_children") from exc
        remaining = _browse_category_assignments(session, category_id)
        # The rollback also RESTORES the rows a `detach=true` request had just
        # deleted, so their mere presence proves nothing: only an assignment
        # this request had NOT already accounted for can be the racing insert
        # that fired the RESTRICT FK. With `detach=false` nothing was accounted
        # for, so any row still means `category_in_use`, exactly as before.
        if remaining and not {row.model_id for row in remaining} <= set(detached_ids):
            raise ValueError("category_in_use") from exc
        # Neither RESTRICT FK is actually violated, so this integrity failure
        # came from somewhere else — the commit also flushes the audit row,
        # whose actor FK fails when the acting admin's `user` row is gone.
        # Claiming `category_in_use` here would be a confident wrong answer the
        # client cannot falsify (`detach=true` fails identically and there is
        # nothing left to detach). Re-raise instead, so the cause surfaces
        # exactly as it already does on the sibling routes.
        raise


def list_browse_categories_admin(session: Session) -> list[BrowseCategoryAdminRead]:
    """Story 52.2 (B-1) — every browse category in the ADMIN shape, flat,
    ordered `(position, slug)`.

    The admin shape is `BrowseCategoryRead`'s nine public keys PLUS
    `inclusion_criterion`, which the public contract deliberately omits
    (Decision AY keyset). Before this route the field was writable, seeded and
    echoed on writes but exposed by no read — so reading it meant issuing a
    mutating `PATCH {}` that also wrote an audit row. That is the defect the
    49.5 code review ledgered as belonging to this story.

    Counts come from the READ-side `_browse_category_model_counts` whole-table
    GROUP BY, NOT from `browse_category_model_count` per row. Two reasons, both
    load-bearing: the per-row helper would make this endpoint O(categories) in
    statements, and sharing the read-side helper makes agreement with
    `GET /api/categories` true by construction rather than by coincidence —
    the property `test_browse_category_model_count_agrees_with_read_side_for_
    every_category` already pins for the write path.
    """
    rows = session.exec(
        select(BrowseCategory).order_by(BrowseCategory.position, BrowseCategory.slug)
    ).all()
    counts = _browse_category_model_counts(session)
    return [
        BrowseCategoryAdminRead(
            id=c.id,
            slug=c.slug,
            name_en=c.name_en,
            name_pl=c.name_pl,
            description_en=c.description_en,
            description_pl=c.description_pl,
            position=c.position,
            parent_id=c.parent_id,
            model_count=counts.get(c.id, 0),
            inclusion_criterion=c.inclusion_criterion,
        )
        for c in rows
    ]


def replace_model_categories(
    session: Session,
    *,
    model_id: uuid.UUID,
    payload: ModelCategoriesReplace,
    actor_user_id: uuid.UUID,
) -> list[BrowseCategory]:
    """Replace ALL browse categories for a model with the provided set.

    Whole-set, idempotent, explicit last-writer-wins. There is no merge, no
    diff and no optimistic-concurrency precondition (no `revision`, no
    `If-Match`) — the contract must never claim conflict detection it does not
    have.

    The ENTIRE payload is validated before ANY row is touched, so a rejected
    call leaves the existing set provably unchanged rather than half-replaced.
    The empty set is valid and clears every assignment: a model with zero
    categories stays fully valid and public (FR26-CAT-2).

    Validation cannot close the window between itself and the flush/COMMIT,
    though, so the write carries the same safety net `delete_browse_category`
    does: a model or category that vanishes in that window fires one of
    `ModelBrowseCategory`'s two RESTRICT FKs, and the cause is re-derived from
    the post-rollback state onto the documented 404 rather than leaking a 500.

    The duplicate-id pre-check is a deliberate improvement over the structural
    precedent `replace_model_tags`, which promises it in its docstring but does
    not implement it — a literal-duplicate payload there reaches an uncaught
    IntegrityError on the composite PK. That precedent is NOT retro-patched
    here; this is a different, closed story's surface.

    Raises:
        LookupError("model not found") — model absent or soft-deleted.
        ValueError("duplicate_category_ids")
        ValueError("category not found: <id>")
    """
    _get_model_active(session, model_id)

    if len(payload.category_ids) != len(set(payload.category_ids)):
        raise ValueError("duplicate_category_ids")

    _validate_browse_category_ids(session, payload.category_ids)

    existing_rows = session.exec(
        select(ModelBrowseCategory).where(ModelBrowseCategory.model_id == model_id)
    ).all()
    before_ids = [row.category_id for row in existing_rows]
    after_ids = list(payload.category_ids)

    try:
        for row in existing_rows:
            session.delete(row)
        session.flush()

        for cid in payload.category_ids:
            session.add(ModelBrowseCategory(model_id=model_id, category_id=cid))
        session.flush()

        # Reuses the existing entity_type="model" / action="model.update" convention
        # `replace_model_tags` established — no new M:N-specific entity_type.
        _audit_entity(
            session,
            action="model.update",
            entity_type="model",
            entity_id=model_id,
            actor_user_id=actor_user_id,
            before={"category_ids": [str(c) for c in before_ids]},
            after={"category_ids": [str(c) for c in after_ids]},
        )

        session.commit()
    except IntegrityError as exc:
        # Safety net for the validation -> flush/COMMIT window, the sibling of
        # the one `delete_browse_category` already carries. The rollback also
        # discards the audit row, so a losing race leaves the existing set
        # provably unchanged — the same no-partial-replace guarantee the
        # proactive validation gives.
        _raise_model_categories_commit_error(
            session, exc, model_id=model_id, category_ids=payload.category_ids
        )

    if not after_ids:
        return []
    cats = session.exec(
        select(BrowseCategory)
        .where(BrowseCategory.id.in_(after_ids))  # type: ignore[attr-defined]
        .order_by(BrowseCategory.position, BrowseCategory.slug)
    ).all()
    return list(cats)


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
        body_pl=payload.body_pl,
        body_en=payload.body_en,
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

    # Initiative 10 Story 16.1 (Decision L) — legacy edit-path mirror.
    # The pre-bilingual EditDescriptionSheet patches only `body`; without
    # this mirror the post-migration display chain would read stale
    # `body_en` (backfilled at migration time) and silently hide the
    # admin's fresh edit. Story 16.2 will introduce explicit body_pl +
    # body_en editor fields and remove the need for this mirror.
    if note.kind == NoteKind.description and "body" in data and "body_en" not in data:
        note.body_en = note.body

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


# ---------------------------------------------------------------------------
# Photo reorder
# ---------------------------------------------------------------------------


def reorder_model_photos(
    session: Session,
    *,
    model_id: uuid.UUID,
    ordered_ids: list[uuid.UUID],
    actor_user_id: uuid.UUID,
    request_id: str | None,
) -> None:
    """Assign sequential positions (0..N-1) to the given files in order.

    Validates that each file_id belongs to the model and is image/print kind.
    Raises ValueError on any mismatch (router translates to 400).
    """
    rows = list(
        session.exec(
            select(ModelFile)
            .where(ModelFile.model_id == model_id)
            .where(ModelFile.id.in_(ordered_ids))
        ).all()
    )
    by_id = {row.id: row for row in rows}
    if len(by_id) != len(ordered_ids) or set(by_id.keys()) != set(ordered_ids):
        raise ValueError("one or more file ids do not belong to this model")
    for row in rows:
        if row.kind not in (ModelFileKind.image, ModelFileKind.print):
            raise ValueError(f"file {row.id} is not an image/print kind")

    before = {str(fid): by_id[fid].position for fid in ordered_ids}
    for pos, fid in enumerate(ordered_ids):
        by_id[fid].position = pos
        session.add(by_id[fid])
    session.commit()
    after = {str(fid): pos for pos, fid in enumerate(ordered_ids)}

    record_event(
        get_engine(),
        action="model_photos.reorder",
        entity_type="model",
        entity_id=model_id,
        actor_user_id=actor_user_id,
        before={"positions": before},
        after={"positions": after},
        request_id=request_id,
    )


# ---------------------------------------------------------------------------
# Render trigger
# ---------------------------------------------------------------------------

AUTO_RENDER_NAMES: tuple[str, ...] = (
    "iso-render.png",
    "front-render.png",
    "side-render.png",
    "top-render.png",
)


def model_has_auto_renders(session: Session, model_id: uuid.UUID) -> bool:
    """True if the model already has at least one auto-rendered ModelFile."""
    return (
        session.exec(
            select(ModelFile)
            .where(ModelFile.model_id == model_id)
            .where(ModelFile.kind == ModelFileKind.image)
            .where(ModelFile.original_name.in_(AUTO_RENDER_NAMES))
            .limit(1)
        ).first()
        is not None
    )


async def enqueue_render(
    *,
    arq_pool: Any,  # arq Pool — typed loosely to avoid hard dep
    model_id: uuid.UUID,
    selected_stl_file_ids: list[uuid.UUID],
    actor_user_id: uuid.UUID,
    request_id: str | None,
) -> str:
    """Enqueue a render_model arq job. Returns the redis status key."""
    job = await arq_pool.enqueue_job(
        "render_model",
        str(model_id),
        selected_stl_file_ids=[str(fid) for fid in selected_stl_file_ids],
    )
    job_id = job.job_id if job is not None else "no-job"

    record_event(
        get_engine(),
        action="model.render.triggered",
        entity_type="model",
        entity_id=model_id,
        actor_user_id=actor_user_id,
        before=None,
        after={
            "job_id": job_id,
            "selected_stl_file_ids": [str(fid) for fid in selected_stl_file_ids],
        },
        request_id=request_id,
    )
    return f"render:status:{model_id}"
