from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config_for_tests import override_catalog_paths
from app.core.audit import record_event
from app.core.auth.jwt import encode_token
from app.core.db.session import get_engine
from app.main import create_app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/a.db")
    monkeypatch.setenv("CATALOG_DATA_DIR", str(FIXTURES / "catalog"))
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    from app.core.config import get_settings
    from app.core.db.session import get_engine as ge

    get_settings.cache_clear()
    ge.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        override_catalog_paths(app, index_path=FIXTURES / "index.json")
        # Seed audit events. The admin user (id=1) is created by lifespan seed_admin.
        engine = get_engine()
        for i in range(5):
            record_event(engine, kind=f"test.event.{i}", actor_user_id=1, payload={"i": i})
        token = encode_token(subject="1", role="admin", secret="test", ttl_minutes=30)
        yield c, token
    get_settings.cache_clear()
    from app.core.db.session import get_engine as ge2

    ge2.cache_clear()


def test_audit_requires_admin(client):
    c, _ = client
    assert c.get("/api/admin/audit").status_code == 401


def test_audit_returns_paginated_events(client):
    c, token = client
    headers = {"Authorization": f"Bearer {token}"}
    r = c.get("/api/admin/audit?limit=3", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body["events"]) == 3
    assert body["total"] >= 5
    # Newest first.
    kinds = [e["kind"] for e in body["events"]]
    assert kinds[0] == "test.event.4"


def test_audit_offset_paginates(client):
    c, token = client
    headers = {"Authorization": f"Bearer {token}"}
    page1 = c.get("/api/admin/audit?limit=2&offset=0", headers=headers).json()["events"]
    page2 = c.get("/api/admin/audit?limit=2&offset=2", headers=headers).json()["events"]
    assert {e["id"] for e in page1}.isdisjoint({e["id"] for e in page2})
