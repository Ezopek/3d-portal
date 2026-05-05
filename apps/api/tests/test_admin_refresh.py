import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

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

    renders_dir = tmp_path / "renders"
    renders_dir.mkdir()

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/r.db")
    monkeypatch.setenv("CATALOG_DATA_DIR", str(FIXTURES / "catalog"))
    monkeypatch.setenv("RENDERS_DIR", str(renders_dir))
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    from app.core.config import get_settings
    from app.core.db.session import get_engine

    get_settings.cache_clear()
    get_engine.cache_clear()
    app = create_app()

    arq_pool = MagicMock()
    arq_pool.enqueue_job = AsyncMock(return_value=MagicMock(job_id="job-x"))

    async def _arq_close():
        return None

    arq_pool.aclose = _arq_close

    with TestClient(app) as c:
        override_catalog_paths(app, index_path=dst)
        app.state.arq = arq_pool
        # Retrieve the seeded admin user UUID for use in token and repo calls.
        from sqlmodel import Session, select

        from app.core.db.models import User

        engine = get_engine()
        with Session(engine) as s:
            user = s.exec(select(User).where(User.email == "admin@localhost.localdomain")).first()
            user_id = user.id
        token = encode_token(subject=str(user_id), role="admin", secret="test", ttl_minutes=30)
        yield c, token, dst, renders_dir, arq_pool
    get_settings.cache_clear()
    get_engine.cache_clear()


def test_refresh_requires_admin(setup):
    client, _token, _path, _renders, _arq = setup
    r = client.post("/api/admin/refresh-catalog")
    assert r.status_code == 401


def test_refresh_picks_up_index_changes(setup):
    client, token, index_path, _renders, _arq = setup
    headers = {"Authorization": f"Bearer {token}"}

    r0 = client.get("/api/catalog/models")
    assert r0.json()["total"] == 3

    # Replace the file with a single-entry catalog.
    new_data = json.loads(index_path.read_text())[:1]
    index_path.write_text(json.dumps(new_data))

    r = client.post("/api/admin/refresh-catalog", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 1

    # The list reflects the change.
    assert client.get("/api/catalog/models").json()["total"] == 1


def test_refresh_enqueues_render_for_models_missing_iso_png(setup):
    client, token, _index, renders_dir, arq = setup
    headers = {"Authorization": f"Bearer {token}"}

    # 002 already has a render — only 001 and 003 should be queued.
    (renders_dir / "002").mkdir()
    (renders_dir / "002" / "iso.png").write_bytes(b"fake png")

    r = client.post("/api/admin/refresh-catalog", headers=headers)
    assert r.status_code == 200
    assert r.json()["renders_enqueued"] == 2

    queued_ids = sorted(call.args[1] for call in arq.enqueue_job.call_args_list)
    assert queued_ids == ["001", "003"]
    for call in arq.enqueue_job.call_args_list:
        assert call.args[0] == "render_model"


def test_refresh_enqueues_nothing_when_all_renders_present(setup):
    client, token, _index, renders_dir, arq = setup
    headers = {"Authorization": f"Bearer {token}"}

    for model_id in ("001", "002", "003"):
        (renders_dir / model_id).mkdir()
        (renders_dir / model_id / "iso.png").write_bytes(b"fake png")

    r = client.post("/api/admin/refresh-catalog", headers=headers)
    assert r.status_code == 200
    assert r.json()["renders_enqueued"] == 0
    arq.enqueue_job.assert_not_called()
