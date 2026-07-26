import uuid

from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.auth.password import hash_password
from app.core.db.models import BrowseCategory, Tag, TagGroup, User, UserRole


def seed_admin(engine: Engine, *, email: str, password: str, display_name: str) -> None:
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == email)).first()
        if existing is not None:
            return
        user = User(
            email=email,
            display_name=display_name,
            role=UserRole.admin,
            password_hash=hash_password(password),
        )
        session.add(user)
        try:
            session.commit()
        except IntegrityError:
            # Concurrent startup race: another worker inserted the same admin row.
            # Treat as success — the goal (admin user exists) is achieved.
            session.rollback()


# ---------------------------------------------------------------------------
# Starter facet taxonomy (Story 41.3)
# ---------------------------------------------------------------------------

# OWNER-EDITABLE seed content, derived from HANDOFF-tagi-fasetowe.md §8
# ("do edycji przez właściciela"). This is deliberately a plain, ordered Python
# data structure — not a frozen contract. The owner may add/rename/reorder
# groups and tags here; because the seed is create-if-absent by slug and never
# updates existing rows, edits made after a group/tag already exists in the DB
# do NOT propagate (admin governance of renames/reorders wins — HANDOFF §9).
#
# Slugs are HAND-AUTHORED ASCII (English-derived), globally unique, and are
# NEVER derived by feeding name_pl through admin_service._slugify: that regex is
# diacritic-lossy ("Łazienka" -> "azienka", "Oświetlenie" -> "o-wietlenie") and
# would produce mangled, collision-prone slugs. name_en is NOT NULL on both the
# TagGroup and Tag ORM entities, so every row carries a mechanically-translated
# English name. §9.3 pins Typ (position 0) and Pomieszczenie (position 1) as the
# two primary axes; group order otherwise follows §8 top-to-bottom. Each group's
# tags carry a dense, 0-based group_position in the order listed here.
STARTER_TAXONOMY: list[dict] = [
    {
        "slug": "type",
        "name_en": "Type",
        "name_pl": "Typ",
        "position": 0,
        "tags": [
            {"slug": "decorations", "name_en": "Decorations", "name_pl": "Dekoracje"},
            {"slug": "vases", "name_en": "Vases", "name_pl": "Wazony"},
            {"slug": "containers", "name_en": "Containers", "name_pl": "Pojemniki"},
            {"slug": "organizers", "name_en": "Organizers", "name_pl": "Organizery"},
            {
                "slug": "articulated-figures",
                "name_en": "Articulated figures",
                "name_pl": "Figurki ruchome",
            },
            {"slug": "holders", "name_en": "Holders", "name_pl": "Uchwyty"},
            {"slug": "lighting", "name_en": "Lighting", "name_pl": "Oświetlenie"},
            {"slug": "furniture", "name_en": "Furniture", "name_pl": "Meble"},
            {"slug": "clips", "name_en": "Clips", "name_pl": "Klipsy"},
            {"slug": "gadgets", "name_en": "Gadgets", "name_pl": "Gadżety"},
            {"slug": "cases", "name_en": "Cases", "name_pl": "Etui"},
            {"slug": "plant-pots", "name_en": "Plant pots", "name_pl": "Doniczki"},
        ],
    },
    {
        "slug": "room",
        "name_en": "Room",
        "name_pl": "Pomieszczenie",
        "position": 1,
        "tags": [
            {"slug": "kitchen", "name_en": "Kitchen", "name_pl": "Kuchnia"},
            {"slug": "bathroom", "name_en": "Bathroom", "name_pl": "Łazienka"},
            {"slug": "desk", "name_en": "Desk", "name_pl": "Biurko"},
            {"slug": "home", "name_en": "Home", "name_pl": "Dom"},
            {"slug": "car", "name_en": "Car", "name_pl": "Auto"},
            {"slug": "pets", "name_en": "Pets", "name_pl": "Zwierzęta"},
            {"slug": "garden", "name_en": "Garden", "name_pl": "Ogród"},
        ],
    },
    {
        "slug": "system",
        "name_en": "System",
        "name_pl": "System",
        "position": 2,
        "tags": [
            {"slug": "gridfinity", "name_en": "Gridfinity", "name_pl": "Gridfinity"},
            {"slug": "multiboard", "name_en": "Multiboard", "name_pl": "Multiboard"},
            {"slug": "bin-shells", "name_en": "Bin Shells", "name_pl": "Bin Shells"},
        ],
    },
    {
        "slug": "use-case",
        "name_en": "Use case",
        "name_pl": "Zastosowanie",
        "position": 3,
        "tags": [
            {"slug": "repairs", "name_en": "Repairs", "name_pl": "Naprawy"},
            {"slug": "storage", "name_en": "Storage", "name_pl": "Przechowywanie"},
            {"slug": "electronics", "name_en": "Electronics", "name_pl": "Elektronika"},
            {"slug": "soldering", "name_en": "Soldering", "name_pl": "Lutowanie"},
            {"slug": "inserts", "name_en": "Inserts", "name_pl": "Wkładki"},
            {"slug": "calibration", "name_en": "Calibration", "name_pl": "Kalibracja"},
        ],
    },
    {
        "slug": "printer",
        "name_en": "Printer",
        "name_pl": "Drukarka",
        "position": 4,
        "tags": [
            {"slug": "k1-max", "name_en": "K1 Max", "name_pl": "K1 Max"},
            {"slug": "accessories", "name_en": "Accessories", "name_pl": "Akcesoria"},
        ],
    },
    {
        "slug": "material",
        "name_en": "Material",
        "name_pl": "Materiał",
        "position": 5,
        "tags": [
            {"slug": "pla", "name_en": "PLA", "name_pl": "PLA"},
            {"slug": "petg", "name_en": "PETG", "name_pl": "PETG"},
            {"slug": "pctg", "name_en": "PCTG", "name_pl": "PCTG"},
            {"slug": "tpu", "name_en": "TPU", "name_pl": "TPU"},
        ],
    },
    {
        "slug": "creator",
        "name_en": "Creator (premium)",
        "name_pl": "Twórca (premium)",
        "position": 6,
        # §8 lists "Jarek, …" — the ellipsis is illustrative. Seed only the
        # confirmed entry; the owner adds more via admin governance.
        "tags": [
            {"slug": "jarek", "name_en": "Jarek", "name_pl": "Jarek"},
        ],
    },
    {
        "slug": "level",
        "name_en": "Level",
        "name_pl": "Poziom",
        "position": 7,
        "tags": [
            {"slug": "premium", "name_en": "Premium", "name_pl": "Premium"},
        ],
    },
]


def seed_taxonomy(engine: Engine) -> None:
    """Idempotently populate the starter facet taxonomy (TagGroup + Tag only).

    Mirrors ``seed_admin``: create-if-absent keyed on the unique ``slug``, never
    updates or deletes an existing row (an admin rename/reorder wins), and treats
    a concurrent-insert ``IntegrityError`` as success by rolling back.

    Transaction boundary (AC #9): **per-row commit** — each group and each tag is
    committed on its own, matching ``seed_admin``'s single-entity commit. A
    failure partway through therefore leaves already-committed rows in place; a
    clean re-run is create-if-absent and completes the remainder, converging to
    the full dataset exactly once with no duplicates or orphan tags.

    Writes ONLY ``tag_group`` and ``tag`` rows — no ``Model`` or ``ModelTag``
    reads/writes; models stay untagged after seeding (HANDOFF §1/§5).

    Deliberate admin-run action — NOT wired into the FastAPI lifespan (unlike
    ``seed_admin``), so a redeploy cannot resurrect an owner-deleted group.
    Invoke explicitly, e.g.::

        python -c "from app.core.db.seed import seed_taxonomy; \\
from app.core.db.session import get_engine; seed_taxonomy(get_engine())"

    or run ``python -m`` / ``python scripts/seed_taxonomy.py`` (see that script).
    """
    with Session(engine) as session:
        group_ids: dict[str, uuid.UUID] = {}
        for group in STARTER_TAXONOMY:
            group_ids[group["slug"]] = _upsert_absent_group(session, group)
        for group in STARTER_TAXONOMY:
            parent_id = group_ids[group["slug"]]
            for position, tag in enumerate(group["tags"]):
                _insert_absent_tag(session, tag, parent_id, position)


def _upsert_absent_group(session: Session, group: dict) -> uuid.UUID:
    existing = session.exec(select(TagGroup).where(TagGroup.slug == group["slug"])).first()
    if existing is not None:
        return existing.id
    row = TagGroup(
        slug=group["slug"],
        name_en=group["name_en"],
        name_pl=group["name_pl"],
        position=group["position"],
    )
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        # Concurrent insert of the same group slug — treat as success and adopt
        # the row the other writer committed.
        session.rollback()
        return session.exec(select(TagGroup).where(TagGroup.slug == group["slug"])).one().id
    session.refresh(row)
    return row.id


def _insert_absent_tag(
    session: Session, tag: dict, group_id: uuid.UUID, group_position: int
) -> None:
    existing = session.exec(select(Tag).where(Tag.slug == tag["slug"])).first()
    if existing is not None:
        return
    row = Tag(
        slug=tag["slug"],
        name_en=tag["name_en"],
        name_pl=tag["name_pl"],
        group_id=group_id,
        group_position=group_position,
    )
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        # Concurrent insert of the same tag slug — treat as success.
        session.rollback()


# ---------------------------------------------------------------------------
# Starter browse categories (Story 49.2)
# ---------------------------------------------------------------------------

# OWNER-EDITABLE seed content for the Initiative 26 browse taxonomy, transcribed
# from the approved eight-row set in the UX experience spine
# (_bmad-output/planning-artifacts/ux-designs/ux-3d-portal-2026-07-26/EXPERIENCE.md
# :84-91 for slug/labels/position, :101-156 for the per-category inclusion
# criterion). Gate G26-CAT-SET closed this content on 2026-07-26 (commit 48db6bb),
# so the set, its order and its wording are approved content — not a dev-time
# judgement call and not something to "improve" here.
#
# EVIDENCE, and its limits (Story 49.2 §6 F-1). EXPERIENCE.md:192 owed a
# distribution check confirming each of the eight would land >= 3 models under
# deliberate curation. It was discharged on 2026-07-26, READ-ONLY (SQLite
# `mode=ro` URI — no write was possible) over 131 active catalogue records
# exposed as name + tag slugs only, then analysed TWICE independently: a full
# many-to-many curation (verdict PASS, coverage 122/131) and an adversarial
# falsification attempt (verdict PASS — the ">= 3" claim could not be refuted).
# Both agree that every category clears the bar, and that `replacement-parts`
# clears it at EXACTLY three. That zero-margin row therefore stays, unchanged and
# un-merged, and is registered as a tiny-category monitoring item for Story 52.3;
# any later merge or retirement is admin governance (Story 49.5), never a re-seed.
# Conclusion: keep the approved eight — reorder nothing, merge nothing, drop
# nothing. The capture and both reports live under .hermes/run-logs/ (local,
# gitignored). NOTHING in the test suite can re-derive that evidence: the tests
# run against an empty scratch database with no access to the real catalogue, so
# the dataset tests are a POST-DECISION DRIFT GUARD and nothing more.
#
# `inclusion_criterion` stores the CANONICAL ENGLISH sentence: the entity has
# exactly one such field (`_entities.py:157`) and EXPERIENCE.md supplies the
# criteria in English only — "bilingual" applies to the labels. Exactly two
# normalisations were applied to the source sentences: (1) strip markdown `*`
# emphasis, which affects only `storage-organization`, and (2) capitalise the
# first letter. Everything else is preserved byte-for-byte, including the
# `printer-3d` em dash and the `toys-games` Oxford comma.
#
# Like STARTER_TAXONOMY above, this is a plain ordered data structure and NOT a
# frozen contract — but because the seed is create-if-absent by slug and never
# updates an existing row, edits made here after a category already exists in the
# DB do NOT propagate (admin governance of renames/reorders wins). `description_en`,
# `description_pl` and `parent_id` are deliberately absent: EXPERIENCE.md supplies
# no description distinct from the criterion, and its rejected-candidates table
# explicitly rejects seeding a starter parent->child tree.
STARTER_BROWSE_CATEGORIES: list[dict] = [
    {
        "slug": "storage-organization",
        "name_en": "Storage & Organization",
        "name_pl": "Przechowywanie i organizacja",
        "position": 0,
        "inclusion_criterion": (
            "The model's primary purpose is to hold, sort or tidy other objects."
        ),
    },
    {
        "slug": "home-decor",
        "name_en": "Home Decor",
        "name_pl": "Dekoracje i wystrój",
        "position": 1,
        "inclusion_criterion": (
            "The model is chosen mainly for how it looks in a living space, "
            "not for a job it performs."
        ),
    },
    {
        "slug": "holders-mounts",
        "name_en": "Holders & Mounts",
        "name_pl": "Uchwyty i mocowania",
        "position": 2,
        "inclusion_criterion": (
            "The model exists to hold one specific object in a fixed position, "
            "or to attach something to a surface."
        ),
    },
    {
        "slug": "electronics-cables",
        "name_en": "Electronics & Cables",
        "name_pl": "Elektronika i kable",
        "position": 3,
        "inclusion_criterion": (
            "The model houses, routes, protects or mounts electronics, wiring or connectors."
        ),
    },
    {
        "slug": "tools-workshop",
        "name_en": "Tools & Workshop",
        "name_pl": "Narzędzia i warsztat",
        "position": 4,
        "inclusion_criterion": (
            "The model is a tool, jig, fixture or aid used while making, measuring "
            "or repairing something."
        ),
    },
    {
        "slug": "printer-3d",
        "name_en": "3D Printer & Accessories",
        "name_pl": "Drukarka 3D i akcesoria",
        "position": 5,
        "inclusion_criterion": (
            "The model only makes sense to someone who owns a 3D printer — "
            "it upgrades, maintains or feeds the printer itself."
        ),
    },
    {
        "slug": "toys-games",
        "name_en": "Toys, Games & Figures",
        "name_pl": "Zabawki, gry i figurki",
        "position": 6,
        "inclusion_criterion": (
            "The model's purpose is play, collecting, or display as a character "
            "or object of interest."
        ),
    },
    {
        "slug": "replacement-parts",
        "name_en": "Replacement Parts",
        "name_pl": "Części zamienne",
        "position": 7,
        "inclusion_criterion": (
            "The model replaces or repairs a broken or missing part of an existing "
            "manufactured object."
        ),
    },
]


def seed_browse_categories(engine: Engine) -> None:
    """Idempotently create the approved starter browse categories (Story 49.2).

    Mirrors ``seed_taxonomy``: create-if-absent keyed on the unique ``slug``, never
    updates and never deletes an existing row (an admin rename, reorder or
    rewritten criterion wins), and treats a concurrent-insert ``IntegrityError``
    as success by rolling back.

    Transaction boundary (AC-13): **per-row commit**, matching ``seed_taxonomy``.
    A failure partway through therefore leaves the rows committed before the fault
    in place; a clean re-run is create-if-absent and completes the remainder,
    converging to the eight rows exactly once with no duplicates.

    Writes ONLY ``browse_category`` rows — no ``ModelBrowseCategory``, ``Model``,
    ``Tag`` or ``TagGroup`` read or write. Nothing is assigned to a category here:
    a model with zero categories is valid and stays public (FR26-CAT-2), and
    curation is a later, deliberate admin activity.

    Deliberate admin-run action — NOT wired into the FastAPI lifespan (unlike
    ``seed_admin``), so a redeploy cannot resurrect an owner-deleted category.
    Invoke it once, on purpose, against the target database::

        python -m scripts.seed_browse_categories
    """
    with Session(engine) as session:
        for category in STARTER_BROWSE_CATEGORIES:
            _insert_absent_category(session, category)


def _insert_absent_category(session: Session, category: dict) -> None:
    existing = session.exec(
        select(BrowseCategory).where(BrowseCategory.slug == category["slug"])
    ).first()
    if existing is not None:
        return
    row = BrowseCategory(
        slug=category["slug"],
        name_en=category["name_en"],
        name_pl=category["name_pl"],
        position=category["position"],
        inclusion_criterion=category["inclusion_criterion"],
    )
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        # Concurrent insert of the same category slug — treat as success. NO
        # post-rollback re-query here: _upsert_absent_group only does that because
        # it must return an id for its tag phase, and this seed has no second
        # phase. Stay exactly on the _insert_absent_tag contract.
        session.rollback()
