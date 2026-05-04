"""Read-side query functions for SoT entity tables.

Each function takes an explicit Session, returns Pydantic schemas (not
ORM rows), and queries the DB directly. No caching, no auth — this is
the raw query layer.
"""

import uuid

from sqlmodel import Session, select

from app.core.db.models import Category
from app.modules.sot.schemas import CategoryNode, CategoryTree


def list_categories_tree(session: Session) -> CategoryTree:
    """Return the full category hierarchy as a nested tree."""
    rows: list[Category] = list(session.exec(select(Category)).all())
    by_id: dict[uuid.UUID, CategoryNode] = {
        row.id: CategoryNode(
            id=row.id,
            parent_id=row.parent_id,
            slug=row.slug,
            name_en=row.name_en,
            name_pl=row.name_pl,
            children=[],
        )
        for row in rows
    }
    roots: list[CategoryNode] = []
    for node in by_id.values():
        if node.parent_id is None:
            roots.append(node)
        else:
            parent = by_id.get(node.parent_id)
            if parent is not None:
                parent.children.append(node)
            # Orphaned rows (parent missing) are silently skipped — they should
            # not exist given the FK RESTRICT, but defensive.

    # Stable order: by slug at each level
    def _sort_recursive(node: CategoryNode) -> None:
        node.children.sort(key=lambda c: c.slug)
        for c in node.children:
            _sort_recursive(c)

    roots.sort(key=lambda r: r.slug)
    for r in roots:
        _sort_recursive(r)

    return CategoryTree(roots=roots)
