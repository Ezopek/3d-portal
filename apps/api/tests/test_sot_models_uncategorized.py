"""Story 52.2 — GET /api/models?uncategorized=true (B-2).

The curation queue on `/admin/categories` needs the set of models carrying ZERO
browse categories. Nothing shipped could produce it: `ModelSummary` deliberately
omits `categories` (Decision AY — "list cards render no categories in the MVP
IA"), so a client-side derivation would cost one detail fetch per model, and
`GET /api/categories`' `model_count` values cannot be subtracted from the corpus
total because membership is M:N and the counts overlap.

This is the byte-analogue of the shipped `untagged` predicate
(`service.py`, `Model.id.notin_(select(ModelTag.model_id))`), applied as a PURE
AND (D-2) rather than OR-unioned with `category` the way `untagged` unions with
`tag_ids` — see `test_uncategorized_and_category_scope_is_empty` for why that is
a true statement rather than a special case.

The session-scoped shared DB (conftest `_isolated_db`) persists rows across
tests, so every seed uses unique slugs and every assertion is scoped to its own
seeded rows via `q=<prefix>`. No DB-global count is ever asserted.
"""

import datetime
import uuid

import pytest
from sqlmodel import Session

from app.core.auth.cookies import ACCESS_COOKIE
from app.core.auth.jwt import encode_token
from app.core.db.models import (
    BrowseCategory,
    Model,
    ModelBrowseCategory,
    ModelSource,
    ModelStatus,
    ModelTag,
    Tag,
)
from app.core.db.session import get_engine


@pytest.fixture(autouse=True)
def _default_admin_cookie(client):
    """GET /api/models is default-deny; authenticate every request."""
    token = encode_token(
        subject=str(uuid.uuid4()),
        role="admin",
        secret="test-secret-not-real",
        ttl_minutes=30,
    )
    client.cookies.set(ACCESS_COOKIE, token)
    yield
    client.cookies.delete(ACCESS_COOKIE)


def _prefix() -> str:
    return f"uc-{uuid.uuid4().hex[:6]}"


def _mk_cat(s, slug, **kw):
    c = BrowseCategory(slug=slug, name_en=slug.upper(), **kw)
    s.add(c)
    s.commit()
    s.refresh(c)
    return c


def _mk_model(s, slug, **kw):
    m = Model(
        slug=slug,
        name_en=kw.pop("name_en", slug.upper()),
        status=kw.pop("status", ModelStatus.not_printed),
        **kw,
    )
    s.add(m)
    s.commit()
    s.refresh(m)
    return m


def _assign(s, model_id, category_id):
    s.add(ModelBrowseCategory(model_id=model_id, category_id=category_id))
    s.commit()


def _slugs(body):
    return {item["slug"] for item in body["items"]}


# --- AC-24: the predicate itself -------------------------------------------


def test_uncategorized_returns_only_models_with_no_category(client):
    """AC-24 — `uncategorized=true` returns exactly the models with no
    `model_browse_category` row, and `total` equals that count."""
    p = _prefix()
    with Session(get_engine()) as s:
        cat = _mk_cat(s, f"{p}-cat")
        _assign(s, _mk_model(s, f"{p}-assigned").id, cat.id)
        _mk_model(s, f"{p}-loose-1")
        _mk_model(s, f"{p}-loose-2")

    body = client.get(f"/api/models?uncategorized=true&q={p}&limit=200").json()
    assert _slugs(body) == {f"{p}-loose-1", f"{p}-loose-2"}
    assert body["total"] == 2


def test_uncategorized_default_false_leaves_response_unchanged(client):
    """AC-24 — the parameter defaults to false, and omitting it is byte-identical
    to passing it explicitly false: both return assigned AND unassigned models."""
    p = _prefix()
    with Session(get_engine()) as s:
        cat = _mk_cat(s, f"{p}-cat")
        _assign(s, _mk_model(s, f"{p}-assigned").id, cat.id)
        _mk_model(s, f"{p}-loose")

    omitted = client.get(f"/api/models?q={p}&limit=200").json()
    explicit_false = client.get(f"/api/models?uncategorized=false&q={p}&limit=200").json()
    assert _slugs(omitted) == {f"{p}-assigned", f"{p}-loose"}
    assert omitted == explicit_false


def test_model_becomes_categorized_and_leaves_the_queue(client):
    """AC-24 — the queue is derived, not cached: assigning a category removes the
    model from the `uncategorized` page on the very next read."""
    p = _prefix()
    with Session(get_engine()) as s:
        cat = _mk_cat(s, f"{p}-cat")
        m = _mk_model(s, f"{p}-mover")
        model_id, cat_id = m.id, cat.id

    before = client.get(f"/api/models?uncategorized=true&q={p}&limit=200").json()
    assert _slugs(before) == {f"{p}-mover"}

    with Session(get_engine()) as s:
        _assign(s, model_id, cat_id)

    after = client.get(f"/api/models?uncategorized=true&q={p}&limit=200").json()
    assert after["items"] == []
    assert after["total"] == 0


def test_uncategorized_excludes_soft_deleted_models(client):
    """AC-24 — a soft-deleted zero-category model is NOT curation work; the
    shipped soft-delete filter keeps governing."""
    p = _prefix()
    with Session(get_engine()) as s:
        _mk_model(s, f"{p}-live")
        _mk_model(s, f"{p}-dead", deleted_at=datetime.datetime.now(datetime.UTC))

    body = client.get(f"/api/models?uncategorized=true&q={p}&limit=200").json()
    assert _slugs(body) == {f"{p}-live"}
    assert body["total"] == 1


def test_multi_category_model_is_never_uncategorized(client):
    """AC-24 — a model in TWO categories is excluded exactly once; the `NOT IN`
    membership predicate cannot double-count or leak it back in."""
    p = _prefix()
    with Session(get_engine()) as s:
        cat_a = _mk_cat(s, f"{p}-a")
        cat_b = _mk_cat(s, f"{p}-b")
        shared = _mk_model(s, f"{p}-shared")
        _assign(s, shared.id, cat_a.id)
        _assign(s, shared.id, cat_b.id)
        _mk_model(s, f"{p}-loose")

    body = client.get(f"/api/models?uncategorized=true&q={p}&limit=200").json()
    assert _slugs(body) == {f"{p}-loose"}
    assert body["total"] == 1


# --- AC-24: composition (D-2 — pure AND) -----------------------------------


def test_uncategorized_and_category_scope_is_empty(client):
    """AC-24 / D-2 — `uncategorized=true&category=<slug>` is an empty page with
    `total: 0`.

    This is a TRUE STATEMENT, not a special case: no model is simultaneously
    assigned to a category and assigned to none. It is pinned so a future
    refactor cannot quietly turn this into an OR-union the way `untagged`
    unions with `tag_ids` — that union exists because both address the same
    axis via one shipped checkbox list, which has no category analogue.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        cat = _mk_cat(s, f"{p}-cat")
        _assign(s, _mk_model(s, f"{p}-assigned").id, cat.id)
        _mk_model(s, f"{p}-loose")

    body = client.get(f"/api/models?uncategorized=true&category={p}-cat&limit=200").json()
    assert body["items"] == []
    assert body["total"] == 0


def test_uncategorized_composes_with_status_and_source(client):
    """AC-24 — pure AND with `status` and with `source`."""
    p = _prefix()
    with Session(get_engine()) as s:
        cat = _mk_cat(s, f"{p}-cat")
        _assign(s, _mk_model(s, f"{p}-assigned", status=ModelStatus.printed).id, cat.id)
        _mk_model(s, f"{p}-loose-printed", status=ModelStatus.printed)
        _mk_model(s, f"{p}-loose-fresh")
        _mk_model(s, f"{p}-loose-thangs", source=ModelSource.thangs)

    by_status = client.get(f"/api/models?uncategorized=true&status=printed&q={p}&limit=200").json()
    assert _slugs(by_status) == {f"{p}-loose-printed"}
    assert by_status["total"] == 1

    by_source = client.get(f"/api/models?uncategorized=true&source=thangs&q={p}&limit=200").json()
    assert _slugs(by_source) == {f"{p}-loose-thangs"}


def test_uncategorized_composes_with_untagged_without_widening_it(client):
    """AC-24 — `uncategorized` is applied OUTSIDE the tag/`untagged` composition,
    so combining the two is an intersection (no tags AND no categories), never a
    union. A model with tags but no categories must NOT appear."""
    p = _prefix()
    with Session(get_engine()) as s:
        tag = Tag(slug=f"{p}-t", name_en="T")
        s.add(tag)
        s.commit()
        s.refresh(tag)
        cat = _mk_cat(s, f"{p}-cat")

        _mk_model(s, f"{p}-bare")  # no tags, no categories

        tagged = _mk_model(s, f"{p}-tagged-only")  # tags, no categories
        s.add(ModelTag(model_id=tagged.id, tag_id=tag.id))
        s.commit()

        cat_only = _mk_model(s, f"{p}-cat-only")  # no tags, has a category
        _assign(s, cat_only.id, cat.id)

    both = client.get(f"/api/models?uncategorized=true&untagged=true&q={p}&limit=200").json()
    assert _slugs(both) == {f"{p}-bare"}
    assert both["total"] == 1

    # And each flag alone still means only its own thing.
    only_uncat = client.get(f"/api/models?uncategorized=true&q={p}&limit=200").json()
    assert _slugs(only_uncat) == {f"{p}-bare", f"{p}-tagged-only"}
    only_untagged = client.get(f"/api/models?untagged=true&q={p}&limit=200").json()
    assert _slugs(only_untagged) == {f"{p}-bare", f"{p}-cat-only"}


def test_uncategorized_composes_with_pagination_and_sort(client):
    """AC-24 — `total` is the full uncategorized count, independent of the page
    window, and `sort` still orders the page."""
    p = _prefix()
    base = datetime.datetime(2026, 3, 1, tzinfo=datetime.UTC)
    with Session(get_engine()) as s:
        cat = _mk_cat(s, f"{p}-cat")
        _assign(s, _mk_model(s, f"{p}-assigned").id, cat.id)
        for i, name in enumerate(["Zeta", "Alpha", "Mu", "Beta"]):
            _mk_model(
                s,
                f"{p}-loose{i}",
                name_en=name,
                created_at=base + datetime.timedelta(days=i),
            )

    seen = set()
    for offset in (0, 2):
        body = client.get(
            f"/api/models?uncategorized=true&q={p}&sort=name_asc&offset={offset}&limit=2"
        ).json()
        assert body["total"] == 4, (offset, body["total"])
        assert body["offset"] == offset
        assert body["limit"] == 2
        seen |= _slugs(body)
    assert seen == {f"{p}-loose{i}" for i in range(4)}

    ordered = client.get(f"/api/models?uncategorized=true&q={p}&sort=name_asc&limit=200").json()
    assert [i["name_en"] for i in ordered["items"]] == ["Alpha", "Beta", "Mu", "Zeta"]
