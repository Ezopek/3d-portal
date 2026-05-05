"""Idempotent one-shot script: backfill `Model.thumbnail_file_id` for legacy data.

The original migration (``scripts.migrate_from_index_json``) only set the
thumbnail when the legacy ``index.json`` named one explicitly. Models migrated
without that field landed with ``thumbnail_file_id IS NULL`` and the catalog
list shows no preview image.

For each ``Model`` with a NULL thumbnail this script picks the earliest
attached ``ModelFile`` whose kind is ``image`` or ``print``, ordered by
``(position NULLS LAST, created_at)``. If no such file exists, the model is
left untouched. Models that already have a thumbnail are never modified.

Each backfill is recorded in ``audit_log`` as ``model.thumbnail.backfill`` with
before/after JSON capturing the previous (NULL) and new ``thumbnail_file_id``.

Usage::

    python -m scripts.backfill_thumbnails [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
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


@dataclass
class BackfillStats:
    backfilled: int = 0
    already_set: int = 0
    no_image: int = 0


def pick_thumbnail_file(session: Session, model_id: uuid.UUID) -> ModelFile | None:
    """Return the earliest image/print file for a model, or None.

    Ordering matches the catalog file listing: position NULLS LAST first, then
    upload-time (``created_at``) ascending.
    """
    from sqlalchemy import nullslast

    stmt = (
        select(ModelFile)
        .where(
            ModelFile.model_id == model_id,
            ModelFile.kind.in_([ModelFileKind.image, ModelFileKind.print]),
        )
        .order_by(nullslast(ModelFile.position.asc()), ModelFile.created_at.asc())
        .limit(1)
    )
    return session.exec(stmt).first()


def backfill_thumbnails(engine: Engine, *, dry_run: bool = False) -> BackfillStats:
    """Walk every Model and backfill ``thumbnail_file_id`` from image/print files.

    Each successful backfill is committed in its own transaction together with
    the corresponding ``audit_log`` row, so a partial failure cannot leave the
    DB in a skewed state.
    """
    stats = BackfillStats()

    with Session(engine) as session:
        models = list(session.exec(select(Model)).all())

    for m in models:
        if m.thumbnail_file_id is not None:
            stats.already_set += 1
            continue

        with Session(engine) as session:
            # Re-fetch in this session to avoid using a detached row.
            model = session.exec(select(Model).where(Model.id == m.id)).one()
            if model.thumbnail_file_id is not None:
                # Concurrent update — treat as already-set.
                stats.already_set += 1
                continue

            chosen = pick_thumbnail_file(session, model.id)
            if chosen is None:
                stats.no_image += 1
                logger.info(
                    "no image/print file for model %s (%s) — skipping",
                    model.slug,
                    model.id,
                )
                continue

            before = {"thumbnail_file_id": None}
            after = {"thumbnail_file_id": str(chosen.id)}

            if dry_run:
                logger.info(
                    "[dry-run] would set thumbnail of %s to %s (file %s)",
                    model.slug,
                    chosen.id,
                    chosen.original_name,
                )
                stats.backfilled += 1
                continue

            model.thumbnail_file_id = chosen.id
            session.add(model)
            session.add(
                AuditLog(
                    actor_user_id=None,
                    action="model.thumbnail.backfill",
                    entity_type="model",
                    entity_id=model.id,
                    before_json=json.dumps(before),
                    after_json=json.dumps(after),
                )
            )
            session.commit()
            stats.backfilled += 1
            logger.info(
                "backfilled thumbnail for %s (%s) → %s",
                model.slug,
                model.id,
                chosen.original_name,
            )

    return stats


def print_summary(stats: BackfillStats, *, dry_run: bool) -> None:
    prefix = "[dry-run] " if dry_run else ""
    print(f"{prefix}Thumbnail backfill summary")
    print(f"  Backfilled:   {stats.backfilled}")
    print(f"  Already set:  {stats.already_set}")
    print(f"  No image:     {stats.no_image}")
    total = stats.backfilled + stats.already_set + stats.no_image
    print(f"  Total models: {total}")


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and print the summary without writing any changes",
    )
    args = p.parse_args(argv)

    engine = get_engine()
    stats = backfill_thumbnails(engine, dry_run=args.dry_run)
    print_summary(stats, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
