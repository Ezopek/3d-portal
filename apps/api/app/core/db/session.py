from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import event, func
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

# `Tag` is imported for `unicode_lower`'s `session.get_bind(Tag)` below: the
# helper needs the mapper its predicate targets. The leaf `_entities` path is
# NOT a layering boundary -- importing it still executes the models package
# `__init__`, which imports `app.modules.invite.models`, and `app.core.config`
# above already pulled that identical chain at baseline. No coupling is added.
from app.core.db.models._entities import Tag

# Initiative 26 (Story 49.4, FR26-SEARCH-1). SQLite's built-in lower() folds
# ASCII only, so a tag stored as "Łazienka" (shipped in seed.py's starter
# taxonomy) never matches a LIKE pattern folded by Python's full-Unicode
# str.lower() — not even in its own casing. Register str.lower under an explicit
# name instead of overriding lower(), so only the queries that opt in change
# semantics.
UNICODE_LOWER_SQLITE_FN = "portal_lower"


def _unicode_lower(value: str | None) -> str | None:
    return value.lower() if value is not None else None


def unicode_lower(session: Session) -> Any:
    """Return the SQL function to use for FULL-UNICODE case-folding on `session`.

    SQLite needs the `portal_lower` shim registered below. PostgreSQL — the
    documented migration target — already folds non-ASCII in its built-in
    `lower()` under any non-C collation, so it keeps `lower()` and gains no
    dependency on a connection-level function.

    The bind is resolved through `Tag`, the mapper this predicate targets, not
    through an argument-less `get_bind()`: the latter raises
    `UnboundExecutionError` on a `Session(binds={...})` bound per mapper, a
    shape that ran `list_models(q=...)` fine before this helper existed because
    bind resolution then happened per statement. Pinned by
    `tests/test_sot_models_tag_search.py::
    test_per_mapper_bound_session_still_folds_tag_names`.
    """
    if session.get_bind(Tag).dialect.name == "sqlite":
        return getattr(func, UNICODE_LOWER_SQLITE_FN)
    return func.lower


def create_engine_for_url(url: str) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, echo=False)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _enable_sqlite_pragmas(dbapi_conn, _connection_record):  # type: ignore[no-untyped-def]
            dbapi_conn.execute("PRAGMA foreign_keys = ON")
            # WAL allows concurrent api + worker writers. Set per-connection
            # because pysqlite resets pragmas on new connections.
            dbapi_conn.execute("PRAGMA journal_mode = WAL")
            # 5 s busy timeout — if the other writer holds the lock, wait
            # rather than fail immediately. Render writes are short-lived
            # (4 INSERTs + maybe an UPDATE) so 5 s is generous.
            dbapi_conn.execute("PRAGMA busy_timeout = 5000")
            # Full-Unicode case-folding for the queries that ask for it by name
            # (see UNICODE_LOWER_SQLITE_FN above). Registered per-connection
            # because sqlite3 functions live on the connection, not the file.
            #
            # DEPENDENCY, deliberate and narrow: the listener is bound to THIS
            # engine, so `portal_lower` exists only on engines built here. A
            # Session bound to a bare `create_engine(...)` raises
            # `OperationalError: no such function: portal_lower` out of
            # `list_models(q=...)`'s tag disjunct rather than degrading to an
            # ASCII-only match. Latent today: `list_models` has exactly one
            # caller (`app/modules/sot/router.py`) and every shipped engine path
            # -- `get_engine()`, `apps/api/scripts/*`, the render worker -- goes
            # through this factory; the in-tree raw-`create_engine` sites are
            # schema/entity tests that never call it. Pinned by
            # `tests/test_sot_models_tag_search.py::
            # test_factory_built_engine_resolves_the_unicode_lower_shim` and
            # recorded in `_bmad-output/implementation-artifacts/deferred-work.md`
            # -- moving the registration to the class-level `Engine` "connect"
            # event is the durable fix, and belongs with whatever story first
            # needs `list_models` on a non-factory engine.
            dbapi_conn.create_function(
                UNICODE_LOWER_SQLITE_FN, 1, _unicode_lower, deterministic=True
            )

    return engine


def init_schema(engine: Engine) -> None:
    # Ensure SQLite parent dir exists for file-backed DBs.
    if engine.url.drivername.startswith("sqlite") and engine.url.database:
        db_path = Path(engine.url.database)
        # Path(":memory:").parent == Path("."), so this guard correctly skips
        # mkdir for both in-memory and current-directory SQLite URLs.
        if db_path.parent != Path("."):
            db_path.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine_for_url(get_settings().database_url)


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
