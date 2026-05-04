import datetime
import uuid

import pytest
import sqlalchemy.exc
from sqlmodel import Session, select

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
    ModelTag,
    NoteKind,
    Tag,
)
from app.core.db.session import create_engine_for_url, init_schema


def test_model_source_enum_values():
    assert ModelSource.unknown.value == "unknown"
    assert ModelSource.printables.value == "printables"
    assert ModelSource.thangs.value == "thangs"
    assert ModelSource.makerworld.value == "makerworld"
    assert ModelSource.cults3d.value == "cults3d"
    assert ModelSource.thingiverse.value == "thingiverse"
    assert ModelSource.own.value == "own"
    assert ModelSource.other.value == "other"


def test_model_status_enum_values():
    assert {m.value for m in ModelStatus} == {
        "not_printed",
        "printed",
        "in_progress",
        "broken",
    }


def test_model_file_kind_enum_values():
    assert {m.value for m in ModelFileKind} == {
        "stl",
        "image",
        "print",
        "source",
        "archive_3mf",
    }


def test_external_source_enum_values():
    assert {m.value for m in ExternalSource} == {
        "printables",
        "thangs",
        "makerworld",
        "cults3d",
        "thingiverse",
        "other",
    }


def test_note_kind_enum_values():
    assert {m.value for m in NoteKind} == {
        "description",
        "operational",
        "ai_review",
        "other",
    }


@pytest.fixture()
def engine(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine_for_url(f"sqlite:///{db_path}")
    init_schema(engine)
    return engine


def test_category_basic_persist_and_query(engine):
    with Session(engine) as session:
        cat = Category(slug="decorum", name_en="Decorum")
        session.add(cat)
        session.commit()
        session.refresh(cat)

        assert isinstance(cat.id, uuid.UUID)
        assert isinstance(cat.created_at, datetime.datetime)
        assert isinstance(cat.updated_at, datetime.datetime)
        assert cat.parent_id is None
        assert cat.name_pl is None

        rows = session.exec(select(Category)).all()
        assert len(rows) == 1


def test_category_parent_child_relationship(engine):
    with Session(engine) as session:
        parent = Category(slug="drukarka_3d", name_en="3D Printer")
        session.add(parent)
        session.commit()
        session.refresh(parent)

        child = Category(parent_id=parent.id, slug="k1_max", name_en="K1 Max")
        session.add(child)
        session.commit()
        session.refresh(child)

        assert child.parent_id == parent.id


def test_category_slug_unique_per_parent(engine):
    with Session(engine) as session:
        a = Category(slug="accessories", name_en="A")
        b = Category(slug="accessories", name_en="B")
        session.add(a)
        session.add(b)
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            session.commit()


def test_category_same_slug_under_different_parents_allowed(engine):
    with Session(engine) as session:
        p1 = Category(slug="parent_a", name_en="A")
        p2 = Category(slug="parent_b", name_en="B")
        session.add_all([p1, p2])
        session.commit()
        session.refresh(p1)
        session.refresh(p2)

        c1 = Category(parent_id=p1.id, slug="accessories", name_en="A.acc")
        c2 = Category(parent_id=p2.id, slug="accessories", name_en="B.acc")
        session.add_all([c1, c2])
        session.commit()  # must NOT raise


def test_tag_basic_persist(engine):
    with Session(engine) as session:
        t = Tag(slug="dragon", name_en="Dragon", name_pl="Smok")
        session.add(t)
        session.commit()
        session.refresh(t)

        assert isinstance(t.id, uuid.UUID)
        assert t.slug == "dragon"
        assert t.name_pl == "Smok"


def test_tag_slug_unique_globally(engine):
    with Session(engine) as session:
        a = Tag(slug="dragon", name_en="A")
        b = Tag(slug="dragon", name_en="B")
        session.add_all([a, b])
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            session.commit()


def test_model_basic_persist(engine):
    with Session(engine) as session:
        cat = Category(slug="decorum", name_en="Decorum")
        session.add(cat)
        session.commit()
        session.refresh(cat)

        m = Model(
            slug="dragon-001",
            name_en="Dragon",
            category_id=cat.id,
        )
        session.add(m)
        session.commit()
        session.refresh(m)

        assert isinstance(m.id, uuid.UUID)
        assert m.source == ModelSource.unknown
        assert m.status == ModelStatus.not_printed
        assert m.deleted_at is None
        assert m.legacy_id is None
        assert m.rating is None


def test_model_legacy_id_unique(engine):
    with Session(engine) as session:
        cat = Category(slug="decorum", name_en="Decorum")
        session.add(cat)
        session.commit()
        session.refresh(cat)

        a = Model(slug="a-001", name_en="A", category_id=cat.id, legacy_id="001")
        b = Model(slug="b-001", name_en="B", category_id=cat.id, legacy_id="001")
        session.add_all([a, b])
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            session.commit()


def test_model_slug_unique(engine):
    with Session(engine) as session:
        cat = Category(slug="decorum", name_en="Decorum")
        session.add(cat)
        session.commit()
        session.refresh(cat)

        a = Model(slug="dup", name_en="A", category_id=cat.id)
        b = Model(slug="dup", name_en="B", category_id=cat.id)
        session.add_all([a, b])
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            session.commit()


def test_model_rating_check_constraint_rejects_out_of_range(engine):
    with Session(engine) as session:
        cat = Category(slug="decorum", name_en="Decorum")
        session.add(cat)
        session.commit()
        session.refresh(cat)

        m = Model(
            slug="bad-rating",
            name_en="Bad",
            category_id=cat.id,
            rating=6.0,
        )
        session.add(m)
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            session.commit()


def test_model_rating_accepts_float_in_range(engine):
    with Session(engine) as session:
        cat = Category(slug="decorum", name_en="Decorum")
        session.add(cat)
        session.commit()
        session.refresh(cat)

        m = Model(
            slug="good-rating",
            name_en="Good",
            category_id=cat.id,
            rating=4.3,
        )
        session.add(m)
        session.commit()
        session.refresh(m)
        assert m.rating == pytest.approx(4.3)


def test_model_category_restrict_on_delete(engine):
    with Session(engine) as session:
        cat = Category(slug="decorum", name_en="Decorum")
        session.add(cat)
        session.commit()
        session.refresh(cat)

        m = Model(slug="x", name_en="X", category_id=cat.id)
        session.add(m)
        session.commit()

        session.delete(cat)
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            session.commit()


def _make_model(session, slug="m1"):
    cat = Category(slug=f"cat-{slug}", name_en="C")
    session.add(cat)
    session.commit()
    session.refresh(cat)
    m = Model(slug=slug, name_en=slug, category_id=cat.id)
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


def test_model_file_basic_persist(engine):
    with Session(engine) as session:
        m = _make_model(session)
        f = ModelFile(
            model_id=m.id,
            kind=ModelFileKind.stl,
            original_name="dragon.stl",
            storage_path=f"models/{m.id}/files/abc.stl",
            sha256="a" * 64,
            size_bytes=1234,
            mime_type="model/stl",
        )
        session.add(f)
        session.commit()
        session.refresh(f)

        assert isinstance(f.id, uuid.UUID)
        assert f.kind == ModelFileKind.stl


def test_model_file_storage_path_unique(engine):
    with Session(engine) as session:
        m = _make_model(session)
        f1 = ModelFile(
            model_id=m.id,
            kind=ModelFileKind.stl,
            original_name="a.stl",
            storage_path="dup/path.stl",
            sha256="a" * 64,
            size_bytes=1,
            mime_type="model/stl",
        )
        f2 = ModelFile(
            model_id=m.id,
            kind=ModelFileKind.image,
            original_name="b.png",
            storage_path="dup/path.stl",
            sha256="b" * 64,
            size_bytes=1,
            mime_type="image/png",
        )
        session.add_all([f1, f2])
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            session.commit()


def test_model_file_unique_per_model_sha_kind(engine):
    with Session(engine) as session:
        m = _make_model(session)
        f1 = ModelFile(
            model_id=m.id,
            kind=ModelFileKind.stl,
            original_name="a.stl",
            storage_path="p1.stl",
            sha256="a" * 64,
            size_bytes=1,
            mime_type="model/stl",
        )
        f2 = ModelFile(
            model_id=m.id,
            kind=ModelFileKind.stl,
            original_name="b.stl",
            storage_path="p2.stl",
            sha256="a" * 64,
            size_bytes=1,
            mime_type="model/stl",
        )
        session.add_all([f1, f2])
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            session.commit()


def test_model_file_same_sha_different_kind_allowed(engine):
    with Session(engine) as session:
        m = _make_model(session)
        f1 = ModelFile(
            model_id=m.id,
            kind=ModelFileKind.stl,
            original_name="a.stl",
            storage_path="p1.stl",
            sha256="a" * 64,
            size_bytes=1,
            mime_type="model/stl",
        )
        f2 = ModelFile(
            model_id=m.id,
            kind=ModelFileKind.image,
            original_name="a.png",
            storage_path="p2.png",
            sha256="a" * 64,
            size_bytes=1,
            mime_type="image/png",
        )
        session.add_all([f1, f2])
        session.commit()  # must NOT raise


def test_model_file_cascade_on_model_delete(engine):
    with Session(engine) as session:
        m = _make_model(session)
        f = ModelFile(
            model_id=m.id,
            kind=ModelFileKind.stl,
            original_name="x.stl",
            storage_path="x.stl",
            sha256="c" * 64,
            size_bytes=1,
            mime_type="model/stl",
        )
        session.add(f)
        session.commit()

        session.delete(m)
        session.commit()

        rows = session.exec(select(ModelFile)).all()
        assert rows == []


def test_model_thumbnail_set_to_file(engine):
    with Session(engine) as session:
        m = _make_model(session, slug="m-thumb")
        f = ModelFile(
            model_id=m.id,
            kind=ModelFileKind.image,
            original_name="thumb.png",
            storage_path="thumb.png",
            sha256="t" * 64,
            size_bytes=10,
            mime_type="image/png",
        )
        session.add(f)
        session.commit()
        session.refresh(f)

        m.thumbnail_file_id = f.id
        session.add(m)
        session.commit()
        session.refresh(m)

        assert m.thumbnail_file_id == f.id


def test_model_thumbnail_set_null_on_file_delete(engine):
    with Session(engine) as session:
        m = _make_model(session, slug="m-null")
        f = ModelFile(
            model_id=m.id,
            kind=ModelFileKind.image,
            original_name="t.png",
            storage_path="t.png",
            sha256="n" * 64,
            size_bytes=10,
            mime_type="image/png",
        )
        session.add(f)
        session.commit()
        session.refresh(f)
        m.thumbnail_file_id = f.id
        session.add(m)
        session.commit()

        session.delete(f)
        session.commit()
        session.refresh(m)

        assert m.thumbnail_file_id is None


def test_model_tag_basic_persist(engine):
    with Session(engine) as session:
        m = _make_model(session, slug="m-tag")
        t = Tag(slug="dragon", name_en="Dragon")
        session.add(t)
        session.commit()
        session.refresh(t)

        link = ModelTag(model_id=m.id, tag_id=t.id)
        session.add(link)
        session.commit()

        rows = session.exec(select(ModelTag)).all()
        assert len(rows) == 1


def test_model_tag_composite_pk_prevents_duplicate(engine):
    with Session(engine) as session:
        m = _make_model(session, slug="m-tag-dup")
        t = Tag(slug="dragon", name_en="Dragon")
        session.add(t)
        session.commit()
        session.refresh(t)

        a = ModelTag(model_id=m.id, tag_id=t.id)
        b = ModelTag(model_id=m.id, tag_id=t.id)
        session.add(a)
        session.commit()
        session.add(b)
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            session.commit()


def test_model_tag_cascade_on_model_delete(engine):
    with Session(engine) as session:
        m = _make_model(session, slug="m-tag-cascade")
        t = Tag(slug="dragon", name_en="Dragon")
        session.add(t)
        session.commit()
        session.refresh(t)

        link = ModelTag(model_id=m.id, tag_id=t.id)
        session.add(link)
        session.commit()

        session.delete(m)
        session.commit()

        rows = session.exec(select(ModelTag)).all()
        assert rows == []


def test_model_tag_restrict_on_tag_delete_when_in_use(engine):
    with Session(engine) as session:
        m = _make_model(session, slug="m-tag-restrict")
        t = Tag(slug="dragon", name_en="Dragon")
        session.add(t)
        session.commit()
        session.refresh(t)

        link = ModelTag(model_id=m.id, tag_id=t.id)
        session.add(link)
        session.commit()

        session.delete(t)
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            session.commit()


def test_model_print_basic_persist(engine):
    with Session(engine) as session:
        m = _make_model(session, slug="m-print")
        p = ModelPrint(model_id=m.id, note="first print")
        session.add(p)
        session.commit()
        session.refresh(p)

        assert isinstance(p.id, uuid.UUID)
        assert p.photo_file_id is None
        assert p.printed_at is None


def test_model_print_photo_set_null_on_file_delete(engine):
    with Session(engine) as session:
        m = _make_model(session, slug="m-print-photo")
        f = ModelFile(
            model_id=m.id,
            kind=ModelFileKind.print,
            original_name="ph.jpg",
            storage_path="ph.jpg",
            sha256="p" * 64,
            size_bytes=10,
            mime_type="image/jpeg",
        )
        session.add(f)
        session.commit()
        session.refresh(f)

        p = ModelPrint(model_id=m.id, photo_file_id=f.id, note="ok")
        session.add(p)
        session.commit()

        session.delete(f)
        session.commit()
        session.refresh(p)
        assert p.photo_file_id is None


def test_model_print_cascade_on_model_delete(engine):
    with Session(engine) as session:
        m = _make_model(session, slug="m-print-cascade")
        p = ModelPrint(model_id=m.id, note="x")
        session.add(p)
        session.commit()

        session.delete(m)
        session.commit()

        rows = session.exec(select(ModelPrint)).all()
        assert rows == []


def test_external_link_basic_persist(engine):
    with Session(engine) as session:
        m = _make_model(session, slug="m-link")
        link = ModelExternalLink(
            model_id=m.id,
            source=ExternalSource.printables,
            external_id="12345",
            url="https://printables.com/model/12345",
        )
        session.add(link)
        session.commit()
        session.refresh(link)

        assert isinstance(link.id, uuid.UUID)
        assert link.external_id == "12345"


def test_external_link_unique_per_model_source(engine):
    with Session(engine) as session:
        m = _make_model(session, slug="m-link-dup")
        a = ModelExternalLink(
            model_id=m.id,
            source=ExternalSource.printables,
            url="https://example.com/a",
        )
        b = ModelExternalLink(
            model_id=m.id,
            source=ExternalSource.printables,
            url="https://example.com/b",
        )
        session.add_all([a, b])
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            session.commit()


def test_external_link_cascade_on_model_delete(engine):
    with Session(engine) as session:
        m = _make_model(session, slug="m-link-cascade")
        link = ModelExternalLink(
            model_id=m.id,
            source=ExternalSource.thangs,
            url="https://thangs.com/x",
        )
        session.add(link)
        session.commit()

        session.delete(m)
        session.commit()

        rows = session.exec(select(ModelExternalLink)).all()
        assert rows == []


def test_model_note_basic_persist(engine):
    with Session(engine) as session:
        m = _make_model(session, slug="m-note")
        n = ModelNote(
            model_id=m.id,
            kind=NoteKind.description,
            body="From Printables: a great dragon",
        )
        session.add(n)
        session.commit()
        session.refresh(n)

        assert isinstance(n.id, uuid.UUID)
        assert n.kind == NoteKind.description


def test_model_note_cascade_on_model_delete(engine):
    with Session(engine) as session:
        m = _make_model(session, slug="m-note-cascade")
        n = ModelNote(model_id=m.id, kind=NoteKind.operational, body="print at 220")
        session.add(n)
        session.commit()

        session.delete(m)
        session.commit()

        rows = session.exec(select(ModelNote)).all()
        assert rows == []


def test_model_note_does_not_yet_have_author_id():
    # Slice 1A intentionally omits author_id; it is added in Slice 1B
    # alongside the User UUID migration.
    assert "author_id" not in ModelNote.model_fields
