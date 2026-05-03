import datetime
import uuid

import pytest
import sqlalchemy.exc
from sqlmodel import Session, select

from app.core.db.models import (
    Category,
    ExternalSource,
    Model,
    ModelFileKind,
    ModelSource,
    ModelStatus,
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
