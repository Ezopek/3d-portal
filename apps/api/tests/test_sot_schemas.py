import uuid

import pytest
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
    ModelSource,
    ModelStatus,
    NoteKind,
    Tag,
)
from app.core.db.session import create_engine_for_url, init_schema
from app.modules.sot.schemas import (
    CategoryNode,
    CategoryTree,
    ExternalLinkRead,
    FileListResponse,
    ModelDetail,
    ModelFileRead,
    ModelListResponse,
    ModelSummary,
    NoteRead,
    PrintRead,
    TagRead,
)


@pytest.fixture()
def engine(tmp_path):
    db_path = tmp_path / "test.db"
    e = create_engine_for_url(f"sqlite:///{db_path}")
    init_schema(e)
    return e


def test_tag_read_from_orm(engine):
    with Session(engine) as session:
        t = Tag(slug="dragon", name_en="Dragon", name_pl="Smok")
        session.add(t)
        session.commit()
        session.refresh(t)
        schema = TagRead.model_validate(t)
        assert schema.slug == "dragon"
        assert schema.name_pl == "Smok"
        assert isinstance(schema.id, uuid.UUID)


def test_category_node_recursive_shape():
    """CategoryNode allows nested children at any depth."""
    leaf = CategoryNode(
        id=uuid.uuid4(),
        parent_id=uuid.uuid4(),
        slug="leaf",
        name_en="Leaf",
        name_pl=None,
        children=[],
    )
    parent = CategoryNode(
        id=uuid.uuid4(),
        parent_id=None,
        slug="parent",
        name_en="Parent",
        name_pl=None,
        children=[leaf],
    )
    tree = CategoryTree(roots=[parent])
    assert tree.roots[0].children[0].slug == "leaf"


def test_model_summary_from_orm_includes_tags(engine):
    with Session(engine) as session:
        cat = Category(slug="decorum", name_en="Decorum")
        session.add(cat)
        session.commit()
        session.refresh(cat)
        m = Model(
            slug="dragon-001",
            name_en="Dragon",
            name_pl="Smok",
            category_id=cat.id,
            source=ModelSource.printables,
            status=ModelStatus.printed,
            rating=4.5,
        )
        session.add(m)
        session.commit()
        session.refresh(m)

        schema = ModelSummary.model_validate(
            {
                **m.model_dump(),
                "tags": [],
                "gallery_file_ids": [],
                "image_count": 0,
            }
        )
        assert schema.slug == "dragon-001"
        assert schema.source == "printables"
        assert schema.status == "printed"
        assert schema.rating == 4.5
        assert schema.tags == []
        assert schema.gallery_file_ids == []
        assert schema.image_count == 0


def test_model_detail_from_orm_with_embeds(engine):
    with Session(engine) as session:
        cat = Category(slug="decorum", name_en="Decorum")
        session.add(cat)
        session.commit()
        session.refresh(cat)
        m = Model(
            slug="dragon-002",
            name_en="Dragon",
            category_id=cat.id,
        )
        session.add(m)
        session.commit()
        session.refresh(m)

        f = ModelFile(
            model_id=m.id,
            kind=ModelFileKind.stl,
            original_name="dragon.stl",
            storage_path=f"models/{m.id}/files/abc.stl",
            sha256="a" * 64,
            size_bytes=1024,
            mime_type="model/stl",
        )
        session.add(f)
        session.commit()
        session.refresh(f)

        n = ModelNote(model_id=m.id, kind=NoteKind.description, body="hello")
        session.add(n)
        session.commit()
        session.refresh(n)

        link = ModelExternalLink(
            model_id=m.id,
            source=ExternalSource.printables,
            external_id="12345",
            url="https://example.com/12345",
        )
        session.add(link)
        session.commit()
        session.refresh(link)

        p = ModelPrint(model_id=m.id, note="ok", photo_file_id=None)
        session.add(p)
        session.commit()
        session.refresh(p)

        # Refresh m and cat after multiple commits to avoid SQLAlchemy expiry
        session.refresh(m)
        session.refresh(cat)

        schema = ModelDetail.model_validate(
            {
                **m.model_dump(),
                "tags": [],
                "gallery_file_ids": [],
                "image_count": 0,
                "category": {
                    "id": cat.id,
                    "parent_id": cat.parent_id,
                    "slug": cat.slug,
                    "name_en": cat.name_en,
                    "name_pl": cat.name_pl,
                },
                "files": [ModelFileRead.model_validate(f)],
                "prints": [PrintRead.model_validate(p)],
                "notes": [NoteRead.model_validate(n)],
                "external_links": [ExternalLinkRead.model_validate(link)],
            }
        )
        assert schema.category.slug == "decorum"
        assert len(schema.files) == 1
        assert schema.files[0].kind == "stl"
        assert len(schema.notes) == 1
        assert schema.notes[0].kind == "description"
        assert len(schema.external_links) == 1
        assert schema.external_links[0].source == "printables"


def test_model_list_response_pagination_envelope():
    resp = ModelListResponse(
        items=[],
        total=0,
        offset=0,
        limit=50,
    )
    assert resp.items == []
    assert resp.total == 0
    assert resp.limit == 50


def test_file_list_response():
    resp = FileListResponse(items=[])
    assert resp.items == []
