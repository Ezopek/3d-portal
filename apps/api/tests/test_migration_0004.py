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
    # downgrade one revision (0004 -> 0003)
    r = _run_alembic(["downgrade", "-1"], env=env, cwd=api_dir, alembic_bin=alembic_bin)
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

    new_tables = {
        "category",
        "tag",
        "model",
        "model_file",
        "model_tag",
        "model_print",
        "model_external_link",
        "model_note",
    }
    assert names.isdisjoint(new_tables), (
        f"these new-tables remained after downgrade -1: {names & new_tables}"
    )
    # Existing pre-0004 tables are still there
    assert "user" in names
    assert "auditevent" in names
    assert "thumbnailoverride" in names
    assert "renderselection" in names
