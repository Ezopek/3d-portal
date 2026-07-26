"""Alembic round-trip for migration 0020_browse_categories (additive, reversible).

Story 49.1 (Initiative 26 / Epic 49, Decisions AX + AZ). AC-13: upgrading to
``0020_browse_categories`` creates ``browse_category`` + ``model_browse_category``
with both NAMED indexes and the declared column/PK/FK shape; ``downgrade`` to
``0019_drop_category`` removes exactly those objects while the pre-existing
catalog + facet-tag tables survive; re-``upgrade`` restores everything
identically (idempotency).

Unlike ``0018``/``0019`` this migration's ``downgrade()`` is IMPLEMENTED — it
drops only tables it created itself, so the downward leg below is a real
traversal rather than an expected raise. Every traversal is pinned to an
explicit revision id (never ``"head"``), so a future ``0021`` cannot silently
change what this test exercises.

Uses its own tmpdir DB and bypasses the session-scope ``_isolated_db`` fixture by
overriding ``DATABASE_URL`` for the duration of the test (``env.py`` reads
``get_settings().database_url`` and ignores the URL passed via the Alembic
``Config`` directly, so the env var is the only knob that works). Fixture mirrors
``test_migration_0018.py`` verbatim.
"""

from __future__ import annotations

import importlib.util
import os
import sqlite3
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations

# Every column BrowseCategory declares (AC-1) — asserted as an exact set so a
# stray or missing column is a failure, not a silent pass.
BROWSE_CATEGORY_COLUMNS = {
    "id",
    "slug",
    "name_en",
    "name_pl",
    "description_en",
    "description_pl",
    "inclusion_criterion",
    "position",
    "parent_id",
    "created_at",
    "updated_at",
}


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


def _pk_columns(db_path: Path, table: str) -> set[str]:
    """Return the set of column names participating in ``table``'s primary key."""
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows if r[5]}


def _foreign_keys(db_path: Path, table: str) -> list[dict[str, str]]:
    """Return the outbound foreign keys of ``table`` as {table, from, to, on_delete}.

    PRAGMA foreign_key_list columns: id, seq, table, from, to, on_update,
    on_delete, match. SQLite does NOT expose the constraint *name* here, so FK
    identity is pinned by target table/column + ON DELETE action.
    """
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()
    return [{"table": r[2], "from": r[3], "to": r[4], "on_delete": r[6]} for r in rows]


def _load_revision(name: str) -> ModuleType:
    """Import a revision file directly so its ``downgrade()`` can be driven by hand.

    ``alembic.command`` builds its own engine from ``env.py``; loading the module
    lets the test execute the very same ``downgrade()`` body against a connection
    it controls (see the FK-enforcement test below).
    """
    path = Path(__file__).parent.parent / "migrations" / "versions" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_revision_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_migration_0020_round_trip(_round_trip_db: Path) -> None:
    db_path = _round_trip_db
    cfg = _alembic_cfg(db_path)

    # --- Forward to 0020 ---------------------------------------------------
    command.upgrade(cfg, "0020_browse_categories")
    objs = _objects(db_path)
    assert "browse_category" in objs
    assert "model_browse_category" in objs
    # Both indexes exist under their EXPLICIT names — the drift trap AC-3 guards.
    assert "uq_browse_category_slug" in objs
    assert "ix_model_browse_category_cat_model" in objs

    # browse_category column shape (AC-1), asserted as an exact set.
    cat_cols = _columns(db_path, "browse_category")
    assert set(cat_cols) == BROWSE_CATEGORY_COLUMNS

    # id is the single-column primary key — asserted directly, not inferred from
    # the parity gate, so a 0020 that lost primary_key=True fails HERE.
    assert _pk_columns(db_path, "browse_category") == {"id"}

    # Required vs optional is part of the declared shape, so pin both halves
    # explicitly rather than only the four columns spot-checked below.
    for required in ("id", "slug", "name_en", "position", "created_at", "updated_at"):
        assert cat_cols[required][1] == 1, f"{required} must be NOT NULL"
    for optional in (
        "name_pl",
        "description_en",
        "description_pl",
        "inclusion_criterion",
        "parent_id",
    ):
        assert cat_cols[optional][1] == 0, f"{optional} must be nullable"

    # position is NOT NULL with server_default "0"; SQLite quotes the reflected
    # default, so strip to compare the literal. The point is NOT NULL +
    # default-zero, not quoting.
    pos_type, pos_notnull, pos_default = cat_cols["position"]
    assert pos_notnull == 1
    assert pos_default.strip("'") == "0"

    # parent_id is nullable — a root/flat category is DB-valid.
    assert cat_cols["parent_id"][1] == 0

    # Timestamps are NOT NULL with NO server_default (the ORM supplies them via
    # default_factory=_now_utc), matching the 0018 idiom.
    for ts in ("created_at", "updated_at"):
        assert cat_cols[ts][1] == 1
        assert cat_cols[ts][2] is None

    # model_browse_category: BOTH columns form the composite PK.
    assert _pk_columns(db_path, "model_browse_category") == {"model_id", "category_id"}
    assert set(_columns(db_path, "model_browse_category")) == {
        "model_id",
        "category_id",
        "created_at",
    }

    # FK proof via PRAGMA — executable, not by source inspection.
    join_fks = _foreign_keys(db_path, "model_browse_category")
    assert {
        "table": "model",
        "from": "model_id",
        "to": "id",
        "on_delete": "CASCADE",
    } in join_fks
    assert {
        "table": "browse_category",
        "from": "category_id",
        "to": "id",
        "on_delete": "RESTRICT",
    } in join_fks

    # Self-referential FK on browse_category.parent_id, RESTRICT.
    assert _foreign_keys(db_path, "browse_category") == [
        {
            "table": "browse_category",
            "from": "parent_id",
            "to": "id",
            "on_delete": "RESTRICT",
        }
    ]

    # Additive-only: the migration inserts ZERO rows (no seed content, AC-6).
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT count(*) FROM browse_category").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM model_browse_category").fetchone()[0] == 0

    # No retired name was reused or resurrected (AC-8): 0019 is not reverted.
    legacy = "category"
    assert legacy not in objs
    assert f"ix_model_{legacy}_id" not in objs
    assert f"{legacy}_id" not in _columns(db_path, "model")

    # --- Step down to 0019 -------------------------------------------------
    # Pinned to 0019_drop_category explicitly; 0020.downgrade() is implemented,
    # so this is a real reversibility proof (AC-7).
    command.downgrade(cfg, "0019_drop_category")
    objs = _objects(db_path)
    assert "browse_category" not in objs
    assert "model_browse_category" not in objs
    assert "uq_browse_category_slug" not in objs
    assert "ix_model_browse_category_cat_model" not in objs

    # Everything 0020 did not create survives the downgrade untouched.
    for survivor in ("model", "tag", "tag_group", "model_tag"):
        assert survivor in objs

    # --- Re-upgrade: idempotency ------------------------------------------
    command.upgrade(cfg, "0020_browse_categories")
    objs = _objects(db_path)
    assert "browse_category" in objs
    assert "model_browse_category" in objs
    assert "uq_browse_category_slug" in objs
    assert "ix_model_browse_category_cat_model" in objs

    # Restored identically — same column shape, same PK, same FK semantics.
    assert set(_columns(db_path, "browse_category")) == BROWSE_CATEGORY_COLUMNS
    assert _columns(db_path, "browse_category")["position"] == (
        pos_type,
        pos_notnull,
        pos_default,
    )
    assert _pk_columns(db_path, "model_browse_category") == {"model_id", "category_id"}
    assert _foreign_keys(db_path, "model_browse_category") == join_fks
    assert _foreign_keys(db_path, "browse_category") == [
        {
            "table": "browse_category",
            "from": "parent_id",
            "to": "id",
            "on_delete": "RESTRICT",
        }
    ]


def test_migration_0020_downgrade_under_foreign_key_enforcement(_round_trip_db: Path) -> None:
    """``0020.downgrade()`` completes with SQLite FK enforcement ARMED (AC-7).

    ``migrations/env.py`` builds its engine via ``engine_from_config`` and never
    issues ``PRAGMA foreign_keys=ON``, so the ``command.downgrade`` traversal in
    the round-trip test above runs with enforcement OFF and is structurally
    blind to this class of failure. Here the revision's own ``downgrade()`` body
    is executed through ``Operations(MigrationContext.configure(connection))``
    on a connection whose pragma is explicitly set AND asserted, with a
    parent/child pair present. Before the repair, ``DROP TABLE browse_category``
    performed an implicit per-row delete and the self-referential
    ``ON DELETE RESTRICT`` fired, aborting the drop after
    ``uq_browse_category_slug`` had already been dropped — a half-reverted
    schema. The regression below proves the current repair prevents that state.

    The seed also arms the CROSS-TABLE RESTRICT — one ``model`` row and one
    ``model_browse_category`` row — so the child-before-parent drop order that
    ``0020_browse_categories.downgrade()`` relies on is under test here too.
    With a category/child pair alone, only the self-FK is live and reversing
    the two ``drop_table`` calls still passes.

    The proof is that the downgrade is COMPLETE, not merely that it did not
    raise: both tables and both named indexes must be gone afterwards.
    """
    db_path = _round_trip_db
    cfg = _alembic_cfg(db_path)
    command.upgrade(cfg, "0020_browse_categories")

    # sa.Uuid(as_uuid=True) stores as CHAR(32) hex on SQLite; the values only
    # have to be self-consistent for the self-FK to link parent → child.
    parent_id = uuid.uuid4().hex
    child_id = uuid.uuid4().hex
    model_id = uuid.uuid4().hex
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO browse_category "
            "(id, slug, name_en, position, parent_id, created_at, updated_at) "
            "VALUES (?, ?, ?, 0, ?, '2026-07-26 00:00:00', '2026-07-26 00:00:00')",
            [(parent_id, "home", "Home", None), (child_id, "lamps", "Lamps", parent_id)],
        )
        # Minimal legal row on the post-0019 `model` schema: id / slug / name_en
        # / date_added / created_at / updated_at are its only NOT NULL columns
        # without a server_default. source and status default, rating stays NULL
        # (satisfying ck_model_rating_range) and thumbnail_file_id stays NULL, so
        # no model_file row is needed.
        conn.execute(
            "INSERT INTO model (id, slug, name_en, date_added, created_at, updated_at) "
            "VALUES (?, 'desk-lamp', 'Desk lamp', '2026-07-26', "
            "'2026-07-26 00:00:00', '2026-07-26 00:00:00')",
            (model_id,),
        )
        # One assignment row arms model_browse_category.category_id →
        # browse_category.id (ON DELETE RESTRICT) — the CROSS-table FK the
        # child-before-parent drop order exists to satisfy.
        conn.execute(
            "INSERT INTO model_browse_category (model_id, category_id, created_at) "
            "VALUES (?, ?, '2026-07-26 00:00:00')",
            (model_id, child_id),
        )

    engine = sa.create_engine(f"sqlite:///{db_path}")
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            # Assert, do not assume: SQLite silently IGNORES this pragma when it
            # is issued inside an open transaction, which would make the whole
            # test vacuous.
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1

            # Both FKs really are armed going in — pinned so a future schema or
            # insert drift silently emptying the seed cannot make this test pass
            # for the wrong reason.
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM browse_category WHERE parent_id IS NOT NULL"
                ).scalar()
                == 1
            )
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM model_browse_category "
                    "WHERE model_id = ? AND category_id = ?",
                    (model_id, child_id),
                ).scalar()
                == 1
            )
            # The seed itself is FK-legal, so any IntegrityError below comes from
            # the drop order under test and never from a broken fixture.
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []

            revision = _load_revision("0020_browse_categories")
            with Operations.context(MigrationContext.configure(connection)):
                revision.downgrade()
            connection.commit()
    finally:
        engine.dispose()

    objs = _objects(db_path)
    assert "browse_category" not in objs
    assert "model_browse_category" not in objs
    assert "uq_browse_category_slug" not in objs
    assert "ix_model_browse_category_cat_model" not in objs

    # Nothing outside this revision's own two tables was disturbed.
    for survivor in ("model", "tag", "tag_group", "model_tag"):
        assert survivor in objs
