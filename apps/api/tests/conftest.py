import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(autouse=True, scope="session")
def _isolated_db():
    tmp_dir = Path(tempfile.mkdtemp(prefix="portal-test-"))
    db_path = tmp_dir / "portal.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["ADMIN_EMAIL"] = "admin@localhost.localdomain"
    os.environ["ADMIN_PASSWORD"] = "test-admin-pw"
    os.environ["JWT_SECRET"] = "test-secret-not-real"
    # Clear any cached settings or engine that read env at import time
    from app.core.config import get_settings
    from app.core.db.session import get_engine

    get_settings.cache_clear()
    get_engine.cache_clear()
    yield
    # Cleanup tmp dir best-effort
    import shutil

    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
