"""apps/api/app/workers/generate_thumbnail.py — Story 13.2 / Decision P.

On-upload thumbnail generation for image-kind ModelFiles.

Pipeline:
    Pillow → exif_transpose → thumbnail(800px longest side) → WebP @ q80

Output file co-located with original: ``<original_storage_path>.thumb.webp``.
Idempotent: skips if the sibling thumbnail already exists.

Realises FR8-THUMB-1 (on-upload variant creation) and the worker side of
FR8-THUMB-2 (variant endpoint reads the file this task writes).
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.db.models import ModelFile, ModelFileKind
from app.core.db.session import get_engine

_LOG = logging.getLogger("app.workers.thumbnail")

# Decision P — pipeline constants
THUMBNAIL_LONGEST_SIDE_PX = 800
WEBP_QUALITY = 80
THUMBNAIL_SUFFIX = ".thumb.webp"


def thumbnail_path_for(original: Path) -> Path:
    """Return sibling thumbnail path for ``original`` (``<filename>.thumb.webp``)."""
    return original.with_name(original.name + THUMBNAIL_SUFFIX)


def generate_thumbnail_sync(
    engine,
    model_file_id: uuid.UUID,
    *,
    content_dir: Path | None = None,
) -> dict:
    """Generate the WebP thumbnail for an image ``ModelFile`` row.

    Returns a structured result dict suitable for logging / test assertion::

        {"status": "ok|skipped|missing|not_image|row_missing|error",
         "thumbnail_path": "<relative path or None>",
         "size_bytes": <int or None>,
         "reason": "<optional>"}

    Idempotent: returns ``skipped`` when the thumbnail file already exists.
    Tolerates a missing original or non-image kind (logged + returned as
    structured non-error so backfill / retry doesn't crash on stale rows).

    Raises only on unrecoverable infrastructure faults (DB engine missing).
    """
    if content_dir is None:
        content_dir = get_settings().portal_content_dir

    with Session(engine) as s:
        row = s.exec(select(ModelFile).where(ModelFile.id == model_file_id)).first()
        if row is None:
            _LOG.info(
                "thumbnail.row_missing",
                extra={
                    "event.action": "thumbnail.row_missing",
                    "labels.model_file_id": str(model_file_id),
                },
            )
            return {"status": "row_missing", "thumbnail_path": None, "size_bytes": None}

        if row.kind not in (ModelFileKind.image, ModelFileKind.print):
            _LOG.info(
                "thumbnail.not_image",
                extra={
                    "event.action": "thumbnail.not_image",
                    "labels.model_file_id": str(model_file_id),
                    "labels.kind": row.kind.value,
                },
            )
            return {
                "status": "not_image",
                "thumbnail_path": None,
                "size_bytes": None,
                "reason": f"kind={row.kind.value}",
            }

        original_abs = (content_dir / row.storage_path).resolve()
        base = content_dir.resolve()
        try:
            original_abs.relative_to(base)
        except ValueError:
            _LOG.error(
                "thumbnail.path_escape",
                extra={
                    "event.action": "thumbnail.path_escape",
                    "labels.model_file_id": str(model_file_id),
                    "labels.storage_path": row.storage_path,
                },
            )
            return {
                "status": "error",
                "thumbnail_path": None,
                "size_bytes": None,
                "reason": "path_escape",
            }

        if not original_abs.is_file():
            _LOG.warning(
                "thumbnail.original_missing",
                extra={
                    "event.action": "thumbnail.original_missing",
                    "labels.model_file_id": str(model_file_id),
                    "labels.storage_path": row.storage_path,
                },
            )
            return {
                "status": "missing",
                "thumbnail_path": None,
                "size_bytes": None,
                "reason": "original_missing",
            }

        thumb_abs = thumbnail_path_for(original_abs)
        thumb_rel = row.storage_path + THUMBNAIL_SUFFIX

        if thumb_abs.exists():
            _LOG.info(
                "thumbnail.skipped",
                extra={
                    "event.action": "thumbnail.skipped",
                    "labels.model_file_id": str(model_file_id),
                    "labels.thumbnail_path": thumb_rel,
                    "labels.size_bytes": thumb_abs.stat().st_size,
                },
            )
            return {
                "status": "skipped",
                "thumbnail_path": thumb_rel,
                "size_bytes": thumb_abs.stat().st_size,
            }

        try:
            size_bytes = _render_thumbnail(original_abs, thumb_abs)
        except UnidentifiedImageError as exc:
            _LOG.warning(
                "thumbnail.unidentified",
                extra={
                    "event.action": "thumbnail.unidentified",
                    "labels.model_file_id": str(model_file_id),
                    "labels.storage_path": row.storage_path,
                    "labels.error": str(exc),
                },
            )
            return {
                "status": "error",
                "thumbnail_path": None,
                "size_bytes": None,
                "reason": "unidentified_image",
            }
        except Exception as exc:
            _LOG.exception(
                "thumbnail.error",
                extra={
                    "event.action": "thumbnail.error",
                    "labels.model_file_id": str(model_file_id),
                    "labels.storage_path": row.storage_path,
                    "labels.error": repr(exc),
                },
            )
            return {
                "status": "error",
                "thumbnail_path": None,
                "size_bytes": None,
                "reason": repr(exc),
            }

        _LOG.info(
            "thumbnail.ok",
            extra={
                "event.action": "thumbnail.ok",
                "labels.model_file_id": str(model_file_id),
                "labels.thumbnail_path": thumb_rel,
                "labels.size_bytes": size_bytes,
            },
        )
        return {"status": "ok", "thumbnail_path": thumb_rel, "size_bytes": size_bytes}


def _render_thumbnail(original_abs: Path, thumb_abs: Path) -> int:
    """Open ``original_abs`` and write a WebP thumbnail to ``thumb_abs``.

    Returns size of the written thumbnail in bytes.
    """
    with Image.open(original_abs) as im:
        # Honour EXIF orientation tag so portrait phone photos don't end up rotated.
        im = ImageOps.exif_transpose(im)
        # WebP encoder needs RGB / RGBA — palette images and the (mostly
        # alpha-channel) "P" mode would otherwise round-trip via PNG fallback.
        if im.mode == "P":
            im = im.convert("RGBA")
        # Pillow.thumbnail mutates in-place; preserves aspect ratio; uses LANCZOS.
        im.thumbnail((THUMBNAIL_LONGEST_SIDE_PX, THUMBNAIL_LONGEST_SIDE_PX))
        # Write to a temp file then rename for atomic visibility — another
        # concurrent task or the variant endpoint must never read a partial
        # WebP. The temp path is in the same directory so the rename is atomic
        # on POSIX volumes (portal-content is bind-mounted ext4 / overlayfs).
        #
        # P2-3 fix-up on Codex review aa6a8eb: per-job unique tmp suffix
        # (pid + 8-hex uuid) so two concurrent generate_thumbnail jobs on the
        # SAME ModelFile (e.g. upload-enqueued + backfill-enqueued races) do
        # NOT clobber each other's `.tmp` mid-save. Previously both jobs wrote
        # to a shared `<name>.thumb.webp.tmp`, where one rename could land
        # while the other was still saving — outcome: corrupt or missing
        # thumbnail. Each job now owns its own tmp file; whichever finishes
        # last wins the canonical name via atomic replace (same final byte-
        # exact WebP either way — pipeline is deterministic). The finally
        # clause cleans up our own tmp only.
        tmp_abs = thumb_abs.with_name(f"{thumb_abs.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
        try:
            im.save(tmp_abs, format="WEBP", quality=WEBP_QUALITY, method=6)
            tmp_abs.replace(thumb_abs)
        finally:
            tmp_abs.unlink(missing_ok=True)
    return thumb_abs.stat().st_size


async def generate_thumbnail(_ctx, model_file_id: uuid.UUID | str) -> dict:
    """arq task entry point.

    Accepts UUID or str; arq serialises params via msgpack which preserves
    UUID round-trip in newer arq, but admin-side enqueues already coerce to
    UUID so the str branch is defensive only.
    """
    if isinstance(model_file_id, str):
        model_file_id = uuid.UUID(model_file_id)
    return generate_thumbnail_sync(get_engine(), model_file_id)
