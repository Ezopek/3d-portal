"""Round-trip Alembic migration 0009 — refresh_tokens."""
import os
import subprocess
import sys
from pathlib import Path

_API_DIR = Path(__file__).resolve().parents[1]
_ALEMBIC_BIN = _API_DIR / ".venv" / "bin" / "alembic"


def _alembic(env: dict, *args: str) -> subprocess.CompletedProcess:
    if _ALEMBIC_BIN.exists():
        cmd = [str(_ALEMBIC_BIN), *args]
    else:
        cmd = [sys.executable, "-m", "alembic", *args]
    return subprocess.run(
        cmd,
        cwd=_API_DIR,
        env={**env, "PATH": os.environ["PATH"]},
        capture_output=True,
        text=True,
        check=False,
    )


def test_migration_0009_round_trips(tmp_path):
    db_path = tmp_path / "rt.db"
    env = {"DATABASE_URL": f"sqlite:///{db_path}"}
    up1 = _alembic(env, "upgrade", "head")
    assert up1.returncode == 0, up1.stderr
    down = _alembic(env, "downgrade", "0008")
    assert down.returncode == 0, down.stderr
    up2 = _alembic(env, "upgrade", "head")
    assert up2.returncode == 0, up2.stderr


def test_migration_0009_partial_unique_invariant(tmp_path):
    """Two active rows in the same family must violate the partial UNIQUE."""
    import sqlite3
    import uuid
    db_path = tmp_path / "inv.db"
    env = {"DATABASE_URL": f"sqlite:///{db_path}"}
    assert _alembic(env, "upgrade", "head").returncode == 0

    # Need a real user UUID to satisfy the FK.
    conn = sqlite3.connect(db_path)
    user_id = str(uuid.uuid4())
    conn.execute(
        'INSERT INTO "user" (id, email, display_name, role, password_hash, created_at) '
        'VALUES (?, ?, ?, ?, ?, datetime("now"))',
        (user_id, "u@x", "u", "admin", "x"),
    )
    conn.commit()

    family = str(uuid.uuid4())
    now = "2026-05-07 10:00:00"
    exp = "2026-06-07 10:00:00"
    conn.execute(
        "INSERT INTO refresh_tokens "
        "(id, user_id, family_id, family_issued_at, token_hash, issued_at, expires_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), user_id, family, now, "h1", now, exp),
    )
    conn.commit()

    import pytest
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO refresh_tokens "
            "(id, user_id, family_id, family_issued_at, token_hash, issued_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, family, now, "h2", now, exp),
        )
        conn.commit()
    conn.close()
