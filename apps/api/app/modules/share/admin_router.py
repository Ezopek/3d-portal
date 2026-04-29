from fastapi import APIRouter, HTTPException, Request, Response

from app.core.audit import record_event
from app.core.auth.dependencies import current_admin
from app.core.db.session import get_engine
from app.modules.share.models import (
    CreateShareRequest,
    CreateShareResponse,
    ShareToken,
)
from app.modules.share.service import ShareService

router = APIRouter(prefix="/api/admin/share", tags=["admin", "share"])


def _service(request: Request) -> ShareService:
    return ShareService(redis=request.app.state.redis.get())


@router.post("", status_code=201, response_model=CreateShareResponse)
async def create_share(
    payload: CreateShareRequest,
    request: Request,
    user_id: int = current_admin,
) -> CreateShareResponse:
    catalog = request.app.state.catalog_service
    if catalog.get_model(payload.model_id) is None:
        raise HTTPException(404, f"Model {payload.model_id} not found")
    record = await _service(request).create(
        model_id=payload.model_id,
        expires_in_hours=payload.expires_in_hours,
        created_by=user_id,
    )
    record_event(
        get_engine(),
        kind="share.created",
        actor_user_id=user_id,
        payload={"token": record.token, "model_id": record.model_id},
    )
    return CreateShareResponse(
        token=record.token,
        url=f"/share/{record.token}",
        expires_at=record.expires_at,
    )


@router.get("", response_model=dict)
async def list_share(request: Request, _user_id: int = current_admin) -> dict[str, list[ShareToken]]:
    tokens = await _service(request).list_active()
    return {"tokens": tokens}


@router.delete("/{token}", status_code=204)
async def revoke_share(
    token: str,
    request: Request,
    user_id: int = current_admin,
) -> Response:
    await _service(request).revoke(token)
    record_event(
        get_engine(),
        kind="share.revoked",
        actor_user_id=user_id,
        payload={"token": token},
    )
    return Response(status_code=204)
