"""Deliberate admin-run entrypoint for the starter facet taxonomy (Story 41.3).

Populates the starter ``TagGroup`` + ``Tag`` rows (HANDOFF §8) idempotently by
delegating to ``app.core.db.seed.seed_taxonomy``. Writes NO ``Model`` /
``ModelTag`` rows — models stay untagged.

This is intentionally NOT wired into the FastAPI lifespan the way ``seed_admin``
is: auto-seeding a fixed taxonomy on every boot/deploy would resurrect
owner-deleted groups and fight the admin governance of renames/reorders/deletes
(HANDOFF §9). Run it once, on purpose, against the target database::

    python -m scripts.seed_taxonomy

or, if you prefer a one-liner::

    python -c "from app.core.db.seed import seed_taxonomy; \\
from app.core.db.session import get_engine; seed_taxonomy(get_engine())"

The seed is create-if-absent by slug and safe to re-run: it never duplicates
rows and never clobbers an existing (admin-edited) row.
"""

from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.db.models import Tag, TagGroup
from app.core.db.seed import seed_taxonomy
from app.core.db.session import get_engine


def main(engine: Engine | None = None) -> None:
    """Seed the starter taxonomy and print a truthful post-condition count.

    ``engine`` is injectable for tests (a throwaway SQLite engine); it defaults to
    the app engine for the real admin-run invocation. The reported group/tag counts
    are queried FROM THE DATABASE after seeding — not printed from the dataset
    constants — so a partial seed is visibly distinguishable from a full one.
    """
    engine = engine or get_engine()
    seed_taxonomy(engine)
    with Session(engine) as session:
        group_count = len(session.exec(select(TagGroup)).all())
        tag_count = len(session.exec(select(Tag)).all())
    print(f"seeded taxonomy: {group_count} groups / {tag_count} tags present")


if __name__ == "__main__":
    main()
