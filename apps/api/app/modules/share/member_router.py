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

from fastapi import APIRouter, HTTPException, Request, Response

from app.core.audit import record_event
from app.core.auth.dependencies import current_user
from app.core.db.session import get_engine
from app.modules.share.models import ShareToken
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
