from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session, func, select

from app.core.audit import record_event
from app.core.auth.dependencies import current_admin
from app.core.db.models import AuditEvent
from app.core.db.session import get_engine, get_session

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/refresh-catalog")
def refresh_catalog(request: Request, user_id: int = current_admin) -> dict[str, int]:
    service = request.app.state.catalog_service
    service.refresh()
    response = service.list_models()
    record_event(
        get_engine(),
        kind="catalog.refresh",
        actor_user_id=user_id,
        payload={"total": response.total},
    )
    return {"total": response.total}


@router.post("/render/{model_id}", status_code=202)
async def trigger_render(
    model_id: str,
    request: Request,
    user_id: int = current_admin,
) -> dict[str, str]:
    catalog = request.app.state.catalog_service
    if catalog.get_model(model_id) is None:
        raise HTTPException(404, f"Model {model_id} not found")
    job = await request.app.state.arq.enqueue_job("render_model", model_id)
    record_event(
        get_engine(),
        kind="render.triggered",
        actor_user_id=user_id,
        payload={"model_id": model_id, "job_id": job.job_id},
    )
    return {"job_id": job.job_id, "model_id": model_id}


@router.get("/jobs/{model_id}")
async def render_status(
    model_id: str,
    request: Request,
    _user_id: int = current_admin,
) -> dict[str, str]:
    redis = request.app.state.redis.get()
    raw = await redis.get(f"render:status:{model_id}")
    if raw is None:
        return {"model_id": model_id, "status": "unknown"}
    return {"model_id": model_id, "status": raw.decode()}


@router.post("/sentry-test", status_code=204)
def sentry_test(_user_id: int = current_admin) -> None:
    """Deliberately raise to verify GlitchTip plumbing. Admin-only."""
    raise RuntimeError("sentry-test: deliberate test event")


@router.get("/audit")
def list_audit(
    session: Annotated[Session, Depends(get_session)],
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _user_id: int = current_admin,
) -> dict:
    total = session.exec(select(func.count()).select_from(AuditEvent)).one()
    rows = session.exec(
        select(AuditEvent).order_by(AuditEvent.id.desc()).offset(offset).limit(limit),
    ).all()
    return {
        "total": total,
        "events": [
            {
                "id": e.id,
                "at": e.at.isoformat(),
                "actor_user_id": e.actor_user_id,
                "kind": e.kind,
                "payload": e.payload,
            }
            for e in rows
        ],
    }
