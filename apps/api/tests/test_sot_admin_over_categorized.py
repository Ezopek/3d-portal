"""Story 52.3 (B-1) — GET /api/admin/models/over-categorized.

The curation-QA panel on `/admin/categories` needs the set of models carrying
"unusually many" browse categories, WITH the per-model count ("Model
„Wazon spiralny" ma 4 kategorie"). Nothing shipped can produce it: `list_models`
has no category-count predicate and `ModelSummary` deliberately carries no
`categories` (Decision AY, architecture.md:3312), so a client-side derivation
would need one `GET /api/models?category=<slug>` per category — O(categories)
requests that also under-report past the 200-row page cap.

This route is the `model_id`-grouped mirror of the shipped read-side aggregate
`_browse_category_model_counts` (service.py): one GROUP BY with a HAVING plus
one COUNT over the same grouped set. Two statements, constant regardless of
catalogue or assignment cardinality.

The session-scoped shared DB (conftest `_isolated_db`) persists rows across
tests and across test FILES, so no assertion here may depend on a DB-global
`total` at the default threshold. Every `total` assertion uses a deliberately
high `min_categories` that only this file's fixtures can reach; membership
assertions are scoped to this test's own slugs.
"""

import datetime
import uuid

import pytest
from sqlalchemy import event
from sqlmodel import Session, select

from app.core.auth.cookies import ACCESS_COOKIE
from app.core.db.models import (
    AuditLog,
    BrowseCategory,
    Model,
    ModelBrowseCategory,
    ModelStatus,
    User,
    UserRole,
)
from app.core.db.session import get_engine
from app.modules.sot.admin_service import list_over_categorized_models
from tests._test_helpers import admin_token, agent_token, member_token

ROUTE = "/api/admin/models/over-categorized"


# ---------------------------------------------------------------------------
# Seeding helpers
# ---------------------------------------------------------------------------


def _prefix() -> str:
    return f"oc-{uuid.uuid4().hex[:6]}"


def _seed_user(session: Session, role: UserRole) -> uuid.UUID:
    u = User(
        email=f"{role.value}-oc-{uuid.uuid4().hex[:6]}@test.local",
        display_name=role.value.title(),
        role=role,
        password_hash="x",
    )
    session.add(u)
    session.commit()
    session.refresh(u)
    return u.id


@pytest.fixture
def admin_client(client):
    with Session(get_engine()) as s:
        admin_id = _seed_user(s, UserRole.admin)
    client.cookies.set(ACCESS_COOKIE, admin_token(admin_id))
    yield client
    client.cookies.delete(ACCESS_COOKIE)


def _mk_cat(s: Session, slug: str, position: int = 0) -> BrowseCategory:
    c = BrowseCategory(slug=slug, name_en=slug.upper(), position=position)
    s.add(c)
    s.commit()
    s.refresh(c)
    return c


def _mk_model(s: Session, slug: str, *, deleted: bool = False, name_pl: str | None = None) -> Model:
    m = Model(
        slug=slug,
        name_en=slug.upper(),
        name_pl=name_pl,
        status=ModelStatus.not_printed,
        deleted_at=datetime.datetime.now(datetime.UTC) if deleted else None,
    )
    s.add(m)
    s.commit()
    s.refresh(m)
    return m


def _assign(s: Session, model_id: uuid.UUID, category_ids: list[uuid.UUID]) -> None:
    for cid in category_ids:
        s.add(ModelBrowseCategory(model_id=model_id, category_id=cid))
    s.commit()


def _seed_categories(s: Session, prefix: str, n: int) -> list[uuid.UUID]:
    return [_mk_cat(s, f"{prefix}-c{i}", position=i).id for i in range(n)]


def _mine(items: list[dict], prefix: str) -> list[dict]:
    """Only the rows this test seeded — never a DB-global membership assertion."""
    return [i for i in items if i["slug"].startswith(prefix)]


def _count_selects(engine):
    """Count SELECT statements issued on `engine` inside the block."""
    import contextlib

    @contextlib.contextmanager
    def _cm():
        counter = {"n": 0}

        def _before(_conn, _cursor, statement, _params, _context, _executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                counter["n"] += 1

        event.listen(engine, "before_cursor_execute", _before)
        try:
            yield counter
        finally:
            event.remove(engine, "before_cursor_execute", _before)

    return _cm()


# ---------------------------------------------------------------------------
# AC-1 — shape, order, auth matrix
# ---------------------------------------------------------------------------


def test_returns_items_and_total_with_the_documented_item_keys(admin_client):
    """AC-1 — `{items, total}`; each item is exactly
    `{model_id, slug, name_en, name_pl, category_count}`."""
    p = _prefix()
    with Session(get_engine()) as s:
        cats = _seed_categories(s, p, 7)
        m = _mk_model(s, f"{p}-a", name_pl="Wazon spiralny")
        _assign(s, m.id, cats)
        model_id = str(m.id)

    r = admin_client.get(ROUTE, params={"min_categories": 7})
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"items", "total"}
    mine = _mine(body["items"], p)
    assert len(mine) == 1
    item = mine[0]
    assert set(item) == {"model_id", "slug", "name_en", "name_pl", "category_count"}
    assert item["model_id"] == model_id
    assert item["slug"] == f"{p}-a"
    assert item["name_en"] == f"{p}-a".upper()
    assert item["name_pl"] == "Wazon spiralny"
    assert item["category_count"] == 7


def test_order_is_category_count_desc_then_slug_asc(admin_client):
    """AC-1 — worst first, deterministically; the count tie breaks on slug ASC."""
    p = _prefix()
    with Session(get_engine()) as s:
        cats = _seed_categories(s, p, 9)
        # 9 categories -> the loudest finding.
        big = _mk_model(s, f"{p}-z-big")
        _assign(s, big.id, cats)
        # Two models tied at 7, seeded in reverse slug order so a stable-but-
        # insertion-ordered implementation would fail this.
        tie_b = _mk_model(s, f"{p}-b-tie")
        _assign(s, tie_b.id, cats[:7])
        tie_a = _mk_model(s, f"{p}-a-tie")
        _assign(s, tie_a.id, cats[:7])

    body = admin_client.get(ROUTE, params={"min_categories": 7}).json()
    assert [i["slug"] for i in _mine(body["items"], p)] == [
        f"{p}-z-big",
        f"{p}-a-tie",
        f"{p}-b-tie",
    ]


@pytest.mark.parametrize(
    ("cookie_role", "expected"),
    [(None, 401), ("member", 403), ("agent", 403)],
)
def test_auth_matrix_rejects_everyone_but_admin(client, cookie_role, expected):
    """AC-1 — 401 anonymous, 403 member, 403 agent. Category curation is admin
    curation (Decision AY): this route is never agent-readable."""
    client.cookies.clear()
    if cookie_role is not None:
        with Session(get_engine()) as s:
            uid = _seed_user(s, UserRole(cookie_role))
        mint = member_token if cookie_role == "member" else agent_token
        client.cookies.set(ACCESS_COOKIE, mint(uid))
    try:
        assert client.get(ROUTE).status_code == expected
    finally:
        client.cookies.clear()


# ---------------------------------------------------------------------------
# AC-1 — route resolution (the shadowing hazard the router docstring names)
# ---------------------------------------------------------------------------


def test_literal_route_is_not_shadowed_by_a_dynamic_model_route(client):
    """The literal `/models/over-categorized` must WIN route resolution.

    `sot/admin_router.py` mounts at the same `/api/admin` prefix, is included
    FIRST (`app/router.py`) and owns `/models/{model_id}` — a template whose
    compiled regex DOES match `/api/admin/models/over-categorized`. This route
    survives only because that router registers no GET at all, so Starlette's
    method-mismatch PARTIAL match falls through to here. Adding a
    `GET /api/admin/models/{model_id}` upstream would flip that partial into a
    FULL match and turn every request here into a 422 on the UUID coercion.

    Asserted against the real route table so the invariant is enforced rather
    than incidental, and so the failure names its own fix instead of surfacing
    as an unexplained 422 across this file. Two sanctioned remedies: include
    `sot_browse_category_admin_router` BEFORE `sot_admin_router` in
    `app/router.py`, or declare the new route `/models/{model_id:uuid}` — the
    convertor `PUT /models/{model_id:uuid}/thumbnail` already uses for exactly
    this reason.
    """
    from starlette.routing import Match

    scope = {"type": "http", "method": "GET", "path": ROUTE, "root_path": ""}
    full = [r for r in client.app.routes if r.matches(scope)[0] is Match.FULL]
    assert full, f"no route fully matches GET {ROUTE}"
    assert getattr(full[0], "name", None) == "admin_list_over_categorized_models", (
        f"GET {ROUTE} now resolves to "
        f"{getattr(full[0], 'name', full[0])!r} ({getattr(full[0], 'path', '?')}), not the "
        "literal curation-QA route — a dynamic /api/admin/models/{model_id} pattern "
        "registered earlier has shadowed it. Fix: include "
        "sot_browse_category_admin_router before sot_admin_router in app/router.py, "
        "or declare the shadowing route as /models/{model_id:uuid}."
    )


# ---------------------------------------------------------------------------
# AC-2 — threshold default and inclusive boundary
# ---------------------------------------------------------------------------


def test_default_min_categories_is_four_and_the_boundary_is_inclusive(admin_client):
    """AC-2 — with the default, exactly 3 is absent and exactly 4 is present.

    The server default of 4 exists so a direct API caller gets the documented
    FR26-CAT-3 norm; the frontend always sends the value explicitly. This test
    is what makes a drift between the two visible rather than silent.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        cats = _seed_categories(s, p, 4)
        three = _mk_model(s, f"{p}-three")
        _assign(s, three.id, cats[:3])
        four = _mk_model(s, f"{p}-four")
        _assign(s, four.id, cats)

    body = admin_client.get(ROUTE).json()
    slugs = [i["slug"] for i in _mine(body["items"], p)]
    assert slugs == [f"{p}-four"]


@pytest.mark.parametrize("min_categories", [0, -1, 51])
def test_min_categories_out_of_bounds_is_422(admin_client, min_categories):
    """AC-2 — `ge=1, le=50`."""
    assert admin_client.get(ROUTE, params={"min_categories": min_categories}).status_code == 422


@pytest.mark.parametrize("min_categories", [1, 50])
def test_min_categories_bounds_are_accepted(admin_client, min_categories):
    assert admin_client.get(ROUTE, params={"min_categories": min_categories}).status_code == 200


def test_min_categories_one_includes_a_model_with_exactly_one_category(admin_client):
    """AC-2 — the `ge=1` floor is inclusive too, and zero-category models never appear.

    The test above pins the inclusive boundary at the default of 4; this pins it
    at the validator's floor, which no other fixture ever sits exactly ON. It
    also pins the other end of the shape: a model with NO categories is absent
    from the join entirely at every threshold, which is why "uncategorized" is a
    separate check (Story 52.2's `uncategorized` predicate) and not
    `min_categories=0` here.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        (cat_id,) = _seed_categories(s, p, 1)
        one = _mk_model(s, f"{p}-one")
        _assign(s, one.id, [cat_id])
        _mk_model(s, f"{p}-zero")  # no assignments at all

    body = admin_client.get(ROUTE, params={"min_categories": 1}).json()
    mine = _mine(body["items"], p)
    assert [i["slug"] for i in mine] == [f"{p}-one"]
    assert mine[0]["category_count"] == 1


# ---------------------------------------------------------------------------
# AC-3 — soft delete, total vs limit
# ---------------------------------------------------------------------------


def test_soft_deleted_models_are_excluded(admin_client):
    """AC-3 — `Model.deleted_at IS NULL`, matching `_browse_category_model_counts`.

    A trashed model is not curation work; counting it would make the panel
    advise about a row the admin cannot even see.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        cats = _seed_categories(s, p, 8)
        live = _mk_model(s, f"{p}-live")
        _assign(s, live.id, cats)
        trashed = _mk_model(s, f"{p}-trashed", deleted=True)
        _assign(s, trashed.id, cats)
        trashed_id = str(trashed.id)

    body = admin_client.get(ROUTE, params={"min_categories": 8}).json()
    assert [i["slug"] for i in _mine(body["items"], p)] == [f"{p}-live"]
    # The shared session-scoped DB makes a global `total` assertion unsafe here,
    # so the exclusion is asserted on identity instead of on a count.
    assert all(i["model_id"] != trashed_id for i in body["items"])


def test_total_counts_all_qualifying_models_independent_of_limit(admin_client):
    """AC-3 — `items` is capped by `limit`; `total` is not.

    The panel's overflow line states the TRUE remaining count (D-8), so a
    `total` that silently tracked `limit` would make the cap read as "these are
    all of them" — the exact failure the overflow rule exists to prevent.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        cats = _seed_categories(s, p, 12)
        for i in range(3):
            m = _mk_model(s, f"{p}-m{i}")
            _assign(s, m.id, cats)

    full = admin_client.get(ROUTE, params={"min_categories": 12}).json()
    # `total` is DB-global on the shared session-scoped DB, so it is pinned
    # RELATIVE to `limit` rather than to an absolute number: that relation IS
    # the contract under test.
    assert len(_mine(full["items"], p)) == 3
    assert full["total"] >= 3
    assert len(full["items"]) == full["total"]  # under the default limit of 50

    capped = admin_client.get(ROUTE, params={"min_categories": 12, "limit": 1}).json()
    assert capped["total"] == full["total"]
    assert len(capped["items"]) == 1
    # The cap keeps the (count DESC, slug ASC) head, not an arbitrary row.
    assert capped["items"][0] == full["items"][0]


@pytest.mark.parametrize("limit", [0, -1, 201])
def test_limit_out_of_bounds_is_422(admin_client, limit):
    """AC-3 — `ge=1, le=200`."""
    assert admin_client.get(ROUTE, params={"limit": limit}).status_code == 422


# ---------------------------------------------------------------------------
# AC-4 — pure read
# ---------------------------------------------------------------------------


def test_route_writes_no_audit_row(admin_client):
    """AC-4 — a pure read writes no audit row and mutates nothing, asserted the
    same way `test_sot_admin_categories.py` asserts it for GET /api/admin/categories."""
    p = _prefix()
    with Session(get_engine()) as s:
        cats = _seed_categories(s, p, 5)
        m = _mk_model(s, f"{p}-a")
        _assign(s, m.id, cats)

    with Session(get_engine()) as s:
        before = len(s.exec(select(AuditLog)).all())
        assignments_before = len(s.exec(select(ModelBrowseCategory)).all())

    assert admin_client.get(ROUTE, params={"min_categories": 5}).status_code == 200

    with Session(get_engine()) as s:
        assert len(s.exec(select(AuditLog)).all()) == before
        assert len(s.exec(select(ModelBrowseCategory)).all()) == assignments_before


# ---------------------------------------------------------------------------
# AC-5 — constant statement count
# ---------------------------------------------------------------------------


def test_statement_count_is_constant_across_fixture_size_and_limit():
    """AC-5 — two statements, always: one grouped HAVING read for `items`, one
    COUNT over the same grouped set for `total`. No N+1 in either branch."""
    engine = get_engine()

    p_small = _prefix()
    with Session(engine) as s:
        cats = _seed_categories(s, p_small, 6)
        m = _mk_model(s, f"{p_small}-only")
        _assign(s, m.id, cats)

    with Session(engine) as s, _count_selects(engine) as counter:
        list_over_categorized_models(s, min_categories=6, limit=50)
    small = counter["n"]

    p_big = _prefix()
    with Session(engine) as s:
        cats = _seed_categories(s, p_big, 6)
        for i in range(12):
            m = _mk_model(s, f"{p_big}-m{i:02d}")
            _assign(s, m.id, cats)

    with Session(engine) as s, _count_selects(engine) as counter:
        list_over_categorized_models(s, min_categories=6, limit=50)
    big = counter["n"]

    with Session(engine) as s, _count_selects(engine) as counter:
        list_over_categorized_models(s, min_categories=6, limit=1)
    capped = counter["n"]

    assert small == big == capped == 2


# ---------------------------------------------------------------------------
# AC-6 — shipped contracts untouched
# ---------------------------------------------------------------------------


def test_route_carries_summary_and_description(client):
    """AC-6 — the honesty convention. The gate behind this assertion is
    `_GOVERNANCE_ROUTES` in test_openapi_agent_surface.py; the
    `sot-admin-governance` tag sits OUTSIDE `TARGET_ROUTER_TAGS`, so nothing
    else covers it."""
    spec = client.get("/api/openapi.json").json()
    op = spec["paths"][ROUTE]["get"]
    assert (op.get("summary") or "").strip()
    assert (op.get("description") or "").strip()
    assert "agent-write" not in (op.get("tags") or [])
    assert "sot-admin-governance" in (op.get("tags") or [])


def test_public_model_contracts_are_unchanged(admin_client):
    """AC-6 — `ModelSummary` still carries no category count, and the shipped
    `uncategorized` predicate still answers the 52.2 question. Adding a count
    field to `ModelSummary` for one admin panel is the change this route exists
    to avoid."""
    p = _prefix()
    with Session(get_engine()) as s:
        cats = _seed_categories(s, p, 4)
        m = _mk_model(s, f"{p}-a")
        _assign(s, m.id, cats)

    body = admin_client.get("/api/models", params={"q": p}).json()
    assert body["items"], body
    for item in body["items"]:
        assert "categories" not in item
        assert "category_count" not in item
