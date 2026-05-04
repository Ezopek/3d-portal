from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config_for_tests import override_catalog_paths
from app.core.auth.jwt import encode_token
from app.core.db.session import get_engine
from app.main import create_app
from app.modules.catalog.thumbnail_overrides import ThumbnailOverrideRepo

FIXTURES = Path(__file__).parent / "fixtures"

# A fixed UUID used for non-admin "wrong role" token tests (never looked up in DB).
_NON_ADMIN_UUID = "00000000-0000-0000-0000-000000000042"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/t.db")
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
        override_catalog_paths(app, index_path=FIXTURES / "index.json")
        # Retrieve the seeded admin user UUID for token.
        from sqlmodel import Session, select

        from app.core.db.models import User

        engine = get_engine()
        with Session(engine) as s:
            user = s.exec(select(User).where(User.email == "admin@localhost.localdomain")).first()
            user_id = user.id
        token = encode_token(subject=str(user_id), role="admin", secret="test", ttl_minutes=30)
        yield c, token, user_id
    get_settings.cache_clear()
    from app.core.db.session import get_engine as ge2

    ge2.cache_clear()


def _hdrs(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_put_requires_auth(client):
    c, _, _uid = client
    resp = c.put("/api/admin/models/001/thumbnail", json={"path": "iso.png"})
    assert resp.status_code == 401


def test_put_403_for_non_admin(client):
    c, _, _uid = client
    user_token = encode_token(subject=_NON_ADMIN_UUID, role="user", secret="test", ttl_minutes=30)
    resp = c.put(
        "/api/admin/models/001/thumbnail", json={"path": "iso.png"}, headers=_hdrs(user_token)
    )
    assert resp.status_code == 403


def test_put_404_for_unknown_model(client):
    c, token, _uid = client
    resp = c.put("/api/admin/models/999/thumbnail", json={"path": "iso.png"}, headers=_hdrs(token))
    assert resp.status_code == 404


@pytest.mark.parametrize(
    "bad_path",
    [
        "../escape.png",
        "/etc/passwd",
        "decorum/dragon/Dragon.stl",
        "images/x.exe",
        "prints/x",
        "iso.jpg",  # render names are PNG-only by spec
    ],
)
def test_put_400_for_invalid_path(client, bad_path):
    c, token, _uid = client
    resp = c.put("/api/admin/models/001/thumbnail", json={"path": bad_path}, headers=_hdrs(token))
    assert resp.status_code == 400


def test_put_404_when_path_whitelisted_but_file_missing(client):
    c, token, _uid = client
    resp = c.put(
        "/api/admin/models/001/thumbnail",
        json={"path": "prints/does-not-exist.jpg"},
        headers=_hdrs(token),
    )
    assert resp.status_code == 404


def test_put_happy_path_updates_list_and_audit(client):
    c, token, _uid = client
    resp = c.put(
        "/api/admin/models/001/thumbnail", json={"path": "images/Dragon.png"}, headers=_hdrs(token)
    )
    assert resp.status_code == 204

    list_body = c.get("/api/catalog/models").json()
    by_id = {m["id"]: m for m in list_body["models"]}
    assert by_id["001"]["thumbnail_url"] == "/api/files/001/images/Dragon.png"

    audit = c.get("/api/admin/audit", headers=_hdrs(token)).json()
    actions = [e["action"] for e in audit["events"]]
    assert "admin.thumbnail.set" in actions


def test_delete_happy_path_clears_and_audits(client):
    c, token, _uid = client
    c.put(
        "/api/admin/models/001/thumbnail", json={"path": "images/Dragon.png"}, headers=_hdrs(token)
    )
    resp = c.delete("/api/admin/models/001/thumbnail", headers=_hdrs(token))
    assert resp.status_code == 204

    audit = c.get("/api/admin/audit", headers=_hdrs(token)).json()
    actions = [e["action"] for e in audit["events"]]
    assert "admin.thumbnail.cleared" in actions


def test_delete_idempotent_no_audit_on_noop(client):
    c, token, _uid = client
    audit_before = c.get("/api/admin/audit", headers=_hdrs(token)).json()
    n_before = sum(1 for e in audit_before["events"] if e["action"] == "admin.thumbnail.cleared")

    resp = c.delete("/api/admin/models/001/thumbnail", headers=_hdrs(token))
    assert resp.status_code == 204

    audit_after = c.get("/api/admin/audit", headers=_hdrs(token)).json()
    n_after = sum(1 for e in audit_after["events"] if e["action"] == "admin.thumbnail.cleared")
    assert n_after == n_before


def test_refresh_purges_orphan_overrides(client):
    c, token, user_id = client
    # Set an override that points at a real file.
    c.put(
        "/api/admin/models/001/thumbnail",
        json={"path": "images/Dragon.png"},
        headers=_hdrs(token),
    )

    # Bypass the PUT validator to plant an orphan: set a row directly via the
    # repo with a path that whitelists but resolves nowhere.
    repo = ThumbnailOverrideRepo(get_engine())
    repo.set(model_id="002", relative_path="prints/ghost.jpg", user_id=user_id)

    # Refresh — orphan should be purged with an audit event.
    resp = c.post("/api/admin/refresh-catalog", headers=_hdrs(token))
    assert resp.status_code == 200

    audit = c.get("/api/admin/audit", headers=_hdrs(token)).json()
    purged_events = [e for e in audit["events"] if e["action"] == "thumbnail.orphan_purged"]
    assert len(purged_events) >= 1
    assert any((e["after"] or {}).get("model_id") == "002" for e in purged_events)
    # The orphan row is gone.
    assert repo.get("002") is None
    # The legitimate override survives.
    assert repo.get("001") == "images/Dragon.png"
