"""One-shot: rename misnamed legacy renders.

Background
----------
An early version of ``backfill_legacy_renders.py`` hardcoded
``original_name="iso-render.png"`` for every imported render. It always
picked the alphabetically-first PNG in the legacy renders dir, which was
``front.png``. So 89 ModelFile rows ended up wrongly named ``iso-render.png``
when their content was actually the front view.

The fix landed shortly after; the second run imported ``iso.png`` (correctly
named ``iso-render.png``), ``side.png`` (named ``side-render.png``) and
``top.png`` (named ``top-render.png``). Models touched by both runs now have
**two** ModelFile rows named ``iso-render.png`` — the older one is the front
view and needs to be renamed.

This script
-----------
For every model with at least two ``kind=image`` ModelFile rows whose
``original_name == "iso-render.png"``, the OLDEST one (by ``created_at``)
gets renamed to ``front-render.png``. Re-running is a no-op.

CLI: ``python -m scripts.fix_legacy_render_names [--dry-run]``
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.db.models import AuditLog, ModelFile, ModelFileKind
from app.core.db.session import get_engine

logger = logging.getLogger(__name__)


@dataclass
class FixStats:
    renamed: int = 0
    models_inspected: int = 0
    models_with_duplicates: int = 0


def fix_legacy_render_names(engine: Engine, *, dry_run: bool = False) -> FixStats:
    """Rename the OLDEST of multiple ``iso-render.png`` rows per model to ``front-render.png``."""
    stats = FixStats()
    with Session(engine) as session:
        rows = list(
            session.exec(
                select(ModelFile)
                .where(ModelFile.kind == ModelFileKind.image)
                .where(ModelFile.original_name == "iso-render.png")
            ).all()
        )

    by_model: dict[uuid.UUID, list[ModelFile]] = defaultdict(list)
    for row in rows:
        by_model[row.model_id].append(row)
    stats.models_inspected = len(by_model)

    for model_id, files in by_model.items():
        if len(files) < 2:
            continue
        stats.models_with_duplicates += 1
        files_sorted = sorted(files, key=lambda f: f.created_at)
        # Rename all but the LATEST one to front-render.png. With 4-view backfill
        # there will only be one duplicate, but loop handles edge cases too.
        for old in files_sorted[:-1]:
            if dry_run:
                logger.info(
                    "[dry-run] would rename ModelFile %s on model %s: iso-render.png → front",
                    old.id,
                    model_id,
                )
                stats.renamed += 1
                continue

            with Session(engine) as session:
                fresh = session.exec(select(ModelFile).where(ModelFile.id == old.id)).one()
                if fresh.original_name != "iso-render.png":
                    # Already renamed by a parallel run; skip silently.
                    continue
                before = {"original_name": fresh.original_name}
                fresh.original_name = "front-render.png"
                session.add(fresh)
                session.add(
                    AuditLog(
                        actor_user_id=None,
                        action="model_file.legacy_render.rename",
                        entity_type="model_file",
                        entity_id=fresh.id,
                        before_json=json.dumps(before),
                        after_json=json.dumps({"original_name": "front-render.png"}),
                    )
                )
                session.commit()
                stats.renamed += 1
                logger.info(
                    "renamed ModelFile %s on model %s: iso-render.png → front-render.png",
                    old.id,
                    model_id,
                )

    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    stats = fix_legacy_render_names(get_engine(), dry_run=args.dry_run)
    prefix = "[dry-run] " if args.dry_run else ""
    print(f"{prefix}Legacy render name fix summary")
    print(f"  Renamed:                {stats.renamed}")
    print(f"  Models with duplicates: {stats.models_with_duplicates}")
    print(f"  Models inspected:       {stats.models_inspected}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
