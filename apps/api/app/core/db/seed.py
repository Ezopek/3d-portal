import uuid

from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.auth.password import hash_password
from app.core.db.models import Tag, TagGroup, User, UserRole


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

    Writes ONLY ``tag_group`` and ``tag`` rows — no ``Model``, ``ModelTag`` or
    ``Category`` reads/writes; models stay untagged after seeding (HANDOFF §1/§5).

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
