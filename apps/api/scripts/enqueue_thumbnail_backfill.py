"""Story 13.2 / Decision P + 22.1 / Decision W — WebP variant backfill for image-kind ModelFiles.

Runs inside the API container (where the DB + Redis + content volume are all
reachable). Walks every ``ModelFile`` of kind ``image`` or ``print``, checks
the two sibling tiers on disk:

    - ``<storage_path>.thumb.webp``    (Story 13.2, 800 px tier)
    - ``<storage_path>.gallery.webp``  (Story 22.1, 1920 px tier)

A ``ModelFile`` is considered ``already_present`` only when BOTH tiers
exist. If either tier is missing the script either enqueues a single
``generate_thumbnail`` arq job (which now produces both tiers in one
pass — Story 22.1 composite return) OR (with ``--inline``) runs the
Pillow pipelines in-process for synchronous, deterministic feedback.

Idempotent: each tier's ``*_sync`` function short-circuits on its own
sibling presence, so re-running this script is safe even when only one
tier is missing.

Usage (operator-supervised, NOT auto-run by deploy.sh)::

    docker compose -f infra/docker-compose.yml exec api \\
        python -m scripts.enqueue_thumbnail_backfill

    # Bypass arq entirely (synchronous, single-worker):
    docker compose -f infra/docker-compose.yml exec api \\
        python -m scripts.enqueue_thumbnail_backfill --inline

    # Dry-run inventory (no enqueue, no rendering):
    docker compose -f infra/docker-compose.yml exec api \\
        python -m scripts.enqueue_thumbnail_backfill --dry-run

Exit codes:
    0  success (possibly with skipped files)
    1  unexpected error (logged to stderr)

The wrapper script ``infra/scripts/backfill-thumbnails.sh`` runs this from
the operator's workstation against the live ``.190`` deployment.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from dataclasses import dataclass

from arq import create_pool
from arq.connections import RedisSettings
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.db.models import ModelFile, ModelFileKind
from app.core.db.session import get_engine
from app.workers.generate_thumbnail import (
    GALLERY_SUFFIX,
    THUMBNAIL_SUFFIX,
    generate_gallery_sync,
    generate_thumbnail_sync,
)

_LOG = logging.getLogger("scripts.enqueue_thumbnail_backfill")


@dataclass
class BackfillStats:
    inspected: int = 0
    already_present_thumb: int = 0
    already_present_gallery: int = 0
    enqueued: int = 0
    rendered_thumb: int = 0
    rendered_gallery: int = 0
    missing_original: int = 0
    errors: int = 0


_IMAGE_KINDS = (ModelFileKind.image, ModelFileKind.print)


async def run(
    *,
    inline: bool = False,
    dry_run: bool = False,
) -> BackfillStats:
    """Walk every image/print ModelFile and either enqueue or render the variant."""
    settings = get_settings()
    content_dir = settings.portal_content_dir.resolve()
    engine = get_engine()

    pool = None
    if not (inline or dry_run):
        pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))

    stats = BackfillStats()
    try:
        with Session(engine) as s:
            rows = s.exec(select(ModelFile).where(ModelFile.kind.in_(_IMAGE_KINDS))).all()
        for row in rows:
            stats.inspected += 1
            original_abs = (content_dir / row.storage_path).resolve()
            try:
                original_abs.relative_to(content_dir)
            except ValueError:
                stats.errors += 1
                _LOG.warning("path-escape on %s — skipped", row.storage_path)
                continue

            thumb_abs = original_abs.with_name(original_abs.name + THUMBNAIL_SUFFIX)
            gallery_abs = original_abs.with_name(original_abs.name + GALLERY_SUFFIX)
            thumb_present = thumb_abs.exists()
            gallery_present = gallery_abs.exists()
            if thumb_present:
                stats.already_present_thumb += 1
            if gallery_present:
                stats.already_present_gallery += 1
            # Story 22.1 / Decision W — a ModelFile is fully covered only
            # when BOTH tiers exist. Skip enqueue/render only in that case.
            if thumb_present and gallery_present:
                continue

            if not original_abs.exists():
                stats.missing_original += 1
                _LOG.warning("missing original %s for ModelFile %s", row.storage_path, row.id)
                continue

            if dry_run:
                tiers_present = (
                    ("thumb", thumb_present),
                    ("gallery", gallery_present),
                )
                missing_tiers = ",".join(t for t, present in tiers_present if not present)
                _LOG.info(
                    "dry-run would-process ModelFile %s (%s) — missing: %s",
                    row.id,
                    row.storage_path,
                    missing_tiers,
                )
                continue

            if inline:
                # Story 22.1 — invoke each tier's sync function independently.
                # Failure isolation: a render failure on one tier does NOT
                # block the other (mirrors arq composite return semantics).
                if not thumb_present:
                    t_result = generate_thumbnail_sync(engine, row.id, content_dir=content_dir)
                    if t_result["status"] == "ok":
                        stats.rendered_thumb += 1
                    else:
                        stats.errors += 1
                if not gallery_present:
                    g_result = generate_gallery_sync(engine, row.id, content_dir=content_dir)
                    if g_result["status"] == "ok":
                        stats.rendered_gallery += 1
                    else:
                        stats.errors += 1
            else:
                assert pool is not None
                # Route to api-arq-worker's dedicated queue (Story 13.2 post-Codex
                # hot-fix 2026-05-22 — see apps/api/app/workers/__init__.py
                # `API_QUEUE_NAME`) so the render-worker (which consumes the
                # default `arq:queue` and lacks `generate_thumbnail`) does not
                # pick up these jobs and reject them with "function not found".
                #
                # Story 22.1: the arq task now produces BOTH tiers per job;
                # one enqueue per ModelFile still covers the full backfill.
                from app.workers import API_QUEUE_NAME

                await pool.enqueue_job("generate_thumbnail", row.id, _queue_name=API_QUEUE_NAME)
                stats.enqueued += 1
    finally:
        if pool is not None:
            await pool.aclose()
    return stats


def _print_summary(stats: BackfillStats) -> None:
    """Print human-readable summary to stdout (operator-readable).

    Story 22.1 / Decision W extended the format to expose per-tier counters
    so operators can tell which tier(s) the backfill produced. Sample::

        inspected=842 already_present_thumb=812 already_present_gallery=0
        enqueued=830 rendered_thumb=0 rendered_gallery=0
        missing_original=0 errors=0
    """
    print(
        f"inspected={stats.inspected} "
        f"already_present_thumb={stats.already_present_thumb} "
        f"already_present_gallery={stats.already_present_gallery} "
        f"enqueued={stats.enqueued} "
        f"rendered_thumb={stats.rendered_thumb} "
        f"rendered_gallery={stats.rendered_gallery} "
        f"missing_original={stats.missing_original} "
        f"errors={stats.errors}",
        file=sys.stdout,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--inline",
        action="store_true",
        help="Run Pillow pipeline in-process (no arq dependency). Slower but deterministic.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inventory only; do not enqueue and do not render.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable INFO-level logging on script + app.workers.thumbnail.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    try:
        stats = asyncio.run(run(inline=args.inline, dry_run=args.dry_run))
    except Exception:
        _LOG.exception("backfill failed")
        return 1

    _print_summary(stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
