"""TagGroup entity + Tag group membership — round-trip and SET NULL behavior.

Story 41.1 (additive ORM foundation for facet-tag taxonomy). Entity-only
test: constructs models directly against a fresh in-memory SQLite built from
the ORM (`SQLModel.metadata.create_all`), mirroring the self-contained style
of `test_refresh_token_model.py`. No HTTP/TestClient — no login needed.
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.db.models import Tag, TagGroup


@pytest.fixture
def engine():
    e = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    # SQLite does not enforce ON DELETE ... unless PRAGMA foreign_keys is ON.
    from sqlalchemy import event

    @event.listens_for(e, "connect")
    def _fk_pragma(dbapi_conn, _rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    SQLModel.metadata.create_all(e)
    yield e
    e.dispose()


def test_tag_group_round_trips(engine):
    group_id = uuid.uuid4()
    with Session(engine) as s:
        s.add(TagGroup(id=group_id, slug="material", name_en="Material"))
        s.commit()
    with Session(engine) as s:
        got = s.get(TagGroup, group_id)
        assert got is not None
        assert got.slug == "material"
        assert got.name_en == "Material"
        assert got.name_pl is None
        assert got.position == 0


def test_tag_group_position_and_name_pl_persist(engine):
    group_id = uuid.uuid4()
    with Session(engine) as s:
        s.add(TagGroup(id=group_id, slug="scale", name_en="Scale", name_pl="Skala", position=3))
        s.commit()
    with Session(engine) as s:
        got = s.get(TagGroup, group_id)
        assert got.name_pl == "Skala"
        assert got.position == 3


def test_tag_group_slug_is_unique(engine):
    """The explicit uq_tag_group_slug index rejects a duplicate slug."""
    with Session(engine) as s:
        s.add(TagGroup(slug="material", name_en="Material"))
        s.commit()
    with Session(engine) as s:
        s.add(TagGroup(slug="material", name_en="Material (dup)"))
        with pytest.raises(IntegrityError):
            s.commit()


def test_tag_without_group_persists(engine):
    """Groupless tag is allowed — group_id is nullable; group_position defaults to 0."""
    tag_id = uuid.uuid4()
    with Session(engine) as s:
        s.add(Tag(id=tag_id, slug="wip", name_en="WIP", group_id=None))
        s.commit()
    with Session(engine) as s:
        got = s.get(Tag, tag_id)
        assert got is not None
        assert got.group_id is None
        assert got.group_position == 0


def test_tag_resolves_its_group(engine):
    group_id = uuid.uuid4()
    tag_id = uuid.uuid4()
    with Session(engine) as s:
        s.add(TagGroup(id=group_id, slug="material", name_en="Material"))
        s.commit()
        s.add(Tag(id=tag_id, slug="pla", name_en="PLA", group_id=group_id, group_position=2))
        s.commit()
    with Session(engine) as s:
        tag = s.get(Tag, tag_id)
        assert tag.group_id == group_id
        assert tag.group_position == 2
        group = s.get(TagGroup, tag.group_id)
        assert group.slug == "material"


def test_deleting_group_sets_tag_group_id_null(engine):
    """SET NULL: deleting a TagGroup nulls the surviving Tag.group_id."""
    group_id = uuid.uuid4()
    tag_id = uuid.uuid4()
    with Session(engine) as s:
        s.add(TagGroup(id=group_id, slug="material", name_en="Material"))
        s.commit()
        s.add(Tag(id=tag_id, slug="pla", name_en="PLA", group_id=group_id))
        s.commit()
    with Session(engine) as s:
        group = s.get(TagGroup, group_id)
        s.delete(group)
        s.commit()
    with Session(engine) as s:
        tag = s.get(Tag, tag_id)
        assert tag is not None  # tag survives
        assert tag.group_id is None  # FK nulled, not cascaded away
        # sanity: the group is gone
        assert s.exec(select(TagGroup).where(TagGroup.id == group_id)).first() is None
