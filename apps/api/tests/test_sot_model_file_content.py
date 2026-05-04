"""Tests for GET /api/models/{model_id}/files/{file_id}/content."""

import uuid
from pathlib import Path

from sqlmodel import Session

from app.core.config import get_settings
from app.core.db.models import (
    Category,
    Model,
    ModelFile,
    ModelFileKind,
)
from app.core.db.session import get_engine


def _seed_model_with_file(session, *, slug, kind, original_name, content):
    cat = Category(slug=f"cat-content-{slug}", name_en="X")
    session.add(cat)
    session.commit()
    session.refresh(cat)
    m = Model(slug=slug, name_en=slug, category_id=cat.id)
    session.add(m)
    session.commit()
    session.refresh(m)

    file_uuid = uuid.uuid4()
    storage_root = get_settings().portal_content_dir
    storage_root.mkdir(parents=True, exist_ok=True)
    rel = f"models/{m.id}/files/{file_uuid}.bin"
    full = storage_root / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(content)

    f = ModelFile(
        id=file_uuid,
        model_id=m.id,
        kind=kind,
        original_name=original_name,
        storage_path=rel,
        sha256="0" * 64,
        size_bytes=len(content),
        mime_type="application/octet-stream",
    )
    session.add(f)
    session.commit()
    session.refresh(f)
    return m.id, f.id


def test_content_404_for_unknown_file(client):
    r = client.get(f"/api/models/{uuid.uuid4()}/files/{uuid.uuid4()}/content")
    assert r.status_code == 404


def test_content_404_when_file_belongs_to_different_model(client):
    """A real file_uuid must be scoped to its real model; cross-model lookup is 404."""
    engine = get_engine()
    with Session(engine) as s:
        _, file_id = _seed_model_with_file(
            s,
            slug="content-cross-model",
            kind=ModelFileKind.stl,
            original_name="x.stl",
            content=b"FAKE_STL",
        )

    other_model = uuid.uuid4()
    r = client.get(f"/api/models/{other_model}/files/{file_id}/content")
    assert r.status_code == 404


def test_content_streams_file_bytes(client):
    engine = get_engine()
    payload = b"FAKE_STL_PAYLOAD_AAA"
    with Session(engine) as s:
        model_id, file_id = _seed_model_with_file(
            s,
            slug="content-stream",
            kind=ModelFileKind.stl,
            original_name="dragon.stl",
            content=payload,
        )

    r = client.get(f"/api/models/{model_id}/files/{file_id}/content")
    assert r.status_code == 200
    assert r.content == payload
    assert "etag" in {k.lower() for k in r.headers}


def test_content_returns_304_on_matching_etag(client):
    engine = get_engine()
    with Session(engine) as s:
        model_id, file_id = _seed_model_with_file(
            s,
            slug="content-etag",
            kind=ModelFileKind.stl,
            original_name="e.stl",
            content=b"AAA",
        )

    r1 = client.get(f"/api/models/{model_id}/files/{file_id}/content")
    etag = r1.headers["etag"]
    r2 = client.get(
        f"/api/models/{model_id}/files/{file_id}/content",
        headers={"If-None-Match": etag},
    )
    assert r2.status_code == 304
    # 304 should be empty body
    assert r2.content == b""


def test_content_404_when_db_row_exists_but_file_missing_on_disk(client):
    """Integrity edge case: if DB has a row but the file is gone, 404 with
    a distinguishable message. Used for ops debugging."""
    engine = get_engine()
    with Session(engine) as s:
        model_id, file_id = _seed_model_with_file(
            s,
            slug="content-missing",
            kind=ModelFileKind.stl,
            original_name="m.stl",
            content=b"AAA",
        )
        # Delete the file on disk to simulate the integrity issue
        storage_root = get_settings().portal_content_dir
        rel = f"models/{model_id}/files/{file_id}.bin"
        Path(storage_root / rel).unlink(missing_ok=True)

    r = client.get(f"/api/models/{model_id}/files/{file_id}/content")
    assert r.status_code == 404


def test_content_download_flag_sets_filename_in_disposition(client):
    engine = get_engine()
    with Session(engine) as s:
        model_id, file_id = _seed_model_with_file(
            s,
            slug="content-dl",
            kind=ModelFileKind.stl,
            original_name="my-original.stl",
            content=b"AAA",
        )

    r_default = client.get(f"/api/models/{model_id}/files/{file_id}/content")
    r_download = client.get(f"/api/models/{model_id}/files/{file_id}/content?download=true")
    # Without ?download=true, no Content-Disposition with filename* expected;
    # with ?download=true, FileResponse adds attachment-style disposition.
    assert "content-disposition" not in {k.lower() for k in r_default.headers}
    assert "content-disposition" in {k.lower() for k in r_download.headers}
    assert "my-original.stl" in r_download.headers["content-disposition"]
