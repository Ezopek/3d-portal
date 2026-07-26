"""Story 49.3 — GET /api/models?category=<slug> browse-category scope.

Covers AC-10..AC-17 (one slug-addressed scope, exclusivity, unknown-slug empty
page, no duplicate rows, the full AC-14 composition matrix, soft-delete posture,
uncategorized models staying visible) plus AC-5 (count/scope agreement) and the
AC-23(c) query-count guard.

The session-scoped shared DB (conftest `_isolated_db`) persists rows across
tests, so every seed uses unique slugs and every assertion is scoped to its own
seeded rows — no DB-global count is ever asserted (§6 F-10).
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
    ModelExternalLink,
    ModelSource,
    ModelStatus,
    ModelTag,
    Tag,
    TagGroup,
)
from app.core.db.session import get_engine
from app.modules.sot.service import list_models


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


# --- seeding helpers -------------------------------------------------------


def _prefix() -> str:
    return f"cs-{uuid.uuid4().hex[:6]}"


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


def _slugs(body):
    return {item["slug"] for item in body["items"]}


# --- AC-10 / AC-11: the scope itself ---------------------------------------


def test_models_scoped_by_category_returns_exactly_that_category(client):
    """AC-10/AC-11 — `?category=<slug>` returns exactly the live models assigned
    to that category, and `total` equals that count. Models in another category
    and uncategorized models are absent."""
    p = _prefix()
    with Session(get_engine()) as s:
        cat_a = _mk_cat(s, f"{p}-a")
        cat_b = _mk_cat(s, f"{p}-b")
        a1 = _mk_model(s, f"{p}-a1")
        a2 = _mk_model(s, f"{p}-a2")
        b1 = _mk_model(s, f"{p}-b1")
        _mk_model(s, f"{p}-loose")
        _assign(s, a1.id, cat_a.id)
        _assign(s, a2.id, cat_a.id)
        _assign(s, b1.id, cat_b.id)

    r = client.get(f"/api/models?category={p}-a&limit=200")
    assert r.status_code == 200, r.text
    body = r.json()
    assert _slugs(body) == {f"{p}-a1", f"{p}-a2"}
    assert body["total"] == 2


def test_models_unknown_category_slug_is_empty_page_not_404(client):
    """AC-12 — an unrecognised slug is 200 + `items: []` + `total: 0`, and the
    `offset`/`limit` echo is unchanged from the request. Never a 404."""
    r = client.get(f"/api/models?category=no-such-cat-{uuid.uuid4().hex[:8]}&offset=3&limit=7")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["offset"] == 3
    assert body["limit"] == 7


def test_uncategorized_model_stays_visible_unscoped(client):
    """AC-17 — a model with ZERO categories is returned (and counted) by an
    unscoped `GET /api/models`. FR26-CAT-2's "renders normally" at the API layer."""
    p = _prefix()
    with Session(get_engine()) as s:
        _mk_model(s, f"{p}-orphan")

    body = client.get(f"/api/models?q={p}-orphan&limit=200").json()
    assert _slugs(body) == {f"{p}-orphan"}
    assert body["total"] == 1


# --- AC-13: duplicate / total invariant (STRUCTURAL GUARD, not a RED) ------


def test_multi_category_model_appears_exactly_once(client):
    """AC-13 — STRUCTURAL GUARD, deliberately NOT presented as a TDD RED.

    Against the mandated IN-subquery implementation this holds by construction:
    `slug` is unique and `model_browse_category`'s composite PK is
    `(model_id, category_id)`, so a single-slug scope matches at most one row
    per model. The guard exists because Story 49.4 adds a tag-name disjunct
    that DOES fan out under a SQL JOIN — this test is the standing invariant
    49.4 inherits."""
    p = _prefix()
    with Session(get_engine()) as s:
        cat_a = _mk_cat(s, f"{p}-a")
        cat_b = _mk_cat(s, f"{p}-b")
        shared = _mk_model(s, f"{p}-shared")
        _assign(s, shared.id, cat_a.id)
        _assign(s, shared.id, cat_b.id)

    scoped = client.get(f"/api/models?category={p}-a&limit=200").json()
    assert [i["slug"] for i in scoped["items"]] == [f"{p}-shared"]
    assert scoped["total"] == 1

    unscoped = client.get(f"/api/models?q={p}-shared&limit=200").json()
    assert [i["slug"] for i in unscoped["items"]] == [f"{p}-shared"]
    assert unscoped["total"] == 1


# --- AC-5: count/scope agreement -------------------------------------------


def test_category_model_count_equals_scoped_models_total(client):
    """AC-5 — `model_count` from GET /api/categories equals `total` from
    GET /api/models?category=<slug> with no other filter applied."""
    p = _prefix()
    with Session(get_engine()) as s:
        cat = _mk_cat(s, f"{p}-agree")
        for i in range(3):
            _assign(s, _mk_model(s, f"{p}-m{i}").id, cat.id)
        # A soft-deleted assignment must be excluded on BOTH sides.
        _assign(
            s,
            _mk_model(s, f"{p}-gone", deleted_at=datetime.datetime.now(datetime.UTC)).id,
            cat.id,
        )

    listed = client.get("/api/categories").json()
    model_count = next(c["model_count"] for c in listed if c["slug"] == f"{p}-agree")
    total = client.get(f"/api/models?category={p}-agree&limit=200").json()["total"]
    assert model_count == total == 3


# --- AC-16: soft-delete posture --------------------------------------------


def test_soft_deleted_assigned_model_is_absent_and_uncounted(client):
    """AC-16 — a soft-deleted model assigned to S is absent from the scoped page
    and contributes nothing to S's `model_count`."""
    p = _prefix()
    with Session(get_engine()) as s:
        cat = _mk_cat(s, f"{p}-sd")
        _assign(s, _mk_model(s, f"{p}-live").id, cat.id)
        _assign(
            s,
            _mk_model(s, f"{p}-dead", deleted_at=datetime.datetime.now(datetime.UTC)).id,
            cat.id,
        )

    body = client.get(f"/api/models?category={p}-sd&limit=200").json()
    assert _slugs(body) == {f"{p}-live"}
    assert body["total"] == 1

    listed = client.get("/api/categories").json()
    assert next(c["model_count"] for c in listed if c["slug"] == f"{p}-sd") == 1


# --- AC-14: composition with every shipped filter family -------------------
#
# AC-14(a)-(j) is complete against the shipped get_models signature: status,
# tag_ids, tag_match, untagged, source, q, external_url, sort, include_deleted,
# offset, limit. Where a case passes on the T3.2 production code it is a
# COMPOSITION GUARD, not a manufactured RED (§5 T3.4).


def test_category_composes_with_q(client):
    """AC-14(a) — pure AND with the `q` substring filter; `q` semantics unchanged."""
    p = _prefix()
    with Session(get_engine()) as s:
        cat_a = _mk_cat(s, f"{p}-a")
        cat_b = _mk_cat(s, f"{p}-b")
        _assign(s, _mk_model(s, f"{p}-keep-a").id, cat_a.id)
        _assign(s, _mk_model(s, f"{p}-drop-a").id, cat_a.id)
        _assign(s, _mk_model(s, f"{p}-keep-b").id, cat_b.id)

    body = client.get(f"/api/models?category={p}-a&q={p}-keep&limit=200").json()
    assert _slugs(body) == {f"{p}-keep-a"}
    assert body["total"] == 1


def _seed_tag_matrix(p):
    """Two facet groups, three tags, three models in cat A + one in cat B."""
    with Session(get_engine()) as s:
        g1 = TagGroup(slug=f"{p}-g1", name_en="G1")
        g2 = TagGroup(slug=f"{p}-g2", name_en="G2")
        s.add(g1)
        s.add(g2)
        s.commit()
        s.refresh(g1)
        s.refresh(g2)
        g1a = Tag(slug=f"{p}-g1a", name_en="G1A", group_id=g1.id)
        g1b = Tag(slug=f"{p}-g1b", name_en="G1B", group_id=g1.id)
        g2a = Tag(slug=f"{p}-g2a", name_en="G2A", group_id=g2.id)
        for t in (g1a, g1b, g2a):
            s.add(t)
        s.commit()
        for t in (g1a, g1b, g2a):
            s.refresh(t)

        cat_a = _mk_cat(s, f"{p}-a")
        cat_b = _mk_cat(s, f"{p}-b")

        def _model(slug, cat, tags):
            m = _mk_model(s, slug)
            _assign(s, m.id, cat.id)
            for t in tags:
                s.add(ModelTag(model_id=m.id, tag_id=t.id))
            s.commit()
            return m

        _model(f"{p}-a-both", cat_a, [g1a, g2a])
        _model(f"{p}-a-orwithin", cat_a, [g1b, g2a])
        _model(f"{p}-a-g1only", cat_a, [g1a])
        _model(f"{p}-b-both", cat_b, [g1a, g2a])
        return [g1a.id, g1b.id, g2a.id]


def _tag_qs(tag_ids):
    return "".join(f"&tag_ids={tid}" for tid in tag_ids)


def test_category_composes_with_tag_match_all(client):
    """AC-14(b)/AC-15 — AND between facet groups, OR within a group, unchanged.

    The category predicate is a separate WHERE: it narrows the result set but
    never enters a tag bucket and never changes how `tag_match` partitions."""
    p = _prefix()
    tag_ids = _seed_tag_matrix(p)

    scoped = client.get(
        f"/api/models?category={p}-a&tag_match=all{_tag_qs(tag_ids)}&limit=200"
    ).json()
    # G1 bucket satisfied by g1a OR g1b; G2 bucket by g2a. -a-g1only misses G2.
    assert _slugs(scoped) == {f"{p}-a-both", f"{p}-a-orwithin"}
    assert scoped["total"] == 2

    # Same tag query WITHOUT the category still yields the identical partitioning
    # plus the category-B model — proof the scope did not alter tag semantics.
    unscoped = client.get(f"/api/models?tag_match=all{_tag_qs(tag_ids)}&limit=200").json()
    assert _slugs(unscoped) == {f"{p}-a-both", f"{p}-a-orwithin", f"{p}-b-both"}


def test_category_composes_with_tag_match_any(client):
    """AC-14(c) — pure OR across the listed tags, grouping ignored, AND-ed with
    the category scope."""
    p = _prefix()
    tag_ids = _seed_tag_matrix(p)

    scoped = client.get(
        f"/api/models?category={p}-a&tag_match=any{_tag_qs(tag_ids)}&limit=200"
    ).json()
    assert _slugs(scoped) == {f"{p}-a-both", f"{p}-a-orwithin", f"{p}-a-g1only"}
    assert scoped["total"] == 3


def test_category_composes_with_untagged_and_the_or_union(client):
    """AC-14(d) — `untagged=true` alone, and the `tag_ids`+`untagged` OR-union,
    both AND-ed with the category scope."""
    p = _prefix()
    with Session(get_engine()) as s:
        cat_a = _mk_cat(s, f"{p}-a")
        cat_b = _mk_cat(s, f"{p}-b")
        tag = Tag(slug=f"{p}-t", name_en="T")
        s.add(tag)
        s.commit()
        s.refresh(tag)

        bare_a = _mk_model(s, f"{p}-a-bare")
        _assign(s, bare_a.id, cat_a.id)
        tagged_a = _mk_model(s, f"{p}-a-tagged")
        _assign(s, tagged_a.id, cat_a.id)
        s.add(ModelTag(model_id=tagged_a.id, tag_id=tag.id))
        s.commit()
        bare_b = _mk_model(s, f"{p}-b-bare")
        _assign(s, bare_b.id, cat_b.id)
        tag_id = tag.id

    only_untagged = client.get(f"/api/models?category={p}-a&untagged=true&limit=200").json()
    assert _slugs(only_untagged) == {f"{p}-a-bare"}

    union = client.get(
        f"/api/models?category={p}-a&untagged=true&tag_ids={tag_id}&limit=200"
    ).json()
    assert _slugs(union) == {f"{p}-a-bare", f"{p}-a-tagged"}
    assert union["total"] == 2


def test_category_composes_with_status(client):
    """AC-14(e) — pure AND with `status`."""
    p = _prefix()
    with Session(get_engine()) as s:
        cat_a = _mk_cat(s, f"{p}-a")
        cat_b = _mk_cat(s, f"{p}-b")
        _assign(s, _mk_model(s, f"{p}-a-printed", status=ModelStatus.printed).id, cat_a.id)
        _assign(s, _mk_model(s, f"{p}-a-fresh").id, cat_a.id)
        _assign(s, _mk_model(s, f"{p}-b-printed", status=ModelStatus.printed).id, cat_b.id)

    body = client.get(f"/api/models?category={p}-a&status=printed&limit=200").json()
    assert _slugs(body) == {f"{p}-a-printed"}
    assert body["total"] == 1


def test_category_composes_with_source(client):
    """AC-14(f) — pure AND with `source`."""
    p = _prefix()
    with Session(get_engine()) as s:
        cat_a = _mk_cat(s, f"{p}-a")
        cat_b = _mk_cat(s, f"{p}-b")
        _assign(s, _mk_model(s, f"{p}-a-thangs", source=ModelSource.thangs).id, cat_a.id)
        _assign(s, _mk_model(s, f"{p}-a-own", source=ModelSource.own).id, cat_a.id)
        _assign(s, _mk_model(s, f"{p}-b-thangs", source=ModelSource.thangs).id, cat_b.id)

    body = client.get(f"/api/models?category={p}-a&source=thangs&limit=200").json()
    assert _slugs(body) == {f"{p}-a-thangs"}
    assert body["total"] == 1


def test_category_composes_with_sort(client):
    """AC-14(g) — `sort` still orders the scoped page (`recent`, `name_asc`)."""
    p = _prefix()
    base = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
    with Session(get_engine()) as s:
        cat = _mk_cat(s, f"{p}-a")
        for idx, (suffix, name) in enumerate([("old", "Zeta"), ("mid", "Alpha"), ("new", "Mu")]):
            m = _mk_model(
                s,
                f"{p}-{suffix}",
                name_en=name,
                created_at=base + datetime.timedelta(days=idx),
            )
            _assign(s, m.id, cat.id)

    recent = client.get(f"/api/models?category={p}-a&sort=recent&limit=200").json()
    assert [i["slug"] for i in recent["items"]] == [f"{p}-new", f"{p}-mid", f"{p}-old"]

    by_name = client.get(f"/api/models?category={p}-a&sort=name_asc&limit=200").json()
    assert [i["name_en"] for i in by_name["items"]] == ["Alpha", "Mu", "Zeta"]


def test_category_composes_with_pagination(client):
    """AC-14(h) — `total` reflects the SCOPED count and is independent of the
    page window; `offset`/`limit` page within the scope."""
    p = _prefix()
    base = datetime.datetime(2026, 2, 1, tzinfo=datetime.UTC)
    with Session(get_engine()) as s:
        cat_a = _mk_cat(s, f"{p}-a")
        cat_b = _mk_cat(s, f"{p}-b")
        for i in range(5):
            m = _mk_model(s, f"{p}-a{i}", created_at=base + datetime.timedelta(days=i))
            _assign(s, m.id, cat_a.id)
        _assign(s, _mk_model(s, f"{p}-b0").id, cat_b.id)

    seen = set()
    for offset in (0, 2, 4):
        body = client.get(
            f"/api/models?category={p}-a&sort=name_asc&offset={offset}&limit=2"
        ).json()
        assert body["total"] == 5, (offset, body["total"])
        assert body["offset"] == offset
        assert body["limit"] == 2
        seen |= _slugs(body)
    assert seen == {f"{p}-a{i}" for i in range(5)}


def test_category_composes_with_include_deleted(client):
    """AC-14(i)/AC-16 — the one composition where the two features could
    genuinely interact wrongly: with `include_deleted=true` the soft-deleted
    ASSIGNED model reappears in the scoped page (the shipped row semantics keep
    governing, the category predicate does not re-filter it out), while
    `model_count` on /api/categories still excludes it."""
    p = _prefix()
    with Session(get_engine()) as s:
        cat_a = _mk_cat(s, f"{p}-a")
        cat_b = _mk_cat(s, f"{p}-b")
        _assign(s, _mk_model(s, f"{p}-a-live").id, cat_a.id)
        _assign(
            s,
            _mk_model(s, f"{p}-a-dead", deleted_at=datetime.datetime.now(datetime.UTC)).id,
            cat_a.id,
        )
        _assign(
            s,
            _mk_model(s, f"{p}-b-dead", deleted_at=datetime.datetime.now(datetime.UTC)).id,
            cat_b.id,
        )

    default_page = client.get(f"/api/models?category={p}-a&limit=200").json()
    assert _slugs(default_page) == {f"{p}-a-live"}
    assert default_page["total"] == 1

    with_deleted = client.get(f"/api/models?category={p}-a&include_deleted=true&limit=200").json()
    assert _slugs(with_deleted) == {f"{p}-a-live", f"{p}-a-dead"}
    assert with_deleted["total"] == 2

    listed = client.get("/api/categories").json()
    assert next(c["model_count"] for c in listed if c["slug"] == f"{p}-a") == 1


def test_category_composes_with_external_url(client):
    """AC-14(j) — AND with the other shipped IN-subquery family; its typically
    0-or-1-row shape is undisturbed."""
    p = _prefix()
    url = f"https://example.invalid/{p}"
    with Session(get_engine()) as s:
        cat_a = _mk_cat(s, f"{p}-a")
        cat_b = _mk_cat(s, f"{p}-b")
        m_a = _mk_model(s, f"{p}-a-linked")
        m_b = _mk_model(s, f"{p}-b-linked")
        _assign(s, m_a.id, cat_a.id)
        _assign(s, m_b.id, cat_b.id)
        for m in (m_a, m_b):
            s.add(ModelExternalLink(model_id=m.id, source=ModelSource.other, url=url))
        s.commit()

    scoped = client.get(f"/api/models?category={p}-a&external_url={url}&limit=200").json()
    assert _slugs(scoped) == {f"{p}-a-linked"}
    assert scoped["total"] == 1

    unscoped = client.get(f"/api/models?external_url={url}&limit=200").json()
    assert _slugs(unscoped) == {f"{p}-a-linked", f"{p}-b-linked"}


# --- AC-23(c): query-count COVERAGE GUARD ----------------------------------
#
# NOT a TDD RED — authored after the T3.2 predicate landed and expected green
# on first run (§5 T5.1). Measured at the SERVICE layer.


def test_scoped_list_models_costs_no_extra_round_trip(client):
    """AC-23(c) — COVERAGE GUARD. A scoped call issues the SAME number of
    SELECTs as the equivalent unscoped call, and that count is independent of
    page size: the scope is a subquery inside the existing statement, not an
    extra round-trip.

    MANDATORY PRECONDITION (§5 T5.3): both compared calls must return a
    NON-EMPTY page of the SAME row count. The shipped eager-tag and
    eager-gallery blocks are each guarded by `if model_ids:`, so `list_models`
    legitimately issues 4 SELECTs on a non-empty page and only 2 on an empty
    one. A scoped-but-empty page compared against a populated unscoped page
    yields 2-vs-4 while the production code is entirely correct — and with
    zero live assignments that is the DEFAULT mistake, not an exotic one.
    Removing or weakening the `if model_ids:` guards to make such a comparison
    pass would introduce a genuine per-page N+1; it is a forbidden regression,
    not a fix."""
    engine = get_engine()
    p = _prefix()
    page = 4
    with Session(engine) as s:
        cat = _mk_cat(s, f"{p}-qc")
        for i in range(page * 2):
            _assign(s, _mk_model(s, f"{p}-qc{i}").id, cat.id)

    with Session(engine) as s, _count_selects(engine) as c_scoped:
        scoped = list_models(s, category=f"{p}-qc", limit=page)
    with Session(engine) as s, _count_selects(engine) as c_unscoped:
        unscoped = list_models(s, limit=page)

    # Precondition, asserted rather than assumed.
    assert len(scoped.items) == len(unscoped.items) == page
    assert c_scoped["n"] == c_unscoped["n"], (c_scoped["n"], c_unscoped["n"])
    assert c_scoped["n"] == 4, c_scoped["n"]  # baseline non-empty-page cost

    # Independent of page size (still non-empty, still equal on both sides).
    with Session(engine) as s, _count_selects(engine) as c_big:
        bigger = list_models(s, category=f"{p}-qc", limit=page * 2)
    assert len(bigger.items) == page * 2
    assert c_big["n"] == c_scoped["n"], (c_big["n"], c_scoped["n"])
