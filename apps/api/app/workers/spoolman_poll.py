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
            snapshot = await service.refresh_summary()
        return 1 if snapshot is not None else 0
    finally:
        await redis_factory.aclose()
