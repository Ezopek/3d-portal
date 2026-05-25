"""Member-scoped share-link endpoints (Initiative 10 Story 16.3).

`/api/admin/share` is admin-only for list + revoke; member-side equivalent
lives here under `/api/me/share-links`. Authenticated members can list
ONLY the tokens they themselves minted (filtered by `created_by`) and
revoke ONLY their own tokens. Admins can use either surface; the
ownership filter makes the member endpoint a strict subset of admin's
list — admins running the member endpoint see only their own tokens
(intentional; keeps the contract simple).

Auth: `current_user` (any role: admin / member). The `agent` role can in
principle hit these endpoints too but agents don't mint share tokens via
the existing flow, so the list is normally empty for them.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlmodel import Session, select

from app.core.audit import record_event
from app.core.auth.dependencies import current_user
from app.core.db.models import Model
from app.core.db.session import get_engine, get_session
from app.modules.share.models import ShareResolveResponse, ShareToken
from app.modules.share.service import ShareService

router = APIRouter(prefix="/api/me/share-links", tags=["share", "member"])


def _service(request: Request) -> ShareService:
    return ShareService(redis=request.app.state.redis.get())


@router.get(
    "",
    response_model=dict,
    summary="List the current user's active share tokens",
    description=(
        "Returns share tokens the current user has minted. The same `ShareToken` shape "
        "as `/api/admin/share` but filtered to `created_by == current_user`. Used by the "
        "'My share links' settings page (Initiative 10 Story 16.3). Requires "
        "authenticated user; Initiative 6 default-deny posture. To revoke one of the "
        "listed tokens, DELETE `/api/me/share-links/{token}`."
    ),
)
async def list_my_share_links(
    request: Request,
    user_id: uuid.UUID = current_user,
) -> dict[str, list[ShareToken]]:
    all_tokens = await _service(request).list_active()
    mine = [t for t in all_tokens if t.created_by == user_id]
    return {"tokens": mine}


@router.delete(
    "/{token}",
    status_code=204,
    summary="Revoke one of the current user's share tokens",
    description=(
        "Revokes the share token if it was minted by the current user. Returns 204 on "
        "success, 404 if the token does not exist, 403 if the token exists but belongs "
        "to another user. Requires authenticated user. Audit-emits "
        "`share.revoke.member`."
    ),
)
async def revoke_my_share_link(
    token: str,
    request: Request,
    user_id: uuid.UUID = current_user,
) -> Response:
    service = _service(request)
    record = await service.resolve(token)
    if record is None:
        raise HTTPException(status_code=404, detail="Share token not found or expired")
    if record.created_by != user_id:
        raise HTTPException(status_code=403, detail="Not your share token")
    await service.revoke(token)
    record_event(
        get_engine(),
        action="share.revoke.member",
        entity_type="share_token",
        entity_id=None,
        actor_user_id=user_id,
        after={"token": token, "model_id": str(record.model_id)},
    )
    return Response(status_code=204)


@router.get(
    "/{token}/resolve",
    response_model=ShareResolveResponse,
    summary="Resolve a share token to its model_id for the authenticated caller",
    description=(
        "Initiative 18 Story 30.1 (Decision AA) — paired with Story 30.2 "
        "`MemberShareView` to enable B5 (active member receiving a share "
        "link from another member) enrich-in-place rendering at "
        "/share/<token>. Returns 200 with {model_id, access:'granted'} for "
        "a valid token + non-soft-deleted model. Uniform 404 on invalid / "
        "expired / revoked / soft-deleted (NFR18-TOKEN-ENUMERATION-1). "
        "Does NOT touch the /api/share/<token>/* public credentialless "
        "family (Decision AA prefix separation preserves NFR10 contract). "
        "Read-only: NO audit emission (mirrors list_my_share_links + "
        "anonymous share-resolve read-pattern conventions)."
    ),
)
async def resolve_my_share_link(
    token: str,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    _user_id: uuid.UUID = current_user,
) -> ShareResolveResponse:
    record = await _service(request).resolve(token)
    if record is None:
        raise HTTPException(status_code=404, detail="Share token not found or expired")

    # AC-5 soft-delete check — uniform 404 (NOT a distinct "model gone"
    # detail). Same enumeration-oracle defense as the anonymous
    # /api/share/<token> resolve_share handler.
    model = session.exec(
        select(Model).where(Model.id == record.model_id, Model.deleted_at.is_(None))
    ).first()
    if model is None:
        raise HTTPException(status_code=404, detail="Share token not found or expired")

    return ShareResolveResponse(model_id=record.model_id, access="granted")
