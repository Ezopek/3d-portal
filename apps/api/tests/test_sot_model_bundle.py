"""Tests for GET /api/models/{model_id}/bundle — Initiative 10 Story 16.6.

Restores bulk-STL-download (ZIP) regression UX after the SoT cutover. The
old filesystem-based bundle endpoint (commit caf4d5a, May 2026) dropped
during the SoT migration; this test suite covers the new SoT-storage
implementation living at apps/api/app/modules/sot/router.py.
"""

import hashlib
import io
import uuid
import zipfile

import pytest
from sqlmodel import Session

from app.core.auth.cookies import ACCESS_COOKIE
from app.core.auth.jwt import encode_token
from app.core.config import get_settings
from app.core.db.models import Category, Model, ModelFile, ModelFileKind
from app.core.db.session import get_engine


@pytest.fixture(autouse=True)
def _default_admin_cookie(client):
    token = encode_token(
        subject=str(uuid.uuid4()),
        role="admin",
        secret="test-secret-not-real",
        ttl_minutes=30,
    )
    client.cookies.set(ACCESS_COOKIE, token)
    yield
    client.cookies.delete(ACCESS_COOKIE)


def _seed_model(session, slug: str, *, name_en: str = "model") -> uuid.UUID:
    cat = Category(slug=f"cat-bundle-{slug}", name_en="X")
    session.add(cat)
    session.commit()
    session.refresh(cat)
    m = Model(slug=slug, name_en=name_en, category_id=cat.id)
    session.add(m)
    session.commit()
    session.refresh(m)
    return m.id


def _seed_file(
    session,
    *,
    model_id: uuid.UUID,
    kind: ModelFileKind,
    original_name: str,
    content: bytes,
    position: int = 0,
) -> uuid.UUID:
    file_uuid = uuid.uuid4()
    storage_root = get_settings().portal_content_dir
    rel = f"models/{model_id}/files/{file_uuid}.bin"
    full = storage_root / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(content)
    f = ModelFile(
        id=file_uuid,
        model_id=model_id,
        kind=kind,
        original_name=original_name,
        storage_path=rel,
        sha256=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
        mime_type="application/octet-stream",
        position=position,
    )
    session.add(f)
    session.commit()
    return file_uuid


def test_bundle_404_when_model_does_not_exist(client):
    r = client.get(f"/api/models/{uuid.uuid4()}/bundle")
    assert r.status_code == 404


def test_bundle_404_when_model_has_no_printable_files(client):
    engine = get_engine()
    with Session(engine) as s:
        model_id = _seed_model(s, slug="bundle-no-printable", name_en="empty")
        # Seed only image kind — not a printable.
        _seed_file(
            s,
            model_id=model_id,
            kind=ModelFileKind.image,
            original_name="photo.jpg",
            content=b"jpg-stub",
        )
    r = client.get(f"/api/models/{model_id}/bundle")
    assert r.status_code == 404


def test_bundle_returns_zip_with_all_printable_kinds(client):
    """STL + source (STEP/F3D) + archive_3mf go into the bundle; image + print don't."""
    engine = get_engine()
    with Session(engine) as s:
        model_id = _seed_model(s, slug="bundle-multi", name_en="Dragon")
        _seed_file(
            s,
            model_id=model_id,
            kind=ModelFileKind.stl,
            original_name="dragon.stl",
            content=b"STL-bytes",
            position=0,
        )
        _seed_file(
            s,
            model_id=model_id,
            kind=ModelFileKind.source,
            original_name="dragon.step",
            content=b"STEP-bytes",
            position=1,
        )
        _seed_file(
            s,
            model_id=model_id,
            kind=ModelFileKind.archive_3mf,
            original_name="dragon.3mf",
            content=b"3MF-archive",
            position=2,
        )
        # Image + print are NOT in the bundle.
        _seed_file(
            s,
            model_id=model_id,
            kind=ModelFileKind.image,
            original_name="photo.jpg",
            content=b"jpg-stub",
        )

    r = client.get(f"/api/models/{model_id}/bundle")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    assert "attachment" in r.headers["content-disposition"].lower()
    # Filename derives from model.name_en sanitized
    assert "Dragon.zip" in r.headers["content-disposition"]

    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = sorted(zf.namelist())
    assert names == ["dragon.3mf", "dragon.step", "dragon.stl"]
    assert zf.read("dragon.stl") == b"STL-bytes"
    assert zf.read("dragon.step") == b"STEP-bytes"
    assert zf.read("dragon.3mf") == b"3MF-archive"


def test_bundle_deduplicates_archive_entries_on_name_collision(client):
    """Two STL rows with the same original_name get distinct archive names."""
    engine = get_engine()
    with Session(engine) as s:
        model_id = _seed_model(s, slug="bundle-dup", name_en="Twins")
        _seed_file(
            s,
            model_id=model_id,
            kind=ModelFileKind.stl,
            original_name="part.stl",
            content=b"v1-bytes",
            position=0,
        )
        _seed_file(
            s,
            model_id=model_id,
            kind=ModelFileKind.stl,
            original_name="part.stl",
            content=b"v2-bytes",
            position=1,
        )

    r = client.get(f"/api/models/{model_id}/bundle")
    assert r.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = sorted(zf.namelist())
    # Both entries present, second gets a numeric suffix before extension.
    assert "part.stl" in names
    assert any(n.startswith("part_") and n.endswith(".stl") for n in names)
    assert len(names) == 2


def test_bundle_sanitizes_path_traversal_in_original_name(client):
    """Codex P2 fix-up: ModelFile.original_name is untrusted (upload + admin
    patch). Reject `../evil.stl` style names — the bundle must contain only
    safe top-level filenames."""
    engine = get_engine()
    with Session(engine) as s:
        model_id = _seed_model(s, slug="bundle-traversal", name_en="Hostile")
        _seed_file(
            s,
            model_id=model_id,
            kind=ModelFileKind.stl,
            original_name="../../../etc/passwd.stl",
            content=b"hostile",
        )
        _seed_file(
            s,
            model_id=model_id,
            kind=ModelFileKind.stl,
            original_name="legit.stl",
            content=b"legit",
            position=1,
        )

    r = client.get(f"/api/models/{model_id}/bundle")
    assert r.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    for name in zf.namelist():
        assert ".." not in name, f"path-traversal sneaked through: {name}"
        assert not name.startswith("/"), f"absolute path: {name}"
        assert "/" not in name, f"directory separator: {name}"
        assert "\\" not in name, f"backslash separator: {name}"


def test_bundle_skips_soft_deleted_models(client):
    """Soft-deleted models surface 404 (consistent with other SoT GET endpoints)."""
    import datetime

    engine = get_engine()
    with Session(engine) as s:
        model_id = _seed_model(s, slug="bundle-soft-deleted", name_en="Ghost")
        _seed_file(
            s,
            model_id=model_id,
            kind=ModelFileKind.stl,
            original_name="ghost.stl",
            content=b"stl",
        )
        m = s.get(Model, model_id)
        m.deleted_at = datetime.datetime.now(datetime.UTC)
        s.add(m)
        s.commit()

    r = client.get(f"/api/models/{model_id}/bundle")
    assert r.status_code == 404


def test_bundle_404_when_db_row_exists_but_blob_missing(client):
    """Defense-in-depth: DB row references a file that doesn't exist on disk → 404."""
    import os

    engine = get_engine()
    with Session(engine) as s:
        model_id = _seed_model(s, slug="bundle-missing-blob", name_en="missing")
        file_id = _seed_file(
            s,
            model_id=model_id,
            kind=ModelFileKind.stl,
            original_name="ghost.stl",
            content=b"will-be-deleted",
        )

    storage_root = get_settings().portal_content_dir
    blob_path = storage_root / f"models/{model_id}/files/{file_id}.bin"
    os.unlink(blob_path)

    r = client.get(f"/api/models/{model_id}/bundle")
    assert r.status_code == 404


def test_bundle_requires_authentication(client):
    """Initiative 6 default-deny — anonymous request gets 401, not the ZIP."""
    engine = get_engine()
    with Session(engine) as s:
        model_id = _seed_model(s, slug="bundle-auth", name_en="locked")
        _seed_file(
            s,
            model_id=model_id,
            kind=ModelFileKind.stl,
            original_name="a.stl",
            content=b"bytes",
        )

    client.cookies.delete(ACCESS_COOKIE)
    r = client.get(f"/api/models/{model_id}/bundle")
    assert r.status_code == 401
