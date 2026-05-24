import contextlib
import hashlib
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, nullslast
from sqlmodel import Session, select

from app.core.audit import record_event
from app.core.auth.ratelimit import _client_ip
from app.core.config import get_settings
from app.core.db.models import (
    Category,
    Model,
    ModelFile,
    ModelFileKind,
    ModelNote,
    ModelTag,
    NoteKind,
    Tag,
)
from app.core.db.session import get_engine, get_session
from app.modules.share.models import (
    PaginatedShareFileList,
    ShareFileListEntry,
    ShareModelView,
)
from app.modules.share.service import ShareService

router = APIRouter(prefix="/api/share", tags=["share"])

# Initiative 6 Story 11.2 Decision N — share-asset endpoint surfaces only
# files of these kinds, mirroring the share-resolve handler's URL emission
# (image + print for thumbnails / image gallery; stl for download/viewer).
# `source` + `archive_3mf` are NEVER surfaced via share path (codex peer-grill
# 2026-05-20 finding: raw scope-check would over-grant same-model files).
# Initiative 12 Story 19.6 (Decision S) added `stl_preview` — auto-generated
# iso/front/side/top renders rendered lazily on share access.
_SHARE_ALLOWED_KINDS: frozenset[ModelFileKind] = frozenset(
    {
        ModelFileKind.image,
        ModelFileKind.print,
        ModelFileKind.stl,
        ModelFileKind.stl_preview,
    }
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

    # Initiative 12 Story 19.6 (Decision S) — lazy STL preview render dispatch.
    # Trigger on every resolve_share hit (not just list_share_files) because
    # the SPA's anonymous viewer currently only calls fetchShareView(); the
    # file-list endpoint is consumed in a follow-up FE story. Worker
    # idempotency guards (require complete 4-view set) absorb repeat
    # dispatches.
    #
    # Story 23.2 (TB-034 / Decision X.2) — fetch the primary STL's sha256
    # alongside its id so we can scope both the dispatch-side idempotency
    # count AND the share-list query to the CURRENT geometry (filter by
    # ``original_name LIKE "%-<sha8>.png"``). Without source-tracking,
    # post-STL-replace would either skip render (orphan rows count toward
    # the 4-view gate) or surface stale previews to share recipients.
    stl_for_preview_row = session.exec(
        select(ModelFile.id, ModelFile.sha256)
        .where(
            ModelFile.model_id == record.model_id,
            ModelFile.kind == ModelFileKind.stl,
        )
        .order_by(ModelFile.created_at.asc())
    ).first()
    stl_for_preview: uuid.UUID | None = None
    stl_sha8: str | None = None
    if stl_for_preview_row is not None:
        stl_for_preview, stl_sha256 = stl_for_preview_row
        stl_sha8 = stl_sha256[:8] if stl_sha256 else None
    if stl_for_preview is not None and stl_sha8 is not None:
        existing_preview_count = session.exec(
            select(func.count())
            .select_from(ModelFile)
            .where(
                ModelFile.model_id == record.model_id,
                ModelFile.kind == ModelFileKind.stl_preview,
                ModelFile.original_name.like(f"%-{stl_sha8}.png"),
            )
        ).one()
        if existing_preview_count < 4:
            # Story 23.2 (TB-034 P2#2) — single-flight Redis SETNX lock
            # prevents concurrent share-view requests from enqueueing
            # duplicate render jobs for the same STL. Lock TTL 300s covers
            # worst-case render wall time + safety margin; worker releases
            # the lock in its ``finally`` block on done/skipped/failed
            # paths. The lock is dispatch-coordination only — visible
            # run-state stays in ``render:stl_preview:<model_file_id>``.
            redis_client = request.app.state.redis.get()
            lock_key = f"share:stl_preview_lock:{stl_for_preview}"
            acquired = await redis_client.set(lock_key, b"1", nx=True, ex=300)
            if acquired:
                try:
                    await request.app.state.arq.enqueue_job(
                        "render_stl_previews", str(stl_for_preview)
                    )
                except Exception:
                    # If enqueue fails AFTER lock acquired, release it
                    # immediately so the next request can retry without
                    # waiting the full 300s TTL.
                    with contextlib.suppress(Exception):
                        await redis_client.delete(lock_key)
                    import logging

                    logging.getLogger("app.share").warning(
                        "stl_preview enqueue failed in resolve_share", exc_info=True
                    )
            # else: another dispatch is in flight for this STL; skip silently.

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
    # Initiative 12 Story 19.6 — STL preview renders (iso/front/side/top)
    # surfaced alongside admin gallery photos. Stored as ModelFile rows with
    # kind=stl_preview, position 0-3, generated lazily by the render-worker
    # task dispatched above. Appended AFTER admin images so admin curation
    # comes first in the carousel.
    #
    # Story 23.2 (TB-034 P2#1 / Decision X.2) — filter to the CURRENT
    # STL's previews by sha8 suffix on ``original_name``. Stale orphan
    # previews (from a prior STL geometry, or pre-Story-23.2 legacy rows
    # named ``iso.png`` without sha8 stamping) do NOT surface in the
    # share carousel. If the model has no primary STL, ``stl_sha8`` is
    # None and ``preview_files`` is empty.
    if stl_sha8 is not None:
        preview_files = session.exec(
            select(ModelFile.id)
            .where(ModelFile.model_id == model.id)
            .where(ModelFile.kind == ModelFileKind.stl_preview)
            .where(ModelFile.original_name.like(f"%-{stl_sha8}.png"))
            .order_by(ModelFile.position.asc(), ModelFile.created_at.asc())
        ).all()
    else:
        preview_files = []
    # Initiative 6 Decision N — emit share-scoped URLs (`/api/share/{token}/...`)
    # instead of legacy `/api/models/{id}/...` URLs. The legacy SoT content
    # endpoint is post-Story-11.1 `current_user`-gated; anonymous share
    # recipients reach assets exclusively via the share path.
    images = [f"/api/share/{token}/files/{fid}/content" for fid in image_files]
    images.extend(f"/api/share/{token}/files/{fid}/content" for fid in preview_files)

    thumbnail_url = None
    if model.thumbnail_file_id is not None:
        thumbnail_url = f"/api/share/{token}/files/{model.thumbnail_file_id}/content"
    elif images:
        thumbnail_url = images[0]

    stl_row = session.exec(
        select(ModelFile.id, ModelFile.size_bytes)
        .where(ModelFile.model_id == model.id)
        .where(ModelFile.kind == ModelFileKind.stl)
        .order_by(ModelFile.created_at.asc())
    ).first()
    stl_url = (
        f"/api/share/{token}/files/{stl_row[0]}/content?download=1" if stl_row is not None else None
    )
    stl_size_bytes = stl_row[1] if stl_row is not None else None

    # Initiative 10 Story 16.3 — anonymous viewer surfaces the description.
    # Pull from ModelNote with kind=description; prefer the bilingual fields
    # introduced in Story 16.1 (body_pl + body_en) with legacy `body` as
    # fallback. The anonymous-viewer DescriptionPanel does the same locale-
    # aware fallback chain frontend-side; passing both fields lets the client
    # pick without a second round-trip.
    desc_note = session.exec(
        select(ModelNote)
        .where(ModelNote.model_id == model.id)
        .where(ModelNote.kind == NoteKind.description)
        .order_by(ModelNote.updated_at.desc())
    ).first()
    notes_en = ""
    notes_pl = ""
    if desc_note is not None:
        notes_en = desc_note.body_en or desc_note.body or ""
        notes_pl = desc_note.body_pl or ""

    return ShareModelView(
        id=model.id,
        name_en=model.name_en,
        name_pl=model.name_pl,
        category=category.slug,
        tags=tags,
        thumbnail_url=thumbnail_url,
        has_3d=stl_row is not None,
        images=images,
        notes_en=notes_en,
        notes_pl=notes_pl,
        stl_url=stl_url,
        stl_size_bytes=stl_size_bytes,
    )


@router.get(
    "/{token}/files",
    summary="List share-scoped model files (anonymous, paginated)",
    description=(
        "Initiative 12 Story 19.4 / Decision T — anonymous share-scoped "
        "file list endpoint. Returns paginated list of files attached to "
        "the share-bound model with share-scoped content URLs (Init 6 "
        "Decision N pattern). Only kinds in {image, print, stl} surfaced; "
        "source + archive_3mf remain hidden from anonymous recipients. "
        "Subject to the Decision Q request-rate cap (60 req/min per "
        "(token, IP)) handled by RateLimitMiddleware. Returns 404 on "
        "token miss / expired / revoked / model soft-deleted (uniform — "
        "no enumeration oracle, mirroring get_share_asset)."
    ),
    response_model=PaginatedShareFileList,
)
async def list_share_files(
    token: str,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedShareFileList:
    """List files belonging to the share-bound model.

    No auth dependency: the share token IS the auth (Decision M
    `/api/share/*` carve-out). Admin / member roles NOT consulted.

    Uniform 404 on any failure mode (invalid token, expired token,
    soft-deleted model) — same enumeration-oracle defense as
    get_share_asset.
    """
    service = ShareService(redis=request.app.state.redis.get())
    record = await service.resolve(token)
    if record is None:
        raise HTTPException(404, "Share token not found or expired")

    model = session.exec(
        select(Model).where(Model.id == record.model_id, Model.deleted_at.is_(None))
    ).first()
    if model is None:
        raise HTTPException(404, "Share token not found or expired")

    # Initiative 12 Story 19.6 dispatch moved to resolve_share (the SPA's
    # anonymous viewer calls fetchShareView only; list_share_files is a
    # secondary surface). Worker idempotency uses complete 4-view set check
    # so partial renders or post-STL-replace re-uploads retry.

    offset = (page - 1) * page_size
    base_filter = (
        ModelFile.model_id == record.model_id,
        ModelFile.kind.in_(_SHARE_ALLOWED_KINDS),
    )
    total = session.exec(select(func.count()).select_from(ModelFile).where(*base_filter)).one()

    items_rows = session.exec(
        select(ModelFile)
        .where(*base_filter)
        .order_by(nullslast(ModelFile.position.asc()), ModelFile.created_at.asc())
        .offset(offset)
        .limit(page_size)
    ).all()

    items = [
        ShareFileListEntry(
            id=str(f.id),
            kind=f.kind,
            original_name=f.original_name,
            mime_type=f.mime_type,
            size_bytes=f.size_bytes,
            position=f.position,
            content_url=f"/api/share/{token}/files/{f.id}/content",
            created_at=f.created_at,
        )
        for f in items_rows
    ]

    return PaginatedShareFileList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
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

    # Step 5: serve with `Cache-Control: no-store`. Starlette's FileResponse
    # auto-populates ETag + Last-Modified validators (in __call__ if no
    # stat_result is passed, or in __init__ if it is).
    #
    # Codex review iteration log (2026-05-20):
    #   - Round 1: flagged validator emission as P2-2 ("violates no-ETag
    #     contract"). Initial fix attempted `del response.headers[...]` at
    #     construction time — no-op because validators don't exist yet.
    #   - Round 2: passed `stat_result=candidate.stat()` to force
    #     set_stat_headers in __init__ so the deletion takes effect.
    #   - Round 3: stripping validators broke Range + If-Range path —
    #     Starlette's `_should_use_range()` reads `headers["last-modified"]`
    #     and `headers["etag"]` unconditionally, raising KeyError → 500 on
    #     legitimate partial-download requests.
    #
    # Resolution: KEEP the validators. The Decision N security property
    # ("revoked tokens cannot bypass scope check via conditional-request
    # short-circuit") is preserved by handler ordering — scope check runs
    # BEFORE FileResponse construction, so every conditional request
    # (If-None-Match, If-Modified-Since, If-Range, Range) goes through the
    # token resolve + scope check pipeline FIRST. Validators present on a
    # `Cache-Control: no-store` response are functionally dead weight
    # (caches MUST NOT store the body so revalidation never originates from
    # cached state) but they are NOT a security hole. The "no validators"
    # variant of Decision N has been retired as overly aggressive.
    return FileResponse(
        candidate,
        media_type=file_row.mime_type,
        filename=file_row.original_name if download else None,
        headers={"Cache-Control": "no-store"},
    )
