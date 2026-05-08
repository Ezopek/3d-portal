"""apps/api/app/workers/cleanup_refresh_tokens.py — daily cleanup of old refresh_tokens rows."""
from __future__ import annotations

import datetime
import logging

from sqlalchemy import delete
from sqlmodel import Session

from app.core.db.models import RefreshToken
from app.core.db.session import get_engine

_LOG = logging.getLogger(__name__)


def cleanup_refresh_tokens_sync(engine) -> int:
    """Delete refresh_tokens rows where revoke or expiry is older than 7 days.

    Returns the number of rows deleted.
    """
    cutoff = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=7)
    with Session(engine) as s:
        stmt = delete(RefreshToken).where(
            (
                (RefreshToken.revoked_at.is_not(None))
                & (RefreshToken.revoked_at < cutoff)
            )
            | (RefreshToken.expires_at < cutoff)
        )
        result = s.exec(stmt)
        s.commit()
        n = result.rowcount or 0
    _LOG.info(
        "auth.refresh.cleanup",
        extra={"event.action": "auth.refresh.cleanup", "labels.deleted_rows": n},
    )
    return n


async def cleanup_refresh_tokens(_ctx) -> int:
    """arq task entry point. The arq context is passed but unused."""
    return cleanup_refresh_tokens_sync(get_engine())
