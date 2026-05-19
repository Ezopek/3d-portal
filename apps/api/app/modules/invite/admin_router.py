"""Admin endpoints for invite-token lifecycle (Initiative 5 Story 6.3).

Mirrors the Init 0 share-admin shape in
``apps/api/app/modules/share/admin_router.py`` with the same conventions:
- ``_service(request)`` factory builds the InviteService per request,
- ``current_admin`` dependency on every route,
- ``record_event()`` emission in the router (NOT the service),
- FastAPI default ``{"detail": "..."}`` error envelope.

Audit actions emitted:
- ``auth.invite.generated`` on POST /api/admin/invites (201)
- ``auth.invite.revoked``  on POST /api/admin/invites/{id}/revoke (204)
"""

from __future__ import annotations

import datetime
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlmodel import Session, select

from app.core.audit import record_event
from app.core.auth.dependencies import current_admin
from app.core.db.session import get_engine, get_session
from app.modules.invite import (
    GenerateInviteRequest,
    GenerateInviteResponse,
    InviteAlreadyResolved,
    InviteListItem,
    InviteListResponse,
    InviteNotFound,
    InviteService,
    InviteToken,
)
from app.modules.invite.admin_schemas import derive_status

router = APIRouter(prefix="/api/admin/invites", tags=["admin", "invite"])


def _service(request: Request) -> InviteService:
    return InviteService(redis=request.app.state.redis.get(), engine=get_engine())


@router.post(
    "",
    status_code=201,
    response_model=GenerateInviteResponse,
    summary="Generate a single-use invite token",
    description=(
        "Mints a fresh invite token (32-byte URL-safe entropy) with the given "
        "role and TTL. Returns the cleartext token EXACTLY ONCE in the response "
        "body; subsequent list-invite reads expose only the token metadata "
        "(never the cleartext). Emits an ``auth.invite.generated`` audit row. "
        "Accept either ``ttl_preset`` (enum-name string, e.g. ``SEVEN_DAYS``) "
        "or ``ttl_seconds`` (raw int in [60, 7776000]); supply EXACTLY ONE."
    ),
)
async def generate_invite(
    payload: GenerateInviteRequest,
    request: Request,
    user_id: uuid.UUID = current_admin,
) -> GenerateInviteResponse:
    ttl_seconds = payload.resolve_ttl_seconds()
    try:
        result = await _service(request).generate_invite(
            role=payload.role,
            ttl_seconds=ttl_seconds,
            generated_by_user_id=user_id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    invite = result.invite
    expires_at = invite.generated_at + datetime.timedelta(seconds=invite.ttl_seconds)
    record_event(
        get_engine(),
        action="auth.invite.generated",
        entity_type="invite_token",
        entity_id=invite.id,
        actor_user_id=user_id,
        after={"role": invite.role, "ttl_seconds": invite.ttl_seconds},
        request_id=request.headers.get("x-request-id"),
    )
    return GenerateInviteResponse(
        invite_id=invite.id,
        token=result.token,
        registration_url=f"/register?token={result.token}",
        role=invite.role,
        ttl_seconds=invite.ttl_seconds,
        expires_at=expires_at,
    )


@router.get(
    "",
    response_model=InviteListResponse,
    summary="List invite tokens with status filter + pagination",
    description=(
        "Returns invite-token rows from the DB (NOT Redis — Decision A "
        "authoritative-history rule). Status is computed per-row from "
        "``(used_at, revoked_at, generated_at + ttl_seconds)`` with precedence "
        "``revoked > used > expired > active``. Cleartext token NEVER appears "
        "in the response (Decision B hygiene rule). Ordering is "
        "``generated_at DESC``; pagination is 1-indexed with ``page_size`` "
        "capped at 200. Pages beyond the last return an empty ``items`` array "
        "(NOT 404)."
    ),
)
async def list_invites(
    session: Annotated[Session, Depends(get_session)],
    status_filter: Annotated[
        Literal["active", "used", "expired", "revoked"] | None,
        Query(alias="status"),
    ] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    _user_id: uuid.UUID = current_admin,
) -> InviteListResponse:
    now = datetime.datetime.now(datetime.UTC)
    # Admin-bounded dataset (O(thousands) lifetime); fetch all rows, compute
    # derived status in Python, filter + slice. See Story 6.3 Dev Notes
    # § "List endpoint — pagination + computed-status interaction".
    rows = session.exec(select(InviteToken).order_by(InviteToken.generated_at.desc())).all()
    items: list[InviteListItem] = []
    for row in rows:
        item_status = derive_status(
            used_at=row.used_at,
            revoked_at=row.revoked_at,
            generated_at=row.generated_at,
            ttl_seconds=row.ttl_seconds,
            now=now,
        )
        if status_filter is not None and item_status != status_filter:
            continue
        items.append(
            InviteListItem(
                invite_id=row.id,
                role=row.role,
                ttl_seconds=row.ttl_seconds,
                generated_by_user_id=row.generated_by_user_id,
                generated_at=row.generated_at,
                expires_at=row.generated_at + datetime.timedelta(seconds=row.ttl_seconds),
                used_by_user_id=row.used_by_user_id,
                used_at=row.used_at,
                used_from_ip=row.used_from_ip,
                revoked_at=row.revoked_at,
                status=item_status,
            )
        )
    total = len(items)
    offset = (page - 1) * page_size
    sliced = items[offset : offset + page_size]
    return InviteListResponse(total=total, items=sliced, page=page, page_size=page_size)


@router.post(
    "/{invite_id}/revoke",
    status_code=204,
    summary="Revoke an active invite token",
    description=(
        "Marks the invite ``revoked_at`` (DB-side CAS predicate "
        "``used_at IS NULL AND revoked_at IS NULL``) and deletes the matching "
        "Redis key. A subsequent ``/register?token=<...>`` returns HTTP 410. "
        "Returns 404 if the id doesn't exist, 409 if the invite is already "
        "used or already revoked. Emits an ``auth.invite.revoked`` audit row."
    ),
)
async def revoke_invite(
    invite_id: uuid.UUID,
    request: Request,
    user_id: uuid.UUID = current_admin,
) -> Response:
    try:
        await _service(request).revoke(invite_id)
    except InviteNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "invite not found") from exc
    except InviteAlreadyResolved as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "invite already used or revoked") from exc
    record_event(
        get_engine(),
        action="auth.invite.revoked",
        entity_type="invite_token",
        entity_id=invite_id,
        actor_user_id=user_id,
        after={"invite_id": str(invite_id)},
        request_id=request.headers.get("x-request-id"),
    )
    return Response(status_code=204)
