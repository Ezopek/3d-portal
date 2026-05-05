"""Idempotent one-shot script: prefer iso-render.png as the auto-thumbnail.

Pre-refactor the catalog used the iso render as the default thumbnail for
models without user-uploaded photos. Post-refactor several models ended up
pointing at a different auto-render (front/side/top) — typically because
either ``backfill_thumbnails.py`` picked the earliest by ``created_at`` or
``backfill_legacy_renders.py`` imported a non-iso PNG first. This script
restores the iso-as-thumbnail convention for models that have no curated
photos.

For each ``Model``:

1. Skip if it has any user-uploaded image (``kind in (image, print)`` and
   ``original_name`` not in the auto-render set). Those models keep
   whatever thumbnail the admin chose.
2. Otherwise, look up the ``ModelFile`` with ``original_name='iso-render.png'``
   for that model. If absent, skip.
3. Skip if ``thumbnail_file_id`` already points at that iso file.
4. Otherwise update ``thumbnail_file_id`` to the iso file id and write an
   audit log entry of action ``model.thumbnail.iso_default``.

Usage::

    python -m scripts.backfill_iso_thumbnail [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.db.models import (
    AuditLog,
    Model,
    ModelFile,
    ModelFileKind,
)
from app.core.db.session import get_engine

logger = logging.getLogger(__name__)

AUTO_RENDER_NAMES = frozenset(f"{view}-render.png" for view in ("front", "side", "top", "iso"))
ISO_NAME = "iso-render.png"


@dataclass
class BackfillStats:
    updated: int = 0
    already_iso: int = 0
    has_user_photos: int = 0
    no_iso_render: int = 0


def run(engine: Engine, *, dry_run: bool) -> BackfillStats:
    stats = BackfillStats()
    with Session(engine) as session:
        models = session.exec(select(Model).where(Model.deleted_at.is_(None))).all()
        for m in models:
            files = session.exec(
                select(ModelFile)
                .where(ModelFile.model_id == m.id)
                .where(ModelFile.kind.in_([ModelFileKind.image, ModelFileKind.print]))
            ).all()
            user_photos = [f for f in files if f.original_name not in AUTO_RENDER_NAMES]
            if user_photos:
                stats.has_user_photos += 1
                continue
            iso = next((f for f in files if f.original_name == ISO_NAME), None)
            if iso is None:
                stats.no_iso_render += 1
                continue
            if m.thumbnail_file_id == iso.id:
                stats.already_iso += 1
                continue
            before = str(m.thumbnail_file_id) if m.thumbnail_file_id is not None else None
            logger.info("model %s: thumbnail %s -> %s (iso-render.png)", m.id, before, iso.id)
            stats.updated += 1
            if dry_run:
                continue
            m.thumbnail_file_id = iso.id
            session.add(m)
            session.add(
                AuditLog(
                    actor_user_id=None,
                    action="model.thumbnail.iso_default",
                    entity_type="model",
                    entity_id=m.id,
                    before_json=json.dumps({"thumbnail_file_id": before}),
                    after_json=json.dumps({"thumbnail_file_id": str(iso.id)}),
                )
            )
        if not dry_run:
            session.commit()
    return stats


def _setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report changes without writing.")
    args = parser.parse_args(argv)
    engine = get_engine()
    stats = run(engine, dry_run=args.dry_run)
    logger.info(
        "done: updated=%d already_iso=%d has_user_photos=%d no_iso_render=%d (dry_run=%s)",
        stats.updated,
        stats.already_iso,
        stats.has_user_photos,
        stats.no_iso_render,
        args.dry_run,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = ["AUTO_RENDER_NAMES", "ISO_NAME", "BackfillStats", "main", "run"]
