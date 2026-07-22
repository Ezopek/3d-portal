"""Alembic round-trip for migration 0014_users_is_active_last_active.

AC-1: upgrade head → downgrade -1 → upgrade head; both new columns present
with the binding shape on first upgrade, absent after downgrade, present
again after re-upgrade. The 0013 columns (totp_secret, totp_enabled_at)
stay through the round-trip.

Uses its own tmpdir DB and bypasses the session-scope ``_isolated_db``
fixture by overriding ``DATABASE_URL`` for the duration of the test
(``env.py`` reads ``get_settings().database_url`` and ignores the URL
passed via the Alembic ``Config`` directly, so the env var is the only
knob that works). Pattern mirrors ``test_migration_0012.py:38-58``
verbatim per story §AC-1.
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


def _user_columns(db_path: Path) -> dict[str, tuple[str, int, str | None]]:
    """Return a dict of column-name → (type, notnull, dflt_value).

    PRAGMA columns order: cid, name, type, notnull, dflt_value, pk.
    """
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("PRAGMA table_info(user)").fetchall()
    return {r[1]: (r[2], r[3], r[4]) for r in rows}


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


def test_migration_0014_round_trip(_round_trip_db: Path) -> None:
    db_path = _round_trip_db
    cfg = _alembic_cfg(db_path)

    # Pinned to 0018_facet_tags (not head): 0019_drop_category is forward-only
    # (downgrade() raises), so any head-downward traversal would fail (Story 47.5).
    # Forward — adds is_active + last_active_at to the user table.
    command.upgrade(cfg, "0018_facet_tags")
    cols = _user_columns(db_path)
    assert "is_active" in cols
    assert "last_active_at" in cols
    is_active_type, is_active_notnull, is_active_default = cols["is_active"]
    assert is_active_type == "BOOLEAN"
    assert is_active_notnull == 1
    assert is_active_default == "1"
    last_active_type, last_active_notnull, last_active_default = cols["last_active_at"]
    assert last_active_type == "DATETIME"
    assert last_active_notnull == 0
    assert last_active_default is None
    # 0013 columns still present.
    assert "totp_secret" in cols
    assert "totp_enabled_at" in cols

    # Step down — should drop is_active + last_active_at; 0013 columns stay.
    command.downgrade(cfg, "0013_users_2fa_columns")
    cols = _user_columns(db_path)
    assert "is_active" not in cols
    assert "last_active_at" not in cols
    assert "totp_secret" in cols
    assert "totp_enabled_at" in cols

    # Re-upgrade — idempotency check.
    command.upgrade(cfg, "0018_facet_tags")
    cols = _user_columns(db_path)
    assert "is_active" in cols
    assert "last_active_at" in cols
    assert cols["is_active"] == (is_active_type, is_active_notnull, is_active_default)
    assert cols["last_active_at"] == (last_active_type, last_active_notnull, last_active_default)
