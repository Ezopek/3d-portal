"""Read-side query functions for SoT entity tables.

Each function takes an explicit Session, returns Pydantic schemas (not
ORM rows), and queries the DB directly. No caching, no auth — this is
the raw query layer.
"""

import uuid
from collections.abc import Sequence
from enum import StrEnum

from sqlalchemy import func, nullslast, or_
from sqlmodel import Session, select

from app.core.db.models import (
    Category,
    Model,
    ModelExternalLink,
    ModelFile,
    ModelFileKind,
    ModelNote,
    ModelPrint,
    ModelSource,
    ModelStatus,
    ModelTag,
    Tag,
)
from app.modules.sot.schemas import (
    CategoryNode,
    CategorySummary,
    CategoryTree,
    ExternalLinkRead,
    FileListResponse,
    ModelDetail,
    ModelFileRead,
    ModelListResponse,
    ModelSummary,
    NoteRead,
    PrintRead,
    TagRead,
)


class ModelListSort(StrEnum):
    recent = "recent"
    oldest = "oldest"
    name_asc = "name_asc"
    name_desc = "name_desc"
    status = "status"
    rating = "rating"


def list_categories_tree(session: Session) -> CategoryTree:
    """Return the full category hierarchy as a nested tree.

    Each node carries `model_count`, the total number of non-deleted models
    in the subtree rooted at that node (i.e. self plus all descendants).
    """
    rows: list[Category] = list(session.exec(select(Category)).all())
    by_id: dict[uuid.UUID, CategoryNode] = {
        row.id: CategoryNode(
            id=row.id,
            parent_id=row.parent_id,
            slug=row.slug,
            name_en=row.name_en,
            name_pl=row.name_pl,
            children=[],
            model_count=0,
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

    # Count models directly attached to each category (excluding soft-deleted),
    # then accumulate up the tree by recursive subtree summation.
    direct_counts: dict[uuid.UUID, int] = {}
    direct_rows = session.exec(
        select(Model.category_id, func.count(Model.id))
        .where(Model.deleted_at.is_(None))
        .group_by(Model.category_id)
    ).all()
    for cat_id, n in direct_rows:
        direct_counts[cat_id] = n

    def _sum_subtree(node: CategoryNode) -> int:
        total = direct_counts.get(node.id, 0)
        for child in node.children:
            total += _sum_subtree(child)
        node.model_count = total
        return total

    for r in roots:
        _sum_subtree(r)

    return CategoryTree(roots=roots)


def list_tags(
    session: Session,
    *,
    q: str | None = None,
    limit: int = 200,
) -> list[TagRead]:
    """Return tags ordered by slug, optionally filtered by q in name_en/name_pl/slug."""
    stmt = select(Tag)
    if q:
        like = f"%{q.lower()}%"
        # SQLite LIKE is case-insensitive for ASCII by default; use lower() for safety
        stmt = stmt.where(
            or_(
                func.lower(Tag.slug).like(like),
                func.lower(Tag.name_en).like(like),
                func.lower(Tag.name_pl).like(like),
            )
        )
    stmt = stmt.order_by(Tag.slug).limit(limit)
    rows = list(session.exec(stmt).all())
    return [TagRead.model_validate(r) for r in rows]


def list_models(
    session: Session,
    *,
    category_ids: list[uuid.UUID] | None = None,
    status: ModelStatus | None = None,
    tag_ids: list[uuid.UUID] | None = None,
    source: ModelSource | None = None,
    q: str | None = None,
    sort: ModelListSort = ModelListSort.recent,
    include_deleted: bool = False,
    offset: int = 0,
    limit: int = 50,
) -> ModelListResponse:
    """List models with optional filters; tags eagerly attached per item.

    - category_ids: OR filter (model is in any of the listed categories).
    - tag_ids: AND filter (model has ALL listed tags).
    - source: exact match.
    - sort: ModelListSort enum; default = recent (created_at desc).
    """
    base = select(Model)
    if not include_deleted:
        base = base.where(Model.deleted_at.is_(None))
    if category_ids:
        base = base.where(Model.category_id.in_(category_ids))
    if status is not None:
        base = base.where(Model.status == status)
    if tag_ids:
        # AND semantics: model_id must appear in ModelTag for every tag_id given.
        for tid in tag_ids:
            base = base.where(Model.id.in_(select(ModelTag.model_id).where(ModelTag.tag_id == tid)))
    if source is not None:
        base = base.where(Model.source == source)
    if q:
        like = f"%{q.lower()}%"
        base = base.where(
            or_(
                func.lower(Model.name_en).like(like),
                func.lower(Model.name_pl).like(like),
                func.lower(Model.slug).like(like),
            )
        )

    # Total before pagination
    total_stmt = select(func.count()).select_from(base.subquery())
    total = session.exec(total_stmt).one()

    base = _apply_sort(base, sort)
    base = base.offset(offset).limit(limit)
    rows: Sequence[Model] = session.exec(base).all()

    # Eagerly fetch tags for the page
    model_ids = [m.id for m in rows]
    tags_by_model: dict[uuid.UUID, list[TagRead]] = {mid: [] for mid in model_ids}
    if model_ids:
        join_stmt = (
            select(ModelTag.model_id, Tag)
            .join(Tag, Tag.id == ModelTag.tag_id)
            .where(ModelTag.model_id.in_(model_ids))
        )
        for model_id, tag_row in session.exec(join_stmt).all():
            tags_by_model[model_id].append(TagRead.model_validate(tag_row))

    # Eagerly fetch gallery hints (top 4 image/print file ids per model + total
    # image/print count) so list cards can render a mini-carousel without a
    # separate fetch per row. Ordering matches list_model_files: position
    # NULLS LAST, then created_at ascending.
    gallery_by_model: dict[uuid.UUID, list[uuid.UUID]] = {mid: [] for mid in model_ids}
    image_counts: dict[uuid.UUID, int] = {mid: 0 for mid in model_ids}
    if model_ids:
        file_stmt = (
            select(
                ModelFile.model_id,
                ModelFile.id,
                ModelFile.kind,
                ModelFile.position,
                ModelFile.created_at,
            )
            .where(ModelFile.model_id.in_(model_ids))
            .where(ModelFile.kind.in_([ModelFileKind.image, ModelFileKind.print]))
            .order_by(nullslast(ModelFile.position.asc()), ModelFile.created_at.asc())
        )
        for row in session.exec(file_stmt).all():
            mid = row[0]
            fid = row[1]
            image_counts[mid] = image_counts.get(mid, 0) + 1
            if len(gallery_by_model[mid]) < 4:
                gallery_by_model[mid].append(fid)

    items = [
        ModelSummary.model_validate(
            {
                **m.model_dump(),
                "tags": tags_by_model.get(m.id, []),
                "gallery_file_ids": gallery_by_model.get(m.id, []),
                "image_count": image_counts.get(m.id, 0),
            }
        )
        for m in rows
    ]
    return ModelListResponse(items=items, total=total, offset=offset, limit=limit)


def _apply_sort(stmt, sort: ModelListSort):
    """Apply ORDER BY based on the sort key. Pure helper for testability."""
    if sort == ModelListSort.recent:
        return stmt.order_by(Model.created_at.desc())
    if sort == ModelListSort.oldest:
        return stmt.order_by(Model.created_at.asc())
    if sort == ModelListSort.name_asc:
        return stmt.order_by(func.lower(Model.name_en).asc())
    if sort == ModelListSort.name_desc:
        return stmt.order_by(func.lower(Model.name_en).desc())
    if sort == ModelListSort.status:
        return stmt.order_by(Model.status.asc(), Model.created_at.desc())
    if sort == ModelListSort.rating:
        # Rating desc, NULLs last; SQLAlchemy: nullslast(col.desc())
        return stmt.order_by(nullslast(Model.rating.desc()), Model.created_at.desc())
    return stmt.order_by(Model.created_at.desc())  # safety net


def get_model_detail(
    session: Session,
    model_id: uuid.UUID,
    *,
    include_deleted: bool = False,
) -> ModelDetail | None:
    """Return a Model with full embed of related entities, or None if not found."""
    stmt = select(Model).where(Model.id == model_id)
    if not include_deleted:
        stmt = stmt.where(Model.deleted_at.is_(None))
    m = session.exec(stmt).first()
    if m is None:
        return None

    cat = session.exec(select(Category).where(Category.id == m.category_id)).one()

    tag_rows = session.exec(
        select(Tag)
        .join(ModelTag, ModelTag.tag_id == Tag.id)
        .where(ModelTag.model_id == model_id)
        .order_by(Tag.slug)
    ).all()
    tags = [TagRead.model_validate(t) for t in tag_rows]

    file_rows = session.exec(
        select(ModelFile).where(ModelFile.model_id == model_id).order_by(ModelFile.created_at)
    ).all()
    files = [ModelFileRead.model_validate(f) for f in file_rows]

    note_rows = session.exec(
        select(ModelNote).where(ModelNote.model_id == model_id).order_by(ModelNote.created_at)
    ).all()
    notes = [NoteRead.model_validate(n) for n in note_rows]

    print_rows = session.exec(
        select(ModelPrint).where(ModelPrint.model_id == model_id).order_by(ModelPrint.created_at)
    ).all()
    prints = [PrintRead.model_validate(p) for p in print_rows]

    link_rows = session.exec(
        select(ModelExternalLink)
        .where(ModelExternalLink.model_id == model_id)
        .order_by(ModelExternalLink.source)
    ).all()
    external_links = [ExternalLinkRead.model_validate(link) for link in link_rows]

    gallery_rows = session.exec(
        select(ModelFile.id)
        .where(ModelFile.model_id == model_id)
        .where(ModelFile.kind.in_([ModelFileKind.image, ModelFileKind.print]))
        .order_by(nullslast(ModelFile.position.asc()), ModelFile.created_at.asc())
    ).all()
    gallery_file_ids = list(gallery_rows)

    return ModelDetail.model_validate(
        {
            **m.model_dump(),
            "tags": tags,
            "gallery_file_ids": gallery_file_ids[:4],
            "image_count": len(gallery_file_ids),
            "category": CategorySummary.model_validate(cat),
            "files": files,
            "prints": prints,
            "notes": notes,
            "external_links": external_links,
        }
    )


def list_model_files(
    session: Session,
    model_id: uuid.UUID,
    *,
    kind: ModelFileKind | None = None,
) -> FileListResponse | None:
    """List files attached to a model.

    Returns None if the model does not exist (so the caller can 404).
    Returns an empty envelope if the model exists but has no files.
    Filtering by kind is exact match.

    For image/print kinds the list is ordered by (position NULLS LAST,
    created_at) so admin-curated ordering takes precedence and unsorted
    files fall back to upload-time order.
    """
    model_exists = session.exec(select(Model.id).where(Model.id == model_id)).first()
    if model_exists is None:
        return None

    stmt = select(ModelFile).where(ModelFile.model_id == model_id)
    if kind is not None:
        stmt = stmt.where(ModelFile.kind == kind)
    if kind in (ModelFileKind.image, ModelFileKind.print):
        from sqlalchemy import nullslast

        stmt = stmt.order_by(nullslast(ModelFile.position.asc()), ModelFile.created_at.asc())
    else:
        stmt = stmt.order_by(ModelFile.created_at.asc())
    rows = session.exec(stmt).all()
    return FileListResponse(items=[ModelFileRead.model_validate(r) for r in rows])
