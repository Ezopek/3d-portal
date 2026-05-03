import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlmodel import Session, func, select

from app.core.audit import record_event
from app.core.auth.dependencies import current_admin
from app.core.db.models import AuditEvent
from app.core.db.session import get_engine, get_session

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/refresh-catalog")
async def refresh_catalog(request: Request, user_id: int = current_admin) -> dict[str, int]:
    service = request.app.state.catalog_service
    overrides = request.app.state.thumbnail_overrides
    service.refresh()
    response = service.list_models()

    purged = overrides.purge_orphans(exists=service.thumbnail_target_exists)
    for model_id, relative_path in purged:
        record_event(
            get_engine(),
            kind="thumbnail.orphan_purged",
            actor_user_id=user_id,
            payload={"model_id": model_id, "relative_path": relative_path},
        )

    # Render-selection orphan purge (analogous to thumbnail orphans).
    selection_purged = request.app.state.render_selection.purge_orphans(
        exists=lambda mid, rel: service.thumbnail_target_exists(mid, rel)
    )
    for model_id, relative_path in selection_purged:
        record_event(
            get_engine(),
            kind="render_selection.orphan_purged",
            actor_user_id=user_id,
            payload={"model_id": model_id, "relative_path": relative_path},
        )

    missing = service.model_ids_missing_renders()
    for model_id in missing:
        selection = request.app.state.render_selection.get(model_id)
        await request.app.state.arq.enqueue_job(
            "render_model",
            model_id,
            selected_paths=selection or None,
        )

    record_event(
        get_engine(),
        kind="catalog.refresh",
        actor_user_id=user_id,
        payload={
            "total": response.total,
            "thumbnails_purged": len(purged),
            "renders_enqueued": len(missing),
        },
    )
    return {"total": response.total, "renders_enqueued": len(missing)}


@router.post("/render/{model_id}", status_code=202)
async def trigger_render(
    model_id: str,
    request: Request,
    user_id: int = current_admin,
) -> dict[str, str]:
    catalog = request.app.state.catalog_service
    if catalog.get_model(model_id) is None:
        raise HTTPException(404, f"Model {model_id} not found")
    selection = request.app.state.render_selection.get(model_id)
    job = await request.app.state.arq.enqueue_job(
        "render_model",
        model_id,
        selected_paths=selection or None,
    )
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


_THUMBNAIL_PATH_RE = re.compile(
    r"^(images|prints)/[^/]+\.(png|jpg|jpeg|webp)$|^(front|iso|side|top)\.png$"
)


class _ThumbnailPayload(BaseModel):
    path: str


@router.put("/models/{model_id}/thumbnail", status_code=204)
def set_thumbnail(
    model_id: str,
    payload: _ThumbnailPayload,
    request: Request,
    user_id: int = current_admin,
) -> None:
    service = request.app.state.catalog_service
    if service.get_model(model_id) is None:
        raise HTTPException(404, f"Model {model_id} not found")
    if not _THUMBNAIL_PATH_RE.match(payload.path):
        raise HTTPException(400, "invalid_thumbnail_path")
    if not service.thumbnail_target_exists(model_id, payload.path):
        raise HTTPException(404, "thumbnail_file_not_found")
    request.app.state.thumbnail_overrides.set(
        model_id=model_id,
        relative_path=payload.path,
        user_id=user_id,
    )
    record_event(
        get_engine(),
        kind="thumbnail.set",
        actor_user_id=user_id,
        payload={"model_id": model_id, "relative_path": payload.path},
    )


@router.delete("/models/{model_id}/thumbnail", status_code=204)
def clear_thumbnail(
    model_id: str,
    request: Request,
    user_id: int = current_admin,
) -> None:
    removed = request.app.state.thumbnail_overrides.clear(model_id)
    if removed:
        record_event(
            get_engine(),
            kind="thumbnail.cleared",
            actor_user_id=user_id,
            payload={"model_id": model_id},
        )


@router.get("/models/{model_id}/render-selection")
def get_render_selection(
    model_id: str,
    request: Request,
    _user_id: int = current_admin,
) -> dict[str, list[str]]:
    service = request.app.state.catalog_service
    if service.get_model(model_id) is None:
        raise HTTPException(404, f"Model {model_id} not found")
    selection = request.app.state.render_selection.get(model_id)
    available = service.list_files(model_id, kind="printable")
    return {"paths": selection, "available_stls": available}


_RENDER_SELECTION_PATH_RE = re.compile(
    r"^[^/.][^/]*(/[^/.][^/]*)*\.stl$",
    re.IGNORECASE,
)
_RENDER_SELECTION_MAX = 16


class _RenderSelectionPayload(BaseModel):
    paths: list[str]


@router.put("/models/{model_id}/render-selection", status_code=204)
async def set_render_selection(
    model_id: str,
    payload: _RenderSelectionPayload,
    request: Request,
    user_id: int = current_admin,
) -> None:
    service = request.app.state.catalog_service
    model = service.get_model(model_id)
    if model is None:
        raise HTTPException(404, f"Model {model_id} not found")

    if len(payload.paths) > _RENDER_SELECTION_MAX:
        raise HTTPException(400, f"too_many_files: max {_RENDER_SELECTION_MAX}")

    catalog_dir = service._catalog_dir  # intentional internal use
    base = (catalog_dir / model.path).resolve()
    for rel in payload.paths:
        if not _RENDER_SELECTION_PATH_RE.match(rel):
            raise HTTPException(400, f"invalid_path: {rel}")
        candidate = (catalog_dir / model.path / rel).resolve()
        try:
            candidate.relative_to(base)
        except ValueError:
            raise HTTPException(400, f"invalid_path: {rel}") from None
        if not (candidate.is_file() and candidate.suffix.lower() == ".stl"):
            raise HTTPException(400, f"file_not_found: {rel}")

    repo = request.app.state.render_selection
    current = set(repo.get(model_id))
    new_set = set(payload.paths)

    if current == new_set:
        return  # no-op, no enqueue

    if payload.paths:
        repo.set(model_id=model_id, paths=payload.paths, user_id=user_id)
        record_event(
            get_engine(),
            kind="render_selection.set",
            actor_user_id=user_id,
            payload={"model_id": model_id, "paths": payload.paths, "count": len(payload.paths)},
        )
    else:
        repo.clear(model_id)
        record_event(
            get_engine(),
            kind="render_selection.cleared",
            actor_user_id=user_id,
            payload={"model_id": model_id},
        )

    await request.app.state.arq.enqueue_job(
        "render_model",
        model_id,
        selected_paths=payload.paths or None,
    )
