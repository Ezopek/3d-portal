import json
import uuid
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.core.db.models import AuditLog


def record_event(
    engine: Engine,
    *,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    actor_user_id: uuid.UUID | None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> None:
    """Record one mutation in audit_log.

    Uses a dedicated session so audit writes commit independently of the
    caller's transaction (e.g. a failed login still records the event).
    """
    with Session(engine) as session:
        log = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_json=json.dumps(before) if before is not None else None,
            after_json=json.dumps(after) if after is not None else None,
            request_id=request_id,
        )
        session.add(log)
        session.commit()
