from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
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
