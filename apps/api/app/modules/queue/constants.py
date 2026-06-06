"""Single source of truth for the three arq pools + the snapshot's magic constants.

The pool table (queue id → role → its arq function names) is shared by the snapshot
service AND the tests, so attribution can never drift between them. Verified against the
worker definitions at baseline 3e6ed4e:

- ``arq:api``    — ``app/workers/__init__.py`` (``API_QUEUE_NAME``)
- ``arq:queue``  — ``workers/render/render/worker.py`` (arq default queue, no override)
- ``arq:slicer`` — ``app/modules/slicer/worker.py`` (``SLICER_QUEUE_NAME``)
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Literal

from arq.constants import health_check_key_suffix
from arq.worker import Worker

QueueRole = Literal["api", "render", "slicer"]


@dataclass(frozen=True)
class PoolSpec:
    """One arq worker pool: its zset/queue id, friendly role, and registered functions."""

    name: str
    role: QueueRole
    functions: frozenset[str]

    @property
    def health_key(self) -> str:
        return f"{self.name}{health_check_key_suffix}"


POOLS: tuple[PoolSpec, ...] = (
    PoolSpec(
        name="arq:api",
        role="api",
        functions=frozenset(
            {"cleanup_refresh_tokens", "generate_thumbnail", "poll_spoolman_summary"}
        ),
    ),
    PoolSpec(
        name="arq:queue",
        role="render",
        functions=frozenset({"render_model", "render_stl_previews"}),
    ),
    PoolSpec(
        name="arq:slicer",
        role="slicer",
        functions=frozenset({"slice_estimate"}),
    ),
)

# Reverse map: arq function name → owning pool. A running job is no longer in any queue
# zset (arq removes it on pick), so we attribute it to a pool by its function name.
FUNCTION_TO_POOL: dict[str, PoolSpec] = {fn: p for p in POOLS for fn in p.functions}


# --- Magic constants (per the story's § Magic-constant discipline) ------------------

# Contract: arq's own ``health_check_interval`` default. None of the three pools override
# it (verified: app/workers/__init__.py:WorkerSettings, app/modules/slicer/worker.py:
# SlicerWorkerSettings, workers/render/render/worker.py:WorkerSettings set no
# health_check_interval). Read it from arq so the console surfaces the worker's ACTUAL
# liveness granularity (~1h today), NOT a console-invented threshold (Decision AP / AC-7).
# If a pool lowers its interval (G-LIVENESS), make this per-pool.
HEALTH_CHECK_INTERVAL_S: int = int(
    inspect.signature(Worker).parameters["health_check_interval"].default
)

# Contract: a display/perf bound — "enough to spot a cluster of failures in the ~1h
# Redis-resident window without an unbounded fetch." Arbitrary-but-bounded MVP default;
# revisit when the durable ledger lands (G-LEDGER). NOT "feels right" (TB-016 lesson).
RECENT_HARD_CAP: int = 50

# Contract: a Redis SCAN cursor batch HINT (not a result cap) — kept small so no single
# SCAN call blocks the homelab single-Redis for long (NFR22-REDIS-LOAD-1).
SCAN_COUNT_HINT: int = 100

RETENTION_NOTE: str = (
    "Recent results are Redis-resident and expire roughly one hour after completion "
    "(arq keep_result TTL); a vanished entry means expired, not resolved."
)
