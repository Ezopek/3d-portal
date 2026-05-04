"""Tests for the SoT admin Model CRUD endpoints (Slice 2C.1).

All tests use the shared `client` fixture from conftest (session-scoped
SQLite DB) and seed their own data with unique slugs to avoid cross-test
collisions.
"""

import datetime
import uuid

from sqlmodel import Session, select

from app.core.auth.jwt import encode_token
from app.core.db.models import (
    AuditLog,
    Category,
    Model,
    ModelFile,
    ModelFileKind,
    User,
    UserRole,
)
from app.core.db.session import get_engine

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

JWT_SECRET = "test-secret-not-real"


def _hdrs(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _admin_token(user_id: uuid.UUID) -> str:
    return encode_token(subject=str(user_id), role="admin", secret=JWT_SECRET, ttl_minutes=30)


def _agent_token(user_id: uuid.UUID) -> str:
    return encode_token(subject=str(user_id), role="agent", secret=JWT_SECRET, ttl_minutes=30)


def _member_token(user_id: uuid.UUID) -> str:
    return encode_token(subject=str(user_id), role="member", secret=JWT_SECRET, ttl_minutes=30)


def _seed_admin(session: Session) -> uuid.UUID:
    u = User(
        email=f"admin-{uuid.uuid4().hex[:6]}@test.local",
        display_name="Admin",
        role=UserRole.admin,
        password_hash="x",
    )
    session.add(u)
    session.flush()
    return u.id


def _seed_agent(session: Session) -> uuid.UUID:
    u = User(
        email=f"agent-{uuid.uuid4().hex[:6]}@test.local",
        display_name="Agent",
        role=UserRole.agent,
        password_hash="x",
    )
    session.add(u)
    session.flush()
    return u.id


def _seed_member(session: Session) -> uuid.UUID:
    u = User(
        email=f"member-{uuid.uuid4().hex[:6]}@test.local",
        display_name="Member",
        role=UserRole.member,
        password_hash="x",
    )
    session.add(u)
    session.flush()
    return u.id


def _seed_category(session: Session) -> uuid.UUID:
    cat = Category(slug=f"test-cat-{uuid.uuid4().hex[:8]}", name_en="Test Category")
    session.add(cat)
    session.flush()
    return cat.id


def _seed_model(session: Session, cat_id: uuid.UUID, *, slug_prefix: str = "m") -> uuid.UUID:
    m = Model(
        slug=f"{slug_prefix}-{uuid.uuid4().hex[:8]}",
        name_en="Test Model",
        category_id=cat_id,
    )
    session.add(m)
    session.flush()
    return m.id


def _seed_model_with_slug(session: Session, cat_id: uuid.UUID, slug: str) -> uuid.UUID:
    m = Model(slug=slug, name_en="Test Model", category_id=cat_id)
    session.add(m)
    session.flush()
    return m.id


# ---------------------------------------------------------------------------
# POST /api/admin/models — create
# ---------------------------------------------------------------------------


def test_create_model_201(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        s.commit()

    r = client.post(
        "/api/admin/models",
        json={"name_en": "My Model", "category_id": str(cat_id)},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name_en"] == "My Model"
    assert body["category_id"] == str(cat_id)
    assert body["tags"] == []
    assert body["files"] == []

    # Verify in DB
    with Session(engine) as s:
        m = s.exec(select(Model).where(Model.id == uuid.UUID(body["id"]))).first()
        assert m is not None
        assert m.name_en == "My Model"


def test_create_model_400_unknown_category(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    r = client.post(
        "/api/admin/models",
        json={"name_en": "Orphan", "category_id": str(uuid.uuid4())},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 400
    assert "category" in r.json()["detail"].lower()


def test_create_model_409_slug_collision(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        existing_id = _seed_model(s, cat_id, slug_prefix="collide")
        s.commit()

    # Fetch the slug from DB
    with Session(engine) as s:
        m = s.get(Model, existing_id)
        existing_slug = m.slug

    r = client.post(
        "/api/admin/models",
        json={"name_en": "Dupe", "category_id": str(cat_id), "slug": existing_slug},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 409


def test_create_model_auto_slug(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        s.commit()

    r = client.post(
        "/api/admin/models",
        json={"name_en": "Auto Slug Model", "category_id": str(cat_id)},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 201
    body = r.json()
    # Slug derived from name_en — should contain "auto"
    assert "auto" in body["slug"]


def test_create_model_writes_audit_log(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        s.commit()

    r = client.post(
        "/api/admin/models",
        json={"name_en": "Audit Create", "category_id": str(cat_id)},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 201
    model_id = uuid.UUID(r.json()["id"])

    with Session(engine) as s:
        logs = s.exec(
            select(AuditLog).where(
                AuditLog.action == "model.create",
                AuditLog.entity_id == model_id,
            )
        ).all()
    assert len(logs) == 1
    assert logs[0].actor_user_id == admin_id


# ---------------------------------------------------------------------------
# PATCH /api/admin/models/{model_id}
# ---------------------------------------------------------------------------


def test_patch_model_200(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    r = client.patch(
        f"/api/admin/models/{model_id}",
        json={"name_en": "Patched Name"},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 200
    assert r.json()["name_en"] == "Patched Name"


def test_patch_model_404_unknown(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    r = client.patch(
        f"/api/admin/models/{uuid.uuid4()}",
        json={"name_en": "X"},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 404


def test_patch_model_404_soft_deleted(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        m = s.get(Model, model_id)
        m.deleted_at = datetime.datetime.now(datetime.UTC)
        s.add(m)
        s.commit()

    r = client.patch(
        f"/api/admin/models/{model_id}",
        json={"name_en": "Ghost"},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 404


def test_patch_model_409_slug_collision(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        m1_id = _seed_model(s, cat_id)
        m2_id = _seed_model(s, cat_id)
        s.commit()

    with Session(engine) as s:
        m1 = s.get(Model, m1_id)
        taken_slug = m1.slug

    r = client.patch(
        f"/api/admin/models/{m2_id}",
        json={"slug": taken_slug},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 409


def test_patch_model_writes_audit_log(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    r = client.patch(
        f"/api/admin/models/{model_id}",
        json={"name_en": "Updated Name"},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 200

    with Session(engine) as s:
        logs = s.exec(
            select(AuditLog).where(
                AuditLog.action == "model.update",
                AuditLog.entity_id == model_id,
            )
        ).all()
    assert len(logs) >= 1
    log = logs[-1]
    assert "name_en" in (log.before_json or "")
    assert "Updated Name" in (log.after_json or "")


# ---------------------------------------------------------------------------
# DELETE /api/admin/models/{model_id} — soft delete
# ---------------------------------------------------------------------------


def test_soft_delete_200(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    r = client.delete(
        f"/api/admin/models/{model_id}",
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 200

    with Session(engine) as s:
        m = s.get(Model, model_id)
        assert m is not None
        assert m.deleted_at is not None


def test_soft_delete_idempotent(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    r1 = client.delete(f"/api/admin/models/{model_id}", headers=_hdrs(_admin_token(admin_id)))
    assert r1.status_code == 200
    r2 = client.delete(f"/api/admin/models/{model_id}", headers=_hdrs(_admin_token(admin_id)))
    assert r2.status_code == 200


def test_soft_delete_writes_audit_log(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    r = client.delete(f"/api/admin/models/{model_id}", headers=_hdrs(_admin_token(admin_id)))
    assert r.status_code == 200

    with Session(engine) as s:
        logs = s.exec(
            select(AuditLog).where(
                AuditLog.action == "model.delete",
                AuditLog.entity_id == model_id,
            )
        ).all()
    assert len(logs) >= 1


# ---------------------------------------------------------------------------
# POST /api/admin/models/{model_id}/restore
# ---------------------------------------------------------------------------


def test_restore_200(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        m = s.get(Model, model_id)
        m.deleted_at = datetime.datetime.now(datetime.UTC)
        s.add(m)
        s.commit()

    r = client.post(
        f"/api/admin/models/{model_id}/restore",
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 200
    assert r.json()["deleted_at"] is None

    with Session(engine) as s:
        m = s.get(Model, model_id)
        assert m is not None
        assert m.deleted_at is None


def test_restore_writes_audit_log(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        m = s.get(Model, model_id)
        m.deleted_at = datetime.datetime.now(datetime.UTC)
        s.add(m)
        s.commit()

    r = client.post(
        f"/api/admin/models/{model_id}/restore",
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 200

    with Session(engine) as s:
        logs = s.exec(
            select(AuditLog).where(
                AuditLog.action == "model.restore",
                AuditLog.entity_id == model_id,
            )
        ).all()
    assert len(logs) >= 1


# ---------------------------------------------------------------------------
# DELETE /api/admin/models/{model_id}?hard=true
# ---------------------------------------------------------------------------


def test_hard_delete_admin_200(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    r = client.delete(
        f"/api/admin/models/{model_id}?hard=true",
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 200

    with Session(engine) as s:
        m = s.get(Model, model_id)
        assert m is None


def test_hard_delete_agent_403(client):
    engine = get_engine()
    with Session(engine) as s:
        agent_id = _seed_agent(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    r = client.delete(
        f"/api/admin/models/{model_id}?hard=true",
        headers=_hdrs(_agent_token(agent_id)),
    )
    assert r.status_code == 403


def test_hard_delete_writes_audit_log_with_snapshot(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        m = s.get(Model, model_id)
        m.name_en = "Snapshot Model"
        s.add(m)
        s.commit()

    r = client.delete(
        f"/api/admin/models/{model_id}?hard=true",
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 200

    with Session(engine) as s:
        logs = s.exec(select(AuditLog).where(AuditLog.action == "model.hard_delete")).all()

    # Find the log for this model (it's gone from DB but audit_log persists)
    matching = [ll for ll in logs if ll.before_json and "Snapshot Model" in ll.before_json]
    assert len(matching) >= 1
    log = matching[0]
    assert log.before_json is not None
    assert "name_en" in log.before_json
    assert log.after_json is None


def test_hard_delete_cleans_storage_files(client):
    """Files in portal_content_dir are removed after hard delete."""
    from app.core.config import get_settings

    settings = get_settings()
    content_dir = settings.portal_content_dir

    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)

        storage_path = f"test-models/{model_id}/file-{uuid.uuid4().hex[:6]}.stl"
        full_path = content_dir / storage_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(b"STL content")

        f = ModelFile(
            model_id=model_id,
            kind=ModelFileKind.stl,
            original_name="file.stl",
            storage_path=storage_path,
            sha256=uuid.uuid4().hex * 2,  # 32-hex * 2 = 64 chars
            size_bytes=11,
            mime_type="model/stl",
        )
        s.add(f)
        s.commit()

    assert full_path.is_file()

    r = client.delete(
        f"/api/admin/models/{model_id}?hard=true",
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 200
    assert not full_path.exists()


# ---------------------------------------------------------------------------
# PUT /api/admin/models/{model_id}/thumbnail
# ---------------------------------------------------------------------------


def test_set_thumbnail_200(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)

        f = ModelFile(
            model_id=model_id,
            kind=ModelFileKind.image,
            original_name="thumb.png",
            storage_path=f"models/{model_id}/thumb-{uuid.uuid4().hex}.png",
            sha256="c" * 64,
            size_bytes=512,
            mime_type="image/png",
        )
        s.add(f)
        s.flush()
        file_id = f.id
        s.commit()

    r = client.put(
        f"/api/admin/models/{model_id}/thumbnail",
        json={"file_id": str(file_id)},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 200
    assert r.json()["thumbnail_file_id"] == str(file_id)


def test_set_thumbnail_400_cross_model_file(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        m1_id = _seed_model(s, cat_id)
        m2_id = _seed_model(s, cat_id)

        f = ModelFile(
            model_id=m1_id,  # belongs to m1
            kind=ModelFileKind.image,
            original_name="thumb.png",
            storage_path=f"models/{m1_id}/cross-{uuid.uuid4().hex}.png",
            sha256="d" * 64,
            size_bytes=256,
            mime_type="image/png",
        )
        s.add(f)
        s.flush()
        file_id = f.id
        s.commit()

    r = client.put(
        f"/api/admin/models/{m2_id}/thumbnail",
        json={"file_id": str(file_id)},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 400
    assert "different model" in r.json()["detail"]


def test_set_thumbnail_400_unknown_file(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    r = client.put(
        f"/api/admin/models/{model_id}/thumbnail",
        json={"file_id": str(uuid.uuid4())},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 400


def test_set_thumbnail_writes_audit_log(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)

        f = ModelFile(
            model_id=model_id,
            kind=ModelFileKind.image,
            original_name="thumb2.png",
            storage_path=f"models/{model_id}/thumb2-{uuid.uuid4().hex}.png",
            sha256="e" * 64,
            size_bytes=256,
            mime_type="image/png",
        )
        s.add(f)
        s.flush()
        file_id = f.id
        s.commit()

    r = client.put(
        f"/api/admin/models/{model_id}/thumbnail",
        json={"file_id": str(file_id)},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 200

    with Session(engine) as s:
        logs = s.exec(
            select(AuditLog).where(
                AuditLog.action == "model.update",
                AuditLog.entity_id == model_id,
            )
        ).all()
    # Find the thumbnail log
    thumb_logs = [ll for ll in logs if ll.after_json and "thumbnail_file_id" in ll.after_json]
    assert len(thumb_logs) >= 1


# ---------------------------------------------------------------------------
# Auth checks
# ---------------------------------------------------------------------------


def test_unauthenticated_create_401(client):
    r = client.post(
        "/api/admin/models",
        json={"name_en": "X", "category_id": str(uuid.uuid4())},
    )
    assert r.status_code == 401


def test_member_role_create_403(client):
    engine = get_engine()
    with Session(engine) as s:
        member_id = _seed_member(s)
        s.commit()

    r = client.post(
        "/api/admin/models",
        json={"name_en": "X", "category_id": str(uuid.uuid4())},
        headers=_hdrs(_member_token(member_id)),
    )
    assert r.status_code == 403
