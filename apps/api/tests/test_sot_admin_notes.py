"""Tests for SoT admin Note write endpoints (Slice 2C.3).

Covers:
  POST   /api/admin/models/{model_id}/notes  — create
  PATCH  /api/admin/notes/{note_id}          — update
  DELETE /api/admin/notes/{note_id}          — delete
"""

import uuid

from sqlmodel import Session, select

from app.core.auth.jwt import encode_token
from app.core.db.models import (
    AuditLog,
    Category,
    Model,
    ModelNote,
    NoteKind,
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
        email=f"admin-notes-{uuid.uuid4().hex[:6]}@test.local",
        display_name="Admin",
        role=UserRole.admin,
        password_hash="x",
    )
    session.add(u)
    session.flush()
    return u.id


def _seed_category(session: Session) -> uuid.UUID:
    cat = Category(slug=f"cat-notes-{uuid.uuid4().hex[:8]}", name_en="Test Cat")
    session.add(cat)
    session.flush()
    return cat.id


def _seed_model(session: Session, cat_id: uuid.UUID) -> uuid.UUID:
    m = Model(
        slug=f"m-notes-{uuid.uuid4().hex[:8]}",
        name_en="Test Model",
        category_id=cat_id,
    )
    session.add(m)
    session.flush()
    return m.id


def _seed_note(session: Session, model_id: uuid.UUID, author_id: uuid.UUID) -> uuid.UUID:
    note = ModelNote(
        model_id=model_id,
        kind=NoteKind.description,
        body="Initial body.",
        author_id=author_id,
    )
    session.add(note)
    session.flush()
    return note.id


# ---------------------------------------------------------------------------
# POST /api/admin/models/{model_id}/notes
# ---------------------------------------------------------------------------


def test_create_note_201(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    r = client.post(
        f"/api/admin/models/{model_id}/notes",
        json={"kind": "description", "body": "This is a note."},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["kind"] == "description"
    assert body["body"] == "This is a note."
    assert body["model_id"] == str(model_id)
    assert body["author_id"] == str(admin_id)
    assert "id" in body


def test_create_note_404_model(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    r = client.post(
        f"/api/admin/models/{uuid.uuid4()}/notes",
        json={"kind": "description", "body": "Note."},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 404


def test_create_note_audit(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    r = client.post(
        f"/api/admin/models/{model_id}/notes",
        json={"kind": "operational", "body": "Audit body."},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 201
    note_id = uuid.UUID(r.json()["id"])

    with Session(get_engine()) as s:
        logs = s.exec(
            select(AuditLog).where(
                AuditLog.action == "model_note.create",
                AuditLog.entity_id == note_id,
            )
        ).all()
    assert len(logs) == 1
    assert logs[0].entity_type == "model_note"


# ---------------------------------------------------------------------------
# PATCH /api/admin/notes/{note_id}
# ---------------------------------------------------------------------------


def test_patch_note_200(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        note_id = _seed_note(s, model_id, admin_id)
        s.commit()

    r = client.patch(
        f"/api/admin/notes/{note_id}",
        json={"body": "Updated body."},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 200, r.text
    assert r.json()["body"] == "Updated body."


def test_patch_note_404(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    r = client.patch(
        f"/api/admin/notes/{uuid.uuid4()}",
        json={"body": "X"},
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 404


def test_patch_note_audit(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        note_id = _seed_note(s, model_id, admin_id)
        s.commit()

    client.patch(
        f"/api/admin/notes/{note_id}",
        json={"body": "Patched body."},
        headers=_hdrs(_admin_token(admin_id)),
    )

    with Session(get_engine()) as s:
        logs = s.exec(
            select(AuditLog).where(
                AuditLog.action == "model_note.update",
                AuditLog.entity_id == note_id,
            )
        ).all()
    assert len(logs) >= 1
    assert "Patched body." in (logs[-1].after_json or "")


# ---------------------------------------------------------------------------
# DELETE /api/admin/notes/{note_id}
# ---------------------------------------------------------------------------


def test_delete_note_204(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        note_id = _seed_note(s, model_id, admin_id)
        s.commit()

    r = client.delete(
        f"/api/admin/notes/{note_id}",
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 204

    with Session(get_engine()) as s:
        assert s.get(ModelNote, note_id) is None


def test_delete_note_404(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    r = client.delete(
        f"/api/admin/notes/{uuid.uuid4()}",
        headers=_hdrs(_admin_token(admin_id)),
    )
    assert r.status_code == 404
