"""Story 49.3 — GET /api/categories[/{slug}] read surface + ModelDetail.categories.

Covers AC-1..AC-4 and AC-6 (flat ordered list, item shape, empty categories,
model_count semantics, auth), AC-7..AC-9 (slug resolve, unknown-slug 404, auth),
AC-18..AC-20 (ModelDetail.categories, empty list, ModelSummary negative) and the
AC-23(a)/(b) query-count guards.

The session-scoped shared DB (conftest `_isolated_db`) persists rows across
tests in this file, and the Story 49.2 starter seed is an explicit admin CLI
with no lifespan wiring — so the test DB starts with ZERO browse categories.
Every seed therefore uses unique slugs and every assertion is scoped to its own
seeded rows; nothing here asserts a DB-global browse-category count (§6 F-10).
"""

import contextlib
import datetime
import uuid

import pytest
from sqlalchemy import event
from sqlmodel import Session

from app.core.auth.cookies import ACCESS_COOKIE
from app.core.auth.jwt import encode_token
from app.core.db.models import (
    BrowseCategory,
    Model,
    ModelBrowseCategory,
    ModelStatus,
)
from app.core.db.session import get_engine
from app.modules.sot.service import get_model_detail, list_browse_categories
from tests._test_helpers import admin_token, agent_token, member_token


@pytest.fixture(autouse=True)
def _default_admin_cookie(client):
    """Authenticate every request — both new routes are default-deny (AC-6/AC-9)."""
    token = encode_token(
        subject=str(uuid.uuid4()),
        role="admin",
        secret="test-secret-not-real",
        ttl_minutes=30,
    )
    client.cookies.set(ACCESS_COOKIE, token)
    yield
    client.cookies.delete(ACCESS_COOKIE)


# --- seeding helpers -------------------------------------------------------


def _prefix() -> str:
    return f"cat-{uuid.uuid4().hex[:6]}"


def _mk_cat(s, slug, **kw):
    c = BrowseCategory(slug=slug, name_en=kw.pop("name_en", slug.upper()), **kw)
    s.add(c)
    s.commit()
    s.refresh(c)
    return c


def _mk_model(s, *, deleted=False):
    m = Model(
        slug=f"m-{uuid.uuid4().hex[:10]}",
        name_en="M",
        status=ModelStatus.not_printed,
        deleted_at=datetime.datetime.now(datetime.UTC) if deleted else None,
    )
    s.add(m)
    s.commit()
    s.refresh(m)
    return m


def _assign(s, model_id, category_id):
    s.add(ModelBrowseCategory(model_id=model_id, category_id=category_id))
    s.commit()


@contextlib.contextmanager
def _count_selects(engine):
    """Count SELECT statements issued on `engine` inside the block."""
    counter = {"n": 0}

    def _before(_conn, _cursor, statement, _params, _context, _executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            counter["n"] += 1

    event.listen(engine, "before_cursor_execute", _before)
    try:
        yield counter
    finally:
        event.remove(engine, "before_cursor_execute", _before)


def _mine(body, prefix):
    """Only the rows this test seeded — never a DB-global assertion (§6 F-10)."""
    return [item for item in body if item["slug"].startswith(prefix)]


# --- AC-1: flat list, deterministic (position, slug) order -----------------


def test_categories_list_is_ordered_by_position_then_slug(client):
    """AC-1 — ordered by (position ASC, slug ASC), including the position tie."""
    p = _prefix()
    with Session(get_engine()) as s:
        _mk_cat(s, f"{p}-b-pos1", position=1)
        _mk_cat(s, f"{p}-a-pos2", position=2)
        # Two categories sharing a position are ordered by slug.
        _mk_cat(s, f"{p}-z-pos0", position=0)
        _mk_cat(s, f"{p}-a-pos0", position=0)

    r = client.get("/api/categories")
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    assert [c["slug"] for c in _mine(body, p)] == [
        f"{p}-a-pos0",
        f"{p}-z-pos0",
        f"{p}-b-pos1",
        f"{p}-a-pos2",
    ]


def test_categories_list_is_flat_even_when_a_row_has_a_parent(client):
    """AC-1 — no nesting: `parent_id` is a scalar and the array stays flat.

    The retired Initiative 25 recursive CategoryTree is NOT coming back."""
    p = _prefix()
    with Session(get_engine()) as s:
        parent = _mk_cat(s, f"{p}-parent", position=0)
        _mk_cat(s, f"{p}-child", position=1, parent_id=parent.id)
        parent_id = parent.id

    body = client.get("/api/categories").json()
    mine = _mine(body, p)
    assert len(mine) == 2
    for item in mine:
        assert "children" not in item
        assert "subcategories" not in item
    child = next(c for c in mine if c["slug"] == f"{p}-child")
    assert child["parent_id"] == str(parent_id)


# --- AC-2: item shape ------------------------------------------------------


def test_categories_item_carries_exactly_the_decision_ay_key_set(client):
    """AC-2 — exact key set; genuine nulls are PRESENT as null, not omitted."""
    p = _prefix()
    with Session(get_engine()) as s:
        _mk_cat(s, f"{p}-full", name_pl="Pelna", description_en="EN", description_pl="PL")
        _mk_cat(s, f"{p}-bare")

    body = client.get("/api/categories").json()
    mine = {c["slug"]: c for c in _mine(body, p)}

    expected = {
        "id",
        "slug",
        "name_en",
        "name_pl",
        "description_en",
        "description_pl",
        "position",
        "parent_id",
        "model_count",
    }
    assert set(mine[f"{p}-full"]) == expected
    bare = mine[f"{p}-bare"]
    assert set(bare) == expected
    assert bare["name_pl"] is None
    assert bare["description_en"] is None
    assert bare["description_pl"] is None
    assert bare["parent_id"] is None
    assert isinstance(bare["model_count"], int)


def test_categories_item_does_not_expose_inclusion_criterion(client):
    """§6 F-12 / Decision AY — `inclusion_criterion` is stored but NOT on the wire."""
    p = _prefix()
    with Session(get_engine()) as s:
        _mk_cat(s, f"{p}-crit", inclusion_criterion="internal curation note")

    item = _mine(client.get("/api/categories").json(), p)[0]
    assert "inclusion_criterion" not in item


# --- AC-3 / AC-4: counts ---------------------------------------------------


def test_categories_list_includes_empty_categories_with_zero_count(client):
    """AC-3 — a zero-assignment category is returned, never filtered out."""
    p = _prefix()
    with Session(get_engine()) as s:
        _mk_cat(s, f"{p}-empty")

    mine = _mine(client.get("/api/categories").json(), p)
    assert len(mine) == 1
    assert mine[0]["model_count"] == 0


def test_categories_model_count_counts_distinct_live_models_only(client):
    """AC-4 — distinct non-soft-deleted assigned models; deleted ones excluded."""
    p = _prefix()
    with Session(get_engine()) as s:
        cat = _mk_cat(s, f"{p}-counted")
        for _ in range(3):
            _assign(s, _mk_model(s).id, cat.id)
        _assign(s, _mk_model(s, deleted=True).id, cat.id)

    mine = _mine(client.get("/api/categories").json(), p)
    assert mine[0]["model_count"] == 3


def test_categories_model_count_is_unaffected_by_other_categories(client):
    """AC-4 — a model in two categories counts once in each, not twice in either."""
    p = _prefix()
    with Session(get_engine()) as s:
        left = _mk_cat(s, f"{p}-left", position=0)
        right = _mk_cat(s, f"{p}-right", position=1)
        shared = _mk_model(s)
        _assign(s, shared.id, left.id)
        _assign(s, shared.id, right.id)

    mine = {c["slug"]: c for c in _mine(client.get("/api/categories").json(), p)}
    assert mine[f"{p}-left"]["model_count"] == 1
    assert mine[f"{p}-right"]["model_count"] == 1


# --- AC-6: auth ------------------------------------------------------------


def test_categories_list_anonymous_returns_401(client):
    """AC-6 — default-deny; the route is outside `_PUBLIC_ROUTES`."""
    client.cookies.delete(ACCESS_COOKIE)
    r = client.get("/api/categories")
    assert r.status_code == 401


@pytest.mark.parametrize("mint", [admin_token, member_token, agent_token])
def test_categories_list_authenticated_roles_return_200(client, mint):
    """AC-6 — admin / member / agent all read the list."""
    client.cookies.set(ACCESS_COOKIE, mint(uuid.uuid4()))
    r = client.get("/api/categories")
    assert r.status_code == 200, r.text


# --- AC-7 / AC-8 / AC-9: GET /api/categories/{slug} ------------------------


def test_category_detail_resolves_by_slug_with_the_list_item_shape(client):
    """AC-7 — the single category, same nine-key shape incl. `model_count`."""
    p = _prefix()
    with Session(get_engine()) as s:
        cat = _mk_cat(s, f"{p}-detail", position=7, name_pl="Detal", description_en="EN")
        _assign(s, _mk_model(s).id, cat.id)
        _assign(s, _mk_model(s).id, cat.id)
        _assign(s, _mk_model(s, deleted=True).id, cat.id)
        cat_id = cat.id

    r = client.get(f"/api/categories/{p}-detail")
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {
        "id",
        "slug",
        "name_en",
        "name_pl",
        "description_en",
        "description_pl",
        "position",
        "parent_id",
        "model_count",
    }
    assert body["id"] == str(cat_id)
    assert body["slug"] == f"{p}-detail"
    assert body["position"] == 7
    assert body["name_pl"] == "Detal"
    assert body["description_pl"] is None
    assert body["parent_id"] is None
    assert body["model_count"] == 2  # soft-deleted assignment excluded (AC-4)


def test_category_detail_unknown_slug_returns_404_with_detail_body(client):
    """AC-8 — unmatched slug is 404 with a JSON `detail`, never a 200 null/{}.

    Deliberately different from `GET /api/models?category=<unknown>` (AC-12,
    empty page): "give me category X" has no resource to return, whereas
    "which models are in X" degrades honestly to an empty catalogue page.

    The asserted `detail` is the route's own message, not FastAPI's generic
    `"Not Found"` — so this test genuinely fails while the route is absent
    instead of passing by construction on a route-missing 404."""
    r = client.get(f"/api/categories/no-such-category-{uuid.uuid4().hex[:8]}")
    assert r.status_code == 404, r.text
    assert r.json().get("detail") == "Browse category not found", r.text


def test_category_detail_anonymous_returns_401(client):
    """AC-9 — default-deny, same posture as the list."""
    p = _prefix()
    with Session(get_engine()) as s:
        _mk_cat(s, f"{p}-anon")
    client.cookies.delete(ACCESS_COOKIE)
    r = client.get(f"/api/categories/{p}-anon")
    assert r.status_code == 401


@pytest.mark.parametrize("mint", [admin_token, member_token, agent_token])
def test_category_detail_authenticated_roles_return_200(client, mint):
    """AC-9 — admin / member / agent all resolve a category."""
    p = _prefix()
    with Session(get_engine()) as s:
        _mk_cat(s, f"{p}-roles")
    client.cookies.set(ACCESS_COOKIE, mint(uuid.uuid4()))
    r = client.get(f"/api/categories/{p}-roles")
    assert r.status_code == 200, r.text


# --- AC-18 / AC-19 / AC-20: ModelDetail.categories -------------------------
#
# Authored HERE rather than in tests/test_sot_models_detail.py so that module
# stays byte-unmodified as the AC-15/AC-26 non-regression witness (§5 T4.1).


def test_model_detail_categories_are_ordered_by_position_then_slug(client):
    """AC-18 — `ModelDetail.categories` is `list[BrowseCategorySummary]` ordered
    `(position ASC, slug ASC)`, WITHOUT `model_count` (embedding it would cost an
    aggregate for a number the detail view never renders)."""
    p = _prefix()
    with Session(get_engine()) as s:
        late = _mk_cat(s, f"{p}-late", position=5)
        tie_z = _mk_cat(s, f"{p}-z-tie", position=1)
        tie_a = _mk_cat(s, f"{p}-a-tie", position=1)
        m = _mk_model(s)
        for cat in (late, tie_z, tie_a):
            _assign(s, m.id, cat.id)
        model_id = m.id

    r = client.get(f"/api/models/{model_id}")
    assert r.status_code == 200, r.text
    categories = r.json()["categories"]
    assert [c["slug"] for c in categories] == [
        f"{p}-a-tie",
        f"{p}-z-tie",
        f"{p}-late",
    ]
    assert set(categories[0]) == {"id", "slug", "name_en", "name_pl", "position", "parent_id"}
    for c in categories:
        assert "model_count" not in c
        assert "children" not in c


def test_model_detail_categories_is_empty_list_not_null(client):
    """AC-19 — a model with no categories returns `categories: []`, never null."""
    with Session(get_engine()) as s:
        model_id = _mk_model(s).id

    body = client.get(f"/api/models/{model_id}").json()
    assert body["categories"] == []


def test_model_summary_does_not_carry_categories(client):
    """AC-20 — no item in GET /api/models gains a `categories` key."""
    p = _prefix()
    with Session(get_engine()) as s:
        cat = _mk_cat(s, f"{p}-summary")
        m = _mk_model(s)
        _assign(s, m.id, cat.id)
        model_slug = m.slug

    body = client.get(f"/api/models?q={model_slug}&limit=200").json()
    assert len(body["items"]) == 1
    assert "categories" not in body["items"][0]


# --- AC-23(a)/(b): query-count COVERAGE GUARDS -----------------------------
#
# NOT a TDD RED. These are authored AFTER T1-T4 landed the production symbols
# they measure and are expected green on first run (§5 T5.1). Their
# load-bearing character was proven separately by a labelled, throwaway N+1
# mutation of `_browse_category_model_counts`, reverted with a byte-identical
# `service.py` sha256 — see the story §15 Dev Agent Record.
#
# Measured at the SERVICE layer, not through TestClient, so auth/session
# overhead does not pollute the count (the shipped test_sot_tag_groups.py
# rationale).


def test_list_browse_categories_query_count_is_constant_and_bounded(client):
    """AC-23(a) — COVERAGE GUARD. `list_browse_categories` issues a constant
    number of SELECTs, independent of category count AND of assignment count,
    and <= 2 (one category select + one counts aggregate)."""
    engine = get_engine()
    p = _prefix()

    def _seed(prefix, n_cats, m_models):
        with Session(engine) as s:
            for ci in range(n_cats):
                cat = _mk_cat(s, f"{prefix}-c{ci}", position=ci)
                for _ in range(m_models):
                    _assign(s, _mk_model(s).id, cat.id)

    _seed(f"{p}-small", 2, 2)
    with Session(engine) as s, _count_selects(engine) as c_small:
        list_browse_categories(s)

    _seed(f"{p}-large", 4, 4)  # doubled cardinality on both axes
    with Session(engine) as s, _count_selects(engine) as c_large:
        list_browse_categories(s)

    assert c_small["n"] == c_large["n"], (c_small["n"], c_large["n"])
    assert c_large["n"] <= 2, c_large["n"]  # BrowseCategory select + counts aggregate


def test_get_model_detail_costs_exactly_one_extra_select(client):
    """AC-23(b) — COVERAGE GUARD. `get_model_detail` issues exactly ONE SELECT
    more than its pre-story baseline, and that cost is independent of how many
    categories the model carries.

    The baseline was measured on the clean tree at 2d4fd75 (T0.2): 7 SELECTs
    (model, tags, files, notes, prints, external_links, gallery-ids). The
    category block is unconditional, so the target is a flat 8 — not 7+N."""
    engine = get_engine()
    p = _prefix()
    with Session(engine) as s:
        bare = _mk_model(s)
        rich = _mk_model(s)
        for i in range(4):
            _assign(s, rich.id, _mk_cat(s, f"{p}-qc{i}", position=i).id)
        bare_id, rich_id = bare.id, rich.id

    with Session(engine) as s, _count_selects(engine) as c_bare:
        detail = get_model_detail(s, bare_id)
    assert detail is not None and detail.categories == []

    with Session(engine) as s, _count_selects(engine) as c_rich:
        detail = get_model_detail(s, rich_id)
    assert detail is not None and len(detail.categories) == 4

    assert c_bare["n"] == c_rich["n"], (c_bare["n"], c_rich["n"])  # no N+1
    assert c_rich["n"] == 8, c_rich["n"]  # measured baseline 7 + exactly one
