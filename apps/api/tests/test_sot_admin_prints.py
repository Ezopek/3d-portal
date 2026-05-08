"""Tests for SoT admin Print write endpoints (Slice 2C.3).

Covers:
  POST   /api/admin/models/{model_id}/prints   — create
  PATCH  /api/admin/prints/{print_id}          — update
  DELETE /api/admin/prints/{print_id}          — delete
"""

import hashlib
import uuid

from sqlmodel import Session, select

from app.core.auth.jwt import encode_token
from app.core.db.models import (
    AuditLog,
    Category,
    Model,
    ModelFile,
    ModelFileKind,
    ModelPrint,
    User,
    UserRole,
)
from app.core.db.session import get_engine

JWT_SECRET = "test-secret-not-real"




def _admin_token(user_id: uuid.UUID) -> str:
    return encode_token(subject=str(user_id), role="admin", secret=JWT_SECRET, ttl_minutes=30)


def _seed_admin(session: Session) -> uuid.UUID:
    u = User(
        email=f"admin-prints-{uuid.uuid4().hex[:6]}@test.local",
        display_name="Admin",
        role=UserRole.admin,
        password_hash="x",
    )
    session.add(u)
    session.flush()
    return u.id


def _seed_category(session: Session) -> uuid.UUID:
    cat = Category(slug=f"cat-prints-{uuid.uuid4().hex[:8]}", name_en="Test Cat")
    session.add(cat)
    session.flush()
    return cat.id


def _seed_model(session: Session, cat_id: uuid.UUID) -> uuid.UUID:
    m = Model(
        slug=f"m-prints-{uuid.uuid4().hex[:8]}",
        name_en="Test Model",
        category_id=cat_id,
    )
    session.add(m)
    session.flush()
    return m.id


def _seed_file(session: Session, model_id: uuid.UUID) -> uuid.UUID:
    content = uuid.uuid4().bytes
    sha256 = hashlib.sha256(content).hexdigest()
    f = ModelFile(
        model_id=model_id,
        kind=ModelFileKind.image,
        original_name="photo.png",
        storage_path=f"models/{model_id}/files/{uuid.uuid4().hex}.png",
        sha256=sha256,
        size_bytes=len(content),
        mime_type="image/png",
    )
    session.add(f)
    session.flush()
    return f.id


def _seed_print(session: Session, model_id: uuid.UUID) -> uuid.UUID:
    pr = ModelPrint(model_id=model_id, note="Initial note.")
    session.add(pr)
    session.flush()
    return pr.id


# ---------------------------------------------------------------------------
# POST /api/admin/models/{model_id}/prints
# ---------------------------------------------------------------------------


def test_create_print_201(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(
        f"/api/admin/models/{model_id}/prints",
        json={"printed_at": "2024-03-01", "note": "Looks great!"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["model_id"] == str(model_id)
    assert body["printed_at"] == "2024-03-01"
    assert body["note"] == "Looks great!"
    assert "id" in body


def test_create_print_flat_path_is_not_mounted(client):
    """Locks the canonical URL: there is no top-level /api/admin/prints POST.

    The frontend used to send to this path and got 404 in production. If that
    ever silently starts working again, this test will fail and force an
    intentional decision about which shape the API exposes.
    """
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(
        "/api/admin/prints",
        json={"model_id": str(model_id)},
    )
    assert r.status_code == 404


def test_create_print_minimal(client):
    """Minimal payload — no printed_at, no note, no photo."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(
        f"/api/admin/models/{model_id}/prints",
        json={},
    )
    assert r.status_code == 201
    assert r.json()["model_id"] == str(model_id)


def test_create_print_with_photo(client):
    """photo_file_id that belongs to the model is accepted."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        file_id = _seed_file(s, model_id)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(
        f"/api/admin/models/{model_id}/prints",
        json={"photo_file_id": str(file_id)},
    )
    assert r.status_code == 201
    assert r.json()["photo_file_id"] == str(file_id)


def test_create_print_400_cross_model_photo(client):
    """photo_file_id belonging to another model → 400."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        other_model_id = _seed_model(s, cat_id)
        file_id = _seed_file(s, other_model_id)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(
        f"/api/admin/models/{model_id}/prints",
        json={"photo_file_id": str(file_id)},
    )
    assert r.status_code == 400


def test_create_print_404_model(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(
        f"/api/admin/models/{uuid.uuid4()}/prints",
        json={},
    )
    assert r.status_code == 404


def test_create_print_audit(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(
        f"/api/admin/models/{model_id}/prints",
        json={"note": "Audit note."},
    )
    assert r.status_code == 201
    print_id = uuid.UUID(r.json()["id"])

    with Session(get_engine()) as s:
        logs = s.exec(
            select(AuditLog).where(
                AuditLog.action == "model_print.create",
                AuditLog.entity_id == print_id,
            )
        ).all()
    assert len(logs) == 1
    assert logs[0].entity_type == "model_print"


# ---------------------------------------------------------------------------
# PATCH /api/admin/prints/{print_id}
# ---------------------------------------------------------------------------


def test_patch_print_200(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        print_id = _seed_print(s, model_id)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.patch(
        f"/api/admin/prints/{print_id}",
        json={"note": "Updated note."},
    )
    assert r.status_code == 200, r.text
    assert r.json()["note"] == "Updated note."


def test_patch_print_404(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.patch(
        f"/api/admin/prints/{uuid.uuid4()}",
        json={"note": "X"},
    )
    assert r.status_code == 404


def test_patch_print_400_cross_model_photo(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        other_id = _seed_model(s, cat_id)
        print_id = _seed_print(s, model_id)
        other_file_id = _seed_file(s, other_id)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.patch(
        f"/api/admin/prints/{print_id}",
        json={"photo_file_id": str(other_file_id)},
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/admin/prints/{print_id}
# ---------------------------------------------------------------------------


def test_delete_print_204(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        print_id = _seed_print(s, model_id)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.delete(
        f"/api/admin/prints/{print_id}",
    )
    assert r.status_code == 204

    with Session(get_engine()) as s:
        assert s.get(ModelPrint, print_id) is None


def test_delete_print_404(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.delete(
        f"/api/admin/prints/{uuid.uuid4()}",
    )
    assert r.status_code == 404
