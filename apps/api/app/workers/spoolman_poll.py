"""Initiative 19 Story 31.1 (Decision AD) — arq cron task that refreshes
the Spoolman snapshot every 60s.

Single-poller leader-election via the SETNX lock in
``SpoolsService.refresh_summary``; safe to run on multiple api-arq replicas.
Returns 1 when this worker acquired the lock and wrote a fresh snapshot, 0
otherwise (lock contention OR upstream Spoolman failure with cache
untouched).
"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.redis import RedisFactory
from app.modules.slicer.spoolman_event_source import build_spoolman_invalidation_handler
from app.modules.spools.client import SpoolmanClient
from app.modules.spools.service import SpoolsService


async def poll_spoolman_summary(_ctx: dict) -> int:
    settings = get_settings()
    redis_factory = RedisFactory(url=settings.redis_url)
    try:
        async with SpoolmanClient(
            base_url=settings.spoolman_url,
            auth_token=settings.spoolman_auth_token,
        ) as client:
            service = SpoolsService(redis_factory=redis_factory, client=client)
            # SPOOL-EVT-1 — wire the live change source onto the EXISTING poll (no second
            # Spoolman read). ``_ctx["redis"]`` is the arq pool arq injects into every job
            # ctx (worker.py:361 ``self.ctx['redis'] = self.pool``); the mapped-override path
            # enqueues re-slices on it. ``.get`` keeps the cron resilient if a future runner
            # invokes it without an arq-provided pool (then no enqueue surface is available,
            # but the cost-only/no-op paths still work — None only breaks an actual enqueue).
            change_handler = build_spoolman_invalidation_handler(
                _ctx.get("redis"), settings=settings
            )
            snapshot = await service.refresh_summary(change_handler=change_handler)
        return 1 if snapshot is not None else 0
    finally:
        await redis_factory.aclose()
