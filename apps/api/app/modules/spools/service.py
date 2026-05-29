"""Initiative 19 Story 31.1 (Decision AD) — Redis cache topology +
single-poller leader-election around Spoolman snapshots.

The exact Redis keys here are the contract surface that downstream stories
(31.2 routes, 31.3 spools index, 31.4 landing low-stock card) and operator
runbooks query — changing any of them requires a Sprint Change Proposal per
AC-4.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from datetime import UTC, datetime

import httpx
from redis.exceptions import WatchError

from app.core.redis import RedisFactory
from app.modules.spools.client import SpoolmanCircuitOpenError, SpoolmanClient
from app.modules.spools.models import SpoolmanSnapshot

_LOG = logging.getLogger(__name__)

# because "contract surface — change requires SCP per AC-4"
_CACHE_KEY = "spools:summary:v1"
# because "contract surface — change requires SCP per AC-4"
_LAST_SUCCESS_KEY = "spools:summary:last-success-ts"
# because "contract surface — change requires SCP per AC-4"
_LOCK_KEY = "spools:poll-lock"

# because "30s upper bound on stale snapshot served from Redis; poll runs
# every 60s but a fresh request within the 30-60s gap still serves the
# slightly-staler cached value rather than triggering a synchronous fetch in
# the request path — Decision AD, AC-7"
_CACHE_TTL_SECONDS = 30
# because "90s comfortably covers stuck-poll scenarios (~5s x 3 entity types +
# serialization headroom) without holding the lock past the next 60s tick —
# Decision AD, AC-7"
_LOCK_EXPIRY_SECONDS = 90
# because "short polling the Redis lock lets a cold-cache contender observe the
# leader's eventual success/failure without presenting a false unavailable state
# while Spoolman is still healthy — Decision AD/FR19-FAILURE-1"
_LOCK_POLL_SLEEP_SECONDS = 0.1


class SpoolsService:
    def __init__(self, *, redis_factory: RedisFactory, client: SpoolmanClient) -> None:
        self._redis = redis_factory.get()
        self._client = client

    async def get_summary(self) -> SpoolmanSnapshot | None:
        cached = await self._redis.get(_CACHE_KEY)
        if cached is not None:
            return SpoolmanSnapshot.model_validate_json(cached)
        # Cold-cache fallback — single lock-protected live fetch.
        snapshot = await self.refresh_summary()
        if snapshot is not None:
            return snapshot

        # ``refresh_summary()`` returns ``None`` both for leader contention and
        # for an actual upstream failure. Re-read cache first to cover the race
        # where the leader completed between SETNX miss and this branch.
        cached = await self._redis.get(_CACHE_KEY)
        if cached is not None:
            return SpoolmanSnapshot.model_validate_json(cached)

        if await self._redis.exists(_LOCK_KEY):
            # Another worker is still refreshing. Wait until it writes the
            # cache or releases/expires the lock; then, if it failed and cache
            # is still empty, this request performs one live fetch of its own.
            while await self._redis.exists(_LOCK_KEY):
                cached = await self._redis.get(_CACHE_KEY)
                if cached is not None:
                    return SpoolmanSnapshot.model_validate_json(cached)
                await asyncio.sleep(_LOCK_POLL_SLEEP_SECONDS)
            cached = await self._redis.get(_CACHE_KEY)
            if cached is not None:
                return SpoolmanSnapshot.model_validate_json(cached)

        # If the contender missed the lock but the leader failed/released it
        # before our existence check, cache is still empty here. Make one final
        # lock-protected live attempt so ``None`` means cache empty + live fetch
        # failed, not a lock-release race.
        snapshot = await self.refresh_summary()
        if snapshot is not None:
            return snapshot
        cached = await self._redis.get(_CACHE_KEY)
        if cached is not None:
            return SpoolmanSnapshot.model_validate_json(cached)
        return None

    async def _release_lock(self, token: bytes) -> None:
        async with self._redis.pipeline(transaction=True) as pipe:
            while True:
                try:
                    await pipe.watch(_LOCK_KEY)
                    current = await pipe.get(_LOCK_KEY)
                    if current != token:
                        await pipe.unwatch()
                        return
                    pipe.multi()
                    pipe.delete(_LOCK_KEY)
                    await pipe.execute()
                    return
                except WatchError:
                    # Foreign writer touched the key between WATCH and EXEC —
                    # re-read; if value still matches our token, retry the CAD;
                    # otherwise leave the new owner's lock untouched.
                    continue

    async def get_last_success_ts(self) -> datetime | None:
        raw = await self._redis.get(_LAST_SUCCESS_KEY)
        if raw is None:
            return None
        value = raw.decode() if isinstance(raw, bytes) else raw
        return datetime.fromisoformat(value)

    async def refresh_summary(self) -> SpoolmanSnapshot | None:
        # Per-refresh unique token so the lock-release path can compare-and-
        # delete on its own value (AC-9 ownership invariant) instead of blindly
        # deleting whatever currently sits at _LOCK_KEY — guards the
        # TTL-expiry race where the 90s lease lapses and a second worker
        # SETNX'd a fresh lock of its own before our finally fires.
        token = secrets.token_hex(16).encode()
        lock_acquired = await self._redis.set(_LOCK_KEY, token, nx=True, ex=_LOCK_EXPIRY_SECONDS)
        if not lock_acquired:
            # AC-9 — another worker holds the lock; idempotent skip.
            return None
        try:
            results = await asyncio.gather(
                self._client.list_spools(lock_held=True),
                self._client.list_filaments(lock_held=True),
                self._client.list_vendors(lock_held=True),
                return_exceptions=True,
            )
            errors = [result for result in results if isinstance(result, BaseException)]
            if errors:
                # Drain all sibling calls before releasing the Redis lock or
                # closing the shared client; then surface the first failure to
                # the common soft-fail logging/return path below.
                raise errors[0]
            spools, filaments, vendors = results
            snapshot = SpoolmanSnapshot(
                spools=spools,
                filaments=filaments,
                vendors=vendors,
                fetched_at=datetime.now(UTC),
            )
            payload = snapshot.model_dump_json()
            now_iso = snapshot.fetched_at.isoformat()
            await self._redis.set(_CACHE_KEY, payload, ex=_CACHE_TTL_SECONDS)
            # ``last-success-ts`` carries no TTL — persists across cache
            # rotations so the FE soft-fail indicator can compute "Xm ago"
            # from arbitrary delays per FR19-FAILURE-1.
            await self._redis.set(_LAST_SUCCESS_KEY, now_iso)
            _LOG.info(
                "spools.poll.refresh",
                extra={
                    "event.action": "spools.poll.refresh",
                    "labels.external_service": "spoolman",
                    "labels.lock_acquired": True,
                    "labels.entity_count": len(spools) + len(filaments) + len(vendors),
                },
            )
            return snapshot
        except (
            httpx.RequestError,
            httpx.HTTPStatusError,
            SpoolmanCircuitOpenError,
            Exception,
        ) as exc:
            _LOG.warning(
                "spools.poll.error",
                extra={
                    "event.action": "spools.poll.error",
                    "labels.external_service": "spoolman",
                    "labels.lock_acquired": True,
                    "labels.error_class": type(exc).__name__,
                },
            )
            # Cache + sibling stay untouched on failure — Decision AD failure
            # semantics (warm-cache requests keep serving the prior snapshot).
            return None
        finally:
            # Ownership-safe lock release via WATCH/MULTI/EXEC compare-and-
            # delete: only DEL when the stored value still matches our
            # per-refresh token. Guards the TTL-expiry race where the 90s
            # lease lapsed and another worker SETNX'd a fresh lock — that
            # foreign value is left intact. TTL covers worker crashes mid-
            # poll. Lua EVAL would be a one-call equivalent but the project's
            # fakeredis test harness lacks lupa, so transactions are the
            # safest primitive supported by both production redis-py and
            # the test fake without an extra dependency.
            await self._release_lock(token)
