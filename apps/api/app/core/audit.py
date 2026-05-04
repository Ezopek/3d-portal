import json
import uuid
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.core.db.models import AuditLog

# Closed set of valid `entity_type` values for audit_log rows. The column is
# typed `text` for now (Slice 1B) so it could hold anything, but every
# record_event call site is expected to use one of these constants. Tightening
# the column to a strict enum in Slice 2 is a no-op once every caller is on
# the closed set.
#   catalog              — admin.refresh_catalog (entity_id always None)
#   category             — future category CRUD (Slice 2C.x)
#   model                — admin.render.trigger + model CRUD (Slice 2C.1)
#   model_external_link  — future link CRUD (Slice 2C.x)
#   model_file           — file upload/delete (Slice 2C.2)
#   model_note           — note CRUD (Slice 2C.x)
#   model_print          — print record CRUD (Slice 2C.x)
#   render_selection     — admin.render.selection.set/delete (entity_id None: legacy str model_id)
#   share_token          — admin.share.create/delete (entity_id None: keyed by token string)
#   tag                  — future tag CRUD (Slice 2C.x)
#   thumbnail_override   — admin.thumbnail.set/unset (entity_id None: legacy str model_id)
#   user                 — auth.login.success/fail
KNOWN_ENTITY_TYPES: frozenset[str] = frozenset(
    {
        "catalog",
        "category",
        "model",
        "model_external_link",
        "model_file",
        "model_note",
        "model_print",
        "render_selection",
        "share_token",
        "tag",
        "thumbnail_override",
        "user",
    }
)


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

    `entity_type` MUST be one of `KNOWN_ENTITY_TYPES`; unknown values raise
    `ValueError`. This is a forward guard for the planned Slice 2 enum
    tightening — silent drift would otherwise pile up across call sites.
    """
    if entity_type not in KNOWN_ENTITY_TYPES:
        raise ValueError(
            f"unknown entity_type {entity_type!r}; "
            f"add it to KNOWN_ENTITY_TYPES in app/core/audit.py if "
            f"this is a new resource"
        )
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
