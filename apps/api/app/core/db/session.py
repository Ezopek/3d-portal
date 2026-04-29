from collections.abc import Iterator
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings


def create_engine_for_url(url: str) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, echo=False)


def init_schema(engine: Engine) -> None:
    # Ensure SQLite parent dir exists for file-backed DBs.
    if engine.url.drivername.startswith("sqlite") and engine.url.database:
        db_path = Path(engine.url.database)
        if db_path.parent != Path("."):
            db_path.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)


_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine_for_url(get_settings().database_url)
    return _engine


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
