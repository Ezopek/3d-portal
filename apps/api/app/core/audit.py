import json
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.core.db.models import AuditEvent


def record_event(
    engine: Engine,
    *,
    kind: str,
    actor_user_id: int | None,
    payload: dict[str, Any] | None = None,
) -> None:
    # Use a dedicated session so audit writes commit independently of any caller's
    # transaction (e.g. a failed login still records the auth.login.fail event).
    with Session(engine) as session:
        event = AuditEvent(
            kind=kind,
            actor_user_id=actor_user_id,
            payload=json.dumps(payload or {}),
        )
        session.add(event)
        session.commit()
