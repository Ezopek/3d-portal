from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup hooks (db, redis, otel) wired in later phases.
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": settings.app_version}

    return app


app = create_app()
