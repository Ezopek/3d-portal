from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI

from app.core.auth.csrf import install_csrf_middleware
from app.core.auth.middleware import LastActiveMiddleware
from app.core.auth.ratelimit import (
    RateLimitMiddleware,
    login_ratelimit_key,
    refresh_ratelimit_key,
    register_ratelimit_key,
    share_ratelimit_key,
    share_retry_after_seconds,
)
from app.core.config import get_settings
from app.core.db.models._enums import UserRole
from app.core.db.seed import seed_admin
from app.core.db.session import get_engine, init_schema
from app.core.logging import configure_logging
from app.core.observability import init_observability, instrument_app
from app.core.redis import RedisFactory
from app.core.sentry import init_sentry
from app.modules.runbook.router import router as runbook_router
from app.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if UserRole.agent in settings.enforce_2fa_for_roles:
        raise RuntimeError(
            "agent role MUST NEVER appear in enforce_2fa_for_roles "
            "(it is a service account; forcing 2FA would brick AI ingestion). "
            "Edit apps/api/app/core/config.py or infra/.env to remove it."
        )
    configure_logging(
        service_name=settings.app_name,
        service_version=settings.app_version,
        environment=settings.environment,
    )
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
    app.state.redis = RedisFactory(url=settings.redis_url)
    app.state.arq = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    yield
    await app.state.arq.aclose()
    await app.state.redis.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    # Init Sentry first so it can capture any errors raised during OTel setup.
    init_sentry(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=settings.portal_version,
    )
    init_observability(
        service_name=settings.app_name,
        service_version=settings.app_version,
        environment=settings.environment,
        otlp_endpoint=settings.otel_exporter_otlp_endpoint,
    )
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    instrument_app(app)
    # Story 6.6: rate-limit middleware (Decision G). Behavioral order required:
    # incoming request → CSRF check → rate-limit (one of three) → route handler.
    # Starlette wraps middleware LIFO: the LAST add_middleware call is the
    # OUTERMOST layer. So the install order in code is the INVERSE of the
    # execution order — rate-limit is added FIRST, then CSRF last, so CSRF
    # wraps outermost and a 403 csrf_required does NOT burn rate-limit budget.
    # The trio's relative order is irrelevant because their key_fn callables
    # are mutually exclusive on path.
    app.add_middleware(
        RateLimitMiddleware,
        scope="login",
        key_fn=login_ratelimit_key,
        window_seconds=settings.ratelimit_login_window_seconds,
        threshold=settings.ratelimit_login_threshold,
    )
    app.add_middleware(
        RateLimitMiddleware,
        scope="refresh",
        key_fn=refresh_ratelimit_key,
        window_seconds=settings.ratelimit_refresh_window_seconds,
        threshold=settings.ratelimit_refresh_threshold,
    )
    app.add_middleware(
        RateLimitMiddleware,
        scope="register",
        key_fn=register_ratelimit_key,
        window_seconds=settings.ratelimit_register_window_seconds,
        threshold=settings.ratelimit_register_threshold,
    )
    # Story 6.7: per-member share-token cap (Decision H). Reuses the Story 6.6
    # middleware class with two new optional params for soft-alert + dynamic
    # Retry-After. Admin exemption + JWT-cookie role check live inside
    # share_ratelimit_key (returns None for admin / anon / non-member roles,
    # short-circuiting the Redis pipeline). Scope: POST /api/admin/share only;
    # DELETE + GET on the same prefix are method-filtered out by the key_fn.
    app.add_middleware(
        RateLimitMiddleware,
        scope="share",
        key_fn=share_ratelimit_key,
        window_seconds=settings.ratelimit_share_window_seconds,
        threshold=settings.ratelimit_share_threshold,
        soft_alert_threshold=settings.ratelimit_share_soft_alert_threshold,
        retry_after_seconds_fn=share_retry_after_seconds,
    )
    install_csrf_middleware(app)
    # Story 8.1 (Decision I): added AFTER CSRF + rate-limit trio per AC-3
    # step 6 verbatim. Under Starlette's LIFO wrapping this means LastActive
    # is the OUTERMOST layer — fine because the middleware is a passthrough
    # on missing/invalid cookie, agent role, and Redis-down, paying only one
    # cookie parse + JWT decode on the authenticated happy path.
    app.add_middleware(LastActiveMiddleware)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": settings.app_version}

    app.include_router(api_router)
    # Root-level discovery resource (NOT under /api/ — it is conceptually
    # the bootstrap URL for fresh-session AI agents, not part of the
    # REST API surface). Public read; no auth.
    app.include_router(runbook_router)

    return app


app = create_app()
