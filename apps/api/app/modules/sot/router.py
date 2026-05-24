"""GET-only endpoints for the SoT entity tables.

Routes here read the new DB-backed entity tables. They coexist with
legacy /api/catalog/* (file-based) at distinct prefixes; legacy is left
untouched until the cutover slice.
"""

import io
import uuid
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlmodel import Session, select

from app.core.auth.dependencies import current_user
from app.core.config import get_settings
from app.core.db.models import Model, ModelFile, ModelFileKind, ModelSource, ModelStatus
from app.core.db.session import get_session
from app.core.etag import file_etag
from app.core.filenames import safe_filename
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
        "creating a model. Requires authenticated user (any role: admin / member / "
        "agent). Initiative 6 default-deny posture (architecture.md § Initiative 6 "
        "Decision M); see `_PUBLIC_ROUTES` allowlist for anonymous-allowed surfaces."
    ),
    response_model=CategoryTree,
)
def get_categories(
    session: Annotated[Session, Depends(get_session)],
    _user_id: uuid.UUID = current_user,
) -> CategoryTree:
    return list_categories_tree(session)


@router.get(
    "/tags",
    summary="List global tags (optional fuzzy search)",
    description=(
        "Returns up to `limit` tags, optionally filtered by substring match against "
        "`q` over `slug`/`name_en`/`name_pl`. Default `limit=50`, max `limit=200`. "
        "Requires authenticated user (any role: admin / member / agent). Initiative 6 "
        "default-deny posture (architecture.md § Initiative 6 Decision M)."
    ),
    response_model=list[TagRead],
)
def get_tags(
    session: Annotated[Session, Depends(get_session)],
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    _user_id: uuid.UUID = current_user,
) -> list[TagRead]:
    return list_tags(session, q=q, limit=limit)


@router.get(
    "/models",
    summary="List models with filtering, sorting, pagination",
    description=(
        "Returns `ModelListResponse` (paged). Filters: `category_ids` (OR — model in "
        "any listed category), `status`, **`tag_ids` (AND — model has ALL listed tags)**, "
        "`source`, `q` (case-insensitive substring across `name_en` / `name_pl` / `slug`; "
        "**does NOT search tag names**), `external_url` (exact match against any of the "
        "model's `model_external_link.url` rows — primary use case is agent-runbook "
        "dedup-by-source-URL pre-flight; typically 0 or 1 result), `include_deleted` "
        "(default false; soft-deleted rows are hidden). Sort modes: see `ModelListSort` "
        "enum (`recent`, etc.). Pagination: `offset` (≥0), `limit` (1-200, default 50). "
        "Requires authenticated user (any role: admin / member / agent). Initiative 6 "
        "default-deny posture (architecture.md § Initiative 6 Decision M)."
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
    external_url: str | None = None,
    sort: ModelListSort = ModelListSort.recent,
    include_deleted: bool = False,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    _user_id: uuid.UUID = current_user,
) -> ModelListResponse:
    return list_models(
        session,
        category_ids=category_ids,
        status=status,
        tag_ids=tag_ids,
        source=source,
        q=q,
        external_url=external_url,
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
        "links, and the `thumbnail_file_id` field (non-null UUID once a render lands). "
        "404 if the model is not found OR is soft-deleted (use `?include_deleted=true` "
        "to include). Requires authenticated user (any role: admin / member / agent). "
        "Initiative 6 default-deny posture (architecture.md § Initiative 6 Decision M)."
    ),
    response_model=ModelDetail,
)
def get_model(
    model_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    include_deleted: bool = False,
    _user_id: uuid.UUID = current_user,
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
        "`ModelFileKind`) narrows results. 404 if model not found. Requires "
        "authenticated user (any role: admin / member / agent). Initiative 6 "
        "default-deny posture (architecture.md § Initiative 6 Decision M). Use the "
        "streaming `/files/{file_id}/content` endpoint to fetch the binary."
    ),
    response_model=FileListResponse,
)
def get_model_files(
    model_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    kind: ModelFileKind | None = None,
    _user_id: uuid.UUID = current_user,
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
        "Content-Disposition with the original filename. `?variant=thumb` returns the "
        "Story 13.2 / Decision P WebP thumbnail variant (800px longest side, q80) when "
        "it exists on disk; `?variant=gallery` returns the Story 22.1 / Decision W "
        "WebP gallery-tier variant (1920px longest side, q80 — designer-locked per "
        "22-3-designer-ux-spec.md §3) when it exists on disk. Both variants silently "
        "fall back to the original blob when the sibling is missing (e.g. for files "
        "uploaded before the pipeline shipped and not yet backfilled, OR for non-image "
        "kinds where variants are never generated). 404 if the file row is not found "
        "OR doesn't belong to the given model (defense against cross-model file id "
        "confusion). 404 if the row exists but the on-disk blob is missing (integrity "
        "issue — applies even when a stale variant sidecar lingers, since variants are "
        "derivatives of the original). 500 if storage path resolution escapes the "
        "storage root (should never happen; defense in depth). Requires authenticated "
        "user (any role: admin / member / agent). Initiative 6 default-deny posture "
        "(architecture.md § Initiative 6 Decision M). Anonymous share-recipients access "
        "this content via the share-scoped endpoint "
        "`/api/share/{token}/files/{file_id}/content` (Decision N) — NOT via this route."
    ),
)
def get_model_file_content(
    model_id: uuid.UUID,
    file_id: uuid.UUID,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    download: bool = False,
    variant: str | None = Query(default=None),
    _user_id: uuid.UUID = current_user,
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

    # Story 13.2 / Decision P + Story 22.1 / Decision W — variant routing.
    # Two tiers, both materialised by ``generate_thumbnail`` arq task on
    # image-kind upload and stored as sibling files of the original:
    #   thumb   → ``<storage_path>.thumb.webp``    (800 px, ~50 KB)
    #   gallery → ``<storage_path>.gallery.webp`` (1920 px, ~150-500 KB)
    # When the requested variant's sibling exists, serve WebP at image/webp
    # media type. Backward-compat fallback to the original blob when the
    # sibling is missing keeps the endpoint safe for pre-pipeline files,
    # ungenerated kinds, and the gallery-tier backfill catch-up window
    # right after Story 22.1 deploy.
    #
    # Integrity gate (P2-2 fix-up on Codex review aa6a8eb): variants are
    # *derivatives* of the original. If the original file is gone on disk
    # the model is broken — return 404 even when a variant sidecar still
    # exists. Without this check, a stale sidecar (e.g. left behind after
    # a manual blob delete that bypassed delete_model_file) would mask the
    # integrity issue by silently serving the WebP. This gate applies to
    # BOTH variant tiers since both are derivatives.
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="File missing in storage")

    served = candidate
    served_mime = row.mime_type
    variant_candidate: Path | None = None
    if variant == "thumb":
        variant_candidate = candidate.with_name(candidate.name + ".thumb.webp")
    elif variant == "gallery":
        # Story 22.1 / Decision W — gallery-tier variant mirrors the thumb
        # branch exactly: resolve + base-check + sibling-is-file gate + same
        # silent-fallback semantics. The only difference is the suffix.
        variant_candidate = candidate.with_name(candidate.name + ".gallery.webp")
    if variant_candidate is not None:
        # Resolve + re-check under base for defense in depth.
        try:
            variant_candidate.resolve().relative_to(base)
        except (ValueError, OSError):
            variant_candidate = candidate  # fall back to original
        if variant_candidate != candidate and variant_candidate.is_file():
            served = variant_candidate
            served_mime = "image/webp"

    etag = file_etag(served)
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    return FileResponse(
        served,
        media_type=served_mime,
        filename=row.original_name if download else None,
        headers={"ETag": etag, "Cache-Control": "private, max-age=300"},
    )


# Initiative 10 Story 16.6 (FR10-DOWNLOAD-1) — bulk STL download (ZIP) restore.
# Pre-SoT migration shipped /api/files/{model_id}/bundle (commit caf4d5a, May
# 2026) using filesystem rglob; that endpoint dropped during the SoT cutover.
# This restores the same UX affordance ("Download all") against the new SoT
# storage layer: enumerate ModelFile rows for the model, filter to printable
# kinds, stream them as a ZIP_STORED archive with the model.name_en stem.
# Initiative 10 Story 16.6 — printable file kinds for bundle download.
# Mirrors the pre-SoT /api/files/bundle filter (caf4d5a, May 2026) under the
# new ModelFileKind enum: stl (canonical printable mesh), archive_3mf (Bambu /
# Orca slicer archives, typically printable directly), source (CAD source files
# — STEP / F3D — operator/designer may want them for remix). Excludes image
# (gallery photos) + print (photos of physical prints).
_BUNDLE_PRINTABLE_KINDS: tuple[ModelFileKind, ...] = (
    ModelFileKind.stl,
    ModelFileKind.archive_3mf,
    ModelFileKind.source,
)


class _ZipStreamBuffer(io.RawIOBase):
    """Append-only buffer that ZipFile writes to; we drain after each chunk."""

    def __init__(self) -> None:
        self._buf = bytearray()

    def writable(self) -> bool:
        return True

    def write(self, b: object) -> int:
        data = bytes(b)  # type: ignore[arg-type]
        self._buf.extend(data)
        return len(data)

    def drain(self) -> bytes:
        data = bytes(self._buf)
        self._buf.clear()
        return data


def _stream_zip(entries: list[tuple[Path, str]]) -> Iterator[bytes]:
    buf = _ZipStreamBuffer()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
        for src_path, arcname in entries:
            with (
                zf.open(arcname, mode="w", force_zip64=True) as zentry,
                src_path.open("rb") as src,
            ):
                while chunk := src.read(64 * 1024):
                    zentry.write(chunk)
                    if drained := buf.drain():
                        yield drained
            if drained := buf.drain():
                yield drained
    if drained := buf.drain():
        yield drained


def _content_disposition(filename: str) -> str:
    encoded = quote(filename, safe="")
    return f"attachment; filename*=UTF-8''{encoded}"


@router.get(
    "/models/{model_id}/bundle",
    summary="Download all printable files in a model as a ZIP",
    description=(
        "Streams every printable file (kinds: stl, step, f3d, three_mf, gcode, other) "
        "attached to the model as a ZIP_STORED archive with the model.name_en stem as "
        "filename. Initiative 10 Story 16.6 (FR10-DOWNLOAD-1) regression restore — the "
        "pre-SoT bundle endpoint (commit caf4d5a, May 2026) was dropped during the SoT "
        "cutover; the affordance is restored on the new storage layer. Requires "
        "authenticated user (any role). 404 if model not found OR no printable files. "
        "404 if any matched file's on-disk blob is missing (defense-in-depth integrity "
        "check). 500 if storage-path resolution escapes the storage root."
    ),
)
def download_model_bundle(
    model_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    _user_id: uuid.UUID = current_user,
) -> Response:
    model = session.exec(
        select(Model).where(Model.id == model_id, Model.deleted_at.is_(None))
    ).first()
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found")

    rows = session.exec(
        select(ModelFile)
        .where(ModelFile.model_id == model_id)
        .where(ModelFile.kind.in_(_BUNDLE_PRINTABLE_KINDS))
        .order_by(ModelFile.position, ModelFile.original_name)
    ).all()
    if not rows:
        raise HTTPException(status_code=404, detail="No printable files in this model")

    settings = get_settings()
    base = settings.portal_content_dir.resolve()
    entries: list[tuple[Path, str]] = []
    seen_arcnames: set[str] = set()
    for row in rows:
        candidate = (base / row.storage_path).resolve()
        try:
            candidate.relative_to(base)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail="Invalid storage path") from exc
        if not candidate.is_file():
            raise HTTPException(
                status_code=404, detail=f"File missing in storage: {row.original_name}"
            )
        # Sanitize the archive entry name. ModelFile.original_name comes from
        # upload-time client filenames + admin metadata patch — both untrusted.
        # Pre-Codex-P2 fix-up the raw value was used, allowing a malicious row
        # to inject "../evil.stl" or absolute paths into the ZIP. Split off the
        # extension before sanitizing the stem (safe_filename strips dots) and
        # re-attach. Empty extension is OK — the stem alone becomes the name.
        raw_name = row.original_name
        if "." in raw_name and not raw_name.startswith("."):
            stem, _, ext = raw_name.rpartition(".")
        else:
            stem, ext = raw_name, ""
        safe_stem = safe_filename(stem, fallback=str(row.id))
        safe_ext = safe_filename(ext, fallback="bin") if ext else ""
        arcname = f"{safe_stem}.{safe_ext}" if safe_ext else safe_stem
        # Deduplicate within the archive if two ModelFile rows happen to produce
        # the same sanitized name (unusual but possible after normalization):
        # append a numeric suffix before the extension.
        if arcname in seen_arcnames:
            suffix = 1
            while True:
                candidate_arc = (
                    f"{safe_stem}_{suffix}.{safe_ext}" if safe_ext else f"{safe_stem}_{suffix}"
                )
                if candidate_arc not in seen_arcnames:
                    arcname = candidate_arc
                    break
                suffix += 1
        seen_arcnames.add(arcname)
        entries.append((candidate, arcname))

    zip_stem = safe_filename(model.name_en or "", fallback=str(model_id))
    zip_filename = f"{zip_stem}.zip"
    return StreamingResponse(
        _stream_zip(entries),
        media_type="application/zip",
        headers={
            "Content-Disposition": _content_disposition(zip_filename),
            "Cache-Control": "private, no-store",
        },
    )
