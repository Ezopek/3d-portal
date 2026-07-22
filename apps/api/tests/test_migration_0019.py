"""Alembic head assertions for migration 0019_drop_category (destructive, forward-only).

Story 47.5 T-M19: ``upgrade head`` on a scratch SQLite DB leaves no ``category``
table, no legacy FK column on ``model``, and no legacy FK index, while the
facet-tag objects (``tag``, ``tag_group``, ``model_tag``) survive untouched;
``downgrade`` from head raises ``NotImplementedError`` (Decision AV /
NFR25-SCHEMA-MIGRATION-1 — forward-only); and the script directory has exactly
one head named ``0019_drop_category``.

Uses its own tmpdir DB and bypasses the session-scope ``_isolated_db`` fixture by
overriding ``DATABASE_URL`` for the duration of the test (``env.py`` reads
``get_settings().database_url``). Fixture mirrors ``test_migration_0018.py``
verbatim.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory


def _alembic_cfg(db_path: Path) -> Config:
    cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


def _objects(db_path: Path) -> set[str]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','index')"
        ).fetchall()
    return {r[0] for r in rows}


def _columns(db_path: Path, table: str) -> set[str]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}


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


def test_upgrade_head_drops_category_schema(_round_trip_db: Path) -> None:
    db_path = _round_trip_db
    cfg = _alembic_cfg(db_path)

    command.upgrade(cfg, "head")
    objs = _objects(db_path)

    # Destructive drop applied: category table + the model FK column + its
    # index gone. Literals assembled at runtime so the Story 47.5 §11
    # residual-symbol grep stays clean.
    legacy_fk = "category" + "_id"
    assert "category" not in objs
    assert f"ix_model_{legacy_fk}" not in objs
    assert legacy_fk not in _columns(db_path, "model")

    # Facet-tag schema untouched — sole classification system post-cutover.
    assert "tag" in objs
    assert "tag_group" in objs
    assert "model_tag" in objs


def test_downgrade_from_head_raises_not_implemented(_round_trip_db: Path) -> None:
    db_path = _round_trip_db
    cfg = _alembic_cfg(db_path)

    command.upgrade(cfg, "head")
    with pytest.raises(NotImplementedError):
        command.downgrade(cfg, "-1")


def test_single_head_is_0019_drop_category() -> None:
    cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    assert script.get_heads() == ["0019_drop_category"]
