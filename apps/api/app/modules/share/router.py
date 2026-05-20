import hashlib
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy import nullslast
from sqlmodel import Session, select

from app.core.audit import record_event
from app.core.auth.ratelimit import _client_ip
from app.core.config import get_settings
from app.core.db.models import (
    Category,
    Model,
    ModelFile,
    ModelFileKind,
    ModelTag,
    Tag,
)
from app.core.db.session import get_engine, get_session
from app.modules.share.models import ShareModelView
from app.modules.share.service import ShareService

router = APIRouter(prefix="/api/share", tags=["share"])

# Initiative 6 Story 11.2 Decision N — share-asset endpoint surfaces only
# files of these kinds, mirroring the share-resolve handler's URL emission
# (image + print for thumbnails / image gallery; stl for download/viewer).
# `source` + `archive_3mf` are NEVER surfaced via share path (codex peer-grill
# 2026-05-20 finding: raw scope-check would over-grant same-model files).
_SHARE_ALLOWED_KINDS: frozenset[ModelFileKind] = frozenset(
    {ModelFileKind.image, ModelFileKind.print, ModelFileKind.stl}
)


@router.get("/{token}", response_model=ShareModelView)
async def resolve_share(
    token: str,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> ShareModelView:
    service = ShareService(redis=request.app.state.redis.get())
    record = await service.resolve(token)
    if record is None:
        raise HTTPException(404, "Share token not found or expired")

    model = session.exec(
        select(Model).where(Model.id == record.model_id, Model.deleted_at.is_(None))
    ).first()
    if model is None:
        raise HTTPException(404, "Model no longer exists")

    category = session.exec(select(Category).where(Category.id == model.category_id)).one()

    tag_rows = session.exec(
        select(Tag.name_en)
        .join(ModelTag, ModelTag.tag_id == Tag.id)
        .where(ModelTag.model_id == model.id)
        .order_by(Tag.slug)
    ).all()
    tags = list(tag_rows)

    image_files = session.exec(
        select(ModelFile.id)
        .where(ModelFile.model_id == model.id)
        .where(ModelFile.kind.in_([ModelFileKind.image, ModelFileKind.print]))
        .order_by(nullslast(ModelFile.position.asc()), ModelFile.created_at.asc())
    ).all()
    # Initiative 6 Decision N — emit share-scoped URLs (`/api/share/{token}/...`)
    # instead of legacy `/api/models/{id}/...` URLs. The legacy SoT content
    # endpoint is post-Story-11.1 `current_user`-gated; anonymous share
    # recipients reach assets exclusively via the share path.
    images = [f"/api/share/{token}/files/{fid}/content" for fid in image_files]

    thumbnail_url = None
    if model.thumbnail_file_id is not None:
        thumbnail_url = f"/api/share/{token}/files/{model.thumbnail_file_id}/content"
    elif images:
        thumbnail_url = images[0]

    stl_row = session.exec(
        select(ModelFile.id)
        .where(ModelFile.model_id == model.id)
        .where(ModelFile.kind == ModelFileKind.stl)
        .order_by(ModelFile.created_at.asc())
    ).first()
    stl_url = (
        f"/api/share/{token}/files/{stl_row}/content?download=1" if stl_row is not None else None
    )

    return ShareModelView(
        id=model.id,
        name_en=model.name_en,
        name_pl=model.name_pl,
        category=category.slug,
        tags=tags,
        thumbnail_url=thumbnail_url,
        has_3d=stl_row is not None,
        images=images,
        notes_en="",
        notes_pl="",
        stl_url=stl_url,
    )


@router.get(
    "/{token}/files/{file_id}/content",
    summary="Stream a share-scoped model file's binary content (anonymous)",
    description=(
        "Initiative 6 Story 11.2 / Decision N — anonymous share-scoped asset endpoint. "
        "Validates the share token via `ShareService.resolve(token)`, checks the file "
        "belongs to the token-bound model AND that the file kind is in "
        "{image, print, stl} (the kinds share-resolve surfaces; `source` + "
        "`archive_3mf` are explicitly NOT exposed via share), AND that the model is "
        "not soft-deleted. ALL failure modes return uniform 404 (no IDOR enumeration "
        "oracle). Cache-Control: no-store (prevents revoked tokens from serving cached "
        "responses post-revoke). No ETag (would short-circuit scope check). The "
        "endpoint is anonymous-allowed under the `/api/share/*` prefix (no auth "
        "dependency); pre-Initiative-6 it was implicit via the nginx allowlist that "
        "Story 10.3 cutover removed."
    ),
)
async def get_share_asset(
    token: str,
    file_id: uuid.UUID,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    download: bool = False,
) -> Response:
    """Serve a share-scoped binary asset to an anonymous share recipient.

    Step 1 — Token resolve (Redis primary). Uniform 404 on miss: do NOT
    distinguish "invalid token" / "expired" / "revoked" externally
    (timing-distinguishable responses leak a token-state oracle).

    Step 2 — Scope check before any disk I/O. The scope query joins
    ModelFile with Model and enforces:
      - file_id matches AND model_id equals the token-bound record.model_id
      - file kind in {image, print, stl} (matches share-resolve URL emission)
      - model.deleted_at IS NULL (no soft-deleted leakage)
    Failure modes (wrong model, wrong kind, soft-deleted, missing row) all
    produce uniform 404.

    Step 3 — Audit emission BEFORE serving. Captures access intent
    regardless of downstream disk outcome. `target_token_hash` is
    sha256 hex of the token; the clear token is NEVER stored in audit.

    Step 4 — Serve content with `Cache-Control: no-store`. Overrides
    the sot/router.py default of `private, max-age=300` so revoked tokens
    cannot serve cached content for up to 300s post-revoke from
    intermediate caches / browser cache. No ETag header (premature
    ETag-match would short-circuit the scope check).
    """
    # Pre-compute token hash + trusted client IP once — used by every audit
    # row (success + every fail branch). Token-hash is computed unconditionally
    # so brute-force / revoked-token-reuse attempts are still auditable even
    # before token resolves.
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    client_ip = _client_ip(request)

    # Step 1: token resolve. Codex P2-1 (2026-05-20) — emit fail audit BEFORE
    # the early return so brute-force / expired-or-revoked-token reuse
    # attempts are captured for NFR6-OBS-1 observability (otherwise only
    # post-resolve scope failures are logged and brute-force is silent).
    service = ShareService(redis=request.app.state.redis.get())
    record = await service.resolve(token)
    if record is None:
        record_event(
            get_engine(),
            action="share.asset.fail",
            entity_type="share_token",
            entity_id=None,
            actor_user_id=None,
            after={
                "target_token_hash": token_hash,
                "target_file_id": str(file_id),
                "reason": "token_resolve_failed",
                "ip": client_ip,
            },
        )
        raise HTTPException(404, "Share asset not found")

    # Step 2: scope check (file belongs to model, kind is shareable, model not soft-deleted)
    file_row = session.exec(
        select(ModelFile)
        .join(Model, Model.id == ModelFile.model_id)
        .where(
            ModelFile.id == file_id,
            ModelFile.model_id == record.model_id,
            ModelFile.kind.in_(_SHARE_ALLOWED_KINDS),
            Model.deleted_at.is_(None),
        )
    ).first()
    if file_row is None:
        # Uniform 404 — no enumeration oracle on wrong-model / wrong-kind /
        # soft-deleted / missing-row.
        record_event(
            get_engine(),
            action="share.asset.fail",
            entity_type="share_token",
            entity_id=None,
            actor_user_id=None,
            after={
                "target_token_hash": token_hash,
                "target_file_id": str(file_id),
                "target_model_id": str(record.model_id),
                "reason": "scope_check_failed",
                "ip": client_ip,
            },
        )
        raise HTTPException(404, "Share asset not found")

    # Step 3: disk-path resolution + path-traversal defense (mirrors sot/router.py)
    settings = get_settings()
    base = settings.portal_content_dir.resolve()
    candidate = (base / file_row.storage_path).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        # Should never happen given DB-controlled storage_path, but defense in depth.
        record_event(
            get_engine(),
            action="share.asset.fail",
            entity_type="share_token",
            entity_id=None,
            actor_user_id=None,
            after={
                "target_token_hash": token_hash,
                "target_file_id": str(file_id),
                "target_model_id": str(record.model_id),
                "reason": "storage_path_escape",
                "ip": client_ip,
            },
        )
        raise HTTPException(500, "Invalid storage path") from exc
    if not candidate.is_file():
        # DB row exists but file missing on disk — integrity issue; uniform 404
        record_event(
            get_engine(),
            action="share.asset.fail",
            entity_type="share_token",
            entity_id=None,
            actor_user_id=None,
            after={
                "target_token_hash": token_hash,
                "target_file_id": str(file_id),
                "target_model_id": str(record.model_id),
                "reason": "file_missing_on_disk",
                "ip": client_ip,
            },
        )
        raise HTTPException(404, "Share asset not found")

    # Step 4: audit emission BEFORE serving (captures access intent)
    record_event(
        get_engine(),
        action="share.asset.fetched",
        entity_type="share_token",
        entity_id=None,
        actor_user_id=None,
        after={
            "target_token_hash": token_hash,
            "target_model_id": str(record.model_id),
            "target_file_id": str(file_id),
            "target_file_kind": file_row.kind.value,
            "download": download,
            "ip": client_ip,
        },
    )

    # Step 5: serve with Cache-Control: no-store. Codex P2-2 (2026-05-20) —
    # Starlette's FileResponse auto-adds ETag + Last-Modified validators
    # from the on-disk stat. The Decision N hardening contract requires no
    # cache validators on share assets. Codex follow-up P2 (2026-05-20):
    # FileResponse calls `set_stat_headers()` at __call__ time (NOT __init__)
    # UNLESS `stat_result` is passed to the constructor — without it, the
    # validators don't exist yet at construction so `del response.headers[...]`
    # is a no-op. Pass the pre-computed stat to force set_stat_headers to run
    # in __init__, then strip the unwanted validators.
    stat_result = candidate.stat()
    response = FileResponse(
        candidate,
        media_type=file_row.mime_type,
        filename=file_row.original_name if download else None,
        headers={"Cache-Control": "no-store"},
        stat_result=stat_result,
    )
    # Validators now populated by FileResponse.__init__ → set_stat_headers().
    # Strip them defensively (`in` guard makes this idempotent if Starlette
    # ever changes the auto-set names).
    for header_name in ("etag", "last-modified"):
        if header_name in response.headers:
            del response.headers[header_name]
    return response
