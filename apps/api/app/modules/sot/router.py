"""GET-only endpoints for the SoT entity tables.

Routes here read the new DB-backed entity tables. They coexist with
legacy /api/catalog/* (file-based) at distinct prefixes; legacy is left
untouched until the cutover slice.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.db.models import ModelFile, ModelFileKind, ModelSource, ModelStatus
from app.core.db.session import get_session
from app.core.etag import file_etag
from app.modules.sot.schemas import (
    CategoryTree,
    FileListResponse,
    ModelDetail,
    ModelListResponse,
    TagRead,
)
from app.modules.sot.service import (
    ModelListSort,
    get_model_detail,
    list_categories_tree,
    list_model_files,
    list_models,
    list_tags,
)

router = APIRouter(prefix="/api", tags=["sot-read"])


@router.get(
    "/categories",
    summary="Get the full category tree",
    description=(
        "Returns the complete hierarchical category tree (`CategoryTree`). Used by "
        "agents during the pre-flight check to confirm a target slug exists before "
        "creating a model. Public, unauthenticated."
    ),
    response_model=CategoryTree,
)
def get_categories(
    session: Annotated[Session, Depends(get_session)],
) -> CategoryTree:
    return list_categories_tree(session)


@router.get(
    "/tags",
    summary="List global tags (optional fuzzy search)",
    description=(
        "Returns up to `limit` tags, optionally filtered by substring match against "
        "`q` over `slug`/`name_en`/`name_pl`. Default `limit=50`, max `limit=200`. "
        "Public, unauthenticated."
    ),
    response_model=list[TagRead],
)
def get_tags(
    session: Annotated[Session, Depends(get_session)],
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[TagRead]:
    return list_tags(session, q=q, limit=limit)


@router.get(
    "/models",
    summary="List models with filtering, sorting, pagination",
    description=(
        "Returns `ModelListResponse` (paged). Filters: `category_ids` (OR), `status`, "
        "`tag_ids` (OR), `source`, `q` (substring search across name + tags), "
        "`include_deleted` (default false; soft-deleted rows are hidden). Sort modes: "
        "see `ModelListSort` enum (`recent`, etc.). Pagination: `offset` (≥0), "
        "`limit` (1-200, default 50). Public, unauthenticated."
    ),
    response_model=ModelListResponse,
)
def get_models(
    session: Annotated[Session, Depends(get_session)],
    category_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    status: ModelStatus | None = None,
    tag_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    source: ModelSource | None = None,
    q: str | None = None,
    sort: ModelListSort = ModelListSort.recent,
    include_deleted: bool = False,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> ModelListResponse:
    return list_models(
        session,
        category_ids=category_ids,
        status=status,
        tag_ids=tag_ids,
        source=source,
        q=q,
        sort=sort,
        include_deleted=include_deleted,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/models/{model_id}",
    summary="Get a single model's full detail",
    description=(
        "Returns `ModelDetail` including category, tags, files, notes, prints, external "
        "links, and the `thumbnail` field (non-null once a render lands). 404 if the "
        "model is not found OR is soft-deleted (use `?include_deleted=true` to include). "
        "Public, unauthenticated."
    ),
    response_model=ModelDetail,
)
def get_model(
    model_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    include_deleted: bool = False,
) -> ModelDetail:
    detail = get_model_detail(session, model_id, include_deleted=include_deleted)
    if detail is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return detail


@router.get(
    "/models/{model_id}/files",
    summary="List a model's files (optionally filtered by kind)",
    description=(
        "Returns `FileListResponse` for the given model. `kind` query (one of "
        "`ModelFileKind`) narrows results. 404 if model not found. Public, "
        "unauthenticated. Use the streaming `/files/{file_id}/content` endpoint to "
        "fetch the binary."
    ),
    response_model=FileListResponse,
)
def get_model_files(
    model_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    kind: ModelFileKind | None = None,
) -> FileListResponse:
    result = list_model_files(session, model_id, kind=kind)
    if result is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return result


@router.get(
    "/models/{model_id}/files/{file_id}/content",
    summary="Stream a model file's binary content",
    description=(
        "Streams the raw bytes of the file from `portal-content` storage. ETag header is "
        "set; If-None-Match returns 304 on cache hit. `?download=true` adds a "
        "Content-Disposition with the original filename. 404 if the file row is not "
        "found OR doesn't belong to the given model (defense against cross-model file "
        "id confusion). 404 if the row exists but the on-disk blob is missing "
        "(integrity issue). 500 if storage path resolution escapes the storage root "
        "(should never happen; defense in depth)."
    ),
)
def get_model_file_content(
    model_id: uuid.UUID,
    file_id: uuid.UUID,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    download: bool = False,
) -> Response:
    """Stream a model file's binary content from portal-content storage.

    Returns 404 if the file row is not found OR if it does not belong to
    the given `model_id` (paths are constructed defensively to prevent
    confused-deputy attacks across models).
    """
    row = session.exec(
        select(ModelFile).where(ModelFile.id == file_id, ModelFile.model_id == model_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="File not found")

    settings = get_settings()
    base = settings.portal_content_dir.resolve()
    candidate = (base / row.storage_path).resolve()
    # Path traversal defense: storage_path comes from DB but assert
    # the resolved path stays under the storage root anyway.
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Invalid storage path") from exc
    if not candidate.is_file():
        # DB row exists but file missing on disk — integrity issue.
        raise HTTPException(status_code=404, detail="File missing in storage")

    etag = file_etag(candidate)
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    return FileResponse(
        candidate,
        media_type=row.mime_type,
        filename=row.original_name if download else None,
        headers={"ETag": etag, "Cache-Control": "private, max-age=300"},
    )
