"""Read-side query functions for SoT entity tables.

Each function takes an explicit Session, returns Pydantic schemas (not
ORM rows), and queries the DB directly. No caching, no auth — this is
the raw query layer.
"""

import uuid
from collections.abc import Sequence
from enum import StrEnum

from sqlalchemy import and_, func, nullslast, or_
from sqlmodel import Session, select

from app.core.db.models import (
    BrowseCategory,
    Model,
    ModelBrowseCategory,
    ModelExternalLink,
    ModelFile,
    ModelFileKind,
    ModelNote,
    ModelPrint,
    ModelSource,
    ModelStatus,
    ModelTag,
    Tag,
    TagGroup,
)
from app.core.db.session import unicode_lower
from app.modules.sot.schemas import (
    BrowseCategoryRead,
    BrowseCategorySummary,
    ExternalLinkRead,
    FileListResponse,
    ModelDetail,
    ModelFileRead,
    ModelListResponse,
    ModelSummary,
    NoteRead,
    PrintRead,
    TagGroupRead,
    TagGroupsResponse,
    TagListItem,
    TagRead,
    TagReadWithCount,
)


class ModelListSort(StrEnum):
    recent = "recent"
    oldest = "oldest"
    name_asc = "name_asc"
    name_desc = "name_desc"
    status = "status"
    rating = "rating"


class TagMatch(StrEnum):
    all = "all"
    any = "any"


def _tag_model_counts(session: Session) -> dict[uuid.UUID, int]:
    """Distinct non-deleted models per tag (Story 42.2 D-COUNT-1).

    One GROUP BY over model_tag joined to model, filtered to live rows
    (`Model.deleted_at IS NULL`). Hits the ix_model_tag_tag_model covering
    index. ModelTag's
    composite PK (model_id, tag_id) means each row is a distinct model per
    tag, so func.count() is the distinct-model count without DISTINCT. No
    N+1: one query feeds both /api/tags?with_counts and /api/tag-groups.
    """
    rows = session.exec(
        select(ModelTag.tag_id, func.count())
        .select_from(ModelTag)
        .join(Model, Model.id == ModelTag.model_id)
        .where(Model.deleted_at.is_(None))
        .group_by(ModelTag.tag_id)
    ).all()
    return {tag_id: n for tag_id, n in rows}


def list_tags(
    session: Session,
    *,
    q: str | None = None,
    limit: int = 200,
    with_counts: bool = False,
) -> list[TagListItem]:
    """Return tags ordered by slug, optionally filtered by q in name_en/name_pl/slug.

    Each item is a TagListItem: the enriched TagRead shape (incl. group_id /
    group_position) plus an opt-in model_count. When with_counts is False the
    count stays None and the TagListItem serializer omits the key entirely;
    when True, one aggregate query (`_tag_model_counts`) attaches the
    distinct-non-deleted-model count to whichever tags the q/limit filter
    returned (Story 42.2 AC #2/#3).
    """
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
    counts = _tag_model_counts(session) if with_counts else {}
    items: list[TagListItem] = []
    for r in rows:
        item = TagListItem.model_validate(r)
        if with_counts:
            item.model_count = counts.get(r.id, 0)
        items.append(item)
    return items


def list_tag_groups(session: Session) -> TagGroupsResponse:
    """Return the facet taxonomy: {groups, groupless} with per-tag counts.

    Story 42.2 (D-ENVELOPE-1). Exactly three reads regardless of cardinality
    (all TagGroup rows, all Tag rows, one `_tag_model_counts` aggregate);
    groups/tags are bucketed in Python (no per-group query, no N+1). Groups
    are ordered `(position, slug)` and include empty groups (`tags: []`);
    within a group tags are ordered `(group_position, slug)`. Tags with
    `group_id IS NULL` are returned in the sibling `groupless` array (same
    ordering), each carrying model_count. No lifecycle filtering — neither
    Tag nor TagGroup has a soft-delete/hidden column (D-LIFECYCLE-1).
    """
    groups = list(session.exec(select(TagGroup)).all())
    tags = list(session.exec(select(Tag)).all())
    counts = _tag_model_counts(session)

    def _with_count(t: Tag) -> TagReadWithCount:
        return TagReadWithCount(
            id=t.id,
            slug=t.slug,
            name_en=t.name_en,
            name_pl=t.name_pl,
            group_id=t.group_id,
            group_position=t.group_position,
            model_count=counts.get(t.id, 0),
        )

    def _tag_sort_key(t: Tag) -> tuple[int, str]:
        return (t.group_position, t.slug)

    tags_by_group: dict[uuid.UUID, list[Tag]] = {}
    groupless_tags: list[Tag] = []
    for t in tags:
        if t.group_id is None:
            groupless_tags.append(t)
        else:
            tags_by_group.setdefault(t.group_id, []).append(t)

    group_reads = [
        TagGroupRead(
            id=g.id,
            slug=g.slug,
            name_en=g.name_en,
            name_pl=g.name_pl,
            position=g.position,
            tags=[_with_count(t) for t in sorted(tags_by_group.get(g.id, []), key=_tag_sort_key)],
        )
        for g in sorted(groups, key=lambda g: (g.position, g.slug))
    ]
    groupless = [_with_count(t) for t in sorted(groupless_tags, key=_tag_sort_key)]
    return TagGroupsResponse(groups=group_reads, groupless=groupless)


def _browse_category_model_counts(session: Session) -> dict[uuid.UUID, int]:
    """Distinct non-deleted models per browse category (Story 49.3 AC-4).

    Sibling of `_tag_model_counts`, deliberately NOT a generalization of it —
    that one is keyed by tag_id and feeds /api/tags + /api/tag-groups. One
    GROUP BY over model_browse_category joined to model, filtered to live rows
    (`Model.deleted_at IS NULL`). Hits the ix_model_browse_category_cat_model
    covering index. ModelBrowseCategory's composite PK (model_id, category_id)
    means each row is a distinct model per category, so func.count() is the
    distinct-model count without DISTINCT. One statement regardless of
    category or assignment cardinality — that is AC-23(a).
    """
    rows = session.exec(
        select(ModelBrowseCategory.category_id, func.count())
        .select_from(ModelBrowseCategory)
        .join(Model, Model.id == ModelBrowseCategory.model_id)
        .where(Model.deleted_at.is_(None))
        .group_by(ModelBrowseCategory.category_id)
    ).all()
    return {category_id: n for category_id, n in rows}


def _browse_category_read(c: BrowseCategory, counts: dict[uuid.UUID, int]) -> BrowseCategoryRead:
    """Decision AY's nine-key public-read item. `inclusion_criterion` is stored
    on the entity but deliberately absent from this contract."""
    return BrowseCategoryRead(
        id=c.id,
        slug=c.slug,
        name_en=c.name_en,
        name_pl=c.name_pl,
        description_en=c.description_en,
        description_pl=c.description_pl,
        position=c.position,
        parent_id=c.parent_id,
        model_count=counts.get(c.id, 0),
    )


def list_browse_categories(session: Session) -> list[BrowseCategoryRead]:
    """Return every browse category, flat, ordered `(position, slug)`.

    Story 49.3 (Initiative 26, Decision AY). Exactly two reads regardless of
    cardinality: all BrowseCategory rows (ordered in SQL — unlike
    list_tag_groups there is no bucketing to do in Python) plus one
    `_browse_category_model_counts` aggregate. That is AC-23(a).

    The list is FLAT — `parent_id` is exposed as a scalar and no row is nested
    under another. This is NOT the retired Initiative 25 recursive category
    tree; it is a new additive browse contract that happens to reuse the path.

    Categories with zero assigned models are RETURNED with `model_count: 0`,
    never filtered out (AC-3) — the curation QA surface exists precisely to
    see them. No lifecycle filtering: BrowseCategory has no soft-delete column.
    """
    rows = session.exec(
        select(BrowseCategory).order_by(BrowseCategory.position, BrowseCategory.slug)
    ).all()
    counts = _browse_category_model_counts(session)
    return [_browse_category_read(c, counts) for c in rows]


def get_browse_category_by_slug(session: Session, slug: str) -> BrowseCategoryRead | None:
    """Resolve one browse category by its stable slug, or None if absent.

    Story 49.3 AC-7/AC-8. `slug` is unique (uq_browse_category_slug), so this
    is an exact single-row lookup. Returning None (rather than raising) keeps
    the HTTP concern in the router, mirroring `get_model_detail`.
    """
    row = session.exec(select(BrowseCategory).where(BrowseCategory.slug == slug)).first()
    if row is None:
        return None
    return _browse_category_read(row, _browse_category_model_counts(session))


def list_models(
    session: Session,
    *,
    status: ModelStatus | None = None,
    tag_ids: list[uuid.UUID] | None = None,
    tag_match: TagMatch = TagMatch.all,
    untagged: bool = False,
    source: ModelSource | None = None,
    category: str | None = None,
    uncategorized: bool = False,
    q: str | None = None,
    external_url: str | None = None,
    sort: ModelListSort = ModelListSort.recent,
    include_deleted: bool = False,
    offset: int = 0,
    limit: int = 50,
) -> ModelListResponse:
    """List models with optional filters; tags eagerly attached per item.

    Facet-tag filtering (Initiative 25):

    - tag_ids + tag_match=all (default): AND between facet groups, OR within a
      group. The requested ids are partitioned by `Tag.group_id`; groupless
      tags (`group_id IS NULL`) form one shared "groupless" bucket; a requested
      id absent from the DB becomes its own zero-member bucket → unsatisfiable
      AND → empty result.
    - tag_ids + tag_match=any: pure OR across all listed tags, grouping ignored;
      an unknown id simply never matches and is silently dropped.
    - untagged=true: surfaces zero-tag models (`Model.id NOT IN model_tag`).
      Combined with tag_ids it is OR-unioned with the tag predicate (a model can
      never be both, so AND would be always-empty).
    - The composed tag/untagged predicate is applied to `base` once, before the
      total-count subquery, so `total` and pagination stay filter-correct.
    - source: exact match.
    - category: Initiative 26 browse-category scope (Story 49.3), addressed by
      SLUG, exactly one value, no `category_match` mode. AND-ed onto `base` as
      its own IN-subquery `.where()` — never folded into the tag composition
      and never a SQL JOIN. Applied before the total-count subquery, so `total`
      and pagination stay filter-correct. An unknown slug yields an empty page
      with `total: 0` (200, never 404).
    - uncategorized: Initiative 26 (Story 52.2) zero-category models
      (`Model.id NOT IN model_browse_category`), backing the admin curation
      queue. A PURE AND, structurally outside the tag/untagged composition —
      deliberately NOT OR-unioned with `category` the way `untagged` unions
      with `tag_ids`. That union exists because both address the same axis
      through one shipped checkbox list; categories have no such control (MVP
      allows exactly one slug-addressed scope). Combined with `category` the
      result is therefore an empty page, which is a true statement — no model
      is both in a category and in none — not a special case.
    - external_url: exact match against a model's `ModelExternalLink.url`
      (any source). Primary use case is agent-runbook dedup-by-source-URL
      pre-flight check (TB-004): hit returns the existing model's UUID,
      miss returns empty so the agent proceeds with a fresh import.
    - q: Initiative 26 (Story 49.4) case-insensitive substring over a model's own
      `name_en` / `name_pl` / `slug` PLUS the `name_pl` / `name_en` of any tag
      ASSIGNED to it. The tag branch is one extra disjunct inside the same
      `or_()`, expressed as an `IN` membership subquery (`model_tag` joined to
      `tag`) so the outer SELECT shape — and therefore `total`, sorting and
      pagination — stays unchanged and a model matching several tags is still
      returned exactly once. `tag.slug` is deliberately NOT matched (unlike
      `GET /api/tags?q=`, which does): slugs are internal. Tag-name matching does
      not enter `tag_match` grouping and does not widen `untagged`, which can
      never satisfy a membership predicate. The tag columns are folded with
      `unicode_lower` (full Unicode, so `Łazienka` is reachable by `łazienka`);
      the model-name columns keep the shipped ASCII-only `lower()`, an
      inherited limitation recorded in `deferred-work.md` rather than widened
      here.
    - sort: ModelListSort enum; default = recent (created_at desc).
    """
    base = select(Model)
    if not include_deleted:
        base = base.where(Model.deleted_at.is_(None))
    if status is not None:
        base = base.where(Model.status == status)

    tag_predicate = None
    if tag_ids:
        if tag_match == TagMatch.any:
            # Pure OR across all selected tags; grouping ignored. Unknown ids
            # contribute no rows and are thus silently ignored.
            tag_predicate = Model.id.in_(
                select(ModelTag.model_id).where(ModelTag.tag_id.in_(tag_ids))
            )
        else:
            # tag_match=all: AND between groups, OR within a group. Partition the
            # requested ids by Tag.group_id; groupless tags share one bucket; an
            # unknown id becomes its own zero-member bucket (unsatisfiable AND).
            group_of = dict(
                session.exec(select(Tag.id, Tag.group_id).where(Tag.id.in_(tag_ids))).all()
            )
            buckets: dict[object, set[uuid.UUID]] = {}
            for tid in tag_ids:
                if tid not in group_of:
                    key: object = ("missing", tid)
                elif group_of[tid] is None:
                    key = "groupless"
                else:
                    key = group_of[tid]
                buckets.setdefault(key, set()).add(tid)
            clauses = [
                Model.id.in_(select(ModelTag.model_id).where(ModelTag.tag_id.in_(bucket_ids)))
                for bucket_ids in buckets.values()
            ]
            tag_predicate = and_(*clauses)

    untagged_predicate = None
    if untagged:
        untagged_predicate = Model.id.notin_(select(ModelTag.model_id))

    if tag_predicate is not None and untagged_predicate is not None:
        base = base.where(or_(tag_predicate, untagged_predicate))
    elif tag_predicate is not None:
        base = base.where(tag_predicate)
    elif untagged_predicate is not None:
        base = base.where(untagged_predicate)

    if source is not None:
        base = base.where(Model.source == source)
    if category is not None:
        # Initiative 26 (Story 49.3) — ONE slug-addressed browse-category scope.
        # IN-subquery, never a JOIN: keeps the outer SELECT shape unchanged so the
        # sort / offset-limit / eager-tag / eager-gallery pipeline below applies
        # untouched, exactly as external_url records at the block just past `q`.
        # A join would not inflate rows for a single unique slug today, but 49.4
        # adds a tag-name disjunct that genuinely fans out under one.
        # Structurally OUTSIDE the tag/untagged composition above, so tag_match
        # never sees it and the 42.1 AND-between-groups / OR-within-group
        # semantics are untouched. An unknown slug yields an empty subquery ->
        # unsatisfiable predicate -> empty page with total=0, matching the
        # shipped unknown-tag_id posture (never a 404).
        base = base.where(
            Model.id.in_(
                select(ModelBrowseCategory.model_id)
                .join(BrowseCategory, BrowseCategory.id == ModelBrowseCategory.category_id)
                .where(BrowseCategory.slug == category)
            )
        )
    if uncategorized:
        # Initiative 26 (Story 52.2) — the admin curation queue's source set.
        # Byte-analogue of the `untagged` predicate above, but applied HERE,
        # outside the tag/untagged composition, so it is a pure AND: it never
        # enters a tag bucket, never widens `untagged`, and never unions with
        # the `category` scope (see the docstring for why that union would be
        # wrong rather than merely different).
        base = base.where(Model.id.notin_(select(ModelBrowseCategory.model_id)))
    if q:
        like = f"%{q.lower()}%"
        tag_lower = unicode_lower(session)
        base = base.where(
            or_(
                func.lower(Model.name_en).like(like),
                func.lower(Model.name_pl).like(like),
                func.lower(Model.slug).like(like),
                # Initiative 26 (Story 49.4, FR26-SEARCH-1) — tag-name membership.
                # IN-subquery, never a JOIN onto `base`: a model carrying three
                # matching tags would appear three times under a join, and `total`
                # is count(*) over base.subquery() computed BEFORE pagination
                # (just below), so a join inflates both the page and the count. The
                # join below is INSIDE the subquery (model_tag -> tag) and does not
                # multiply outer rows. `tag.slug` is deliberately NOT matched —
                # slugs are internal (architecture.md § Initiative 26) and matching
                # them would couple the session-scoped test DB's per-module slug
                # prefixes. No soft-delete filter here on purpose: liveness is
                # owned by the outer query above so `include_deleted=true` keeps
                # working symmetrically for name- and tag-matched rows.
                # Case-folded with `unicode_lower`, NOT SQLite's ASCII-only
                # lower(): the shipped taxonomy stores Tag.name_pl values such
                # as "Łazienka" (seed.py), which plain lower() leaves unfolded
                # and therefore unreachable by any casing of themselves. The
                # model-name disjuncts above keep the shipped lower() — widening
                # them is a separate, pre-existing concern (deferred-work.md).
                Model.id.in_(
                    select(ModelTag.model_id)
                    .join(Tag, Tag.id == ModelTag.tag_id)
                    .where(
                        or_(
                            tag_lower(Tag.name_pl).like(like),
                            tag_lower(Tag.name_en).like(like),
                        )
                    )
                ),
            )
        )
    if external_url is not None:
        # TB-004: exact-match join via ModelExternalLink.url. Subquery (not
        # SQL JOIN) mirrors the tag_ids AND pattern above and keeps the
        # outer SELECT shape unchanged — same paging/sort/eager-tag/eager-
        # gallery pipeline applies to the (typically 0-or-1-row) result.
        base = base.where(
            Model.id.in_(
                select(ModelExternalLink.model_id).where(ModelExternalLink.url == external_url)
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

    # Eagerly fetch all image/print file ids per model + total count so list
    # cards can render the full mini-carousel without a separate fetch per
    # row. Lazy-loading on the <img> tag means only the active image is
    # actually fetched. Ordering matches list_model_files: position
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

    tag_rows = session.exec(
        select(Tag)
        .join(ModelTag, ModelTag.tag_id == Tag.id)
        .where(ModelTag.model_id == model_id)
        .order_by(Tag.slug)
    ).all()
    tags = [TagRead.model_validate(t) for t in tag_rows]

    # Initiative 26 (Story 49.3) — ONE extra statement, constant in the number
    # of categories the model carries (AC-23(b): measured 7 -> 8 SELECTs).
    category_rows = session.exec(
        select(BrowseCategory)
        .join(ModelBrowseCategory, ModelBrowseCategory.category_id == BrowseCategory.id)
        .where(ModelBrowseCategory.model_id == model_id)
        .order_by(BrowseCategory.position, BrowseCategory.slug)
    ).all()
    categories = [BrowseCategorySummary.model_validate(c) for c in category_rows]

    file_rows = session.exec(
        select(ModelFile)
        .where(ModelFile.model_id == model_id)
        .order_by(nullslast(ModelFile.position.asc()), ModelFile.created_at.asc())
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
            "categories": categories,
            "gallery_file_ids": gallery_file_ids,
            "image_count": len(gallery_file_ids),
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
