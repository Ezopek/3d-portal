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
#   invite_token         — auth.invite.generated/used/revoked (entity_id = invite_tokens.id UUID)
#   model                — admin.render.trigger + model CRUD (Slice 2C.1)
#   model_external_link  — future link CRUD (Slice 2C.x)
#   model_file           — file upload/delete (Slice 2C.2)
#   model_note           — note CRUD (Slice 2C.x)
#   model_print          — print record CRUD (Slice 2C.x)
#   recovery_code        — auth.recovery_code.used (entity_id = recovery_codes.id UUID)
#   render_selection     — admin.render.selection.set/delete (entity_id None: legacy str model_id)
#   share_token          — admin.share.create/delete (entity_id None: keyed by token string)
#   slicer_profile       — slicer_profile.import (Story 33.2 admin profile import;
#                          entity_id = deterministic (printer_ref, material_class,
#                          quality_tier) slot UUID); slicer_profile.delete reserved for 33.3;
#                          slicer_profile.library_import / .library_delete (PROFILE-LIB-1
#                          separate-block import/delete; entity_id = deterministic block UUID);
#                          slicer_profile.offer_create / .offer_update / .offer_delete
#                          (PROFILE-OFFER-1 PrintProfileOffer CRUD; entity_id = offer_id UUID);
#                          slicer_profile.offer_publish / .offer_unpublish
#                          (PROFILE-PUBLISH-1 publish-state bridge; entity_id = offer_id UUID)
#   tag                  — future tag CRUD (Slice 2C.x)
#   tag_group            — tag_group.create/update/delete (Story 42.4 admin group
#                          governance; entity_id = tag_group.id UUID)
#   thumbnail_override   — admin.thumbnail.set/unset (entity_id None: legacy str model_id)
#   user                 — auth.login.success/fail; auth.totp.enrolled (Story 7.2);
#                          auth.totp.verify.success/auth.totp.verify.fail (Story 7.3 +
#                          7.5 re-auth gates use method=regenerate_reauth/disable_reauth);
#                          auth.recovery_codes.regenerated (Story 7.5);
#                          auth.totp.disabled (Story 7.5);
#                          user.role_changed, user.deactivated, user.reactivated,
#                          user.force_logout (Story 8.3);
#                          auth.totp.enrolled (actor!=target, force_enrolled=true),
#                          auth.totp.disabled (actor!=target, admin_override=true) (Story 8.4);
#                          auth.password.reset.initiated, auth.password.reset.completed
#                          (Story 8.5);
#                          user.display_name.updated (Story 12.3 — self-service edit
#                          via PATCH /api/auth/me/display-name; actor==target)
KNOWN_ENTITY_TYPES: frozenset[str] = frozenset(
    {
        "catalog",
        "invite_token",
        "model",
        "model_external_link",
        "model_file",
        "model_note",
        "model_print",
        "recovery_code",
        "render_selection",
        "share_token",
        "slicer_profile",
        "tag",
        "tag_group",
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
