"""Alembic round-trip for migration 0012_invite_tokens.

AC-1: upgrade head → downgrade -1 → upgrade head with table+indexes intact.

Uses its own tmpdir DB and bypasses the session-scope ``_isolated_db`` fixture
by overriding ``DATABASE_URL`` for the duration of the test (``env.py`` reads
``get_settings().database_url`` and ignores the URL passed via the Alembic
``Config`` directly, so the env var is the only knob that works).
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


def test_migration_0012_round_trip(_round_trip_db: Path) -> None:
    db_path = _round_trip_db
    cfg = _alembic_cfg(db_path)

    # Forward to head — creates the invite_tokens table + indexes.
    command.upgrade(cfg, "head")
    objs = _objects(db_path)
    assert "invite_tokens" in objs
    assert "ux_invite_tokens_token_hash" in objs
    assert "ix_invite_tokens_generated_at" in objs
    assert "ix_invite_tokens_used_by_user_id" in objs

    # Verify column shape: all 10 columns present.
    with sqlite3.connect(db_path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(invite_tokens)")}
    assert cols == {
        "id",
        "token_hash",
        "role",
        "generated_by_user_id",
        "generated_at",
        "ttl_seconds",
        "used_by_user_id",
        "used_at",
        "used_from_ip",
        "revoked_at",
    }

    # Step down — should clean off the table and its indexes.
    command.downgrade(cfg, "0011_index_ext_link_url")
    objs = _objects(db_path)
    assert "invite_tokens" not in objs
    assert "ux_invite_tokens_token_hash" not in objs
    assert "ix_invite_tokens_generated_at" not in objs
    assert "ix_invite_tokens_used_by_user_id" not in objs

    # Re-upgrade — idempotency check.
    command.upgrade(cfg, "head")
    objs = _objects(db_path)
    assert "invite_tokens" in objs
    assert "ux_invite_tokens_token_hash" in objs
