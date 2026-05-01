import io
import zipfile
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse

from app.core.config import get_settings
from app.core.etag import file_etag
from app.core.filenames import safe_filename
from app.modules.catalog.thumbnails import (
    InvalidWidthError,
    NotAnImageError,
    resize_image,
)

router = APIRouter(prefix="/api/files", tags=["files"])


class _ZipStreamBuffer(io.RawIOBase):
    """Append-only buffer that ZipFile writes to; we drain after each chunk."""

    def __init__(self) -> None:
        self._buf = bytearray()

    def writable(self) -> bool:
        return True

    def write(self, b: object) -> int:  # bytes-like
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


# Bundle route is declared BEFORE the catch-all `/{model_id}/{relative:path}`
# below so the literal segment `bundle` takes precedence. A file literally
# named `bundle` (no extension) at the model root is therefore unreachable via
# the catch-all — acceptable, since real catalog files always have extensions.
@router.get("/{model_id}/bundle")
def download_bundle(model_id: str, request: Request) -> Response:
    settings = get_settings()
    service = request.app.state.catalog_service
    model = service.get_model(model_id)
    if model is None:
        raise HTTPException(404, f"Model {model_id} not found")

    catalog_dir = service._catalog_dir  # intentional internal use
    base = (catalog_dir / model.path).resolve()
    if not base.is_dir():
        raise HTTPException(404, "Model directory not found")

    extensions = {ext.lower() for ext in settings.download_extensions}
    matches: list[Path] = []
    for path in sorted(base.rglob("*")):
        if path.is_file() and path.suffix.lower() in extensions:
            matches.append(path)

    if not matches:
        raise HTTPException(404, "No printable files in this model")

    bundle_stem = safe_filename(model.name_en, fallback=model.id)

    if len(matches) == 1:
        only = matches[0]
        etag = file_etag(only)
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers={"ETag": etag})
        return FileResponse(
            only,
            filename=only.name,
            headers={"ETag": etag, "Cache-Control": "private, max-age=300"},
        )

    entries = [(p, str(p.relative_to(base)).replace("\\", "/")) for p in matches]
    zip_filename = f"{bundle_stem}.zip"
    return StreamingResponse(
        _stream_zip(entries),
        media_type="application/zip",
        headers={
            "Content-Disposition": _content_disposition(zip_filename),
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/{model_id}/{relative:path}")
def serve_file(
    model_id: str,
    relative: str,
    request: Request,
    download: bool = False,
    w: int | None = None,
) -> Response:
    service = request.app.state.catalog_service
    model = service.get_model(model_id)
    if model is None:
        raise HTTPException(404, f"Model {model_id} not found")

    catalog_dir = service._catalog_dir  # intentional internal use
    settings = get_settings()
    renders_dir = settings.renders_dir

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
        if not candidate.is_file():
            continue
        if w is not None and candidate.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            try:
                resized = resize_image(candidate, width=w, cache_root=settings.catalog_cache_dir)
            except InvalidWidthError as exc:
                raise HTTPException(400, str(exc)) from exc
            except NotAnImageError:
                # Decoder couldn't read it — fall through and serve original.
                pass
            else:
                etag = file_etag(resized)
                if request.headers.get("if-none-match") == etag:
                    return Response(status_code=304, headers={"ETag": etag})
                return FileResponse(
                    resized,
                    media_type="image/webp",
                    headers={"ETag": etag, "Cache-Control": "public, max-age=86400"},
                )
        etag = file_etag(candidate)
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers={"ETag": etag})
        return FileResponse(
            candidate,
            filename=candidate.name if download else None,
            headers={"ETag": etag, "Cache-Control": "private, max-age=300"},
        )
    raise HTTPException(404, "File not found")
