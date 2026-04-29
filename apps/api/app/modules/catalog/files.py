from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.etag import file_etag

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/{model_id}/{relative:path}")
def serve_file(model_id: str, relative: str, request: Request) -> Response:
    service = request.app.state.catalog_service
    model = service.get_model(model_id)
    if model is None:
        raise HTTPException(404, f"Model {model_id} not found")

    catalog_dir = service._catalog_dir  # intentional internal use
    renders_dir = get_settings().renders_dir

    candidates = []

    base_catalog = (catalog_dir / model.path).resolve()
    candidate_catalog = (base_catalog / relative).resolve()
    try:
        candidate_catalog.relative_to(base_catalog)
        candidates.append(candidate_catalog)
    except ValueError as exc:
        raise HTTPException(400, "Invalid path") from exc

    base_renders = (renders_dir / model_id).resolve()
    candidate_renders = (base_renders / relative).resolve()
    try:
        candidate_renders.relative_to(base_renders)
        candidates.append(candidate_renders)
    except ValueError:
        pass  # renders path traversal — silently skip, the catalog candidate already validated

    for candidate in candidates:
        if candidate.is_file():
            etag = file_etag(candidate)
            if request.headers.get("if-none-match") == etag:
                return Response(status_code=304, headers={"ETag": etag})
            return FileResponse(
                candidate,
                headers={"ETag": etag, "Cache-Control": "private, max-age=300"},
            )
    raise HTTPException(404, "File not found")
