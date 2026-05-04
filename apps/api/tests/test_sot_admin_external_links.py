"""Tests for SoT admin ExternalLink write endpoints (Slice 2C.3).

Covers:
  POST   /api/admin/models/{model_id}/external-links   — create
  PATCH  /api/admin/external-links/{link_id}           — update
  DELETE /api/admin/external-links/{link_id}           — delete
"""

import uuid

from sqlmodel import Session, select

from app.core.auth.jwt import encode_token
from app.core.db.models import (
    AuditLog,
    Category,
    Model,
    ModelExternalLink,
    User,
    UserRole,
)
from app.core.db.session import get_engine

JWT_SECRET = "test-secret-not-real"


def _hdrs(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _admin_token(user_id: uuid.UUID) -> str:
    return encode_token(subject=str(user_id), role="admin", secret=JWT_SECRET, ttl_minutes=30)


def _seed_admin(session: Session) -> uuid.UUID:
    u = User(
        email=f"admin-links-{uuid.uuid4().hex[:6]}@test.local",
        display_name="Admin",
        role=UserRole.admin,
        password_hash="x",
    )
    session.add(u)
    session.flush()
    return u.id


def _seed_category(session: Session) -> uuid.UUID:
    cat = Category(slug=f"cat-links-{uuid.uuid4().hex[:8]}", name_en="Test Cat")
    session.add(cat)
    session.flush()
    return cat.id


def _seed_model(session: Session, cat_id: uuid.UUID) -> uuid.UUID:
    m = Model(
        slug=f"m-links-{uuid.uuid4().hex[:8]}",
        name_en="Test Model",
        category_id=cat_id,
    )
    session.add(m)
    session.flush()
    return m.id


def _seed_link(session: Session, model_id: uuid.UUID, *, source: str = "other") -> uuid.UUID:
    link = ModelExternalLink(
        model_id=model_id,
        source=source,
        url=f"https://example.com/{uuid.uuid4().hex}",
    )
    session.add(link)
    session.flush()
    return link.id


# ---------------------------------------------------------------------------
# POST /api/admin/models/{model_id}/external-links
# ---------------------------------------------------------------------------


def test_create_link_201(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    r = client.post(
        f"/api/admin/models/{model_id}/external-links",
        json={
            "source": "printables",
            "url": "https://printables.com/model/123",
            "external_id": "123",
        },
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["source"] == "printables"
    assert body["url"] == "https://printables.com/model/123"
    assert body["external_id"] == "123"
    assert body["model_id"] == str(model_id)


def test_create_link_409_source_conflict(client):
    """409 when model already has a link for the same source."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        _seed_link(s, model_id, source="printables")
        s.commit()

    r = client.post(
        f"/api/admin/models/{model_id}/external-links",
        json={"source": "printables", "url": "https://printables.com/model/999"},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 409


def test_create_link_404_model(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    r = client.post(
        f"/api/admin/models/{uuid.uuid4()}/external-links",
        json={"source": "other", "url": "https://example.com"},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 404


def test_create_link_audit(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    r = client.post(
        f"/api/admin/models/{model_id}/external-links",
        json={"source": "thingiverse", "url": "https://thingiverse.com/thing/1"},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 201
    link_id = uuid.UUID(r.json()["id"])

    with Session(get_engine()) as s:
        logs = s.exec(
            select(AuditLog).where(
                AuditLog.action == "model_external_link.create",
                AuditLog.entity_id == link_id,
            )
        ).all()
    assert len(logs) == 1
    assert logs[0].entity_type == "model_external_link"


# ---------------------------------------------------------------------------
# PATCH /api/admin/external-links/{link_id}
# ---------------------------------------------------------------------------


def test_patch_link_200(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        link_id = _seed_link(s, model_id)
        s.commit()

    new_url = "https://updated.example.com/xyz"
    r = client.patch(
        f"/api/admin/external-links/{link_id}",
        json={"url": new_url},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 200, r.text
    assert r.json()["url"] == new_url


def test_patch_link_404(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    r = client.patch(
        f"/api/admin/external-links/{uuid.uuid4()}",
        json={"url": "https://x.com"},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 404


def test_patch_link_409_source_conflict(client):
    """Changing source to one already present on same model → 409."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        link1_id = _seed_link(s, model_id, source="other")
        _seed_link(s, model_id, source="thingiverse")
        s.commit()

    r = client.patch(
        f"/api/admin/external-links/{link1_id}",
        json={"source": "thingiverse"},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 409


def test_patch_link_audit(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        link_id = _seed_link(s, model_id)
        s.commit()

    client.patch(
        f"/api/admin/external-links/{link_id}",
        json={"url": "https://audit-updated.example.com"},
        headers=_hdrs(_admin_token(admin_id)),
    )

    with Session(get_engine()) as s:
        logs = s.exec(
            select(AuditLog).where(
                AuditLog.action == "model_external_link.update",
                AuditLog.entity_id == link_id,
            )
        ).all()
    assert len(logs) >= 1


# ---------------------------------------------------------------------------
# DELETE /api/admin/external-links/{link_id}
# ---------------------------------------------------------------------------


def test_delete_link_204(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        link_id = _seed_link(s, model_id)
        s.commit()

    r = client.delete(
        f"/api/admin/external-links/{link_id}",
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 204

    with Session(get_engine()) as s:
        assert s.get(ModelExternalLink, link_id) is None


def test_delete_link_404(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    r = client.delete(
        f"/api/admin/external-links/{uuid.uuid4()}",
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 404
