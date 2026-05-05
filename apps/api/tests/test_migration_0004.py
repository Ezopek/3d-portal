import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def alembic_env(tmp_path):
    """A scratch SQLite DB path + env vars for invoking alembic."""
    db_path = tmp_path / "alembic-test.db"
    env_vars = {
        "DATABASE_URL": f"sqlite:///{db_path}",
        # Settings used at import time by app.main / app.core.config
        "ADMIN_EMAIL": "admin@localhost",
        "ADMIN_PASSWORD": "test-pw",
        "JWT_SECRET": "test",
    }
    return db_path, env_vars


@pytest.fixture(scope="module")
def api_dir():
    # Tests run from any cwd; we always invoke alembic with cwd=apps/api.
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def alembic_bin(api_dir):
    """Resolve the alembic binary inside the api venv."""
    candidate = api_dir / ".venv" / "bin" / "alembic"
    if candidate.exists():
        return str(candidate)
    # Fallback: the same Python that runs pytest should resolve alembic via -m
    return None  # signal: use python -m alembic


def _run_alembic(args, env, cwd, alembic_bin):
    cmd = [alembic_bin, *args] if alembic_bin else [sys.executable, "-m", "alembic", *args]
    return subprocess.run(
        cmd,
        env={**env, "PATH": os.environ["PATH"]},
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_alembic_upgrade_head_creates_all_new_tables(alembic_env, api_dir, alembic_bin):
    db_path, env = alembic_env
    result = _run_alembic(["upgrade", "head"], env=env, cwd=api_dir, alembic_bin=alembic_bin)
    assert result.returncode == 0, (
        f"alembic upgrade head failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )

    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = {r[0] for r in rows}
    finally:
        conn.close()

    expected = {
        "category",
        "tag",
        "model",
        "model_file",
        "model_tag",
        "model_print",
        "model_external_link",
        "model_note",
    }
    missing = expected - names
    assert not missing, f"missing tables: {missing}; have: {sorted(names)}"


def test_alembic_downgrade_then_upgrade_is_idempotent(alembic_env, api_dir, alembic_bin):
    _db_path, env = alembic_env
    r = _run_alembic(["upgrade", "head"], env=env, cwd=api_dir, alembic_bin=alembic_bin)
    assert r.returncode == 0, r.stderr
    r = _run_alembic(["downgrade", "base"], env=env, cwd=api_dir, alembic_bin=alembic_bin)
    assert r.returncode == 0, r.stderr
    r = _run_alembic(["upgrade", "head"], env=env, cwd=api_dir, alembic_bin=alembic_bin)
    assert r.returncode == 0, r.stderr


def test_alembic_downgrade_one_removes_only_new_tables(alembic_env, api_dir, alembic_bin):
    db_path, env = alembic_env
    r = _run_alembic(["upgrade", "head"], env=env, cwd=api_dir, alembic_bin=alembic_bin)
    assert r.returncode == 0, r.stderr
    # downgrade to 0004: audit_log and UUID user go away,
    # auditevent + int-id user come back; entity tables introduced in 0004 remain.
    r = _run_alembic(["downgrade", "0004"], env=env, cwd=api_dir, alembic_bin=alembic_bin)
    assert r.returncode == 0, r.stderr

    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = {r[0] for r in rows}
    finally:
        conn.close()

    # Entity tables are still present (created in 0004, not touched by 0005 downgrade).
    entity_tables = {
        "category",
        "tag",
        "model",
        "model_file",
        "model_tag",
        "model_print",
        "model_external_link",
        "model_note",
    }
    missing_entity = entity_tables - names
    assert not missing_entity, (
        f"entity tables unexpectedly removed by downgrade -1: {missing_entity}"
    )
    # 0005 downgrade restores auditevent and removes audit_log
    assert "auditevent" in names, "auditevent should be restored after downgrade -1"
    assert "audit_log" not in names, "audit_log should be removed after downgrade -1"
    # Existing pre-0004 tables are still there
    assert "user" in names
    assert "thumbnailoverride" in names
    assert "renderselection" in names


def test_alembic_and_sqlmodel_emit_equivalent_index_sets(
    alembic_env, api_dir, alembic_bin, tmp_path
):
    """Schema parity guard between alembic migration 0004 and SQLModel.metadata.create_all.

    These two paths produce different DBs in this codebase: production uses
    alembic, while tests use init_schema() (SQLModel.metadata.create_all).
    They MUST agree on which indexes exist on the new entity tables, so
    test fixtures are representative of production.
    """
    import sqlite3

    from app.core.db.session import create_engine_for_url, init_schema

    # Path A: alembic-driven schema
    db_path_a, env = alembic_env
    r = _run_alembic(["upgrade", "head"], env=env, cwd=api_dir, alembic_bin=alembic_bin)
    assert r.returncode == 0, r.stderr

    # Path B: SQLModel-driven schema (separate tmp DB)
    db_path_b = tmp_path / "sqlmodel-test.db"
    engine_b = create_engine_for_url(f"sqlite:///{db_path_b}")
    init_schema(engine_b)

    new_tables = [
        "category",
        "tag",
        "model",
        "model_file",
        "model_tag",
        "model_print",
        "model_external_link",
        "model_note",
    ]

    def _index_set(db_path, table):
        conn = sqlite3.connect(db_path)
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='index' AND tbl_name=? "
                "AND name NOT LIKE 'sqlite_autoindex_%' "
                "ORDER BY name",
                (table,),
            ).fetchall()
            return {r[0] for r in rows}
        finally:
            conn.close()

    drifts = {}
    for table in new_tables:
        a = _index_set(db_path_a, table)
        b = _index_set(db_path_b, table)
        if a != b:
            drifts[table] = {
                "only_in_alembic": sorted(a - b),
                "only_in_sqlmodel": sorted(b - a),
            }

    assert drifts == {}, f"alembic vs SQLModel index set drift on new entity tables: {drifts}"
