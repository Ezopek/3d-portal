"""Default-matrix backfill — operator-supervised one-shot script (Story 35.6).

Pre-computes the bounded default-matrix estimates: for each (published offer ×
enabled material_default) pair, walks all catalog ``kind=stl`` ModelFile rows and
idempotently enqueues the ``(stl_hash, bundle_hash)`` slice job.

Idempotent: a ``(stl_hash, bundle_hash)`` pair that already has a ``fresh`` estimate
is skipped (``already_fresh``). Duplicate enqueues while one is queued/running are
de-duped by arq's ``slice_job_id`` — re-running the script is safe (FR23-BACKFILL-1).

NOT auto-run by ``deploy.sh`` — operator-supervised only (same posture as
``enqueue_estimate_backfill.py``).

Usage (operator-supervised)::

    docker compose -f infra/docker-compose.yml exec api \\
        python -m scripts.enqueue_default_matrix_backfill

    # Dry-run: enumerate matrix + STL count only (no bundle resolve, no enqueue):
    docker compose -f infra/docker-compose.yml exec api \\
        python -m scripts.enqueue_default_matrix_backfill --dry-run

    # Include per-Spoolman-filament overrides (opt-in only — G-BACKFILL-OPT-IN):
    docker compose -f infra/docker-compose.yml exec api \\
        python -m scripts.enqueue_default_matrix_backfill --include-overrides

Exit codes:
    0  success (possibly with classified failures)
    1  unexpected error (logged to stderr)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from arq import create_pool
from arq.connections import RedisSettings
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.db.models import ModelFile, ModelFileKind
from app.core.db.session import get_engine
from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.estimate_store import EstimateStore
from app.modules.slicer.matrix_backfill import (
    ResolvedMatrixCell,
    enumerate_matrix_cells,
    load_active_matrix,
    resolve_matrix_cells,
)
from app.modules.slicer.models import EstimateStatus
from app.modules.slicer.profile_offer import list_offers
from app.modules.slicer.profile_policy import ProfilePolicyStore
from app.modules.slicer.resolver import VendoredProfileSource
from app.modules.slicer.stl_cache import StlCache, is_content_hash
from app.modules.slicer.validation import NullCliValidator

_LOG = logging.getLogger("scripts.enqueue_default_matrix_backfill")


@dataclass
class MatrixBackfillStats:
    """Classified counters for the default-matrix backfill run (AC-5)."""

    inspected: int = 0          # total STL rows inspected
    cells_total: int = 0        # total matrix cells enumerated
    cells_resolved: int = 0     # cells with a resolved bundle_hash
    cells_resolve_failed: int = 0  # cells that failed to resolve
    enqueued: int = 0
    already_fresh: int = 0
    missing_stl: int = 0
    errors: int = 0
    # Dry-run only: STL parts on disk that WOULD be enqueued (per matrix cell)
    would_enqueue: int = 0


def _inventory_stl(
    row: ModelFile, *, content_root: Path, stats: MatrixBackfillStats, cells_resolved: int
) -> None:
    """Dry-run classification of one STL part (path + existence only, no resolve/enqueue)."""
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
    stats.would_enqueue += cells_resolved
    _LOG.info("dry-run would-enqueue ModelFile %s (%s) × %d cells", row.id, row.storage_path, cells_resolved)


async def run(
    *,
    engine: Any,
    stl_cache: StlCache,
    estimate_store: EstimateStore,
    arq_pool: Any,
    matrix_cells: list[ResolvedMatrixCell],
    content_dir: Path,
    dry_run: bool = False,
    _session_factory: Any = None,
) -> MatrixBackfillStats:
    """Walk all ``kind=stl`` ModelFile rows and ingest (or inventory) for each matrix cell.

    Seam-injected: ``engine``, ``stl_cache``, ``estimate_store``, ``arq_pool``,
    ``matrix_cells``, ``content_dir``, and ``dry_run`` are all parameters.
    ``_session_factory`` is a test seam — production uses ``Session(engine)``.
    """
    from app.modules.slicer.enqueue import enqueue_slice_estimate

    if _session_factory is None:
        _session_factory = lambda eng: Session(eng)  # noqa: E731

    content_root = Path(content_dir).resolve()
    stats = MatrixBackfillStats()

    # Classify cells up front
    active_cells = [rc for rc in matrix_cells if rc.bundle_hash is not None]
    failed_cells = [rc for rc in matrix_cells if rc.resolve_failed]
    stats.cells_total = len(matrix_cells)
    stats.cells_resolved = len(active_cells)
    stats.cells_resolve_failed = len(failed_cells)

    with _session_factory(engine) as session:
        rows = session.exec(select(ModelFile).where(ModelFile.kind == ModelFileKind.stl)).all()

    for row in rows:
        stats.inspected += 1
        if dry_run:
            _inventory_stl(row, content_root=content_root, stats=stats, cells_resolved=len(active_cells))
            continue

        abs_path = (content_root / row.storage_path).resolve()
        try:
            abs_path.relative_to(content_root)
        except ValueError:
            stats.errors += len(active_cells) if active_cells else 1
            _LOG.warning("path-escape on ModelFile %s (%s) — skipped", row.id, row.storage_path)
            continue
        if not abs_path.is_file():
            stats.missing_stl += len(active_cells) if active_cells else 1
            _LOG.warning("missing STL for ModelFile %s (%s)", row.id, row.storage_path)
            continue

        candidate_stl_hash = row.sha256
        if not is_content_hash(candidate_stl_hash):
            stats.errors += len(active_cells) if active_cells else 1
            _LOG.warning(
                "ModelFile %s carries non-content-hash sha256 %r — skipped",
                row.id,
                candidate_stl_hash,
            )
            continue

        for rc in active_cells:
            existing = estimate_store.read(candidate_stl_hash, rc.bundle_hash)
            if existing is not None and existing.status == EstimateStatus.fresh:
                stats.already_fresh += 1
                continue
            try:
                await enqueue_slice_estimate(
                    arq_pool,
                    source_stl=abs_path,
                    bundle_hash=rc.bundle_hash,
                    stl_cache=stl_cache,
                )
                stats.enqueued += 1
            except Exception:
                _LOG.exception(
                    "enqueue failed for ModelFile %s cell offer_id=%s material=%s",
                    row.id,
                    rc.cell.offer_id,
                    rc.cell.material,
                )
                stats.errors += 1

    return stats


async def _run_production(*, dry_run: bool, include_overrides: bool) -> MatrixBackfillStats:
    """Wire the real settings-backed seams and run the backfill."""
    settings = get_settings()
    content_dir = settings.portal_content_dir.resolve()
    engine = get_engine()
    stl_cache = StlCache(settings.slicer_stl_cache_dir)
    estimate_store = EstimateStore(settings.slicer_estimate_store_dir)
    source = VendoredProfileSource(settings.slicer_vendored_profiles_dir)
    store = BundleStore(settings.slicer_bundle_store_dir)
    policy_store = ProfilePolicyStore(settings.slicer_profile_policy_dir)

    offers = list_offers(source.root)
    policy = policy_store.load()
    cells = enumerate_matrix_cells(offers, policy)

    # G-BACKFILL-OPT-IN: additionally include filament_overrides (Story 35.6 fix)
    if include_overrides and policy.filament_overrides:
        from app.modules.slicer.matrix_backfill import MatrixCell
        from app.modules.slicer.profile_policy import normalize_material
        from app.modules.spools.service import SpoolsService

        # We need the Spoolman snapshot to know which material each ref belongs to
        # so we can find compatible offers.
        _LOG.info("Loading Spoolman snapshot to resolve override compatibility...")
        snapshot = await SpoolsService(redis_factory=None, client=None).get_summary()
        ref_to_material = {
            f"{f.vendor_name or ''}\x1f{f.name}": normalize_material(f.material)
            for f in snapshot.filaments
        }

        for ref, override in policy.filament_overrides.items():
            if not override.enabled:
                continue
            material = ref_to_material.get(ref)
            if not material:
                continue
            for sidecar in offers:
                if publish_state_of(sidecar).publish_state != PUBLISH_STATE_PUBLISHED:
                    continue
                compatible = set(sidecar.get("compatible_material_categories") or [])
                if material in compatible:
                    cells.append(
                        MatrixCell(
                            offer_id=sidecar.get("offer_id", ""),
                            offer_label=sidecar.get("label", ""),
                            material=material,
                            orca_profile_ref=override.orca_filament_profile_ref,
                        )
                    )

    if dry_run:
        stl_count = 0
        with Session(engine) as sess:
            stl_count = len(
                sess.exec(select(ModelFile).where(ModelFile.kind == ModelFileKind.stl)).all()
            )
        stats = MatrixBackfillStats()
        stats.cells_total = len(cells)
        stats.cells_resolved = len(cells)
        stats.would_enqueue = len(cells) * stl_count
        return stats

    resolved = resolve_matrix_cells(
        cells,
        source=source,
        store=store,
        orca_version=settings.orca_version,
        validator=NullCliValidator(),
        offers_map={s.get("offer_id", ""): s for s in offers if s.get("offer_id")},
    )

    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        stats = await run(
            engine=engine,
            stl_cache=stl_cache,
            estimate_store=estimate_store,
            arq_pool=pool,
            matrix_cells=resolved,
            content_dir=content_dir,
            dry_run=False,
        )
    finally:
        await pool.aclose()

    return stats


def _print_summary(stats: MatrixBackfillStats, *, dry_run: bool) -> None:
    """Print human-readable operator summary to stdout."""
    if dry_run:
        print(
            f"[dry-run] matrix_cells={stats.cells_total} "
            f"would_enqueue={stats.would_enqueue} "
            f"missing_stl={stats.missing_stl}",
            file=sys.stdout,
        )
        return
    print(
        f"inspected={stats.inspected} "
        f"cells={stats.cells_total} "
        f"enqueued={stats.enqueued} "
        f"already_fresh={stats.already_fresh} "
        f"resolve_failed={stats.cells_resolve_failed} "
        f"missing_stl={stats.missing_stl} "
        f"errors={stats.errors}",
        file=sys.stdout,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Enumerate matrix + STL count only; do not resolve, do not enqueue.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable INFO-level logging.",
    )
    parser.add_argument(
        "--include-overrides",
        action="store_true",
        help="Also backfill filament_overrides entries (G-BACKFILL-OPT-IN; off by default).",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    try:
        stats = asyncio.run(_run_production(dry_run=args.dry_run, include_overrides=args.include_overrides))
    except Exception:
        _LOG.exception("default-matrix backfill failed")
        return 1

    if not args.dry_run:
        _print_summary(stats, dry_run=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
