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
    functions: ClassVar[list] = [render_model]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    job_timeout = 5 * 60
    max_jobs = 2  # trimesh + matplotlib are heavy; 2 concurrent is plenty
