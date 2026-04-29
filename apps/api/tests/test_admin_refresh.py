import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config_for_tests import override_catalog_paths
from app.core.auth.jwt import encode_token
from app.main import create_app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def setup(tmp_path, monkeypatch):
    src = FIXTURES / "index.json"
    dst = tmp_path / "index.json"
    dst.write_text(src.read_text())

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/r.db")
    monkeypatch.setenv("CATALOG_DATA_DIR", str(FIXTURES / "catalog"))
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    from app.core.config import get_settings
    from app.core.db.session import get_engine
    get_settings.cache_clear()
    get_engine.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        override_catalog_paths(app, index_path=dst)
        token = encode_token(subject="1", role="admin", secret="test", ttl_minutes=30)
        yield c, token, dst
    get_settings.cache_clear()
    get_engine.cache_clear()


def test_refresh_requires_admin(setup):
    client, _token, _path = setup
    r = client.post("/api/admin/refresh-catalog")
    assert r.status_code == 401


def test_refresh_picks_up_index_changes(setup):
    client, token, index_path = setup
    headers = {"Authorization": f"Bearer {token}"}

    r0 = client.get("/api/catalog/models")
    assert r0.json()["total"] == 3

    # Replace the file with a single-entry catalog.
    new_data = json.loads(index_path.read_text())[:1]
    index_path.write_text(json.dumps(new_data))

    # Without refresh, cache still has 3.
    assert client.get("/api/catalog/models").json()["total"] == 3

    r = client.post("/api/admin/refresh-catalog", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 1

    # Now the list reflects the change.
    assert client.get("/api/catalog/models").json()["total"] == 1
