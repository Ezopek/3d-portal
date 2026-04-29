from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings


def create_engine_for_url(url: str) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, echo=False)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_conn, _connection_record):  # type: ignore[no-untyped-def]
            dbapi_conn.execute("PRAGMA foreign_keys = ON")

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
