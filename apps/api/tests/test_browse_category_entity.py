"""BrowseCategory + ModelBrowseCategory entities — round-trip and FK behaviour.

Story 49.1 (Initiative 26 / Epic 49, Decision AX). Entity-only test: constructs
models directly against a fresh in-memory SQLite built from the ORM
(`SQLModel.metadata.create_all`), mirroring the self-contained style of
`test_tag_group_entity.py`. No HTTP/TestClient — no login needed.

The explicit `PRAGMA foreign_keys=ON` listener is load-bearing: SQLite does not
enforce `ON DELETE CASCADE` / `RESTRICT` without it. Dropping it does NOT make
the CASCADE and RESTRICT assertions below pass vacuously — they fail loudly
(`DID NOT RAISE` for RESTRICT, surviving child rows for CASCADE) or stop
exercising any DB action at all. The listener is what makes them correct, not
what makes them non-empty.
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.db.models import BrowseCategory, Model, ModelBrowseCategory


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


def _model(**kw) -> Model:
    """A minimal valid catalog Model — only slug/name_en are required."""
    kw.setdefault("slug", f"m-{uuid.uuid4().hex[:8]}")
    kw.setdefault("name_en", "Some Model")
    return Model(**kw)


# --- AC-12 (a) -------------------------------------------------------------


def test_browse_category_round_trips_with_defaults(engine):
    """Defaults land as declared: position 0, every optional field None."""
    cat_id = uuid.uuid4()
    with Session(engine) as s:
        s.add(BrowseCategory(id=cat_id, slug="lamps", name_en="Lamps"))
        s.commit()
    with Session(engine) as s:
        got = s.get(BrowseCategory, cat_id)
        assert got is not None
        assert got.slug == "lamps"
        assert got.name_en == "Lamps"
        assert got.position == 0
        assert got.name_pl is None
        assert got.description_en is None
        assert got.description_pl is None
        assert got.inclusion_criterion is None
        assert got.parent_id is None
        assert got.created_at is not None
        assert got.updated_at is not None


def test_browse_category_optional_fields_persist(engine):
    cat_id = uuid.uuid4()
    with Session(engine) as s:
        s.add(
            BrowseCategory(
                id=cat_id,
                slug="kitchen",
                name_en="Kitchen",
                name_pl="Kuchnia",
                description_en="Kitchen things",
                description_pl="Rzeczy kuchenne",
                inclusion_criterion="Used in a kitchen.",
                position=4,
            )
        )
        s.commit()
    with Session(engine) as s:
        got = s.get(BrowseCategory, cat_id)
        assert got.name_pl == "Kuchnia"
        assert got.description_en == "Kitchen things"
        assert got.description_pl == "Rzeczy kuchenne"
        assert got.inclusion_criterion == "Used in a kitchen."
        assert got.position == 4


# --- AC-12 (b) -------------------------------------------------------------


def test_browse_category_slug_is_unique(engine):
    """The explicit uq_browse_category_slug index rejects a duplicate slug.

    Uniqueness is global, NOT per-parent — the retired category taxonomy's
    uq_category_root_slug partial-index shape is deliberately not reproduced.
    """
    with Session(engine) as s:
        s.add(BrowseCategory(slug="lamps", name_en="Lamps"))
        s.commit()
    with Session(engine) as s:
        s.add(BrowseCategory(slug="lamps", name_en="Lamps (dup)"))
        with pytest.raises(IntegrityError):
            s.commit()


def test_browse_category_child_slug_still_collides_with_root(engine):
    """A child may not reuse a root's slug — global uniqueness, not per-parent."""
    parent_id = uuid.uuid4()
    with Session(engine) as s:
        s.add(BrowseCategory(id=parent_id, slug="home", name_en="Home"))
        s.add(BrowseCategory(slug="lamps", name_en="Lamps"))
        s.commit()
    with Session(engine) as s:
        s.add(BrowseCategory(slug="lamps", name_en="Lamps (child)", parent_id=parent_id))
        with pytest.raises(IntegrityError):
            s.commit()


# --- AC-12 (c) -------------------------------------------------------------


def test_duplicate_model_category_pair_rejected(engine):
    """Composite PK (model_id, category_id) makes the pair unique."""
    model_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    with Session(engine) as s:
        s.add(_model(id=model_id))
        s.add(BrowseCategory(id=cat_id, slug="lamps", name_en="Lamps"))
        s.commit()
        s.add(ModelBrowseCategory(model_id=model_id, category_id=cat_id))
        s.commit()
    with Session(engine) as s:
        s.add(ModelBrowseCategory(model_id=model_id, category_id=cat_id))
        with pytest.raises(IntegrityError):
            s.commit()


def test_model_may_hold_several_categories(engine):
    """M:N — the same model in two categories is legal."""
    model_id = uuid.uuid4()
    cat_a, cat_b = uuid.uuid4(), uuid.uuid4()
    with Session(engine) as s:
        s.add(_model(id=model_id))
        s.add(BrowseCategory(id=cat_a, slug="lamps", name_en="Lamps"))
        s.add(BrowseCategory(id=cat_b, slug="kitchen", name_en="Kitchen"))
        s.commit()
        s.add(ModelBrowseCategory(model_id=model_id, category_id=cat_a))
        s.add(ModelBrowseCategory(model_id=model_id, category_id=cat_b))
        s.commit()
    with Session(engine) as s:
        rows = s.exec(
            select(ModelBrowseCategory).where(ModelBrowseCategory.model_id == model_id)
        ).all()
        assert {r.category_id for r in rows} == {cat_a, cat_b}


# --- AC-12 (d) -------------------------------------------------------------


def test_deleting_model_cascades_its_category_rows(engine):
    """CASCADE: deleting a Model removes its model_browse_category rows."""
    model_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    with Session(engine) as s:
        s.add(_model(id=model_id))
        s.add(BrowseCategory(id=cat_id, slug="lamps", name_en="Lamps"))
        s.commit()
        s.add(ModelBrowseCategory(model_id=model_id, category_id=cat_id))
        s.commit()
    with Session(engine) as s:
        s.delete(s.get(Model, model_id))
        s.commit()
    with Session(engine) as s:
        assert s.exec(select(ModelBrowseCategory)).all() == []
        # The category itself survives — only the assignment cascaded away.
        assert s.get(BrowseCategory, cat_id) is not None


# --- AC-12 (e) -------------------------------------------------------------


def test_deleting_assigned_category_is_restricted(engine):
    """RESTRICT: a BrowseCategory holding assignments cannot be deleted."""
    model_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    with Session(engine) as s:
        s.add(_model(id=model_id))
        s.add(BrowseCategory(id=cat_id, slug="lamps", name_en="Lamps"))
        s.commit()
        s.add(ModelBrowseCategory(model_id=model_id, category_id=cat_id))
        s.commit()
    with Session(engine) as s:
        s.delete(s.get(BrowseCategory, cat_id))
        with pytest.raises(IntegrityError):
            s.commit()


def test_unassigned_category_can_be_deleted(engine):
    """RESTRICT only bites while assignments exist."""
    cat_id = uuid.uuid4()
    with Session(engine) as s:
        s.add(BrowseCategory(id=cat_id, slug="lamps", name_en="Lamps"))
        s.commit()
    with Session(engine) as s:
        s.delete(s.get(BrowseCategory, cat_id))
        s.commit()
    with Session(engine) as s:
        assert s.get(BrowseCategory, cat_id) is None


# --- AC-12 (f) -------------------------------------------------------------


def test_root_category_persists_without_parent(engine):
    """parent_id is nullable — a flat/root category is DB-valid."""
    cat_id = uuid.uuid4()
    with Session(engine) as s:
        s.add(BrowseCategory(id=cat_id, slug="lamps", name_en="Lamps", parent_id=None))
        s.commit()
    with Session(engine) as s:
        assert s.get(BrowseCategory, cat_id).parent_id is None


def test_child_category_resolves_its_parent(engine):
    parent_id = uuid.uuid4()
    child_id = uuid.uuid4()
    with Session(engine) as s:
        s.add(BrowseCategory(id=parent_id, slug="home", name_en="Home"))
        s.commit()
        s.add(BrowseCategory(id=child_id, slug="lamps", name_en="Lamps", parent_id=parent_id))
        s.commit()
    with Session(engine) as s:
        child = s.get(BrowseCategory, child_id)
        assert child.parent_id == parent_id
        parent = s.get(BrowseCategory, child.parent_id)
        assert parent.slug == "home"


def test_deleting_parent_with_child_is_restricted(engine):
    """RESTRICT on the self-FK: a parent holding a child cannot be deleted."""
    parent_id = uuid.uuid4()
    with Session(engine) as s:
        s.add(BrowseCategory(id=parent_id, slug="home", name_en="Home"))
        s.commit()
        s.add(BrowseCategory(slug="lamps", name_en="Lamps", parent_id=parent_id))
        s.commit()
    with Session(engine) as s:
        s.delete(s.get(BrowseCategory, parent_id))
        with pytest.raises(IntegrityError):
            s.commit()


# --- AC-12 (g) -------------------------------------------------------------


def test_model_with_zero_categories_persists(engine):
    """A Model may have NO categories at all and is fully DB-valid that way."""
    model_id = uuid.uuid4()
    with Session(engine) as s:
        s.add(_model(id=model_id, slug="uncategorized-thing", name_en="Uncategorized Thing"))
        s.commit()
    with Session(engine) as s:
        got = s.get(Model, model_id)
        assert got is not None
        assert got.slug == "uncategorized-thing"
        assert (
            s.exec(
                select(ModelBrowseCategory).where(ModelBrowseCategory.model_id == model_id)
            ).all()
            == []
        )


def test_uncategorized_model_unaffected_by_other_assignments(engine):
    """Categorising one model does not touch an uncategorised sibling."""
    assigned_id = uuid.uuid4()
    bare_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    with Session(engine) as s:
        s.add(_model(id=assigned_id))
        s.add(_model(id=bare_id))
        s.add(BrowseCategory(id=cat_id, slug="lamps", name_en="Lamps"))
        s.commit()
        s.add(ModelBrowseCategory(model_id=assigned_id, category_id=cat_id))
        s.commit()
    with Session(engine) as s:
        assert s.get(Model, bare_id) is not None
        rows = s.exec(select(ModelBrowseCategory)).all()
        assert [r.model_id for r in rows] == [assigned_id]
