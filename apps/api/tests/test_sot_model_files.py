import uuid

from sqlmodel import Session

from app.core.db.models import (
    Category,
    Model,
    ModelFile,
    ModelFileKind,
)
from app.core.db.session import get_engine


def _seed_model_with_files(session, slug, file_specs):
    cat = Category(slug=f"cat-6-{slug}", name_en="X")
    session.add(cat)
    session.commit()
    session.refresh(cat)
    m = Model(slug=slug, name_en=slug, category_id=cat.id)
    session.add(m)
    session.commit()
    session.refresh(m)
    for kind, name, sha in file_specs:
        f = ModelFile(
            model_id=m.id,
            kind=kind,
            original_name=name,
            storage_path=f"models/{m.id}/files/{name}",
            sha256=sha,
            size_bytes=1,
            mime_type="application/octet-stream",
        )
        session.add(f)
    session.commit()
    session.refresh(m)
    return m


def test_list_files_404_for_unknown_model(client):
    r = client.get(f"/api/models/{uuid.uuid4()}/files")
    assert r.status_code == 404


def test_list_files_returns_envelope_for_empty_model(client):
    engine = get_engine()
    with Session(engine) as s:
        m = _seed_model_with_files(s, "model-6-empty", [])
        model_id = m.id

    r = client.get(f"/api/models/{model_id}/files")
    assert r.status_code == 200
    assert r.json() == {"items": []}


def test_list_files_returns_all_files_for_seeded_model(client):
    engine = get_engine()
    with Session(engine) as s:
        m = _seed_model_with_files(
            s,
            "model-6-many",
            [
                (ModelFileKind.stl, "a.stl", "a" * 64),
                (ModelFileKind.image, "a.png", "b" * 64),
                (ModelFileKind.print, "first.jpg", "c" * 64),
            ],
        )
        model_id = m.id

    r = client.get(f"/api/models/{model_id}/files")
    body = r.json()
    assert len(body["items"]) == 3
    kinds = {f["kind"] for f in body["items"]}
    assert kinds == {"stl", "image", "print"}


def test_list_files_filter_by_kind(client):
    engine = get_engine()
    with Session(engine) as s:
        m = _seed_model_with_files(
            s,
            "model-6-kind",
            [
                (ModelFileKind.stl, "a.stl", "1" * 64),
                (ModelFileKind.image, "a.png", "2" * 64),
                (ModelFileKind.image, "b.png", "3" * 64),
            ],
        )
        model_id = m.id

    r = client.get(f"/api/models/{model_id}/files?kind=image")
    body = r.json()
    assert len(body["items"]) == 2
    assert all(f["kind"] == "image" for f in body["items"])
