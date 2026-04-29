from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.db.seed import seed_admin
from app.core.db.session import get_engine, init_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine = get_engine()
    # Production schema is owned by alembic (deploy script runs `alembic upgrade head`
    # before the container starts). In dev/test we let SQLModel create the schema
    # so contributors and the pytest suite can run without invoking alembic.
    if settings.environment != "production":
        init_schema(engine)
    seed_admin(
        engine,
        email=settings.admin_email,
        password=settings.admin_password,
        display_name="Admin",
    )
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
