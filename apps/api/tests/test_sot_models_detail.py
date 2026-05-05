import uuid

from sqlmodel import Session

from app.core.db.models import (
    Category,
    ExternalSource,
    Model,
    ModelExternalLink,
    ModelFile,
    ModelFileKind,
    ModelNote,
    ModelPrint,
    ModelTag,
    NoteKind,
    Tag,
)
from app.core.db.session import get_engine


def test_get_model_detail_404_for_unknown_id(client):
    r = client.get(f"/api/models/{uuid.uuid4()}")
    assert r.status_code == 404


def test_get_model_detail_full_embed(client):
    engine = get_engine()
    with Session(engine) as s:
        cat = Category(slug="cat-5-decorum", name_en="Decorum")
        s.add(cat)
        s.commit()
        s.refresh(cat)
        cat_slug = cat.slug

        tag = Tag(slug="tag-5-dragon", name_en="Dragon", name_pl="Smok")
        s.add(tag)
        s.commit()
        s.refresh(tag)

        m = Model(
            slug="model-5-detail",
            name_en="Detail Model",
            name_pl="Model Detal",
            category_id=cat.id,
        )
        s.add(m)
        s.commit()
        s.refresh(m)
        model_id = m.id

        s.add(ModelTag(model_id=model_id, tag_id=tag.id))

        f = ModelFile(
            model_id=model_id,
            kind=ModelFileKind.stl,
            original_name="dragon.stl",
            storage_path=f"models/{model_id}/files/abc.stl",
            sha256="a" * 64,
            size_bytes=1024,
            mime_type="model/stl",
        )
        s.add(f)
        s.add(ModelNote(model_id=model_id, kind=NoteKind.description, body="hello"))
        s.add(ModelPrint(model_id=model_id, note="first print", photo_file_id=None))
        s.add(
            ModelExternalLink(
                model_id=model_id,
                source=ExternalSource.printables,
                external_id="12345",
                url="https://example.com/12345",
            )
        )
        s.commit()

    r = client.get(f"/api/models/{model_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["slug"] == "model-5-detail"
    assert body["category"]["slug"] == cat_slug
    assert {t["slug"] for t in body["tags"]} == {"tag-5-dragon"}
    assert len(body["files"]) == 1
    assert body["files"][0]["kind"] == "stl"
    assert len(body["notes"]) == 1
    assert body["notes"][0]["kind"] == "description"
    assert len(body["prints"]) == 1
    assert len(body["external_links"]) == 1
    assert body["external_links"][0]["source"] == "printables"


def test_get_model_detail_404_for_soft_deleted_by_default(client):
    import datetime

    engine = get_engine()
    with Session(engine) as s:
        cat = Category(slug="cat-5-sd-cat", name_en="X")
        s.add(cat)
        s.commit()
        s.refresh(cat)
        m = Model(slug="model-5-sd", name_en="SD", category_id=cat.id)
        m.deleted_at = datetime.datetime.now(datetime.UTC)
        s.add(m)
        s.commit()
        s.refresh(m)
        model_id = m.id

    r = client.get(f"/api/models/{model_id}")
    assert r.status_code == 404


def test_get_model_detail_include_deleted_returns_soft_deleted(client):
    import datetime

    engine = get_engine()
    with Session(engine) as s:
        cat = Category(slug="cat-5-incl-cat", name_en="X")
        s.add(cat)
        s.commit()
        s.refresh(cat)
        m = Model(slug="model-5-incl", name_en="incl", category_id=cat.id)
        m.deleted_at = datetime.datetime.now(datetime.UTC)
        s.add(m)
        s.commit()
        s.refresh(m)
        model_id = m.id

    r = client.get(f"/api/models/{model_id}?include_deleted=true")
    assert r.status_code == 200
    assert r.json()["slug"] == "model-5-incl"


def test_get_model_detail_files_ordered_by_position(client):
    engine = get_engine()
    with Session(engine) as s:
        cat = Category(slug="cat-5-pos-order", name_en="Pos")
        s.add(cat)
        s.commit()
        s.refresh(cat)

        m = Model(slug="model-5-pos-order", name_en="Pos", category_id=cat.id)
        s.add(m)
        s.commit()
        s.refresh(m)
        model_id = m.id

        # Insert in upload-time (created_at) order: render first, then phone
        # photos. Then assign positions so phone photos come first — this is
        # what the admin Photos drag-and-drop produces.
        render = ModelFile(
            model_id=model_id,
            kind=ModelFileKind.image,
            original_name="iso-render.png",
            storage_path=f"models/{model_id}/files/iso.png",
            sha256="r" * 64,
            size_bytes=1,
            mime_type="image/png",
            position=2,
        )
        s.add(render)
        s.commit()
        phone_a = ModelFile(
            model_id=model_id,
            kind=ModelFileKind.image,
            original_name="phone-a.jpg",
            storage_path=f"models/{model_id}/files/a.jpg",
            sha256="a" * 64,
            size_bytes=1,
            mime_type="image/jpeg",
            position=0,
        )
        s.add(phone_a)
        s.commit()
        phone_b = ModelFile(
            model_id=model_id,
            kind=ModelFileKind.image,
            original_name="phone-b.jpg",
            storage_path=f"models/{model_id}/files/b.jpg",
            sha256="b" * 64,
            size_bytes=1,
            mime_type="image/jpeg",
            position=1,
        )
        s.add(phone_b)
        # An stl with NULL position must keep falling back to created_at order.
        stl = ModelFile(
            model_id=model_id,
            kind=ModelFileKind.stl,
            original_name="thing.stl",
            storage_path=f"models/{model_id}/files/thing.stl",
            sha256="c" * 64,
            size_bytes=1,
            mime_type="model/stl",
        )
        s.add(stl)
        s.commit()

    r = client.get(f"/api/models/{model_id}")
    assert r.status_code == 200
    names = [f["original_name"] for f in r.json()["files"]]
    # Position-sorted images first (admin order), then NULL-position files.
    assert names == ["phone-a.jpg", "phone-b.jpg", "iso-render.png", "thing.stl"]
