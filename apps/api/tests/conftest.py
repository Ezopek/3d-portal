import os
import tempfile
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(autouse=True)
def _patch_arq_pool():
    """Prevent arq create_pool from connecting to a real Redis in tests."""
    fake_pool = MagicMock()
    fake_pool.enqueue_job = AsyncMock(return_value=MagicMock(job_id="mock-job"))

    async def _aclose():
        return None

    fake_pool.aclose = _aclose

    async def _fake_create_pool(*args, **kwargs):
        return fake_pool

    with patch("app.main.create_pool", side_effect=_fake_create_pool):
        yield fake_pool


@pytest.fixture(autouse=True, scope="session")
def _isolated_db():
    tmp_dir = Path(tempfile.mkdtemp(prefix="portal-test-"))
    db_path = tmp_dir / "portal.db"
    content_dir = tmp_dir / "content"
    content_dir.mkdir()
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["ADMIN_EMAIL"] = "admin@localhost.localdomain"
    os.environ["ADMIN_PASSWORD"] = "test-admin-pw"
    os.environ["JWT_SECRET"] = "test-secret-not-real"
    # Story 7.1 / Decision D — deterministic Fernet key for TOTP tests.
    # 32 url-safe-base64-encoded bytes; trailing "=" pads to 44 chars total.
    os.environ["TOTP_FERNET_KEY"] = "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM="
    os.environ["PORTAL_CONTENT_DIR"] = str(content_dir)
    os.environ["COOKIE_SECURE"] = "false"  # TestClient uses http://testserver (not HTTPS)
    # Clear any cached settings or engine that read env at import time
    from app.core.config import get_settings
    from app.core.db.session import get_engine, init_schema

    get_settings.cache_clear()
    get_engine.cache_clear()
    # Initialize schema once for the session so tests that don't use the
    # `client` fixture (which runs lifespan + init_schema) can still query
    # the DB directly via get_engine().
    init_schema(get_engine())
    yield
    # Cleanup tmp dir best-effort
    import shutil

    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()
    with TestClient(app) as test_client:
        test_client.headers.update({"X-Portal-Client": "web"})
        yield test_client


@pytest.fixture
def isolated_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Story 8.1 (AC-7) — promoted per-test isolation fixture.

    Yields a ``(TestClient, FakeRedis)`` tuple after building a fresh app
    bound to a per-test tmpdir SQLite + a fakeredis instance swapped onto
    ``app.state.redis``. Mirrors the per-file fixture shape from
    ``test_2fa_enrollment.py:50-74`` saturated across ~10 files (Epic 6
    retro item §4, Epic 7 retro item §6).

    Use for NEW Epic 8+ test files that need per-test DB + Redis isolation.
    The existing per-file ``client`` fixtures in 10 callers are NOT being
    deleted in this story (mass refactor would balloon the diff and risk
    subtle behavior drift in 10 test files — that refactor lands
    opportunistically when each file is next touched, or as a separate
    dedicated chore commit per the Story 8.1 OUT-OF-SCOPE boundary).

    Name deviates from the AC-7 verbatim ``client`` because that name is
    already bound to a different-shaped session-scoped fixture in this
    conftest (200+ existing tests consume the plain-TestClient one);
    renaming it would constitute the mass refactor explicitly forbidden by
    the story scope. The shape, fakeredis swap, and per-test isolation all
    honor AC-7 verbatim.
    """
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-real")
    monkeypatch.setenv("TOTP_FERNET_KEY", "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM=")

    from app.core.config import get_settings
    from app.core.db.session import get_engine

    get_settings.cache_clear()
    get_engine.cache_clear()
    try:
        app = create_app()
        fake = fakeredis.aioredis.FakeRedis()
        factory = MagicMock()
        factory.get = MagicMock(return_value=fake)

        async def _aclose():
            return None

        factory.aclose = _aclose
        with TestClient(app) as c:
            c.headers.update({"X-Portal-Client": "web"})
            app.state.redis = factory
            yield c, fake
    finally:
        get_settings.cache_clear()
        get_engine.cache_clear()
