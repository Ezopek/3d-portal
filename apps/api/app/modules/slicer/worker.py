"""Dedicated slicer-worker arq entrypoint (Story 32.2, AC-1/AC-7, Decision AI).

The configs-side ``slicer-worker`` container (AC-12) runs::

    arq app.modules.slicer.worker.SlicerWorkerSettings

Mirrors the proven render-worker shape (``workers/render/render/worker.py``): a bare
class-attribute ``redis_settings`` (the classmethod gotcha would brick the container
in a restart loop), an ``on_startup`` that wires the injected deps into ``ctx``, and a
SMALL bounded ``max_jobs`` cap so a minutes-long CPU-heavy slice cannot starve the
API/render workers on ``.190`` (NFR20-RESOURCE-1). Its OWN dedicated queue keeps the
slicer pool from grabbing a render/api job and rejecting it (the cross-queue-grab
bug documented in ``app/workers/__init__.py``).
"""

from __future__ import annotations

from typing import Any, ClassVar

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.observability import init_observability
from app.core.sentry import init_sentry
from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.cli import OrcaCli
from app.modules.slicer.stl_cache import StlCache
from app.modules.slicer.worker_job import slice_estimate

#: Dedicated slicer queue — because "dedicated queue so the slicer pool never grabs a
#: render/api job and rejects it 'function not found' — the cross-queue-grab bug in
#: app/workers/__init__.py; mirrors API_QUEUE_NAME" (AC-10). Distinct from the render
#: default ``arq:queue`` and the api ``arq:api``.
SLICER_QUEUE_NAME = "arq:slicer"


async def startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    init_observability(
        service_name="3d-portal-slicer-worker",
        service_version=settings.app_version,
        environment=settings.environment,
        otlp_endpoint=settings.otel_exporter_otlp_endpoint,
    )
    init_sentry(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=settings.portal_version,
    )
    ctx["cli"] = OrcaCli.from_settings(settings)
    ctx["stl_cache"] = StlCache(settings.slicer_stl_cache_dir)
    ctx["bundle_store"] = BundleStore(settings.slicer_bundle_store_dir)
    ctx["orca_version"] = settings.orca_version
    # gcode_sink defaults to the no-op discard (worker_job); Story 32.3 wires a parser.


class SlicerWorkerSettings:
    """arq worker configuration for the dedicated slicer pool."""

    queue_name: ClassVar[str] = SLICER_QUEUE_NAME
    functions: ClassVar[list] = [slice_estimate]
    on_startup = startup
    # Bare class attribute + eager call — arq reads `.host` on it directly; wrapping
    # in @classmethod resolves to a bound method with no .host and bricks the
    # container in a restart loop (the gotcha from app/workers/__init__.py).
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    # Small bounded cap (default 1) so a minutes-long slice can't starve API/render
    # workers on .190 — NFR20-RESOURCE-1 / OD-6 (AC-7/AC-10). Sourced from settings so
    # the configs-side container can lift it to 2 if headroom allows.
    max_jobs = get_settings().slicer_max_concurrency
    # arq job-execution backstop: generously above our own subprocess wall-time bound
    # (slice + info + overhead) so arq never kills the job before cli.py classifies a
    # `timeout` itself (AC-7). The subprocess runner owns the real wall-time terminate.
    job_timeout = (
        get_settings().slicer_slice_timeout_seconds
        + get_settings().slicer_info_timeout_seconds
        + 60
    )
