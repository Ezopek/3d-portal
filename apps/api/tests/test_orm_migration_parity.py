"""ORM ↔ migration parity gate (Story 47.5 T-PAR; E41 retro parity action item).

``alembic upgrade head`` on a scratch SQLite DB must yield a schema for which
``alembic.autogenerate.compare_metadata`` against the live ``SQLModel.metadata``
reports an empty diff — proving the ORM entities (d5) and the migration chain
(d6) describe the same schema and cannot drift apart within a commit.

Fixture mirrors ``test_migration_0018.py`` / ``test_migration_0019.py``.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine
from sqlmodel import SQLModel

# Import side-effects: register every table on SQLModel.metadata (same pair of
# imports migrations/env.py performs).
from app.core.db import models  # noqa: F401
from app.modules.invite import models as _invite_models  # noqa: F401


def _alembic_cfg(db_path: Path) -> Config:
    cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


@pytest.fixture
def _round_trip_db(tmp_path: Path) -> Iterator[Path]:
    db_path = tmp_path / "rt.db"
    prior_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    from app.core.config import get_settings
    from app.core.db.session import get_engine

    get_settings.cache_clear()
    get_engine.cache_clear()
    try:
        yield db_path
    finally:
        if prior_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = prior_url
        get_settings.cache_clear()
        get_engine.cache_clear()


def test_migrated_schema_matches_orm_metadata(_round_trip_db: Path) -> None:
    db_path = _round_trip_db
    command.upgrade(_alembic_cfg(db_path), "head")

    engine = create_engine(f"sqlite:///{db_path}")
    try:
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            diff = compare_metadata(ctx, SQLModel.metadata)
    finally:
        engine.dispose()

    # ``alembic_version`` is migration bookkeeping, not ORM surface — it never
    # appears in SQLModel.metadata, and compare_metadata already ignores it via
    # the version-table exclusion. Any remaining entry is a real drift.
    assert diff == [], f"ORM metadata and migrated schema differ:\n{diff}"
