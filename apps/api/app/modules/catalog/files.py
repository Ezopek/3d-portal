from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse

from app.core.etag import file_etag

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/{model_id}/{relative:path}")
def serve_file(model_id: str, relative: str, request: Request) -> Response:
    service = request.app.state.catalog_service
    model = service.get_model(model_id)
    if model is None:
        raise HTTPException(404, f"Model {model_id} not found")

    catalog_dir = service._catalog_dir  # intentional internal use
    base = (catalog_dir / model.path).resolve()
    candidate = (base / relative).resolve()

    # Path-traversal guard: candidate must remain inside base.
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise HTTPException(400, "Invalid path") from exc

    if not candidate.is_file():
        raise HTTPException(404, "File not found")

    etag = file_etag(candidate)
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})

    return FileResponse(
        candidate,
        headers={"ETag": etag, "Cache-Control": "private, max-age=300"},
    )
