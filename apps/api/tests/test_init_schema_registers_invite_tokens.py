"""Regression test: ``init_schema()`` registers ``invite_tokens`` on a cold start.

Catches the case where the side-effect import of ``app.modules.invite.models``
from ``app.core.db.models.__init__`` is removed: without it,
``SQLModel.metadata`` never sees the ``InviteToken`` table and a fresh dev DB
boot (apps/api/app/main.py lifespan) or any non-Alembic test path would
silently miss the ``invite_tokens`` table.

We spawn a fresh Python subprocess so the test runs in a process that has not
yet had ``app.modules.invite.models`` pulled in by any other test module — the
side-effect import in ``app.core.db.models`` is the only registration path.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import textwrap


def test_init_schema_registers_invite_tokens_table() -> None:
    script = textwrap.dedent("""
        from sqlalchemy import inspect

        # Importing the package alone must side-effect-register InviteToken
        # on SQLModel.metadata. No explicit invite import here on purpose.
        import app.core.db.models  # noqa: F401
        from app.core.db.session import create_engine_for_url, init_schema

        engine = create_engine_for_url("sqlite:///:memory:")
        init_schema(engine)
        names = set(inspect(engine).get_table_names())
        assert "invite_tokens" in names, (
            f"invite_tokens missing from create_all output; tables: {sorted(names)}"
        )
        print("OK")
    """)
    # Pin cwd to apps/api/ so the spawned interpreter resolves `app` regardless
    # of where pytest itself was invoked from (repo root vs apps/api/).
    api_root = pathlib.Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
        cwd=api_root,
    )
    assert result.returncode == 0, (
        f"subprocess failed (rc={result.returncode}):\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "OK" in result.stdout
