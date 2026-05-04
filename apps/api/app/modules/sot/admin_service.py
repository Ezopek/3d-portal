"""Write-side service functions for Model admin operations.

Each function owns its own transaction (commit) and writes an audit_log
row inside the same tx for atomicity. Callers receive the mutated Model
row; they are responsible for building the full response via
`get_model_detail`.

Audit log entries are inserted as direct AuditLog rows (not via
`record_event`) so they share the same session/tx as the mutation.
"""

import datetime
import json
import re
import uuid
from pathlib import Path

from sqlmodel import Session, select

from app.core.db.models import (
    AuditLog,
    Category,
    Model,
    ModelFile,
)
from app.modules.sot.admin_schemas import ModelCreate, ModelPatch

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
