"""Tests for the idempotent starter-taxonomy seed (Story 41.3).

Plain-sync tests against a throwaway tmp_path SQLite DB — the fixture idiom is
copied verbatim from ``test_seed.py`` (``create_engine_for_url`` + ``init_schema``).
No live DB, no ``TestClient``, no async app ``session`` fixture: ``init_schema``
builds the ORM-defined ``tag_group`` / ``tag`` tables via ``create_all`` so no
Alembic run is needed.
"""

import uuid

import pytest
from sqlmodel import Session, select

from app.core.db.models import Category, Model, ModelTag, Tag, TagGroup
from app.core.db.seed import (
    STARTER_TAXONOMY,
    _insert_absent_tag,
    _upsert_absent_group,
    seed_taxonomy,
)
from app.core.db.session import create_engine_for_url, init_schema
from scripts.seed_taxonomy import main as seed_taxonomy_script_main

# --- Dataset expectations derived from STARTER_TAXONOMY (single source of truth) ---

_EXPECTED_GROUP_SLUGS = [g["slug"] for g in STARTER_TAXONOMY]
_EXPECTED_TAG_SLUGS = [t["slug"] for g in STARTER_TAXONOMY for t in g["tags"]]
_TAG_PARENT_SLUG = {t["slug"]: g["slug"] for g in STARTER_TAXONOMY for t in g["tags"]}


def _seeded_engine(tmp_path):
    engine = create_engine_for_url(f"sqlite:///{tmp_path}/seed.db")
    init_schema(engine)
    return engine


def test_dataset_shape_is_the_declared_starter_set():
    # Guards the §8 starter dataset: 8 groups / 36 tags, all slugs ASCII + globally unique.
    assert len(_EXPECTED_GROUP_SLUGS) == 8
    assert len(_EXPECTED_TAG_SLUGS) == 36
    assert len(set(_EXPECTED_GROUP_SLUGS)) == 8, "group slugs must be globally unique"
    assert len(set(_EXPECTED_TAG_SLUGS)) == 36, "tag slugs must be globally unique"
    for slug in _EXPECTED_GROUP_SLUGS + _EXPECTED_TAG_SLUGS:
        assert slug == slug.encode("ascii").decode("ascii"), f"{slug!r} not ASCII"
        assert slug == slug.lower(), f"{slug!r} not lowercase"
    # Every tag carries a NOT-NULL English name (name_en is NOT NULL on the ORM).
    for group in STARTER_TAXONOMY:
        assert group["name_en"]
        for tag in group["tags"]:
            assert tag["name_en"]


def test_seed_taxonomy_populates_full_set(tmp_path):
    engine = _seeded_engine(tmp_path)
    seed_taxonomy(engine)
    with Session(engine) as s:
        groups = s.exec(select(TagGroup)).all()
        tags = s.exec(select(Tag)).all()
    assert {g.slug for g in groups} == set(_EXPECTED_GROUP_SLUGS)
    assert {t.slug for t in tags} == set(_EXPECTED_TAG_SLUGS)
    # Exactly one row per slug (no duplicates).
    assert len(groups) == len(_EXPECTED_GROUP_SLUGS)
    assert len(tags) == len(_EXPECTED_TAG_SLUGS)


def test_seed_taxonomy_primary_axes_ordering(tmp_path):
    # AC #4: Typ (position 0) and Pomieszczenie (position 1) are the first two axes.
    engine = _seeded_engine(tmp_path)
    seed_taxonomy(engine)
    with Session(engine) as s:
        by_slug = {g.slug: g for g in s.exec(select(TagGroup)).all()}
    assert by_slug["type"].position == 0
    assert by_slug["type"].name_pl == "Typ"
    assert by_slug["room"].position == 1
    assert by_slug["room"].name_pl == "Pomieszczenie"
    # Group positions are dense + distinct (a stable, reproducible ordering).
    positions = sorted(g.position for g in by_slug.values())
    assert positions == list(range(len(by_slug)))


def test_seed_taxonomy_group_positions_dense_within_each_group(tmp_path):
    engine = _seeded_engine(tmp_path)
    seed_taxonomy(engine)
    with Session(engine) as s:
        groups = {g.slug: g for g in s.exec(select(TagGroup)).all()}
        tags = s.exec(select(Tag)).all()
    for group in STARTER_TAXONOMY:
        gid = groups[group["slug"]].id
        member_positions = sorted(t.group_position for t in tags if t.group_id == gid)
        assert member_positions == list(range(len(group["tags"])))


def test_seed_taxonomy_group_linkage(tmp_path):
    # AC #5: every seeded tag links to its declared parent group (no dangling group_id).
    engine = _seeded_engine(tmp_path)
    seed_taxonomy(engine)
    with Session(engine) as s:
        groups = {g.slug: g for g in s.exec(select(TagGroup)).all()}
        tags = s.exec(select(Tag)).all()
    for tag in tags:
        assert tag.group_id is not None
        assert tag.group_id == groups[_TAG_PARENT_SLUG[tag.slug]].id


def test_seed_taxonomy_is_idempotent(tmp_path):
    # AC #7: running twice yields exactly one row per group slug and per tag slug,
    # and a STANDARD seeded row (not just a custom admin edit) is preserved verbatim
    # across the second identical run — create-if-absent never recreates or updates it.
    engine = _seeded_engine(tmp_path)
    seed_taxonomy(engine)
    with Session(engine) as s:
        g1 = s.exec(select(TagGroup).where(TagGroup.slug == "type")).one()
        t1 = s.exec(select(Tag).where(Tag.slug == "vases")).one()
        first_group = (g1.id, g1.name_en, g1.name_pl, g1.position)
        first_tag = (t1.id, t1.name_en, t1.name_pl, t1.group_id, t1.group_position)

    seed_taxonomy(engine)

    with Session(engine) as s:
        groups = s.exec(select(TagGroup)).all()
        tags = s.exec(select(Tag)).all()
        g2 = s.exec(select(TagGroup).where(TagGroup.slug == "type")).one()
        t2 = s.exec(select(Tag).where(Tag.slug == "vases")).one()
    assert len(groups) == len(_EXPECTED_GROUP_SLUGS)
    assert len(tags) == len(_EXPECTED_TAG_SLUGS)
    assert {g.slug for g in groups} == set(_EXPECTED_GROUP_SLUGS)
    assert {t.slug for t in tags} == set(_EXPECTED_TAG_SLUGS)
    # Standard seeded rows are byte-for-byte identical after the 2nd run (same id
    # → not recreated; same names/positions → not updated).
    assert (g2.id, g2.name_en, g2.name_pl, g2.position) == first_group
    assert (t2.id, t2.name_en, t2.name_pl, t2.group_id, t2.group_position) == first_tag


def test_seed_taxonomy_does_not_clobber_existing(tmp_path):
    # AC #8: an admin rename/reorder survives a re-seed (create-if-absent, never update).
    engine = _seeded_engine(tmp_path)
    with Session(engine) as s:
        group = TagGroup(slug="type", name_en="CUSTOM EN", name_pl="CUSTOM PL", position=99)
        s.add(group)
        s.commit()
        s.refresh(group)
        preexisting_group_id = group.id
        tag = Tag(
            slug="vases",
            name_en="CUSTOM TAG EN",
            name_pl="CUSTOM TAG PL",
            group_id=group.id,
            group_position=99,
        )
        s.add(tag)
        s.commit()
        s.refresh(tag)
        preexisting_tag_id = tag.id

    seed_taxonomy(engine)

    with Session(engine) as s:
        group_rows = s.exec(select(TagGroup).where(TagGroup.slug == "type")).all()
        tag_rows = s.exec(select(Tag).where(Tag.slug == "vases")).all()
    assert len(group_rows) == 1
    assert len(tag_rows) == 1
    group_row = group_rows[0]
    tag_row = tag_rows[0]
    # The pre-existing (admin-edited) values are untouched.
    assert group_row.id == preexisting_group_id
    assert group_row.name_en == "CUSTOM EN"
    assert group_row.name_pl == "CUSTOM PL"
    assert group_row.position == 99
    assert tag_row.id == preexisting_tag_id
    assert tag_row.name_en == "CUSTOM TAG EN"
    assert tag_row.name_pl == "CUSTOM TAG PL"
    assert tag_row.group_position == 99


def test_seed_taxonomy_no_model_side_effects(tmp_path):
    # AC #6: no Model / ModelTag writes; a pre-existing model stays untagged.
    engine = _seeded_engine(tmp_path)
    with Session(engine) as s:
        category = Category(slug="root", name_en="Root")
        s.add(category)
        s.commit()
        s.refresh(category)
        s.add(Model(slug="m1", name_en="Model 1", category_id=category.id))
        s.commit()

    seed_taxonomy(engine)

    with Session(engine) as s:
        assert len(s.exec(select(ModelTag)).all()) == 0
        assert len(s.exec(select(Model)).all()) == 1
        # AC #6: the seed provably never touches Category either — the pre-created
        # root category survives untouched (count unchanged, no seed-side writes).
        assert len(s.exec(select(Category)).all()) == 1


def test_seed_taxonomy_converges_after_midtag_failure(tmp_path, monkeypatch):
    # AC #9: a failure partway through the TAG phase does not wedge the seed. The
    # subset committed before the fault stays consistent (every committed tag links
    # to its parent group — no orphans), and a clean re-run converges to the full
    # dataset exactly once (per-row commit boundary).
    engine = _seeded_engine(tmp_path)

    real_commit = Session.commit
    state = {"n": 0}

    # seed_taxonomy commits all 8 groups first (commits 1-8), then the 36 tags
    # (commits 9-44). Failing on the 11th commit lands mid-TAG-phase with a few
    # tags already persisted, so the no-orphan assertion below is actually
    # exercised rather than vacuously true (a group-phase fault would commit zero
    # tags, making "every tag has a group_id" trivially hold).
    def flaky_commit(self):
        state["n"] += 1
        if state["n"] == 11:
            raise RuntimeError("injected mid-tag-phase failure")
        return real_commit(self)

    monkeypatch.setattr(Session, "commit", flaky_commit, raising=True)
    with pytest.raises(RuntimeError):
        seed_taxonomy(engine)
    monkeypatch.undo()

    # Mid-fault state: all groups + a NON-EMPTY, STRICT subset of tags committed,
    # and each committed tag already points at its declared parent group.
    with Session(engine) as s:
        partial_groups = s.exec(select(TagGroup)).all()
        partial_tags = s.exec(select(Tag)).all()
    assert len(partial_groups) == len(_EXPECTED_GROUP_SLUGS)
    assert 0 < len(partial_tags) < len(_EXPECTED_TAG_SLUGS)
    group_id_by_slug = {g.slug: g.id for g in partial_groups}
    for tag in partial_tags:
        assert tag.group_id is not None
        assert tag.group_id == group_id_by_slug[_TAG_PARENT_SLUG[tag.slug]]

    # A clean re-run completes the remainder and converges to the full set exactly once.
    seed_taxonomy(engine)
    with Session(engine) as s:
        groups = s.exec(select(TagGroup)).all()
        tags = s.exec(select(Tag)).all()
    assert len(groups) == len(_EXPECTED_GROUP_SLUGS)
    assert len(tags) == len(_EXPECTED_TAG_SLUGS)
    assert {g.slug for g in groups} == set(_EXPECTED_GROUP_SLUGS)
    assert {t.slug for t in tags} == set(_EXPECTED_TAG_SLUGS)
    # No orphan tags after convergence either.
    for tag in tags:
        assert tag.group_id is not None


def test_seed_taxonomy_slug_uniqueness_holds_in_db(tmp_path):
    engine = _seeded_engine(tmp_path)
    seed_taxonomy(engine)
    with Session(engine) as s:
        group_slugs = [g.slug for g in s.exec(select(TagGroup)).all()]
        tag_slugs = [t.slug for t in s.exec(select(Tag)).all()]
    assert len(group_slugs) == len(set(group_slugs))
    assert len(tag_slugs) == len(set(tag_slugs))


def test_ids_are_uuid(tmp_path):
    engine = _seeded_engine(tmp_path)
    seed_taxonomy(engine)
    with Session(engine) as s:
        group = s.exec(select(TagGroup)).first()
        tag = s.exec(select(Tag)).first()
    assert isinstance(group.id, uuid.UUID)
    assert isinstance(tag.id, uuid.UUID)


class _MissingRow:
    """A SELECT result whose ``.first()`` misses the row.

    Injected as the existence check inside a seed helper so the helper proceeds to
    INSERT a slug that ANOTHER writer has already committed — reproducing the
    check-then-insert race deterministically, without threads or a live DB.
    """

    def first(self):
        return None


def _first_call_misses(session, monkeypatch):
    """Make the helper's FIRST ``session.exec`` (the existence check) miss the row.

    Later calls (e.g. the group helper's post-rollback ``.one()`` re-query) fall
    through to the real ``session.exec``.
    """
    real_exec = session.exec
    calls = {"n": 0}

    def racy_exec(statement, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _MissingRow()
        return real_exec(statement, *args, **kwargs)

    monkeypatch.setattr(session, "exec", racy_exec)


def test_upsert_absent_group_tolerates_real_integrity_error(tmp_path, monkeypatch):
    # Drives the GENUINE IntegrityError branch in _upsert_absent_group (seed.py:206-212):
    # a concurrent writer commits the same group slug AFTER this session's existence
    # SELECT missed it, so this session's INSERT raises a real unique-constraint
    # IntegrityError. The helper rolls back, re-queries, and adopts the racer's row id
    # (never a duplicate, never a clobber). A RuntimeError would bypass this handler.
    engine = _seeded_engine(tmp_path)
    group = STARTER_TAXONOMY[0]  # "type"

    with Session(engine) as racer:
        racer.add(TagGroup(slug=group["slug"], name_en="RACER", name_pl="RACER", position=42))
        racer.commit()

    with Session(engine) as session:
        _first_call_misses(session, monkeypatch)
        adopted_id = _upsert_absent_group(session, group)

    with Session(engine) as s:
        rows = s.exec(select(TagGroup).where(TagGroup.slug == group["slug"])).all()
    assert len(rows) == 1  # the failed INSERT created no duplicate
    assert rows[0].id == adopted_id  # helper adopted (returned) the racer's row id
    assert rows[0].name_en == "RACER"  # racer's row left untouched (create-if-absent)


def test_insert_absent_tag_tolerates_real_integrity_error(tmp_path, monkeypatch):
    # Drives the GENUINE IntegrityError branch in _insert_absent_tag (seed.py:231-236):
    # a concurrent writer commits the same tag slug after the existence SELECT missed
    # it → a real unique-constraint violation, swallowed via rollback and reported as
    # success (no raise, no duplicate, racer's row preserved).
    engine = _seeded_engine(tmp_path)
    with Session(engine) as s:
        parent = TagGroup(slug="type", name_en="Type", name_pl="Typ", position=0)
        s.add(parent)
        s.commit()
        s.refresh(parent)
        parent_id = parent.id
        s.add(
            Tag(
                slug="vases",
                name_en="RACER TAG",
                name_pl="RACER",
                group_id=parent_id,
                group_position=7,
            )
        )
        s.commit()

    tag = {"slug": "vases", "name_en": "Vases", "name_pl": "Wazony"}
    with Session(engine) as session:
        _first_call_misses(session, monkeypatch)
        # Must NOT raise — the IntegrityError is tolerated as success.
        _insert_absent_tag(session, tag, parent_id, 1)

    with Session(engine) as s:
        rows = s.exec(select(Tag).where(Tag.slug == "vases")).all()
    assert len(rows) == 1  # no duplicate
    assert rows[0].name_en == "RACER TAG"  # racer's row untouched


def test_script_main_prints_truthful_post_condition_count(tmp_path, capsys):
    # AC #11 ergonomics: the admin-run script reports counts QUERIED FROM THE DB
    # after seeding (not constants), and runs against an injected engine — no live DB.
    engine = _seeded_engine(tmp_path)
    seed_taxonomy_script_main(engine=engine)

    with Session(engine) as s:
        group_count = len(s.exec(select(TagGroup)).all())
        tag_count = len(s.exec(select(Tag)).all())
    out = capsys.readouterr().out
    # Reported numbers equal the real DB totals AND the fully-seeded starter set.
    assert f"{group_count} groups / {tag_count} tags" in out
    assert "8 groups / 36 tags" in out
