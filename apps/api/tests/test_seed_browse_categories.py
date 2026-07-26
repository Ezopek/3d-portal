"""Tests for the idempotent starter browse-category seed (Story 49.2).

Plain-sync tests against a throwaway tmp_path SQLite DB — the fixture idiom is
copied from ``test_seed_taxonomy.py`` (``create_engine_for_url`` + ``init_schema``).
No live DB, no ``TestClient``, no async app ``session`` fixture, and no Alembic
run: ``init_schema`` builds the ORM-defined ``browse_category`` table via
``create_all``.

Scope note (AC-12): nothing here re-derives the real-catalogue distribution
evidence that discharged the ``EXPERIENCE.md:192`` obligation — a unit test on an
empty scratch database has no access to the live catalogue. The dataset tests are
a POST-DECISION DRIFT GUARD over the approved eight rows, and nothing more.
"""

import itertools
import re
import uuid
from pathlib import Path

import pytest
from sqlmodel import Session, select

from app.core.db.models import (
    BrowseCategory,
    Model,
    ModelBrowseCategory,
    ModelTag,
    Tag,
    TagGroup,
)
from app.core.db.seed import (
    STARTER_BROWSE_CATEGORIES,
    _insert_absent_category,
    seed_browse_categories,
)
from app.core.db.session import create_engine_for_url, init_schema
from scripts.seed_browse_categories import main as seed_categories_script_main

_API_ROOT = Path(__file__).resolve().parents[1]

# --- The approved dataset, transcribed literally from Story 49.2 §4 AC-1/AC-2 ---
#
# This is a DELIBERATE second copy of the approved content, not a derivation from
# STARTER_BROWSE_CATEGORIES: comparing the dataset against itself would prove
# nothing. Source of truth is EXPERIENCE.md:84-91 (rows) and :101-156 (criteria),
# the latter under exactly the two normalisations AC-2 fixes (strip markdown `*`
# emphasis — which affects only `storage-organization`; capitalise the first
# letter). A silent reorder, rename or drop by a later editor fails here.

_APPROVED_ROWS: list[tuple[int, str, str, str]] = [
    (0, "storage-organization", "Przechowywanie i organizacja", "Storage & Organization"),
    (1, "home-decor", "Dekoracje i wystrój", "Home Decor"),
    (2, "holders-mounts", "Uchwyty i mocowania", "Holders & Mounts"),
    (3, "electronics-cables", "Elektronika i kable", "Electronics & Cables"),
    (4, "tools-workshop", "Narzędzia i warsztat", "Tools & Workshop"),
    (5, "printer-3d", "Drukarka 3D i akcesoria", "3D Printer & Accessories"),
    (6, "toys-games", "Zabawki, gry i figurki", "Toys, Games & Figures"),
    (7, "replacement-parts", "Części zamienne", "Replacement Parts"),
]

_APPROVED_CRITERIA: dict[str, str] = {
    "storage-organization": ("The model's primary purpose is to hold, sort or tidy other objects."),
    "home-decor": (
        "The model is chosen mainly for how it looks in a living space, not for a job it performs."
    ),
    "holders-mounts": (
        "The model exists to hold one specific object in a fixed position, "
        "or to attach something to a surface."
    ),
    "electronics-cables": (
        "The model houses, routes, protects or mounts electronics, wiring or connectors."
    ),
    "tools-workshop": (
        "The model is a tool, jig, fixture or aid used while making, measuring "
        "or repairing something."
    ),
    "printer-3d": (
        "The model only makes sense to someone who owns a 3D printer — "
        "it upgrades, maintains or feeds the printer itself."
    ),
    "toys-games": (
        "The model's purpose is play, collecting, or display as a character or object of interest."
    ),
    "replacement-parts": (
        "The model replaces or repairs a broken or missing part of an existing manufactured object."
    ),
}

_APPROVED_SLUGS = [slug for _position, slug, _name_pl, _name_en in _APPROVED_ROWS]


def _fresh_engine(tmp_path):
    """An EMPTY scratch database — the 41.3 fixture idiom (test_seed_taxonomy.py:32-35)."""
    engine = create_engine_for_url(f"sqlite:///{tmp_path}/seed.db")
    init_schema(engine)
    return engine


def _snapshot(row: BrowseCategory) -> tuple:
    """Every field AC-6/AC-7 require to survive a re-seed byte-identical.

    Includes ``id`` (same id → the row was not recreated) and ``updated_at``
    (unchanged → the row was not updated).
    """
    return (
        row.id,
        row.slug,
        row.name_en,
        row.name_pl,
        row.description_en,
        row.description_pl,
        row.inclusion_criterion,
        row.position,
        row.parent_id,
        row.created_at,
        row.updated_at,
    )


# --------------------------------------------------------------------------- #
# Dataset shape — AC-1, AC-2, AC-3, AC-12
# --------------------------------------------------------------------------- #


def test_dataset_is_the_approved_eight_rows_in_the_approved_order():
    # AC-1 + AC-12: the exact ordered (slug, position) sequence. A reorder, a
    # rename of a slug, an addition or a drop is a failing test, not a style choice.
    assert [(c["slug"], c["position"]) for c in STARTER_BROWSE_CATEGORIES] == [
        (slug, position) for position, slug, _name_pl, _name_en in _APPROVED_ROWS
    ]
    assert len(STARTER_BROWSE_CATEGORIES) == 8


def test_dataset_positions_are_dense_and_strictly_increasing_in_list_order():
    # AC-12: dense 0..7, strictly increasing in list order.
    positions = [c["position"] for c in STARTER_BROWSE_CATEGORIES]
    assert positions == list(range(8))
    assert all(later > earlier for earlier, later in itertools.pairwise(positions))


def test_dataset_slugs_are_unique_lowercase_ascii_identifiers():
    # AC-12: the slug is the idempotency key, so it must be a stable ASCII token.
    slugs = [c["slug"] for c in STARTER_BROWSE_CATEGORIES]
    assert len(set(slugs)) == 8, "slugs must be unique"
    for slug in slugs:
        assert slug == slug.lower(), f"{slug!r} not lowercase"
        assert slug == slug.encode("ascii").decode("ascii"), f"{slug!r} not ASCII"
        assert re.fullmatch(r"[a-z0-9-]+", slug), f"{slug!r} outside [a-z0-9-]"


def test_dataset_labels_match_the_approved_table():
    # AC-1: bilingual labels compared LITERALLY against the approved table.
    by_slug = {c["slug"]: c for c in STARTER_BROWSE_CATEGORIES}
    for _position, slug, name_pl, name_en in _APPROVED_ROWS:
        assert by_slug[slug]["name_pl"] == name_pl
        assert by_slug[slug]["name_en"] == name_en


def test_dataset_inclusion_criteria_match_the_approved_table():
    # AC-2: the canonical English one-sentence criterion per slug, byte-for-byte —
    # including the printer-3d em dash and the toys-games Oxford comma.
    by_slug = {c["slug"]: c for c in STARTER_BROWSE_CATEGORIES}
    assert set(_APPROVED_CRITERIA) == set(by_slug)
    for slug, criterion in _APPROVED_CRITERIA.items():
        assert by_slug[slug]["inclusion_criterion"] == criterion
    for category in STARTER_BROWSE_CATEGORIES:
        text = category["inclusion_criterion"]
        # Normalisation 1: markdown emphasis markers stripped.
        assert "*" not in text
        # Normalisation 2: first letter capitalised. Trailing stop preserved.
        assert text[0].isupper()
        assert text.endswith(".")


def test_dataset_leaves_descriptions_and_parent_unset():
    # AC-3: no invented descriptions and no starter parent->child tree.
    for category in STARTER_BROWSE_CATEGORIES:
        assert category.get("description_en") is None
        assert category.get("description_pl") is None
        assert category.get("parent_id") is None


# --------------------------------------------------------------------------- #
# Seeding behaviour — AC-5 ... AC-9
# --------------------------------------------------------------------------- #


def test_seed_populates_exactly_the_eight_approved_rows(tmp_path):
    # AC-5: one call against an empty table yields exactly the eight rows, no duplicates.
    engine = _fresh_engine(tmp_path)
    seed_browse_categories(engine)

    with Session(engine) as s:
        rows = s.exec(select(BrowseCategory)).all()
    assert len(rows) == 8
    by_slug = {r.slug: r for r in rows}
    assert set(by_slug) == set(_APPROVED_SLUGS)
    for position, slug, name_pl, name_en in _APPROVED_ROWS:
        row = by_slug[slug]
        assert (row.position, row.name_pl, row.name_en) == (position, name_pl, name_en)
        assert row.inclusion_criterion == _APPROVED_CRITERIA[slug]
        # AC-3 again, this time as persisted state rather than dataset shape.
        assert row.description_en is None
        assert row.description_pl is None
        assert row.parent_id is None
        assert isinstance(row.id, uuid.UUID)


def test_seed_is_idempotent_and_byte_stable(tmp_path):
    # AC-6: a second identical call neither recreates (same id) nor updates
    # (same field values AND same updated_at) any row.
    engine = _fresh_engine(tmp_path)
    seed_browse_categories(engine)
    with Session(engine) as s:
        before = {r.slug: _snapshot(r) for r in s.exec(select(BrowseCategory)).all()}

    seed_browse_categories(engine)

    with Session(engine) as s:
        rows = s.exec(select(BrowseCategory)).all()
    assert len(rows) == 8
    assert {r.slug: _snapshot(r) for r in rows} == before


def test_admin_edited_row_survives_a_reseed_untouched(tmp_path):
    # AC-7: divergent labels, a rewritten criterion, a moved position, a set
    # description_pl and a non-null parent_id all survive verbatim, and no second
    # row is created for that slug.
    engine = _fresh_engine(tmp_path)
    with Session(engine) as s:
        parent = BrowseCategory(slug="home-decor", name_en="Home Decor")
        s.add(parent)
        s.commit()
        s.refresh(parent)
        edited = BrowseCategory(
            slug="storage-organization",
            name_en="ADMIN RENAMED EN",
            name_pl="ADMIN RENAMED PL",
            description_en="admin description en",
            description_pl="admin description pl",
            inclusion_criterion="ADMIN REWROTE THIS CRITERION.",
            position=99,
            parent_id=parent.id,
        )
        s.add(edited)
        s.commit()
        s.refresh(edited)
        before = _snapshot(edited)

    seed_browse_categories(engine)

    with Session(engine) as s:
        rows = s.exec(
            select(BrowseCategory).where(BrowseCategory.slug == "storage-organization")
        ).all()
        total = len(s.exec(select(BrowseCategory)).all())
    assert len(rows) == 1, "create-if-absent must not add a second row for an existing slug"
    assert _snapshot(rows[0]) == before
    assert total == 8


def test_partial_dataset_is_completed_without_disturbing_existing_rows(tmp_path):
    # AC-8: a strict non-empty subset (one of them admin-edited) is left
    # byte-identical while the missing rows are created; converges to exactly 8.
    engine = _fresh_engine(tmp_path)
    with Session(engine) as s:
        preexisting = [
            BrowseCategory(
                slug="home-decor",
                name_en="Home Decor",
                name_pl="Dekoracje i wystrój",
                position=1,
            ),
            BrowseCategory(slug="toys-games", name_en="ADMIN RENAMED", position=42),
            BrowseCategory(slug="tools-workshop", name_en="Tools & Workshop", position=4),
        ]
        for row in preexisting:
            s.add(row)
            s.commit()
            s.refresh(row)
        before = {row.slug: _snapshot(row) for row in preexisting}
    assert 0 < len(before) < 8
    assert set(before) < set(_APPROVED_SLUGS)

    seed_browse_categories(engine)

    with Session(engine) as s:
        rows = s.exec(select(BrowseCategory)).all()
    slugs = [r.slug for r in rows]
    assert len(slugs) == 8
    assert len(set(slugs)) == 8, "no duplicates"
    assert set(slugs) == set(_APPROVED_SLUGS)
    after = {r.slug: _snapshot(r) for r in rows}
    for slug, snapshot in before.items():
        assert after[slug] == snapshot, f"pre-existing row {slug!r} was disturbed"
    # The five genuinely-created rows carry the approved content.
    created = set(_APPROVED_SLUGS) - set(before)
    by_slug = {r.slug: r for r in rows}
    for slug in created:
        assert by_slug[slug].inclusion_criterion == _APPROVED_CRITERIA[slug]


def test_seed_writes_nothing_outside_browse_category(tmp_path):
    # AC-9: zero model<->category assignments, and no Model / Tag / TagGroup /
    # ModelTag write on this code path.
    engine = _fresh_engine(tmp_path)
    with Session(engine) as s:
        model = Model(slug="m1", name_en="Model 1")
        s.add(model)
        s.commit()
        s.refresh(model)
        group = TagGroup(slug="type", name_en="Type", name_pl="Typ", position=0)
        s.add(group)
        s.commit()
        s.refresh(group)
        tag = Tag(
            slug="vases",
            name_en="Vases",
            name_pl="Wazony",
            group_id=group.id,
            group_position=0,
        )
        s.add(tag)
        s.commit()
        s.refresh(tag)
        s.add(ModelTag(model_id=model.id, tag_id=tag.id))
        s.commit()

        models_before = [(m.id, m.slug, m.name_en) for m in s.exec(select(Model)).all()]
        groups_before = [
            (g.id, g.slug, g.name_en, g.name_pl, g.position) for g in s.exec(select(TagGroup)).all()
        ]
        tags_before = [
            (t.id, t.slug, t.name_en, t.name_pl, t.group_id, t.group_position)
            for t in s.exec(select(Tag)).all()
        ]
        model_tags_before = [(mt.model_id, mt.tag_id) for mt in s.exec(select(ModelTag)).all()]
    assert model_tags_before, "the ModelTag assertion below must not be vacuous"

    seed_browse_categories(engine)

    with Session(engine) as s:
        assert s.exec(select(ModelBrowseCategory)).all() == []
        assert [(m.id, m.slug, m.name_en) for m in s.exec(select(Model)).all()] == models_before
        assert [
            (g.id, g.slug, g.name_en, g.name_pl, g.position) for g in s.exec(select(TagGroup)).all()
        ] == groups_before
        assert [
            (t.id, t.slug, t.name_en, t.name_pl, t.group_id, t.group_position)
            for t in s.exec(select(Tag)).all()
        ] == tags_before
        assert [
            (mt.model_id, mt.tag_id) for mt in s.exec(select(ModelTag)).all()
        ] == model_tags_before


# --------------------------------------------------------------------------- #
# No boot auto-seeding — AC-10
# --------------------------------------------------------------------------- #


def test_seed_is_not_wired_into_the_app_lifespan():
    # AC-10: source-level, import-free grep-equivalent. A boot-time seed would
    # resurrect owner-deleted categories on every redeploy, so an accidental
    # lifespan wiring must fail the suite rather than change behaviour silently.
    main_source = (_API_ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "seed_browse_categories" not in main_source
    assert "seed_admin" in main_source, "seed_admin is still the only lifespan-wired seeder"


def test_seed_browse_categories_is_referenced_only_by_its_own_definition():
    # AC-10: no import in main.py, no router, no dependency, no worker.
    hits = sorted(
        path.relative_to(_API_ROOT).as_posix()
        for path in (_API_ROOT / "app").rglob("*.py")
        if "seed_browse_categories" in path.read_text(encoding="utf-8")
    )
    assert hits == ["app/core/db/seed.py"]


# --------------------------------------------------------------------------- #
# Admin-run entrypoint — AC-11
# --------------------------------------------------------------------------- #


def test_script_main_prints_a_truthful_post_seed_count(tmp_path, capsys):
    # AC-11: runs against an injected throwaway engine (never a live DB) and
    # reports the count QUERIED FROM THE DB after seeding.
    engine = _fresh_engine(tmp_path)
    seed_categories_script_main(engine=engine)

    with Session(engine) as s:
        count = len(s.exec(select(BrowseCategory)).all())
    out = capsys.readouterr().out
    assert f"seeded browse categories: {count} categories present" in out
    assert "seeded browse categories: 8 categories present" in out


def test_script_main_count_is_queried_from_the_db_not_the_dataset_constant(tmp_path, capsys):
    # AC-11: with one extra admin-created row present the DB holds 9 categories.
    # Printing len(STARTER_BROWSE_CATEGORIES) would claim 8 and hide the difference,
    # which is exactly the "partial seed looks like a full seed" failure AC-11 forbids.
    engine = _fresh_engine(tmp_path)
    with Session(engine) as s:
        s.add(BrowseCategory(slug="admin-added-extra", name_en="Admin Added Extra"))
        s.commit()

    seed_categories_script_main(engine=engine)

    out = capsys.readouterr().out
    assert "seeded browse categories: 9 categories present" in out


# --------------------------------------------------------------------------- #
# Transaction boundary and concurrency — AC-13, AC-14
# --------------------------------------------------------------------------- #


def test_seed_converges_after_a_midrun_commit_failure(tmp_path, monkeypatch):
    # AC-13: per-row commit boundary. RuntimeError deliberately, NEVER
    # IntegrityError — the latter is swallowed by design and would make this
    # test vacuous.
    engine = _fresh_engine(tmp_path)

    real_commit = Session.commit
    state = {"n": 0}

    # One commit per row, so commit N is row N. Failing on the 4th leaves three
    # rows durably committed, which is what makes the "non-empty STRICT subset"
    # assertion below exercised rather than trivially true.
    def flaky_commit(self):
        state["n"] += 1
        if state["n"] == 4:
            raise RuntimeError("injected mid-run failure")
        return real_commit(self)

    monkeypatch.setattr(Session, "commit", flaky_commit, raising=True)
    with pytest.raises(RuntimeError):
        seed_browse_categories(engine)
    monkeypatch.undo()

    with Session(engine) as s:
        partial_slugs = [r.slug for r in s.exec(select(BrowseCategory)).all()]
    assert 0 < len(partial_slugs) < 8
    assert len(set(partial_slugs)) == len(partial_slugs), "no duplicates in the partial state"
    assert set(partial_slugs) < set(_APPROVED_SLUGS), "a consistent STRICT subset"

    # A clean re-run completes the remainder and converges exactly once.
    seed_browse_categories(engine)
    with Session(engine) as s:
        rows = s.exec(select(BrowseCategory)).all()
    assert len(rows) == 8
    assert {r.slug for r in rows} == set(_APPROVED_SLUGS)


class _MissingRow:
    """A SELECT result whose ``.first()`` misses the row.

    Injected as the existence check inside the seed helper so it proceeds to
    INSERT a slug ANOTHER writer has already committed — reproducing the
    check-then-insert race deterministically, without threads or a live DB.
    Idiom copied from ``test_seed_taxonomy.py:262-289``.
    """

    def first(self):
        return None


def _first_call_misses(session, monkeypatch):
    """Make the helper's FIRST ``session.exec`` (the existence check) miss the row."""
    real_exec = session.exec
    calls = {"n": 0}

    def racy_exec(statement, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _MissingRow()
        return real_exec(statement, *args, **kwargs)

    monkeypatch.setattr(session, "exec", racy_exec)


def test_insert_absent_category_tolerates_a_real_integrity_error(tmp_path, monkeypatch):
    # AC-14: drives the GENUINE IntegrityError branch. A concurrent writer commits
    # the same slug after this session's existence SELECT missed it, so the INSERT
    # violates uq_browse_category_slug. The helper rolls back and returns: no raise,
    # no duplicate, racer's row preserved. Exactly the shipped _insert_absent_tag
    # contract (seed.py:231-236) — no re-query, no adopt, no partial update.
    engine = _fresh_engine(tmp_path)
    category = STARTER_BROWSE_CATEGORIES[0]

    with Session(engine) as racer:
        racer.add(BrowseCategory(slug=category["slug"], name_en="RACER", position=42))
        racer.commit()

    with Session(engine) as session:
        _first_call_misses(session, monkeypatch)
        # Must NOT raise — the IntegrityError is tolerated as success.
        _insert_absent_category(session, category)

    with Session(engine) as s:
        rows = s.exec(select(BrowseCategory).where(BrowseCategory.slug == category["slug"])).all()
    assert len(rows) == 1, "the failed INSERT created no duplicate"
    assert rows[0].name_en == "RACER", "racer's row left untouched"
    assert rows[0].position == 42
