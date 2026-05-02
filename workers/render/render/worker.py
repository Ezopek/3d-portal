import json
from pathlib import Path
from typing import Any, ClassVar

import sentry_sdk
from arq.connections import RedisSettings

from render.config import get_settings
from render.observability import init_observability
from render.sentry import init_sentry
from render.trimesh_render import render_views

_STATUS_KEY = "render:status:"
_STATUS_TTL_SECONDS = 60 * 60


async def render_model(ctx: dict[str, Any], model_id: str) -> dict[str, str]:
    redis = ctx["redis"]
    catalog_dir = Path(ctx["catalog_dir"])
    renders_dir = Path(ctx["renders_dir"])
    size = int(ctx.get("image_size", 768))

    await redis.set(_STATUS_KEY + model_id, b"running", ex=_STATUS_TTL_SECONDS)
    try:
        index = json.loads((catalog_dir / "_index" / "index.json").read_text())
        match = next((m for m in index if m["id"] == model_id), None)
        if match is None:
            await redis.set(_STATUS_KEY + model_id, b"failed", ex=_STATUS_TTL_SECONDS)
            return {"status": "failed", "reason": f"Unknown model {model_id}"}

        model_dir = catalog_dir / match["path"]
        stls = sorted(p for p in model_dir.rglob("*") if p.is_file() and p.suffix.lower() == ".stl")
        if not stls:
            await redis.set(_STATUS_KEY + model_id, b"failed", ex=_STATUS_TTL_SECONDS)
            return {"status": "failed", "reason": "no STL files in model directory"}

        out_dir = renders_dir / model_id
        render_views(stl_path=stls[0], output_dir=out_dir, size=size)
        await redis.set(_STATUS_KEY + model_id, b"done", ex=_STATUS_TTL_SECONDS)
        return {"status": "done", "model_id": model_id}
    except Exception as exc:  # Worker boundary: any failure becomes status=failed
        sentry_sdk.capture_exception(exc)
        await redis.set(_STATUS_KEY + model_id, b"failed", ex=_STATUS_TTL_SECONDS)
        return {"status": "failed", "reason": str(exc)}


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
    ctx["catalog_dir"] = settings.catalog_data_dir
    ctx["renders_dir"] = settings.renders_dir
    ctx["image_size"] = settings.image_size


async def shutdown(ctx: dict[str, Any]) -> None:
    pass


class WorkerSettings:
    functions: ClassVar[list] = [render_model]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
