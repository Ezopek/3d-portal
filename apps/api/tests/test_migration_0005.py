import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def alembic_env(tmp_path):
    db_path = tmp_path / "alembic-test-0005.db"
    env_vars = {
        "DATABASE_URL": f"sqlite:///{db_path}",
        "ADMIN_EMAIL": "admin@localhost",
        "ADMIN_PASSWORD": "test-pw",
        "JWT_SECRET": "test",
    }
    return db_path, env_vars


@pytest.fixture(scope="module")
def api_dir():
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def alembic_bin(api_dir):
    candidate = api_dir / ".venv" / "bin" / "alembic"
    return str(candidate) if candidate.exists() else None


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


def test_alembic_upgrade_head_creates_audit_log_and_drops_auditevent(
    alembic_env, api_dir, alembic_bin
):
    db_path, env = alembic_env
    r = _run_alembic(["upgrade", "head"], env=env, cwd=api_dir, alembic_bin=alembic_bin)
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

    assert "audit_log" in names
    assert "auditevent" not in names
    assert "user" in names
    assert "thumbnailoverride" in names
    assert "renderselection" in names


def test_alembic_downgrade_one_restores_auditevent(alembic_env, api_dir, alembic_bin):
    db_path, env = alembic_env
    r = _run_alembic(["upgrade", "head"], env=env, cwd=api_dir, alembic_bin=alembic_bin)
    assert r.returncode == 0, r.stderr
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

    assert "audit_log" not in names
    assert "auditevent" in names
    # Slice 1A entity tables remain intact at 0004
    assert "category" in names
    assert "model" in names


def test_alembic_full_round_trip(alembic_env, api_dir, alembic_bin):
    _db_path, env = alembic_env
    r = _run_alembic(["upgrade", "head"], env=env, cwd=api_dir, alembic_bin=alembic_bin)
    assert r.returncode == 0, r.stderr
    r = _run_alembic(["downgrade", "base"], env=env, cwd=api_dir, alembic_bin=alembic_bin)
    assert r.returncode == 0, r.stderr
    r = _run_alembic(["upgrade", "head"], env=env, cwd=api_dir, alembic_bin=alembic_bin)
    assert r.returncode == 0, r.stderr


def test_user_pk_is_uuid_type_after_upgrade(alembic_env, api_dir, alembic_bin):
    db_path, env = alembic_env
    r = _run_alembic(["upgrade", "head"], env=env, cwd=api_dir, alembic_bin=alembic_bin)
    assert r.returncode == 0, r.stderr

    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='user'"
        ).fetchone()[0]
    finally:
        conn.close()

    # SQLAlchemy renders sa.Uuid(as_uuid=True) on SQLite as CHAR(32)
    assert "CHAR(32)" in sql or "UUID" in sql.upper()
    # Verify user.id is NOT an INTEGER (the post-condition is "no longer int PK")
    # Get the line containing the id column
    lines = sql.split("\n")
    id_line = next((line for line in lines if line.strip().startswith("id")), "")
    assert "INTEGER" not in id_line.upper(), f"user.id should not be INTEGER; got: {id_line}"


def test_model_note_has_author_id_after_upgrade(alembic_env, api_dir, alembic_bin):
    """Migration 0005 must add model_note.author_id column."""
    db_path, env = alembic_env
    r = _run_alembic(["upgrade", "head"], env=env, cwd=api_dir, alembic_bin=alembic_bin)
    assert r.returncode == 0, r.stderr

    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='model_note'"
        ).fetchone()[0]
    finally:
        conn.close()

    assert "author_id" in sql, f"model_note.author_id missing; got: {sql}"
