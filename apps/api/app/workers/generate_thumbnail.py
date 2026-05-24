"""apps/api/app/workers/generate_thumbnail.py — Story 13.2 / Decision P + Story 22.1 / Decision W.

On-upload variant generation for image-kind ModelFiles.

Two-tier pipeline (Story 22.1 / FR16-TIER-1 / Decision W):
    Tier 1 (thumb)   — Pillow → exif_transpose → thumbnail(800px)  → WebP @ q80
                       Sibling: ``<original_storage_path>.thumb.webp``
                       Used by: catalog cards, carousel preview strip.
    Tier 2 (gallery) — Pillow → exif_transpose → thumbnail(1920px) → WebP @ q80
                       Sibling: ``<original_storage_path>.gallery.webp``
                       Used by: in-page carousel main frame (closes TB-037
                       4-8 MB original bandwidth gap that fired Story 19.2
                       nginx caps / produced 503s on legitimate carousel use).
                       Dimension is designer-locked per
                       ``_bmad-output/implementation-artifacts/22-3-designer-ux-spec.md`` §3
                       — covers 1080p fullscreen + 2x DPR laptop main frames;
                       4K/5K fullscreen falls through to the original blob
                       via ``?variant=full`` (= no variant).

Both variants are idempotent: each ``*_sync`` function skips when its sibling
already exists. The arq task entry point produces BOTH on every job; failure
isolation means each tier's error path is independent — a malformed image
that defeats one tier's render does not block the other from succeeding.

Realises FR8-THUMB-1 (on-upload variant creation), FR8-THUMB-2 (variant
endpoint reads the file this task writes), and FR16-TIER-1 (gallery tier
extension) — both endpoint branches live in ``apps/api/app/modules/sot/router.py``.
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

# Decision W — Story 22.1 / FR16-TIER-1 gallery-tier constants.
# 1920 px is DESIGNER-LOCKED per 22-3-designer-ux-spec.md §3 — not a
# free-choice tunable. Operator tuning requests post-deploy → Init 17+
# candidate, NOT an in-story deviation.
GALLERY_LONGEST_SIDE_PX = 1920
GALLERY_SUFFIX = ".gallery.webp"


def thumbnail_path_for(original: Path) -> Path:
    """Return sibling thumbnail path for ``original`` (``<filename>.thumb.webp``)."""
    return original.with_name(original.name + THUMBNAIL_SUFFIX)


def gallery_path_for(original: Path) -> Path:
    """Return sibling gallery-tier path for ``original`` (``<filename>.gallery.webp``).

    Story 22.1 / Decision W — mirrors ``thumbnail_path_for`` shape.
    """
    return original.with_name(original.name + GALLERY_SUFFIX)


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
    return _render_variant(
        original_abs,
        thumb_abs,
        longest_side_px=THUMBNAIL_LONGEST_SIDE_PX,
    )


def _render_gallery(original_abs: Path, gallery_abs: Path) -> int:
    """Open ``original_abs`` and write a 1920px WebP gallery-tier variant.

    Story 22.1 / Decision W — mirrors ``_render_thumbnail`` shape with the
    designer-locked ``GALLERY_LONGEST_SIDE_PX = 1920`` (22-3-designer-ux-spec.md §3).
    Same EXIF + mode-fix + Pillow.thumbnail + WebP @ q80 + atomic tmp+rename
    pipeline; same P2-3 unique-tmp-per-job race-defence pattern.
    """
    return _render_variant(
        original_abs,
        gallery_abs,
        longest_side_px=GALLERY_LONGEST_SIDE_PX,
    )


def _render_variant(
    original_abs: Path,
    out_abs: Path,
    *,
    longest_side_px: int,
) -> int:
    """Shared Pillow → WebP variant renderer used by both tiers.

    Returns size of the written WebP in bytes.

    Pipeline:
        - EXIF orientation transpose (portrait phone photos render upright)
        - mode fix-up for palette ``P`` → ``RGBA`` (WebP encoder prereq)
        - Pillow.thumbnail() in-place, LANCZOS, aspect preserved
        - Atomic tmp-write + replace, with per-job unique tmp suffix
          (pid + 8-hex uuid) to defend against two concurrent jobs on the
          SAME ModelFile clobbering each other's tmp mid-save. See the
          long-form rationale on the P2-3 Codex aa6a8eb fix-up (Story 13.2).
    """
    with Image.open(original_abs) as im:
        # Honour EXIF orientation tag so portrait phone photos don't end up rotated.
        im = ImageOps.exif_transpose(im)
        # WebP encoder needs RGB / RGBA — palette images and the (mostly
        # alpha-channel) "P" mode would otherwise round-trip via PNG fallback.
        if im.mode == "P":
            im = im.convert("RGBA")
        # Pillow.thumbnail mutates in-place; preserves aspect ratio; uses LANCZOS.
        im.thumbnail((longest_side_px, longest_side_px))
        # Write to a temp file then rename for atomic visibility — another
        # concurrent task or the variant endpoint must never read a partial
        # WebP. The temp path is in the same directory so the rename is atomic
        # on POSIX volumes (portal-content is bind-mounted ext4 / overlayfs).
        #
        # P2-3 fix-up on Codex review aa6a8eb (Story 13.2): per-job unique
        # tmp suffix (pid + 8-hex uuid) so two concurrent generate_thumbnail
        # jobs on the SAME ModelFile (e.g. upload-enqueued + backfill-enqueued
        # races) do NOT clobber each other's `.tmp` mid-save. Each job now
        # owns its own tmp file; whichever finishes last wins the canonical
        # name via atomic replace (same final byte-exact WebP either way —
        # pipeline is deterministic). The finally clause cleans up our own
        # tmp only. This same defence applies to the gallery tier (Story
        # 22.1) which shares this renderer.
        tmp_abs = out_abs.with_name(f"{out_abs.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
        try:
            im.save(tmp_abs, format="WEBP", quality=WEBP_QUALITY, method=6)
            tmp_abs.replace(out_abs)
        finally:
            tmp_abs.unlink(missing_ok=True)
    return out_abs.stat().st_size


def generate_gallery_sync(
    engine,
    model_file_id: uuid.UUID,
    *,
    content_dir: Path | None = None,
) -> dict:
    """Generate the 1920 px gallery-tier WebP for an image ``ModelFile`` row.

    Story 22.1 / FR16-TIER-1 / Decision W — mirrors
    :func:`generate_thumbnail_sync` shape exactly (status enum, idempotency,
    error paths, structured logging). The only differences are:

    - dimension: ``GALLERY_LONGEST_SIDE_PX = 1920`` (designer-locked)
    - sibling suffix: ``.gallery.webp``
    - log event prefix: ``gallery.*`` (vs ``thumbnail.*``)
    - result dict key: ``gallery_path`` (vs ``thumbnail_path``)

    Returns a structured result dict suitable for logging / test assertion::

        {"status": "ok|skipped|missing|not_image|row_missing|error",
         "gallery_path": "<relative path or None>",
         "size_bytes": <int or None>,
         "reason": "<optional>"}

    Idempotent: returns ``skipped`` when the gallery sibling already exists.
    Tolerates missing original or non-image kind (structured non-error).
    """
    if content_dir is None:
        content_dir = get_settings().portal_content_dir

    with Session(engine) as s:
        row = s.exec(select(ModelFile).where(ModelFile.id == model_file_id)).first()
        if row is None:
            _LOG.info(
                "gallery.row_missing",
                extra={
                    "event.action": "gallery.row_missing",
                    "labels.model_file_id": str(model_file_id),
                },
            )
            return {"status": "row_missing", "gallery_path": None, "size_bytes": None}

        if row.kind not in (ModelFileKind.image, ModelFileKind.print):
            _LOG.info(
                "gallery.not_image",
                extra={
                    "event.action": "gallery.not_image",
                    "labels.model_file_id": str(model_file_id),
                    "labels.kind": row.kind.value,
                },
            )
            return {
                "status": "not_image",
                "gallery_path": None,
                "size_bytes": None,
                "reason": f"kind={row.kind.value}",
            }

        original_abs = (content_dir / row.storage_path).resolve()
        base = content_dir.resolve()
        try:
            original_abs.relative_to(base)
        except ValueError:
            _LOG.error(
                "gallery.path_escape",
                extra={
                    "event.action": "gallery.path_escape",
                    "labels.model_file_id": str(model_file_id),
                    "labels.storage_path": row.storage_path,
                },
            )
            return {
                "status": "error",
                "gallery_path": None,
                "size_bytes": None,
                "reason": "path_escape",
            }

        if not original_abs.is_file():
            _LOG.warning(
                "gallery.original_missing",
                extra={
                    "event.action": "gallery.original_missing",
                    "labels.model_file_id": str(model_file_id),
                    "labels.storage_path": row.storage_path,
                },
            )
            return {
                "status": "missing",
                "gallery_path": None,
                "size_bytes": None,
                "reason": "original_missing",
            }

        gallery_abs = gallery_path_for(original_abs)
        gallery_rel = row.storage_path + GALLERY_SUFFIX

        if gallery_abs.exists():
            _LOG.info(
                "gallery.skipped",
                extra={
                    "event.action": "gallery.skipped",
                    "labels.model_file_id": str(model_file_id),
                    "labels.gallery_path": gallery_rel,
                    "labels.size_bytes": gallery_abs.stat().st_size,
                },
            )
            return {
                "status": "skipped",
                "gallery_path": gallery_rel,
                "size_bytes": gallery_abs.stat().st_size,
            }

        try:
            size_bytes = _render_gallery(original_abs, gallery_abs)
        except UnidentifiedImageError as exc:
            _LOG.warning(
                "gallery.unidentified",
                extra={
                    "event.action": "gallery.unidentified",
                    "labels.model_file_id": str(model_file_id),
                    "labels.storage_path": row.storage_path,
                    "labels.error": str(exc),
                },
            )
            return {
                "status": "error",
                "gallery_path": None,
                "size_bytes": None,
                "reason": "unidentified_image",
            }
        except Exception as exc:
            _LOG.exception(
                "gallery.error",
                extra={
                    "event.action": "gallery.error",
                    "labels.model_file_id": str(model_file_id),
                    "labels.storage_path": row.storage_path,
                    "labels.error": repr(exc),
                },
            )
            return {
                "status": "error",
                "gallery_path": None,
                "size_bytes": None,
                "reason": repr(exc),
            }

        _LOG.info(
            "gallery.ok",
            extra={
                "event.action": "gallery.ok",
                "labels.model_file_id": str(model_file_id),
                "labels.gallery_path": gallery_rel,
                "labels.size_bytes": size_bytes,
            },
        )
        return {"status": "ok", "gallery_path": gallery_rel, "size_bytes": size_bytes}


async def generate_thumbnail(_ctx, model_file_id: uuid.UUID | str) -> dict:
    """arq task entry point — produces BOTH thumb AND gallery tiers.

    Story 22.1 / Decision W extends the original Story 13.2 single-tier
    entry point. Each tier's sync function handles its own error path
    independently — a unidentified-image failure on one tier does NOT
    short-circuit the other (failure isolation). The composite return
    shape exposes both result dicts so log/test consumers can act on
    either::

        {"thumbnail": {"status": ..., "thumbnail_path": ..., "size_bytes": ...},
         "gallery":   {"status": ..., "gallery_path":   ..., "size_bytes": ...}}

    Existing dispatchers (admin upload, backfill script, future cron) are
    fire-and-forget and do not pattern-match on the prior single-dict
    return shape; verified by grep in apps/api/. The composite shape is
    therefore backward-compatible.

    Accepts UUID or str; arq serialises params via msgpack which preserves
    UUID round-trip in newer arq, but admin-side enqueues already coerce
    to UUID so the str branch is defensive only.
    """
    if isinstance(model_file_id, str):
        model_file_id = uuid.UUID(model_file_id)
    engine = get_engine()
    return {
        "thumbnail": generate_thumbnail_sync(engine, model_file_id),
        "gallery": generate_gallery_sync(engine, model_file_id),
    }
