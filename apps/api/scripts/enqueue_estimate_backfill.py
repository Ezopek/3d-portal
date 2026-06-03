"""EST-INGEST-1 — operator-supervised first-estimate backfill for catalog STL parts.

Walks every ``kind=stl`` ``ModelFile`` and, for each, triggers the first slicer
estimate via the ingestion service (:func:`app.modules.slicer.ingest.ingest_stl_part`)
— which resolves the configurable default print-intent preset to a persisted bundle,
content-hashes + caches the STL bytes, and idempotently enqueues the deduped
``(stl_hash, bundle_hash)`` job on the dedicated ``arq:slicer`` queue.

Idempotent: a part whose ``(stl_hash, bundle_hash)`` already has a ``fresh`` estimate
is skipped (``already_fresh``); a duplicate enqueue while one is queued/running is a
``slice_job_id`` de-dup no-op. Re-running the backfill never re-slices an
already-estimated part. Classified, never silent: a missing STL, a path escape, or a
resolve failure (no vendored profile / unsupported material) surfaces as a typed
status + log line and the walk continues to the next part — never a silent zero.

Runs inside the API container (DB + Redis + content volume all reachable). Mirrors
``enqueue_thumbnail_backfill.py``; NOT auto-run by deploy.sh.

Usage (operator-supervised)::

    docker compose -f infra/docker-compose.yml exec api \\
        python -m scripts.enqueue_estimate_backfill

    # Dry-run inventory (no resolve, no enqueue):
    docker compose -f infra/docker-compose.yml exec api \\
        python -m scripts.enqueue_estimate_backfill --dry-run

Exit codes:
    0  success (possibly with skipped/classified-failure parts)
    1  unexpected error (logged to stderr)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arq import create_pool
from arq.connections import RedisSettings
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.db.models import ModelFile, ModelFileKind
from app.core.db.session import get_engine
from app.modules.slicer.estimate_store import EstimateStore
from app.modules.slicer.ingest import (
    IngestResult,
    IngestStatus,
    ingest_stl_part,
)
from app.modules.slicer.models import PrintIntentPreset
from app.modules.slicer.resolver import resolve_intent
from app.modules.slicer.stl_cache import StlCache

_LOG = logging.getLogger("scripts.enqueue_estimate_backfill")


@dataclass
class BackfillStats:
    inspected: int = 0
    enqueued: int = 0
    already_fresh: int = 0
    resolve_failed: int = 0
    missing_stl: int = 0
    errors: int = 0
    # Dry-run only: STL parts present on disk that WOULD be enqueued (freshness is not
    # checked in dry-run because that needs a resolve, which persists a bundle).
    would_enqueue: int = 0

    def record(self, result: IngestResult) -> None:
        """Fold one classified ingest result into the counters."""
        if result.status == IngestStatus.enqueued:
            self.enqueued += 1
        elif result.status == IngestStatus.already_fresh:
            self.already_fresh += 1
        elif result.status == IngestStatus.resolve_failed:
            self.resolve_failed += 1
        elif result.status == IngestStatus.missing_stl:
            self.missing_stl += 1
        elif result.status == IngestStatus.error:
            self.errors += 1
        # skipped_non_stl cannot occur — the query pre-filters to kind=stl.


def _default_preset(settings: Any) -> PrintIntentPreset:
    """Build the single default print-intent preset from settings.

    Construction validates ``material_class`` / ``quality_tier`` against their Literal
    sets, so a bad env value fails loud here rather than silently mis-resolving.
    """
    material = settings.slicer_default_material_class
    quality = settings.slicer_default_quality_tier
    return PrintIntentPreset(
        name=f"{material} {quality}",
        material_class=material,
        quality_tier=quality,
        printer_ref=settings.slicer_default_printer_ref,
        is_default=True,
    )


def _inventory_part(row: ModelFile, *, content_root: Path, stats: BackfillStats) -> None:
    """Dry-run classification of one STL part — path/existence only, no resolve/enqueue."""
    abs_path = (content_root / row.storage_path).resolve()
    try:
        abs_path.relative_to(content_root)
    except ValueError:
        stats.errors += 1
        _LOG.warning("path-escape on ModelFile %s (%s) — skipped", row.id, row.storage_path)
        return
    if not abs_path.is_file():
        stats.missing_stl += 1
        _LOG.warning("missing STL for ModelFile %s (%s)", row.id, row.storage_path)
        return
    stats.would_enqueue += 1
    _LOG.info("dry-run would-enqueue ModelFile %s (%s)", row.id, row.storage_path)


async def run(
    *,
    engine: Any,
    stl_cache: StlCache,
    estimate_store: EstimateStore,
    resolve_fn: Any,
    default_preset: PrintIntentPreset,
    content_dir: Path,
    arq_pool: Any = None,
    dry_run: bool = False,
) -> BackfillStats:
    """Walk every ``kind=stl`` ModelFile and ingest (or inventory) each part.

    Seam-injected for testability: ``engine``, ``stl_cache``, ``estimate_store``,
    ``resolve_fn``, ``default_preset``, ``content_dir`` and (enqueue mode) ``arq_pool``
    are all parameters. The production ``main()`` wires the real settings-backed seams.
    """
    content_root = Path(content_dir).resolve()
    with Session(engine) as session:
        rows = session.exec(select(ModelFile).where(ModelFile.kind == ModelFileKind.stl)).all()

    stats = BackfillStats()
    for row in rows:
        stats.inspected += 1
        if dry_run:
            _inventory_part(row, content_root=content_root, stats=stats)
            continue
        result = await ingest_stl_part(
            row,
            arq_pool=arq_pool,
            stl_cache=stl_cache,
            estimate_store=estimate_store,
            resolve_fn=resolve_fn,
            default_preset=default_preset,
            content_dir=content_root,
        )
        stats.record(result)
    return stats


async def _run_production(*, dry_run: bool) -> BackfillStats:
    """Wire the real settings-backed seams and run the backfill."""
    settings = get_settings()
    content_dir = settings.portal_content_dir.resolve()
    engine = get_engine()
    stl_cache = StlCache(settings.slicer_stl_cache_dir)
    estimate_store = EstimateStore(settings.slicer_estimate_store_dir)
    default_preset = _default_preset(settings)

    pool = None
    if not dry_run:
        pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        return await run(
            engine=engine,
            stl_cache=stl_cache,
            estimate_store=estimate_store,
            # resolve_intent is settings-wired: real writing BundleStore (so the worker
            # can load_bundle) + AttributionStore reverse index.
            resolve_fn=resolve_intent,
            default_preset=default_preset,
            content_dir=content_dir,
            arq_pool=pool,
            dry_run=dry_run,
        )
    finally:
        if pool is not None:
            await pool.aclose()


def _print_summary(stats: BackfillStats, *, dry_run: bool) -> None:
    """Print a human-readable operator summary to stdout."""
    if dry_run:
        print(
            f"[dry-run] inspected={stats.inspected} "
            f"would_enqueue={stats.would_enqueue} "
            f"missing_stl={stats.missing_stl} "
            f"errors={stats.errors}",
            file=sys.stdout,
        )
        return
    print(
        f"inspected={stats.inspected} "
        f"enqueued={stats.enqueued} "
        f"already_fresh={stats.already_fresh} "
        f"resolve_failed={stats.resolve_failed} "
        f"missing_stl={stats.missing_stl} "
        f"errors={stats.errors}",
        file=sys.stdout,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inventory only; do not resolve, do not enqueue.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable INFO-level logging on the script + the ingestion service.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    try:
        stats = asyncio.run(_run_production(dry_run=args.dry_run))
    except Exception:
        _LOG.exception("estimate backfill failed")
        return 1

    _print_summary(stats, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
