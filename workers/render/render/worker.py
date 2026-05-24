import hashlib
import json
import logging
import shutil
import tempfile
import uuid as uuidmod
from pathlib import Path
from typing import Any, ClassVar

import sentry_sdk
from app.core.db.models import AuditLog, Model, ModelFile, ModelFileKind
from app.core.db.session import create_engine_for_url
from arq.connections import RedisSettings
from sqlalchemy import func
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from render.config import get_settings
from render.observability import init_observability
from render.sentry import init_sentry
from render.trimesh_render import VIEW_NAMES, render_views

_STATUS_KEY = "render:status:"
_STATUS_TTL_SECONDS = 60 * 60

# Names matching the on-disk-renderer output. Auto-render rows use these
# original_names so they can be cleaned up without touching human-uploaded
# photos, which always have arbitrary names.
AUTO_RENDER_NAMES: tuple[str, ...] = tuple(f"{view}-render.png" for view in VIEW_NAMES)

logger = logging.getLogger(__name__)


async def render_model(
    ctx: dict[str, Any],
    model_id: str,
    *,
    selected_stl_file_ids: list[str] | None = None,
) -> dict[str, str]:
    """Render 4 ISO/front/side/top PNGs for the given model and write them as
    ModelFile rows under portal-content."""
    redis = ctx["redis"]
    engine: Engine = ctx["engine"]
    content_dir = Path(ctx["content_dir"])
    size = int(ctx.get("image_size", 768))

    await redis.set(_STATUS_KEY + model_id, b"running", ex=_STATUS_TTL_SECONDS)
    try:
        model_uuid = uuidmod.UUID(model_id)
        with Session(engine) as session:
            model = session.exec(select(Model).where(Model.id == model_uuid)).first()
            if model is None:
                await redis.set(_STATUS_KEY + model_id, b"failed", ex=_STATUS_TTL_SECONDS)
                return {"status": "failed", "reason": f"unknown model {model_id}"}

            stl_rows = list(
                session.exec(
                    select(ModelFile)
                    .where(ModelFile.model_id == model_uuid)
                    .where(ModelFile.kind == ModelFileKind.stl)
                    .order_by(ModelFile.position.asc().nulls_last(), ModelFile.created_at.asc())
                ).all()
            )
            if not stl_rows:
                await redis.set(_STATUS_KEY + model_id, b"failed", ex=_STATUS_TTL_SECONDS)
                return {"status": "failed", "reason": "no STL files"}

            chosen_rows: list[ModelFile]
            if selected_stl_file_ids:
                wanted = {uuidmod.UUID(s) for s in selected_stl_file_ids}
                chosen_rows = [r for r in stl_rows if r.id in wanted]
                if not chosen_rows:
                    chosen_rows = [stl_rows[0]]
            else:
                # Use admin-persisted selection. Fall back to the first STL
                # when no row is flagged so a model never produces zero
                # renders just because the flag was cleared everywhere.
                chosen_rows = [r for r in stl_rows if r.selected_for_render]
                if not chosen_rows:
                    chosen_rows = [stl_rows[0]]

            stl_paths_on_disk = [content_dir / r.storage_path for r in chosen_rows]
            for path in stl_paths_on_disk:
                if not path.is_file():
                    await redis.set(_STATUS_KEY + model_id, b"failed", ex=_STATUS_TTL_SECONDS)
                    return {"status": "failed", "reason": f"STL missing on disk: {path}"}

        # Render to a temp dir, then move each PNG into portal-content.
        with tempfile.TemporaryDirectory(prefix="portal-render-") as tmp:
            tmp_dir = Path(tmp)
            render_views(stl_paths=stl_paths_on_disk, output_dir=tmp_dir, size=size)

            new_file_ids: dict[str, uuidmod.UUID] = {}
            with Session(engine) as session:
                # 1. Delete prior auto-render rows for this model + their files.
                old_rows = list(
                    session.exec(
                        select(ModelFile)
                        .where(ModelFile.model_id == model_uuid)
                        .where(ModelFile.kind == ModelFileKind.image)
                        .where(ModelFile.original_name.in_(AUTO_RENDER_NAMES))
                    ).all()
                )
                old_thumb_was_auto = False
                model = session.exec(select(Model).where(Model.id == model_uuid)).one()
                for old in old_rows:
                    if model.thumbnail_file_id == old.id:
                        old_thumb_was_auto = True
                        model.thumbnail_file_id = None
                        session.add(model)
                    session.delete(old)
                # Flush so old rows are gone before we insert new ones with same
                # original_name (no unique constraint today, but safer order).
                session.flush()

                # 2. Insert 4 new ModelFile rows + copy bytes.
                iso_id: uuidmod.UUID | None = None
                for view in VIEW_NAMES:
                    src = tmp_dir / f"{view}.png"
                    if not src.is_file():
                        continue
                    file_uuid = uuidmod.uuid4()
                    storage_rel = f"models/{model.id}/files/{file_uuid}.png"
                    dst = content_dir / storage_rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, dst)
                    sha256, size_bytes = _sha256_of(dst)
                    new_file = ModelFile(
                        id=file_uuid,
                        model_id=model.id,
                        kind=ModelFileKind.image,
                        original_name=f"{view}-render.png",
                        storage_path=storage_rel,
                        sha256=sha256,
                        size_bytes=size_bytes,
                        mime_type="image/png",
                        position=None,
                    )
                    session.add(new_file)
                    new_file_ids[view] = file_uuid
                    if view == "iso":
                        iso_id = file_uuid

                session.flush()

                # 3. Set thumbnail to iso if model has none (or had an auto-render
                #    which we just deleted).
                if (model.thumbnail_file_id is None or old_thumb_was_auto) and iso_id is not None:
                    model.thumbnail_file_id = iso_id
                    session.add(model)

                # 4. Audit
                session.add(
                    AuditLog(
                        actor_user_id=None,
                        action="model.render.complete",
                        entity_type="model",
                        entity_id=model.id,
                        before_json=json.dumps(
                            {
                                "deleted_auto_renders": [str(o.id) for o in old_rows],
                            }
                        ),
                        after_json=json.dumps(
                            {
                                "new_file_ids": {k: str(v) for k, v in new_file_ids.items()},
                                "thumbnail_file_id": (
                                    str(model.thumbnail_file_id)
                                    if model.thumbnail_file_id is not None
                                    else None
                                ),
                            }
                        ),
                    )
                )
                session.commit()

                # 5. Best-effort clean up old PNGs from disk.
                for old in old_rows:
                    target = content_dir / old.storage_path
                    try:
                        target.unlink(missing_ok=True)
                    except OSError as exc:
                        logger.warning("failed to delete old render %s: %s", target, exc)

        await redis.set(_STATUS_KEY + model_id, b"done", ex=_STATUS_TTL_SECONDS)
        return {"status": "done", "model_id": model_id, "rendered_views": list(new_file_ids.keys())}
    except Exception as exc:  # Worker boundary
        sentry_sdk.capture_exception(exc)
        await redis.set(_STATUS_KEY + model_id, b"failed", ex=_STATUS_TTL_SECONDS)
        logger.exception("render_model failed")
        return {"status": "failed", "reason": str(exc)}


async def render_stl_previews(
    ctx: dict[str, Any],
    model_file_id: str,
) -> dict[str, str]:
    """Render 4 STL preview views (iso/front/side/top) for one STL file row.

    Initiative 12 Story 19.6 (Decision S). Dispatched lazily on first
    anonymous share access to /api/share/{token}/files when the share-bound
    model has STL files but no ``stl_preview`` kind rows for those STLs.

    Idempotent: if any ``stl_preview`` row already exists for this
    ``model_file_id``, skip render + return ``{"status": "skipped"}``. The
    share file-list endpoint may dispatch the job on every cold-cache hit;
    the idempotency guard absorbs that.

    Distinct from ``render_model`` task:
    - Targets ONE STL file (single mesh) not "all STLs packed together".
    - Stores under ``kind=stl_preview`` not ``kind=image``.
    - Storage path ``models/<id>/stl_previews/`` (separate subdirectory).
    - Does NOT touch ``Model.thumbnail_file_id`` (admin-managed; previews are
      a parallel surface).
    """
    redis = ctx["redis"]
    engine: Engine = ctx["engine"]
    content_dir = Path(ctx["content_dir"])
    size = int(ctx.get("image_size", 768))
    status_key = f"render:stl_preview:{model_file_id}"

    try:
        file_uuid = uuidmod.UUID(model_file_id)
        await redis.set(status_key, b"running", ex=_STATUS_TTL_SECONDS)

        with Session(engine) as session:
            stl_row = session.exec(
                select(ModelFile).where(
                    ModelFile.id == file_uuid,
                    ModelFile.kind == ModelFileKind.stl,
                )
            ).first()
            if stl_row is None:
                await redis.set(status_key, b"failed", ex=_STATUS_TTL_SECONDS)
                return {"status": "failed", "reason": f"STL file {model_file_id} not found"}

            # Idempotency guard — require the COMPLETE 4-view set (one per
            # VIEW_NAMES entry) before skipping. Partial renders (1-3 rows
            # committed before crash) AND post-STL-replace re-uploads must
            # retry rather than treat any single existing row as "done".
            # Codex Story 19.6 round-2 P2 fix.
            #
            # Story 23.2 (TB-034 P2#1) — source-tracking by STL sha8 suffix
            # in ``original_name``. Counts ONLY previews from the CURRENT
            # STL geometry; orphan previews from a prior STL (delete +
            # reupload, or upload-new + curation swap) do NOT count toward
            # the 4-view completion gate, so the new STL renders fresh.
            stl_sha8 = stl_row.sha256[:8]
            existing_count = session.exec(
                select(func.count())
                .select_from(ModelFile)
                .where(
                    ModelFile.model_id == stl_row.model_id,
                    ModelFile.kind == ModelFileKind.stl_preview,
                    ModelFile.original_name.like(f"%-{stl_sha8}.png"),
                )
            ).one()
            if existing_count >= len(VIEW_NAMES):
                await redis.set(status_key, b"done", ex=_STATUS_TTL_SECONDS)
                return {"status": "skipped", "reason": "previews already exist"}

            stl_path = content_dir / stl_row.storage_path
            if not stl_path.is_file():
                await redis.set(status_key, b"failed", ex=_STATUS_TTL_SECONDS)
                return {"status": "failed", "reason": f"STL missing on disk: {stl_path}"}
            model_id = stl_row.model_id

        with tempfile.TemporaryDirectory(prefix="portal-stl-preview-") as tmp:
            tmp_dir = Path(tmp)
            render_views(stl_paths=[stl_path], output_dir=tmp_dir, size=size)

            new_file_ids: dict[str, str] = {}
            with Session(engine) as session:
                for position, view in enumerate(VIEW_NAMES):
                    src = tmp_dir / f"{view}.png"
                    if not src.is_file():
                        continue
                    new_uuid = uuidmod.uuid4()
                    storage_rel = f"models/{model_id}/stl_previews/{new_uuid}.png"
                    dst = content_dir / storage_rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, dst)
                    sha256, size_bytes = _sha256_of(dst)
                    new_file = ModelFile(
                        id=new_uuid,
                        model_id=model_id,
                        kind=ModelFileKind.stl_preview,
                        # Story 23.2 — sha8 suffix stamps the source-STL
                        # geometry into the row, paired with the LIKE filter
                        # in the idempotency query above and in the share
                        # router dispatch + list queries.
                        original_name=f"{view}-{stl_sha8}.png",
                        storage_path=storage_rel,
                        sha256=sha256,
                        size_bytes=size_bytes,
                        mime_type="image/png",
                        position=position,
                    )
                    session.add(new_file)
                    new_file_ids[view] = str(new_uuid)

                session.add(
                    AuditLog(
                        actor_user_id=None,
                        action="model.stl_preview.complete",
                        entity_type="model",
                        entity_id=model_id,
                        before_json=json.dumps({"source_stl_file_id": model_file_id}),
                        after_json=json.dumps({"new_file_ids": new_file_ids}),
                    )
                )
                session.commit()

        await redis.set(status_key, b"done", ex=_STATUS_TTL_SECONDS)
        return {
            "status": "done",
            "model_file_id": model_file_id,
            "rendered_views": list(new_file_ids.keys()),
        }
    except Exception as exc:  # Worker boundary
        sentry_sdk.capture_exception(exc)
        await redis.set(status_key, b"failed", ex=_STATUS_TTL_SECONDS)
        logger.exception("render_stl_previews failed")
        return {"status": "failed", "reason": str(exc)}
    finally:
        # Story 23.2 (TB-034 P2#2) — release the dispatch single-flight
        # lock acquired by the share router. The lock is a dispatch-side
        # coordination primitive distinct from ``status_key`` (which is
        # the visible run-state marker for observability). Released on
        # done / skipped / failed paths; if release fails the 300s TTL
        # is the safety net so the next share-view hit can re-dispatch
        # without waiting indefinitely.
        try:
            await redis.delete(f"share:stl_preview_lock:{model_file_id}")
        except Exception:
            logger.warning("stl_preview lock release failed", exc_info=True)


def _sha256_of(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(64 * 1024), b""):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


async def startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    init_observability(
        service_name=settings.service_name,
        service_version="0.1.0",
        environment="production",
        otlp_endpoint=settings.otel_exporter_otlp_endpoint,
    )
    init_sentry(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=settings.portal_version,
    )
    ctx["engine"] = create_engine_for_url(settings.database_url)
    ctx["content_dir"] = settings.content_dir
    ctx["image_size"] = settings.image_size


async def shutdown(ctx: dict[str, Any]) -> None:
    engine = ctx.get("engine")
    if engine is not None:
        engine.dispose()


class WorkerSettings:
    functions: ClassVar[list] = [render_model, render_stl_previews]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    job_timeout = 5 * 60
    max_jobs = 2  # trimesh + matplotlib are heavy; 2 concurrent is plenty
