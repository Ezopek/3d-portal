"""Field-allowlist DTOs for the admin queue snapshot (NFR22-LEAK-FENCE-1).

Every model is ``extra="forbid"`` and enumerates ONLY the curated, leak-safe fields.
Raw arq payloads (``args``/``kwargs``/``result``) are projected out in the service layer
and have no field here to land in — the allowlist IS the fence (Decision AQ clause 2).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

QueueRole = Literal["api", "render", "slicer"]
Outcome = Literal["success", "failed"]
Liveness = Literal["alive", "idle", "unknown"]


class JobContext(BaseModel):
    """Curated "what was this job about" — derived ONLY from business-keyed status keys
    or the job id (never from raw args/kwargs/result). ``ref`` is an id / hash-prefix,
    never a filesystem path (Decision AO step 5 / AQ clause 3 / AC-9)."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    ref: str | None = None


class QueueCounters(BaseModel):
    """Raw arq health counters, parsed verbatim from the ``<queue>:health-check`` string."""

    model_config = ConfigDict(extra="forbid")

    complete: int
    failed: int
    retried: int
    ongoing: int
    queued: int


class WorkerLiveness(BaseModel):
    """Per-pool worker liveness (Decision AP). Coarse (~1h) by design for the MVP; the
    raw ``heartbeat_age_s`` + ``interval_s`` are surfaced so the granularity is honest."""

    model_config = ConfigDict(extra="forbid")

    liveness: Liveness
    heartbeat_at: datetime | None = None
    heartbeat_age_s: int | None = None
    interval_s: int
    counters: QueueCounters | None = None


class RunningJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    queue: str
    function: str
    job_id: str
    started_age_s: int
    context: JobContext | None = None


class RecentJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    queue: str
    function: str
    outcome: Outcome
    finished_at: datetime
    duration_s: float
    job_id: str
    context: JobContext | None = None
    error_class: str | None = None


class QueueEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    role: QueueRole
    queued: int
    running: int
    worker: WorkerLiveness


class QueueSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    queues: list[QueueEntry]
    running_jobs: list[RunningJob]
    recent: list[RecentJob]
    retention_note: str
