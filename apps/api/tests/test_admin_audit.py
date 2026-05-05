import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config_for_tests import override_catalog_paths
from app.core.audit import record_event
from app.core.auth.jwt import encode_token
from app.core.db.models import User
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
    from sqlmodel import Session, select

    from app.core.config import get_settings
    from app.core.db.session import get_engine as ge

    get_settings.cache_clear()
    ge.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        override_catalog_paths(app, index_path=FIXTURES / "index.json")
        # The admin user is created by lifespan seed_admin. Retrieve its UUID.
        engine = get_engine()
        with Session(engine) as s:
            user = s.exec(select(User).where(User.email == "admin@localhost.localdomain")).first()
            user_id = user.id
        # Seed audit events using the real user UUID.
        for i in range(5):
            record_event(
                engine,
                action=f"test.event.{i}",
                entity_type="catalog",
                entity_id=None,
                actor_user_id=user_id,
                after={"i": i},
            )
        token = encode_token(subject=str(user_id), role="admin", secret="test", ttl_minutes=30)
        yield c, token, user_id
    get_settings.cache_clear()
    from app.core.db.session import get_engine as ge2

    ge2.cache_clear()


def test_audit_requires_admin(client):
    c, _, _uid = client
    assert c.get("/api/admin/audit").status_code == 401


def test_audit_returns_paginated_events(client):
    c, token, user_id = client
    headers = {"Authorization": f"Bearer {token}"}
    r = c.get("/api/admin/audit?limit=3", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body["events"]) == 3
    assert body["total"] >= 5
    # Newest first.
    actions = [e["action"] for e in body["events"]]
    assert actions[0] == "test.event.4"
    # New fields are present.
    e0 = body["events"][0]
    assert e0["entity_type"] == "catalog"
    assert e0["entity_id"] is None
    assert e0["actor_user_id"] == str(user_id)
    assert e0["before"] is None
    assert e0["after"] == {"i": 4}
    assert "request_id" in e0
    # Old field "kind" / "payload" are gone.
    assert "kind" not in e0
    assert "payload" not in e0


def test_audit_offset_paginates(client):
    c, token, _uid = client
    headers = {"Authorization": f"Bearer {token}"}
    page1 = c.get("/api/admin/audit?limit=2&offset=0", headers=headers).json()["events"]
    page2 = c.get("/api/admin/audit?limit=2&offset=2", headers=headers).json()["events"]
    assert {e["id"] for e in page1}.isdisjoint({e["id"] for e in page2})


def test_audit_log_returns_entries_for_entity_id(client):
    c, token, user_id = client
    headers = {"Authorization": f"Bearer {token}"}
    engine = get_engine()
    target_id = uuid.uuid4()
    other_id = uuid.uuid4()
    record_event(
        engine,
        action="model.create",
        entity_type="model",
        entity_id=target_id,
        actor_user_id=user_id,
        after={"name": "x"},
    )
    record_event(
        engine,
        action="model.update",
        entity_type="model",
        entity_id=target_id,
        actor_user_id=user_id,
        after={"name": "y"},
    )
    record_event(
        engine,
        action="model.create",
        entity_type="model",
        entity_id=other_id,
        actor_user_id=user_id,
        after={"name": "z"},
    )
    r = c.get(
        f"/api/admin/audit-log?entity_type=model&entity_id={target_id}",
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    actions = [e["action"] for e in body["items"]]
    # Newest first.
    assert actions == ["model.update", "model.create"]
    e0 = body["items"][0]
    assert e0["entity_type"] == "model"
    assert e0["entity_id"] == str(target_id)
    assert e0["actor_user_id"] == str(user_id)
    assert e0["before_json"] is None
    assert e0["after_json"] == {"name": "y"}


def test_audit_log_filters_by_entity_type(client):
    c, token, user_id = client
    headers = {"Authorization": f"Bearer {token}"}
    engine = get_engine()
    record_event(
        engine,
        action="file.create",
        entity_type="model_file",
        entity_id=None,
        actor_user_id=user_id,
        after={"k": 1},
    )
    r = c.get("/api/admin/audit-log?entity_type=model_file", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) >= 1
    assert all(e["entity_type"] == "model_file" for e in body["items"])


def test_audit_log_requires_admin(client):
    c, _, _uid = client
    assert c.get("/api/admin/audit-log").status_code == 401
