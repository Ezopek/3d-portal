import os
import tempfile
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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
