"""Build the read-only queue snapshot from bounded Redis reads.

Hard rules (NFR22-REDIS-LOAD-1 / Decision AQ):
- depth via ``zcard`` (exact, O(1));
- ``running``/``recent`` via bounded ``SCAN`` (never ``KEYS`` — arq's ``all_job_results``
  issues an unbounded ``KEYS arq:result:*`` and is deliberately NOT used);
- the queued args are never deserialized (``queued_jobs`` is deliberately NOT used);
- every job is projected to the allowlist DTO — no raw ``args``/``kwargs``/``result``.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from arq.constants import in_progress_key_prefix, job_key_prefix, result_key_prefix
from arq.jobs import DeserializationError, deserialize_job, deserialize_result

from app.modules.queue.constants import (
    FUNCTION_TO_POOL,
    HEALTH_CHECK_INTERVAL_S,
    POOLS,
    RECENT_HARD_CAP,
    RETENTION_NOTE,
    SCAN_COUNT_HINT,
)
from app.modules.queue.schemas import (
    JobContext,
    QueueCounters,
    QueueEntry,
    QueueSnapshot,
    RecentJob,
    RunningJob,
    WorkerLiveness,
)

_LOG = logging.getLogger("app.queue.admin")

_COUNTER_RE = re.compile(
    r"j_complete=(\d+)\s+j_failed=(\d+)\s+j_retried=(\d+)\s+j_ongoing=(\d+)\s+queued=(\d+)"
)

# Curated kind per arq function — leak-safe, never derived from raw payload (AC-9).
_FUNCTION_KIND: dict[str, str] = {
    "render_model": "render",
    "render_stl_previews": "render",
    "generate_thumbnail": "thumbnail",
    "cleanup_refresh_tokens": "maintenance",
    "poll_spoolman_summary": "spoolman",
    "slice_estimate": "estimate",
}


def _decode_key(key: Any) -> str:
    return key.decode() if isinstance(key, (bytes, bytearray)) else str(key)


async def _bounded_scan(
    conn: Any, match: str, *, count: int, hard_cap: int | None = None
) -> list[str]:
    """Cursor-loop ``SCAN MATCH <match> COUNT <count>``; never ``KEYS``.

    Stops early once ``hard_cap`` keys have been collected so a large keyspace cannot
    drive an unbounded fetch (AC-8). Returns decoded key strings.
    """

    out: list[str] = []
    cursor: int = 0
    while True:
        cursor, batch = await conn.scan(cursor, match=match, count=count)
        out.extend(_decode_key(k) for k in batch)
        if hard_cap is not None and len(out) >= hard_cap:
            return out[:hard_cap]
        if cursor == 0:
            return out


def _derive_context(job_id: str, function: str) -> JobContext:
    """Curated context from the job id / function name only — never from args/kwargs.

    The slicer enqueues a deterministic ``slice:<stl_hash>:<bundle_hash>`` job id
    (``app/modules/slicer/enqueue.py``), so a stl-hash *prefix* (not a path) is
    recoverable for slicer jobs. Other pools use random uuids → ``ref`` stays ``None``.
    """

    if job_id.startswith("slice:"):
        parts = job_id.split(":")
        ref = parts[1][:12] if len(parts) > 1 and parts[1] else None
        return JobContext(kind="estimate", ref=ref)
    return JobContext(kind=_FUNCTION_KIND.get(function, "job"), ref=None)


def _parse_counters(value: bytes | str | None) -> QueueCounters | None:
    if value is None:
        return None
    text = value.decode() if isinstance(value, (bytes, bytearray)) else str(value)
    m = _COUNTER_RE.search(text)
    if not m:
        return None
    return QueueCounters(
        complete=int(m.group(1)),
        failed=int(m.group(2)),
        retried=int(m.group(3)),
        ongoing=int(m.group(4)),
        queued=int(m.group(5)),
    )


async def _build_liveness(conn: Any, health_key: str, *, now: datetime) -> WorkerLiveness:
    """Tri-state liveness from the ``<queue>:health-check`` key (Decision AP / AC-7).

    Age is derived from the key's remaining TTL: arq writes the key with TTL
    ``(interval+1)`` seconds, so ``age = (interval+1) - ttl_remaining``. ``unknown`` when
    the key is absent; ``alive`` when ``age < interval``; ``idle`` otherwise.
    """

    interval = HEALTH_CHECK_INTERVAL_S
    pttl_ms = await conn.pttl(health_key)
    if pttl_ms is None or pttl_ms < 0:  # -2 missing, -1 no-expiry (arq always sets one)
        return WorkerLiveness(liveness="unknown", interval_s=interval)

    value = await conn.get(health_key)
    ttl_s = pttl_ms / 1000
    age = max(0, round((interval + 1) - ttl_s))
    liveness = "alive" if age < interval else "idle"
    return WorkerLiveness(
        liveness=liveness,
        heartbeat_at=now - timedelta(seconds=age),
        heartbeat_age_s=age,
        interval_s=interval,
        counters=_parse_counters(value),
    )


async def _build_running(conn: Any, *, now: datetime) -> list[RunningJob]:
    keys = await _bounded_scan(conn, in_progress_key_prefix + "*", count=SCAN_COUNT_HINT)
    running: list[RunningJob] = []
    for key in keys:
        job_id = key[len(in_progress_key_prefix) :]
        blob = await conn.get(job_key_prefix + job_id)
        if blob is None:
            continue
        try:
            jd = deserialize_job(blob)
        except DeserializationError:
            _LOG.warning("queue.snapshot.skip_undeserializable_job", extra={"key": "<redacted>"})
            continue
        pool = FUNCTION_TO_POOL.get(jd.function)
        if pool is None:
            continue
        age = max(0, int((now - jd.enqueue_time).total_seconds()))
        running.append(
            RunningJob(
                queue=pool.name,
                function=jd.function,
                job_id=job_id,
                started_age_s=age,
                context=_derive_context(job_id, jd.function),
            )
        )
    return running


async def _build_recent(conn: Any) -> list[RecentJob]:
    keys = await _bounded_scan(
        conn, result_key_prefix + "*", count=SCAN_COUNT_HINT, hard_cap=RECENT_HARD_CAP
    )
    recent: list[RecentJob] = []
    for key in keys:
        job_id = key[len(result_key_prefix) :]
        blob = await conn.get(result_key_prefix + job_id)
        if blob is None:
            continue
        try:
            jr = deserialize_result(blob)
        except DeserializationError:
            _LOG.warning("queue.snapshot.skip_undeserializable_result")
            continue
        duration = max(0.0, (jr.finish_time - jr.start_time).total_seconds())
        # error_class is the curated exception TYPE NAME only — never the message/traceback
        # (which could embed a path or secret). (AC-11 / Decision AQ clause 3/5.)
        error_class = None if jr.success else type(jr.result).__name__
        recent.append(
            RecentJob(
                queue=jr.queue_name,
                function=jr.function,
                outcome="success" if jr.success else "failed",
                finished_at=jr.finish_time,
                duration_s=duration,
                job_id=job_id,
                context=_derive_context(job_id, jr.function),
                error_class=error_class,
            )
        )
    return recent


async def build_snapshot(conn: Any, *, now: datetime | None = None) -> QueueSnapshot:
    """Assemble the full read-only snapshot for the three pools."""

    now = now or datetime.now(UTC)

    running = await _build_running(conn, now=now)
    recent = await _build_recent(conn)
    running_by_queue: dict[str, int] = {}
    for job in running:
        running_by_queue[job.queue] = running_by_queue.get(job.queue, 0) + 1

    queues: list[QueueEntry] = []
    for pool in POOLS:
        queued = int(await conn.zcard(pool.name))
        worker = await _build_liveness(conn, pool.health_key, now=now)
        queues.append(
            QueueEntry(
                name=pool.name,
                role=pool.role,
                queued=queued,
                running=running_by_queue.get(pool.name, 0),
                worker=worker,
            )
        )

    return QueueSnapshot(
        generated_at=now,
        queues=queues,
        running_jobs=running,
        recent=recent,
        retention_note=RETENTION_NOTE,
    )
