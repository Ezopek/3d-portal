"""Deliberate admin-run entrypoint for the starter browse categories (Story 49.2).

Creates the eight approved ``BrowseCategory`` rows idempotently by delegating to
``app.core.db.seed.seed_browse_categories``. Writes NO ``ModelBrowseCategory``
rows — no model is assigned to a category by this script, and a model with zero
categories is valid and stays public (FR26-CAT-2).

This is intentionally NOT wired into the FastAPI lifespan the way ``seed_admin``
is: auto-seeding fixed content on every boot/deploy would resurrect
owner-deleted categories and fight admin governance of renames, reorders and
deletes (Story 49.5). Run it once, on purpose, against the target database::

    python -m scripts.seed_browse_categories

The seed is create-if-absent by slug and safe to re-run: it never duplicates a
row and never clobbers an existing (admin-edited) row.
"""

from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.db.models import BrowseCategory
from app.core.db.seed import seed_browse_categories
from app.core.db.session import get_engine


def main(engine: Engine | None = None) -> None:
    """Seed the starter browse categories and print a truthful post-condition count.

    ``engine`` is injectable for tests (a throwaway SQLite engine); it defaults to
    the app engine for the real admin-run invocation. The reported count is queried
    FROM THE DATABASE after seeding — not printed from ``STARTER_BROWSE_CATEGORIES``
    — so a partial seed is visibly distinguishable from a full one.
    """
    engine = engine or get_engine()
    seed_browse_categories(engine)
    with Session(engine) as session:
        category_count = len(session.exec(select(BrowseCategory)).all())
    print(f"seeded browse categories: {category_count} categories present")


if __name__ == "__main__":
    main()
