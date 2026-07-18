"""Alembic round-trip for migration 0018_facet_tags (additive facet-tag schema).

AC #6/#7: ``upgrade head`` creates ``tag_group`` + ``uq_tag_group_slug`` index
and adds ``tag.group_id`` (nullable) / ``tag.group_position`` (NOT NULL, default
``"0"``); ``category`` + ``model.category_id`` survive (deferral guard, AC #4 —
proves the destructive drop was NOT performed); ``downgrade`` to 0017 removes
only the facet objects while ``tag`` + ``tag.slug`` + ``ix_tag_slug`` survive;
re-``upgrade`` restores the facet objects (idempotency).

Uses its own tmpdir DB and bypasses the session-scope ``_isolated_db`` fixture by
overriding ``DATABASE_URL`` for the duration of the test (``env.py`` reads
``get_settings().database_url`` and ignores the URL passed via the Alembic
``Config`` directly, so the env var is the only knob that works). Fixture mirrors
``test_migration_0012.py`` / ``test_migration_0014.py`` verbatim.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config


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


def _columns(db_path: Path, table: str) -> dict[str, tuple[str, int, str | None]]:
    """Return a dict of column-name → (type, notnull, dflt_value) for ``table``.

    PRAGMA columns order: cid, name, type, notnull, dflt_value, pk.
    """
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1]: (r[2], r[3], r[4]) for r in rows}


def _foreign_keys(db_path: Path, table: str) -> list[dict[str, str]]:
    """Return the outbound foreign keys of ``table`` as {table, from, to, on_delete}.

    PRAGMA foreign_key_list columns: id, seq, table, from, to, on_update,
    on_delete, match. SQLite does NOT expose the constraint *name* here, so FK
    identity is pinned by target table/column + ON DELETE action rather than by
    ``fk_tag_group_id`` (the name is only checkable via source / a future
    compare_metadata drift guard).
    """
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()
    return [{"table": r[2], "from": r[3], "to": r[4], "on_delete": r[6]} for r in rows]


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


def test_migration_0018_round_trip(_round_trip_db: Path) -> None:
    db_path = _round_trip_db
    cfg = _alembic_cfg(db_path)

    # Forward to head — creates tag_group + uq_tag_group_slug and the facet
    # columns on tag.
    command.upgrade(cfg, "head")
    objs = _objects(db_path)
    assert "tag_group" in objs
    assert "uq_tag_group_slug" in objs

    tag_cols = _columns(db_path, "tag")
    assert "group_id" in tag_cols
    assert "group_position" in tag_cols
    # group_id is nullable; group_position is NOT NULL with server_default "0".
    assert tag_cols["group_id"][1] == 0
    gp_type, gp_notnull, gp_default = tag_cols["group_position"]
    assert gp_notnull == 1
    # SQLite quotes the batch-reflected server_default ("'0'"); strip to compare
    # the underlying literal. The point is NOT NULL + default-zero, not quoting.
    assert gp_default.strip("'") == "0"

    # FK proof (AC #3): tag.group_id -> tag_group.id, ON DELETE SET NULL. The
    # SET-NULL semantics are what the E42 category cut-over will rely on, so pin
    # them executably rather than by source inspection alone.
    group_fks = [fk for fk in _foreign_keys(db_path, "tag") if fk["from"] == "group_id"]
    assert group_fks == [
        {"table": "tag_group", "from": "group_id", "to": "id", "on_delete": "SET NULL"}
    ]

    # Deferral guard (AC #4): the destructive category drop was NOT performed.
    assert "category" in objs
    assert "category_id" in _columns(db_path, "model")

    # Step down to 0017 — removes only the facet objects.
    command.downgrade(cfg, "0017_model_note_bilingual")
    objs = _objects(db_path)
    assert "tag_group" not in objs
    assert "uq_tag_group_slug" not in objs
    tag_cols = _columns(db_path, "tag")
    assert "group_id" not in tag_cols
    assert "group_position" not in tag_cols
    # tag itself and its slug index survive the downgrade.
    assert "tag" in objs
    assert "ix_tag_slug" in objs
    assert "slug" in tag_cols
    # The group_id FK is dropped with the column (batch table-copy) — absent now.
    assert all(fk["from"] != "group_id" for fk in _foreign_keys(db_path, "tag"))

    # Re-upgrade — idempotency check: all facet objects return.
    command.upgrade(cfg, "head")
    objs = _objects(db_path)
    assert "tag_group" in objs
    assert "uq_tag_group_slug" in objs
    tag_cols = _columns(db_path, "tag")
    assert "group_id" in tag_cols
    assert "group_position" in tag_cols
    assert tag_cols["group_position"] == (gp_type, gp_notnull, gp_default)
    # FK restored with the same SET-NULL semantics (idempotency).
    group_fks = [fk for fk in _foreign_keys(db_path, "tag") if fk["from"] == "group_id"]
    assert group_fks == [
        {"table": "tag_group", "from": "group_id", "to": "id", "on_delete": "SET NULL"}
    ]
