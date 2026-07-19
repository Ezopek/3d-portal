"""Admin-only taxonomy-governance write endpoints (Story 42.4).

Prefix: /api/admin
Auth: `current_admin` (admin role only — 403 `admin_required` otherwise).

This router is deliberately SEPARATE from `sot/admin_router.py`: that module is
the agent-write ingestion surface (every route tagged `agent-write`), enforced
by `test_openapi_agent_surface.py`. Facet governance is admin curation, not
agent ingestion (FR25-ADMIN-1 / Decision AW), so it lives here under the
distinct `sot-admin-governance` tag and never advertises an agent capability.

Owns:
  POST   /api/admin/tag-groups             — create a facet group
  PATCH  /api/admin/tag-groups/{group_id}  — rename + reorder
  DELETE /api/admin/tag-groups/{group_id}  — delete (member tags survive groupless)
  POST   /api/admin/tags                   — create a global tag (admin-only,
                                             relocated + tightened from the
                                             agent-write router; D-ADMINONLY-1)
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.auth.dependencies import current_admin
from app.core.db.session import get_session
from app.modules.sot.admin_schemas import TagCreate, TagGroupCreate, TagGroupPatch
from app.modules.sot.admin_service import (
    create_tag,
    create_tag_group,
    delete_tag_group,
    update_tag_group,
)
from app.modules.sot.schemas import TagGroupSummary, TagRead

router = APIRouter(prefix="/api/admin", tags=["sot-admin-governance"])


@router.post(
    "/tag-groups",
    summary="Create a facet tag group",
    description=(
        "Creates a new `TagGroup` facet group. Returns 201 + `TagGroupSummary` "
        "(flat `{id, slug, name_en, name_pl, position}` — NOT the read-side "
        "`TagGroupRead` with embedded tags). 409 if `slug` collides with an "
        "existing group (`TagGroup.slug` is globally unique). 422 on other "
        "Pydantic validation. Admin-only (`current_admin`)."
    ),
    status_code=status.HTTP_201_CREATED,
    response_model=TagGroupSummary,
)
def admin_create_tag_group(
    payload: TagGroupCreate,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = current_admin,
) -> TagGroupSummary:
    try:
        tg = create_tag_group(session, payload=payload, actor_user_id=actor_user_id)
    except ValueError as exc:
        if "slug_conflict" in str(exc):
            raise HTTPException(409, "slug already exists") from exc
        raise HTTPException(422, str(exc)) from exc
    return TagGroupSummary.model_validate(tg)


@router.patch(
    "/tag-groups/{group_id}",
    summary="Rename and/or reorder a facet tag group",
    description=(
        "Partial update of a `TagGroup` (`extra='forbid'`, unknown keys → 422). "
        "Only supplied fields change (`exclude_unset`). An explicit `name_pl: "
        "null` clears the Polish label; an explicit null on `slug`/`name_en`/"
        "`position` is a 422 (those are NOT NULL). An empty `{}` body is a 200 "
        "no-op that still writes one `tag_group.update` audit row with "
        "before == after. Returns 200 + `TagGroupSummary`. 404 if the group "
        "does not exist, 409 on a slug collision. Admin-only."
    ),
    response_model=TagGroupSummary,
)
def admin_patch_tag_group(
    group_id: uuid.UUID,
    patch: TagGroupPatch,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = current_admin,
) -> TagGroupSummary:
    try:
        tg = update_tag_group(session, group_id=group_id, patch=patch, actor_user_id=actor_user_id)
    except LookupError as exc:
        raise HTTPException(404, "tag group not found") from exc
    except ValueError as exc:
        if "slug_conflict" in str(exc):
            raise HTTPException(409, "slug already exists") from exc
        raise HTTPException(422, str(exc)) from exc
    return TagGroupSummary.model_validate(tg)


@router.delete(
    "/tag-groups/{group_id}",
    summary="Delete a facet tag group (member tags survive groupless)",
    description=(
        "Permanent delete. Returns 204. 404 if the group does not exist (not "
        "idempotent-204-on-missing). Deleting a non-empty group is allowed and "
        "clean: the FK `ON DELETE SET NULL` detaches member tags — each becomes "
        "a groupless tag (`group_id = NULL`), never deleted. One bounded "
        "`tag_group.delete` audit row records the detached tag ids; no per-tag "
        "rows. Admin-only."
    ),
    status_code=status.HTTP_204_NO_CONTENT,
)
def admin_delete_tag_group(
    group_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = current_admin,
) -> None:
    try:
        delete_tag_group(session, group_id=group_id, actor_user_id=actor_user_id)
    except LookupError as exc:
        raise HTTPException(404, "tag group not found") from exc


@router.post(
    "/tags",
    summary="Create a new global tag (admin-only)",
    description=(
        "Creates a new `Tag` row visible to all models. Returns 201 + `TagRead`. "
        "409 on slug conflict (tag slugs are globally unique). 422 on other "
        "validation. **Admin-only** (FR25-TAX-2 curated vocabulary): the agent "
        "service role selects existing tags but does not mint new ones. Tag "
        "rename / delete / merge remain admin-or-agent on the agent-write router."
    ),
    response_model=TagRead,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_tag(
    payload: TagCreate,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = current_admin,
) -> TagRead:
    try:
        tag = create_tag(session, payload=payload, actor_user_id=actor_user_id)
    except ValueError as exc:
        if "slug_conflict" in str(exc):
            raise HTTPException(409, "slug already exists") from exc
        raise HTTPException(422, str(exc)) from exc
    return TagRead.model_validate(tag)
