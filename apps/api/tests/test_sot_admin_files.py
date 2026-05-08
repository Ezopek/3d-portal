"""Tests for the SoT admin ModelFile CRUD endpoints (Slice 2C.2).

Covers:
  POST   /api/admin/models/{model_id}/files
  PATCH  /api/admin/models/{model_id}/files/{file_id}
  DELETE /api/admin/models/{model_id}/files/{file_id}
"""

import datetime
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
    User,
    UserRole,
)
from app.core.db.session import get_engine

# ---------------------------------------------------------------------------
# Helpers (mirrors test_sot_admin_models.py pattern)
# ---------------------------------------------------------------------------

JWT_SECRET = "test-secret-not-real"




def _admin_token(user_id: uuid.UUID) -> str:
    return encode_token(subject=str(user_id), role="admin", secret=JWT_SECRET, ttl_minutes=30)


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


def _seed_category(session: Session) -> uuid.UUID:
    cat = Category(slug=f"cat-{uuid.uuid4().hex[:8]}", name_en="Test Cat")
    session.add(cat)
    session.flush()
    return cat.id


def _seed_model(session: Session, cat_id: uuid.UUID, *, deleted: bool = False) -> uuid.UUID:
    m = Model(
        slug=f"m-{uuid.uuid4().hex[:8]}",
        name_en="Test Model",
        category_id=cat_id,
    )
    if deleted:
        m.deleted_at = datetime.datetime.now(datetime.UTC)
    session.add(m)
    session.flush()
    return m.id


def _seed_file(
    session: Session,
    model_id: uuid.UUID,
    *,
    kind: ModelFileKind = ModelFileKind.stl,
    content: bytes = b"STL\x00data",
    original_name: str = "model.stl",
    storage_suffix: str | None = None,
) -> tuple[uuid.UUID, str]:
    """Seed a ModelFile row without writing to disk. Returns (file_id, sha256)."""
    sha256 = hashlib.sha256(content).hexdigest()
    suffix = storage_suffix or uuid.uuid4().hex[:8]
    storage_path = f"models/{model_id}/files/seeded-{suffix}.stl"
    f = ModelFile(
        model_id=model_id,
        kind=kind,
        original_name=original_name,
        storage_path=storage_path,
        sha256=sha256,
        size_bytes=len(content),
        mime_type="model/stl",
    )
    session.add(f)
    session.flush()
    return f.id, sha256


def _multipart(
    content: bytes, filename: str = "upload.stl", kind: str = "stl"
) -> tuple[dict, dict]:
    """Return (files, data) kwargs for client.post."""
    return (
        {"file": (filename, content, "application/octet-stream")},
        {"kind": kind},
    )


# ---------------------------------------------------------------------------
# POST /api/admin/models/{model_id}/files — upload
# ---------------------------------------------------------------------------


def test_upload_201(client, tmp_path):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    content = b"solid test\nendsolid"
    files, data = _multipart(content, "part.stl", "stl")
    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(
        f"/api/admin/models/{model_id}/files",
        files=files,
        data=data,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["model_id"] == str(model_id)
    assert body["kind"] == "stl"
    assert body["original_name"] == "part.stl"
    assert body["mime_type"] == "model/stl"
    assert "id" in body

    # File should exist on disk
    from app.core.config import get_settings

    settings = get_settings()
    storage_path = body["storage_path"]
    full = settings.portal_content_dir / storage_path
    assert full.is_file(), f"Expected file at {full}"
    assert full.read_bytes() == content


def test_upload_404_unknown_model(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    files, data = _multipart(b"data", "f.stl", "stl")
    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(
        f"/api/admin/models/{uuid.uuid4()}/files",
        files=files,
        data=data,
    )
    assert r.status_code == 404


def test_upload_404_soft_deleted_model(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id, deleted=True)
        s.commit()

    files, data = _multipart(b"data", "f.stl", "stl")
    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(
        f"/api/admin/models/{model_id}/files",
        files=files,
        data=data,
    )
    assert r.status_code == 404


def test_upload_dedup_returns_200(client):
    """Uploading identical content + kind twice: first 201, second 200 with same file_id."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    content = b"unique-content-for-dedup-test"
    files, data = _multipart(content, "dup.stl", "stl")

    client.cookies.set("portal_access", _admin_token(admin_id))
    r1 = client.post(
        f"/api/admin/models/{model_id}/files",
        files=files,
        data=data,
    )
    assert r1.status_code == 201

    # Re-create files dict (httpx consumes it)
    files2, data2 = _multipart(content, "dup.stl", "stl")
    client.cookies.set("portal_access", _admin_token(admin_id))
    r2 = client.post(
        f"/api/admin/models/{model_id}/files",
        files=files2,
        data=data2,
    )
    assert r2.status_code == 200
    assert r2.json()["id"] == r1.json()["id"]


def test_upload_writes_audit_log(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    files, data = _multipart(b"audit-test-content", "a.stl", "stl")
    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(
        f"/api/admin/models/{model_id}/files",
        files=files,
        data=data,
    )
    assert r.status_code == 201
    file_id = uuid.UUID(r.json()["id"])

    with Session(engine) as s:
        logs = s.exec(
            select(AuditLog).where(
                AuditLog.action == "model_file.upload",
                AuditLog.entity_id == file_id,
            )
        ).all()
    assert len(logs) == 1
    assert logs[0].actor_user_id == admin_id
    assert logs[0].entity_type == "model_file"


def test_upload_sha256_computed(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    content = b"sha256-check-content"
    expected_sha = hashlib.sha256(content).hexdigest()
    files, data = _multipart(content, "check.stl", "stl")
    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(
        f"/api/admin/models/{model_id}/files",
        files=files,
        data=data,
    )
    assert r.status_code == 201
    assert r.json()["sha256"] == expected_sha


def test_upload_413_size_limit(client, monkeypatch):
    """_write_atomic must raise 413 when content exceeds the threshold."""
    import app.modules.sot.admin_service as svc

    # Lower the limit to 100 bytes for this test
    monkeypatch.setattr(svc, "_MAX_FILE_BYTES", 100)

    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    oversized = b"x" * 200  # 200 bytes > 100 byte limit
    files, data = _multipart(oversized, "big.stl", "stl")
    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(
        f"/api/admin/models/{model_id}/files",
        files=files,
        data=data,
    )
    assert r.status_code == 413


def test_upload_kind_stl_forces_mime_model_stl(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    files, data = _multipart(b"stl-content", "model.stl", "stl")
    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(
        f"/api/admin/models/{model_id}/files",
        files=files,
        data=data,
    )
    assert r.status_code == 201
    assert r.json()["mime_type"] == "model/stl"


# ---------------------------------------------------------------------------
# PATCH /api/admin/models/{model_id}/files/{file_id}
# ---------------------------------------------------------------------------


def test_patch_file_200(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        file_id, _ = _seed_file(s, model_id, kind=ModelFileKind.stl)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.patch(
        f"/api/admin/models/{model_id}/files/{file_id}",
        json={"original_name": "renamed.stl"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["original_name"] == "renamed.stl"

    # Audit log
    with Session(engine) as s:
        logs = s.exec(
            select(AuditLog).where(
                AuditLog.action == "model_file.update",
                AuditLog.entity_id == file_id,
            )
        ).all()
    assert len(logs) >= 1
    assert "renamed.stl" in (logs[-1].after_json or "")


def test_patch_file_404_unknown(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.patch(
        f"/api/admin/models/{model_id}/files/{uuid.uuid4()}",
        json={"original_name": "x.stl"},
    )
    assert r.status_code == 404


def test_patch_file_404_cross_model(client):
    """file_id belongs to a different model → 404."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        m1_id = _seed_model(s, cat_id)
        m2_id = _seed_model(s, cat_id)
        file_id, _ = _seed_file(s, m1_id)  # belongs to m1
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.patch(
        f"/api/admin/models/{m2_id}/files/{file_id}",  # wrong model
        json={"original_name": "cross.stl"},
    )
    assert r.status_code == 404


def test_patch_file_409_kind_change_unique_collision(client):
    """Two files with same sha256, different kind. Changing one's kind to match → 409."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)

        shared_content = b"shared-content-abc123"
        sha = hashlib.sha256(shared_content).hexdigest()

        # File A: kind=stl
        fa = ModelFile(
            model_id=model_id,
            kind=ModelFileKind.stl,
            original_name="a.stl",
            storage_path=f"models/{model_id}/files/a-{uuid.uuid4().hex}.stl",
            sha256=sha,
            size_bytes=len(shared_content),
            mime_type="model/stl",
        )
        session = s
        session.add(fa)
        session.flush()
        fa_id = fa.id

        # File B: kind=image (same sha256, different kind — allowed by UNIQUE)
        fb = ModelFile(
            model_id=model_id,
            kind=ModelFileKind.image,
            original_name="b.png",
            storage_path=f"models/{model_id}/files/b-{uuid.uuid4().hex}.png",
            sha256=sha,
            size_bytes=len(shared_content),
            mime_type="image/png",
        )
        session.add(fb)
        session.flush()
        s.commit()

    # PATCH fa's kind to "image" → would collide with fb (same model, sha256, kind=image)
    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.patch(
        f"/api/admin/models/{model_id}/files/{fa_id}",
        json={"kind": "image"},
    )
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# DELETE /api/admin/models/{model_id}/files/{file_id}
# ---------------------------------------------------------------------------


def test_delete_file_204(client):
    from app.core.config import get_settings

    settings = get_settings()

    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)

        content = b"delete-me"
        storage_rel = f"models/{model_id}/files/del-{uuid.uuid4().hex}.stl"
        full_path = settings.portal_content_dir / storage_rel
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)

        f = ModelFile(
            model_id=model_id,
            kind=ModelFileKind.stl,
            original_name="del.stl",
            storage_path=storage_rel,
            sha256=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
            mime_type="model/stl",
        )
        s.add(f)
        s.flush()
        file_id = f.id
        s.commit()

    assert full_path.is_file()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.delete(
        f"/api/admin/models/{model_id}/files/{file_id}",
    )
    assert r.status_code == 204

    # DB row gone
    with Session(engine) as s:
        assert s.get(ModelFile, file_id) is None

    # Disk file gone
    assert not full_path.exists()


def test_delete_file_writes_audit_log(client):
    from app.core.config import get_settings

    settings = get_settings()

    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)

        content = b"audit-delete"
        storage_rel = f"models/{model_id}/files/auddel-{uuid.uuid4().hex}.stl"
        full_path = settings.portal_content_dir / storage_rel
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)

        f = ModelFile(
            model_id=model_id,
            kind=ModelFileKind.stl,
            original_name="auddel.stl",
            storage_path=storage_rel,
            sha256=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
            mime_type="model/stl",
        )
        s.add(f)
        s.flush()
        file_id = f.id
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.delete(
        f"/api/admin/models/{model_id}/files/{file_id}",
    )
    assert r.status_code == 204

    with Session(engine) as s:
        logs = s.exec(
            select(AuditLog).where(
                AuditLog.action == "model_file.delete",
                AuditLog.entity_id == file_id,
            )
        ).all()
    assert len(logs) == 1
    assert logs[0].before_json is not None
    assert "sha256_prefix" in logs[0].before_json
    assert logs[0].after_json is None


def test_delete_file_404_cross_model(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        m1_id = _seed_model(s, cat_id)
        m2_id = _seed_model(s, cat_id)
        file_id, _ = _seed_file(s, m1_id)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.delete(
        f"/api/admin/models/{m2_id}/files/{file_id}",
    )
    assert r.status_code == 404


def test_delete_file_clears_thumbnail_pointer(client):
    """model.thumbnail_file_id = file_id; after DELETE the FK is SET NULL."""
    from app.core.config import get_settings

    settings = get_settings()

    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)

        content = b"thumb-content"
        storage_rel = f"models/{model_id}/files/thumb-{uuid.uuid4().hex}.png"
        full_path = settings.portal_content_dir / storage_rel
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)

        f = ModelFile(
            model_id=model_id,
            kind=ModelFileKind.image,
            original_name="thumb.png",
            storage_path=storage_rel,
            sha256=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
            mime_type="image/png",
        )
        s.add(f)
        s.flush()
        file_id = f.id

        # Set as thumbnail
        m = s.get(Model, model_id)
        m.thumbnail_file_id = file_id
        s.add(m)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.delete(
        f"/api/admin/models/{model_id}/files/{file_id}",
    )
    assert r.status_code == 204

    with Session(engine) as s:
        m = s.get(Model, model_id)
        assert m is not None
        assert m.thumbnail_file_id is None


# ---------------------------------------------------------------------------
# selected_for_render — admin-curated render selection
# ---------------------------------------------------------------------------


def test_upload_first_stl_is_selected_for_render(client):
    """First STL on a model auto-selects so worker has something to render."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    files, data = _multipart(b"first stl bytes", "first.stl", "stl")
    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(
        f"/api/admin/models/{model_id}/files",
        files=files,
        data=data,
    )
    assert r.status_code == 201, r.text
    assert r.json()["selected_for_render"] is True


def test_upload_second_stl_is_not_selected_for_render(client):
    """Subsequent STLs stay unselected — admin opts them in explicitly."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        s.commit()

    f1, d1 = _multipart(b"first", "a.stl", "stl")
    client.cookies.set("portal_access", _admin_token(admin_id))
    r1 = client.post(
        f"/api/admin/models/{model_id}/files",
        files=f1,
        data=d1,
    )
    assert r1.status_code == 201
    assert r1.json()["selected_for_render"] is True

    f2, d2 = _multipart(b"second", "b.stl", "stl")
    client.cookies.set("portal_access", _admin_token(admin_id))
    r2 = client.post(
        f"/api/admin/models/{model_id}/files",
        files=f2,
        data=d2,
    )
    assert r2.status_code == 201
    assert r2.json()["selected_for_render"] is False


def test_patch_file_selected_for_render_toggle(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        file_id, _ = _seed_file(s, model_id, kind=ModelFileKind.stl)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.patch(
        f"/api/admin/models/{model_id}/files/{file_id}",
        json={"selected_for_render": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["selected_for_render"] is True

    client.cookies.set("portal_access", _admin_token(admin_id))
    r2 = client.patch(
        f"/api/admin/models/{model_id}/files/{file_id}",
        json={"selected_for_render": False},
    )
    assert r2.status_code == 200
    assert r2.json()["selected_for_render"] is False


def test_patch_file_selected_for_render_rejected_on_non_stl(client):
    """Toggling the flag on a non-STL file returns 400 — flag is meaningless
    for photos/sources."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        model_id = _seed_model(s, cat_id)
        file_id, _ = _seed_file(
            s,
            model_id,
            kind=ModelFileKind.image,
            content=b"png-bytes",
            original_name="photo.png",
        )
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.patch(
        f"/api/admin/models/{model_id}/files/{file_id}",
        json={"selected_for_render": True},
    )
    assert r.status_code == 400
