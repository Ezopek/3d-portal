"""Read-only admin queue console endpoint: ``GET /api/admin/queues`` (Story 34.1).

Admin-gated via the ``current_admin`` default-value dependency (so the Init 6 route
enforcement gate passes WITHOUT a ``_PUBLIC_ROUTES`` edit). Read-only: this router
exposes a single ``GET`` and no mutation verb (NFR22-READONLY-1 / AC-12).
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from app.core.auth.dependencies import current_admin
from app.modules.queue.schemas import QueueSnapshot
from app.modules.queue.service import build_snapshot

_LOG = logging.getLogger("app.queue.admin")

router = APIRouter(prefix="/api/admin", tags=["admin-queues"])


def get_queue_conn(request: Request) -> Any:
    """The lifespan-owned arq pool (an ``ArqRedis``/Redis connection to the arq keyspace).

    Reached via ``request.app.state.arq`` only — never an ad-hoc connection (Decision AO /
    AC-3). Overridable in tests via ``app.dependency_overrides``.
    """

    return request.app.state.arq


@router.get(
    "/queues",
    response_model=QueueSnapshot,
    summary="Read-only live snapshot of the three arq worker pools (admin only)",
)
async def read_queue_snapshot(
    conn: Annotated[Any, Depends(get_queue_conn)],
    _user_id: uuid.UUID = current_admin,
) -> QueueSnapshot:
    snapshot = await build_snapshot(conn)
    _LOG.info(
        "queue.snapshot.read",
        extra={
            "queues": len(snapshot.queues),
            "running": len(snapshot.running_jobs),
            "recent": len(snapshot.recent),
        },
    )
    return snapshot
