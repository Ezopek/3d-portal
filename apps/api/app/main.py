from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI

from app.core.config import get_settings
from app.core.db.seed import seed_admin
from app.core.db.session import get_engine, init_schema
from app.core.redis import RedisFactory
from app.modules.catalog.service import CatalogService
from app.router import api_router


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
    app.state.catalog_service = CatalogService(
        catalog_dir=settings.catalog_data_dir,
        index_path=settings.catalog_data_dir / "_index" / "index.json",
    )
    app.state.redis = RedisFactory(url=settings.redis_url)
    app.state.arq = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    yield
    await app.state.arq.aclose()
    await app.state.redis.aclose()


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

    app.include_router(api_router)

    return app


app = create_app()
