"""Admin-only browse-category governance write endpoints (Story 49.5).

Prefix: /api/admin
Auth: `current_admin` (admin role only — 403 `admin_required` otherwise).

Deliberately SEPARATE from `sot/admin_router.py` (the agent-write ingestion
surface): categories are admin curation, never agent-writable — per ratified
Decision AY (architecture.md:3334-3341), which places every route in this
router under `current_admin`, mirroring the identical admin-curation/
agent-ingestion split `tag_group_admin_router.py` already applies (FR25-ADMIN-1
/ Decision AW, D-ADMINONLY-1). Lives under the `sot-admin-governance` tag
alongside tag-group governance and never advertises an agent capability.

Owns:
  POST   /api/admin/categories                    — create
  PATCH  /api/admin/categories/{category_id}      — rename/reorder/reparent
  DELETE /api/admin/categories/{category_id}      — delete (409 unless clean or detach=true)
  PUT    /api/admin/models/{model_id}/categories  — replace-set assignment
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.auth.dependencies import current_admin
from app.core.db.models import BrowseCategory
from app.core.db.session import get_session
from app.modules.sot.admin_schemas import (
    BrowseCategoryCreate,
    BrowseCategoryPatch,
    ModelCategoriesReplace,
)
from app.modules.sot.admin_service import (
    browse_category_model_count,
    create_browse_category,
    delete_browse_category,
    replace_model_categories,
    update_browse_category,
)
from app.modules.sot.schemas import BrowseCategoryAdminRead, BrowseCategorySummary

router = APIRouter(prefix="/api/admin", tags=["sot-admin-governance"])


def _admin_read(session: Session, cat: BrowseCategory) -> BrowseCategoryAdminRead:
    """Build the admin write-response DTO.

    Constructed field-by-field rather than `model_validate(cat)` because
    `model_count` is an aggregate, not an ORM attribute — the same reason the
    read side hand-builds `BrowseCategoryRead`.
    """
    return BrowseCategoryAdminRead(
        id=cat.id,
        slug=cat.slug,
        name_en=cat.name_en,
        name_pl=cat.name_pl,
        description_en=cat.description_en,
        description_pl=cat.description_pl,
        inclusion_criterion=cat.inclusion_criterion,
        position=cat.position,
        parent_id=cat.parent_id,
        model_count=browse_category_model_count(session, cat.id),
    )


@router.post(
    "/categories",
    summary="Create a browse category",
    description=(
        "Creates a new `BrowseCategory`. Returns 201 + `BrowseCategoryAdminRead` "
        "— the nine-key public `BrowseCategoryRead` set PLUS `inclusion_criterion`, "
        "which the public `GET /api/categories` contract deliberately omits. "
        "`model_count` is always 0 on create. 409 if `slug` collides "
        "(`uq_browse_category_slug`). 404 if `parent_id` does not resolve. 422 "
        "`parent_not_root` if `parent_id` points at a category that is itself a "
        "child — the service-layer depth-2 ceiling (FR26-CAT-4), not a DDL "
        "constraint. Admin-only (`current_admin`); never agent-writable."
    ),
    status_code=status.HTTP_201_CREATED,
    response_model=BrowseCategoryAdminRead,
)
def admin_create_category(
    payload: BrowseCategoryCreate,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = current_admin,
) -> BrowseCategoryAdminRead:
    try:
        cat = create_browse_category(session, payload=payload, actor_user_id=actor_user_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        if "slug_conflict" in str(exc):
            raise HTTPException(409, "slug already exists") from exc
        raise HTTPException(422, str(exc)) from exc
    return _admin_read(session, cat)


@router.put(
    "/models/{model_id}/categories",
    summary="Replace the full browse-category set assigned to a model",
    description=(
        "Whole-set replace, idempotent, explicit **last-writer-wins**: the "
        "supplied `category_ids` become the model's complete category set. "
        "There is no merge, no diff and NO optimistic-concurrency precondition "
        "(no `revision`, no `If-Match`) — two admins editing concurrently, the "
        "last call wins silently. An empty `[]` clears every assignment and "
        "leaves the model fully valid and public. Returns 200 + "
        "`list[BrowseCategorySummary]` ordered `(position, slug)`. The ENTIRE "
        "payload is validated before any row is touched, so a rejected call "
        "leaves the existing set unchanged: 400 on duplicate ids in the "
        "payload, 404 if the model is unknown or soft-deleted, 404 if any "
        "`category_ids` entry does not resolve. Writes exactly one "
        "`model.update` audit row per successful call, `before`/`after` "
        "carrying the pre- and post-call id sets. **Admin-only** — unlike "
        "`PUT /api/admin/models/{model_id}/tags`, this route is not agent-"
        "writable (Decision AY: category curation is admin curation)."
    ),
    response_model=list[BrowseCategorySummary],
)
def admin_replace_model_categories(
    model_id: uuid.UUID,
    payload: ModelCategoriesReplace,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = current_admin,
) -> list[BrowseCategorySummary]:
    try:
        cats = replace_model_categories(
            session, model_id=model_id, payload=payload, actor_user_id=actor_user_id
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        if "duplicate_category_ids" in str(exc):
            raise HTTPException(400, str(exc)) from exc
        raise HTTPException(404, str(exc)) from exc
    return [BrowseCategorySummary.model_validate(c) for c in cats]


@router.delete(
    "/categories/{category_id}",
    summary="Delete a browse category (409 unless clean or detach=true)",
    description=(
        "Permanent delete. Returns 204. 404 if the category does not exist (not "
        "idempotent-204-on-missing). TWO independent 409 conflict sources, both "
        "defending an `ON DELETE RESTRICT` FK:\n\n"
        "* `category_has_children` — the category has at least one child "
        "category. Checked FIRST and unconditionally: `detach=true` does NOT "
        'resolve it. Clear the child\'s parent (`PATCH {"parent_id": null}`) or '
        "delete the child first — this route performs no cascading child-delete "
        "and no auto-reparent.\n"
        "* `category_in_use` — the category has model assignments and `detach` "
        "was omitted or false.\n\n"
        "`?detach=true` deletes every `model_browse_category` row for the "
        "category and then the category itself in ONE transaction, and records "
        "`detached_model_ids` + `detached_model_count` on the single "
        "`browse_category.delete` audit row. On a category with no assignments "
        "the flag is a harmless no-op and those two keys are absent. Admin-only."
    ),
    status_code=status.HTTP_204_NO_CONTENT,
)
def admin_delete_category(
    category_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    detach: bool = False,
    actor_user_id: uuid.UUID = current_admin,
) -> None:
    try:
        delete_browse_category(
            session, category_id=category_id, detach=detach, actor_user_id=actor_user_id
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.patch(
    "/categories/{category_id}",
    summary="Rename, reorder and/or reparent a browse category",
    description=(
        "Partial update of a `BrowseCategory` (`extra='forbid'`, unknown keys → "
        "422). Only supplied fields change (`exclude_unset`). An explicit null "
        "on `name_pl` / `description_en` / `description_pl` / "
        "`inclusion_criterion` clears the field; an explicit null on "
        "`slug`/`name_en`/`position` is a 422 (those are NOT NULL); an explicit "
        "`parent_id: null` makes a child a root again and always succeeds. An "
        "empty `{}` body is a 200 no-op that still writes one "
        "`browse_category.update` audit row with before == after. Reparenting "
        "enforces the service-layer depth-2 ceiling: 422 `self_cycle`, 422 "
        "`parent_not_root` (target is itself a child), 422 "
        "`reparent_exceeds_depth` (this category has children, so moving it "
        "would push them to depth 3). Returns 200 + `BrowseCategoryAdminRead`. "
        "404 if the category or the new parent does not exist, 409 on a slug "
        "collision. Admin-only."
    ),
    response_model=BrowseCategoryAdminRead,
)
def admin_patch_category(
    category_id: uuid.UUID,
    patch: BrowseCategoryPatch,
    session: Annotated[Session, Depends(get_session)],
    actor_user_id: uuid.UUID = current_admin,
) -> BrowseCategoryAdminRead:
    try:
        cat = update_browse_category(
            session, category_id=category_id, patch=patch, actor_user_id=actor_user_id
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        if "slug_conflict" in str(exc):
            raise HTTPException(409, "slug already exists") from exc
        raise HTTPException(422, str(exc)) from exc
    return _admin_read(session, cat)
