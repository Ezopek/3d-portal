"""Idempotent one-shot script: import legacy ISO renders as ModelFile rows.

Background
==========

The legacy render worker writes ISO render PNGs to ``<RENDERS_DIR>/<legacy_id>/``
on the .190 host. The original SoT migration only imported binaries that the
legacy ``index.json`` referenced explicitly, so models that *only* had a render
on disk (and no curated images) landed in the portal with
``thumbnail_file_id IS NULL`` and an empty image gallery. The catalog list now
has nothing to fall back to — there is no ISO render anymore.

This script restores that fallback by **importing each legacy render as a
``ModelFile`` row of kind ``image``** so it shows up in the gallery and (if
no other thumbnail exists) becomes the model thumbnail.

Behavior
--------

For every ``Model`` with ``legacy_id IS NOT NULL``:

1. Look in ``<renders-dir>/<legacy_id>/`` for the alphabetically first ``*.png``.
2. If none, the model is counted as ``no-render-found`` and skipped.
3. Compute the SHA-256 of the PNG bytes. If a ``ModelFile`` already exists with
   that ``(model_id, sha256, kind=image)`` triple — typically because the
   script has been run before — count the model as ``skipped`` and move on.
   This is what makes the script idempotent.
4. Otherwise:
   - Copy the PNG bytes to
     ``<PORTAL_CONTENT_DIR>/models/<model.id>/files/<new-file-uuid>.png``.
   - Insert a ``ModelFile`` row (``kind=image``, ``original_name="iso-render.png"``,
     ``position=NULL`` — sorts last in the gallery, behind any curated images).
   - Write an audit log entry of action ``model.legacy_render.import``.
   - If the model still has no thumbnail, set ``thumbnail_file_id`` to the new
     row.

``--dry-run`` prints what *would* happen without writing anything to disk or
the database.

Usage::

    python -m scripts.backfill_legacy_renders [--renders-dir PATH] [--dry-run]

The renders directory defaults to ``$RENDERS_DIR`` (or ``/data/renders`` if
unset) and can be overridden via ``--renders-dir``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.db.models import (
    AuditLog,
    Model,
    ModelFile,
    ModelFileKind,
)
from app.core.db.session import get_engine

logger = logging.getLogger(__name__)


@dataclass
class BackfillStats:
    imported: int = 0
    skipped: int = 0  # already imported on a previous run
    no_render_found: int = 0


# Render-worker view names from `workers/render/render/trimesh_render.py`. Order
# matters: ``iso`` is the most informative single angle so it gets first dibs on
# the model thumbnail when none was set; the other three follow into the gallery.
_PREFERRED_VIEW_ORDER: tuple[str, ...] = ("iso", "front", "side", "top")


def _legacy_render_pngs(renders_dir: Path, legacy_id: str) -> list[Path]:
    """Return all PNGs in the legacy render directory, ordered by preference.

    The legacy render worker writes ``front.png``, ``iso.png``, ``side.png`` and
    ``top.png`` per model. We want all of them imported so the gallery has the
    full multi-angle set. Order: iso → front → side → top, then any extras
    sorted alphabetically.
    """
    src_dir = renders_dir / legacy_id
    if not src_dir.is_dir():
        return []
    pngs = [p for p in src_dir.iterdir() if p.is_file() and p.suffix.lower() == ".png"]
    by_stem = {p.stem.lower(): p for p in pngs}
    ordered: list[Path] = []
    for view in _PREFERRED_VIEW_ORDER:
        if view in by_stem:
            ordered.append(by_stem.pop(view))
    ordered.extend(sorted(by_stem.values()))
    return ordered


def _sha256_of(path: Path) -> tuple[str, int]:
    """Return ``(sha256_hex, size_bytes)`` for a file, streaming in chunks."""
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(64 * 1024), b""):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def backfill_legacy_renders(
    engine: Engine,
    *,
    renders_dir: Path,
    content_dir: Path,
    dry_run: bool = False,
) -> BackfillStats:
    """Walk every Model with a ``legacy_id`` and import its on-disk ISO render.

    Each successful import commits in its own transaction together with the
    corresponding ``audit_log`` row. Re-running is idempotent: a second run
    sees the same ``sha256`` already attached and counts the model as
    ``skipped``.
    """
    stats = BackfillStats()

    with Session(engine) as session:
        models = list(session.exec(select(Model).where(Model.legacy_id.is_not(None))).all())

    for m in models:
        assert m.legacy_id is not None  # narrow for the type-checker
        png_sources = _legacy_render_pngs(renders_dir, m.legacy_id)
        if not png_sources:
            stats.no_render_found += 1
            logger.info(
                "no legacy renders for model %s (legacy_id=%s) — skipping",
                m.slug,
                m.legacy_id,
            )
            continue

        for png_src in png_sources:
            sha256, size_bytes = _sha256_of(png_src)

            with Session(engine) as session:
                # Re-fetch in this session so we don't operate on a detached row.
                model = session.exec(select(Model).where(Model.id == m.id)).one()

                existing = session.exec(
                    select(ModelFile).where(
                        ModelFile.model_id == model.id,
                        ModelFile.sha256 == sha256,
                        ModelFile.kind == ModelFileKind.image,
                    )
                ).first()
                if existing is not None:
                    stats.skipped += 1
                    logger.info(
                        "legacy render %s for %s already imported as %s — skipping",
                        png_src.name,
                        model.slug,
                        existing.id,
                    )
                    continue

                file_uuid = uuid.uuid4()
                storage_rel = f"models/{model.id}/files/{file_uuid}.png"
                dst_path = content_dir / storage_rel
                original_name = f"{png_src.stem}-render.png"

                if dry_run:
                    logger.info(
                        "[dry-run] would import %s → %s for model %s",
                        png_src,
                        storage_rel,
                        model.slug,
                    )
                    stats.imported += 1
                    continue

                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(png_src, dst_path)

                new_file = ModelFile(
                    id=file_uuid,
                    model_id=model.id,
                    kind=ModelFileKind.image,
                    original_name=original_name,
                    storage_path=storage_rel,
                    sha256=sha256,
                    size_bytes=size_bytes,
                    mime_type="image/png",
                    position=None,
                )
                session.add(new_file)
                # Flush so the file row exists before the FK on Model.thumbnail_file_id
                # is checked when we update the model below.
                session.flush()

                before = {"thumbnail_file_id": None}
                after_thumb: str | None = None
                if model.thumbnail_file_id is None:
                    model.thumbnail_file_id = file_uuid
                    after_thumb = str(file_uuid)
                    session.add(model)

                session.add(
                    AuditLog(
                        actor_user_id=None,
                        action="model.legacy_render.import",
                        entity_type="model",
                        entity_id=model.id,
                        before_json=json.dumps(before),
                        after_json=json.dumps(
                            {
                                "model_file_id": str(file_uuid),
                                "storage_path": storage_rel,
                                "original_name": original_name,
                                "thumbnail_file_id": after_thumb,
                            }
                        ),
                    )
                )
                session.commit()
                stats.imported += 1
                logger.info(
                    "imported legacy render %s for %s (legacy_id=%s) → %s",
                    png_src.name,
                    model.slug,
                    model.legacy_id,
                    storage_rel,
                )

    return stats


def print_summary(stats: BackfillStats, *, dry_run: bool) -> None:
    prefix = "[dry-run] " if dry_run else ""
    print(f"{prefix}Legacy render backfill summary")
    print(f"  Imported:        {stats.imported}")
    print(f"  Skipped (done):  {stats.skipped}")
    print(f"  No render found: {stats.no_render_found}")
    total = stats.imported + stats.skipped + stats.no_render_found
    print(f"  Total models:    {total}")


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--renders-dir",
        type=Path,
        default=None,
        help=(
            "Directory containing <legacy_id>/<*>.png subfolders. "
            "Defaults to $RENDERS_DIR (falls back to /data/renders)."
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and print the summary without writing any changes",
    )
    args = p.parse_args(argv)

    settings = get_settings()
    if args.renders_dir is not None:
        renders_dir = args.renders_dir
    else:
        env_dir = os.environ.get("RENDERS_DIR")
        renders_dir = Path(env_dir) if env_dir else settings.renders_dir
    content_dir = settings.portal_content_dir

    engine = get_engine()
    stats = backfill_legacy_renders(
        engine,
        renders_dir=renders_dir,
        content_dir=content_dir,
        dry_run=args.dry_run,
    )
    print_summary(stats, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
