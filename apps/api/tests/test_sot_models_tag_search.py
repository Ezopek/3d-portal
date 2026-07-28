"""Story 49.4 — GET /api/models?q=<s> also matches assigned tag names.

Covers AC-1..AC-18: the tag-name match itself, union-not-subtraction semantics,
exactly-once rows with a distinct `total`, the deliberate `tag.slug` exclusion,
bilingual / null-safe / case-insensitive matching, the AC-10..AC-14 composition
matrix and the AC-15..AC-18 query-count guards.

RED/GUARD honesty (§5 ordering rule): the "T1 — genuine RED", "R-1/R-2 repair
slice" and "N-6 repair slice" tests were each authored and observed FAILING before
their own production fix existed. Everything else was authored green and is labelled
a GUARD in its own docstring. The T5.2 mutation battery reds only the union-correctness
and query-count subset of those guards; the AC-10..AC-14 composition guards are
regression coverage, NOT mutation-proved. Two guards sit outside the battery's reach
entirely and carry their own control: `test_matching_tag_assigned_to_nothing_widens_no_model`
(no mutation makes a `model_tag` row for an unassigned tag) and
`test_factory_built_engine_resolves_the_unicode_lower_shim` (never calls `list_models`,
so no `service.py` mutation reds it; proved by removing `dbapi_conn.create_function`).

The session-scoped shared DB (conftest `_isolated_db`) persists rows across
tests and modules, so every seed uses a unique prefix in slugs AND in tag NAMES
(§6 F-9) and every assertion is scoped to its own seeded rows — no DB-global
count is ever asserted.
"""

import contextlib
import datetime
import uuid

import pytest
from sqlalchemy import event
from sqlmodel import Session, text

from app.core.auth.cookies import ACCESS_COOKIE
from app.core.auth.jwt import encode_token
from app.core.db.models import (
    BrowseCategory,
    ExternalSource,
    Model,
    ModelBrowseCategory,
    ModelExternalLink,
    ModelSource,
    ModelStatus,
    ModelTag,
    Tag,
    TagGroup,
)
from app.core.db.session import create_engine_for_url, get_engine, init_schema, unicode_lower
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
    return f"ts-{uuid.uuid4().hex[:6]}"


def _mk_tag(s, slug, name_en, **kw):
    t = Tag(slug=slug, name_en=name_en, **kw)
    s.add(t)
    s.commit()
    s.refresh(t)
    return t


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


def _assign(s, model_id, tag_id):
    s.add(ModelTag(model_id=model_id, tag_id=tag_id))
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


# ===========================================================================
# T1 — genuine RED slice. Authored and observed FAILING before the production
# membership disjunct existed. See the story's Dev Agent Record for the
# verbatim baseline failure output.
# ===========================================================================


def test_q_matches_an_assigned_tag_name(client):
    """AC-1 — GENUINE RED. A model whose own name_en/name_pl/slug contain nothing
    resembling the query is returned when one of its ASSIGNED tags carries the
    query as a case-insensitive substring of name_pl or name_en.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        tag = _mk_tag(s, f"{p}-cable", f"{p} Cable", name_pl=f"{p} Kabel")
        m = _mk_model(s, f"{p}-m0", name_en=f"{p} M0")
        _assign(s, m.id, tag.id)

    r = client.get("/api/models", params={"q": f"{p} kabel"})
    assert r.status_code == 200
    body = r.json()
    assert _slugs(body) == {f"{p}-m0"}
    assert body["total"] == 1


def test_tag_match_is_a_union_never_a_subtraction(client):
    """AC-2 — GENUINE RED. The result set is the UNION of (name/slug match) and
    (tag match): the model that already matched on its own name still matches,
    and the tag-only model is added — never swapped in.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        tag = _mk_tag(s, f"{p}-cable", f"{p} Cable", name_pl=f"{p} Kabel")
        by_name = _mk_model(s, f"{p}-byname", name_en=f"{p} Kabel Widget")
        by_tag = _mk_model(s, f"{p}-bytag", name_en=f"{p} M1")
        _assign(s, by_tag.id, tag.id)
        assert by_name.id != by_tag.id

    r = client.get("/api/models", params={"q": f"{p} kabel"})
    assert r.status_code == 200
    body = r.json()
    assert _slugs(body) == {f"{p}-byname", f"{p}-bytag"}
    assert body["total"] == 2


def test_tag_names_match_bilingually_and_null_safely(client):
    """AC-7 — GENUINE RED. A tag with `name_pl IS NULL` still matches on
    `name_en`, and a tag matches on `name_pl` alone. No COALESCE / is_not(None)
    guard is needed: `lower(NULL) LIKE ...` is NULL and is absorbed by the OR.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        en_only = _mk_tag(s, f"{p}-en", f"{p} Cable")  # name_pl stays NULL
        pl_only = _mk_tag(s, f"{p}-pl", f"{p} Zzz", name_pl=f"{p} Kabel")
        assert en_only.name_pl is None
        m_en = _mk_model(s, f"{p}-men", name_en=f"{p} M-EN")
        m_pl = _mk_model(s, f"{p}-mpl", name_en=f"{p} M-PL")
        _assign(s, m_en.id, en_only.id)
        _assign(s, m_pl.id, pl_only.id)

    r_en = client.get("/api/models", params={"q": f"{p} cable"})
    assert r_en.status_code == 200
    assert _slugs(r_en.json()) == {f"{p}-men"}

    r_pl = client.get("/api/models", params={"q": f"{p} kabel"})
    assert r_pl.status_code == 200
    assert _slugs(r_pl.json()) == {f"{p}-mpl"}


def test_tag_name_match_is_case_insensitive(client):
    """AC-8 — GENUINE RED. `lower(column) LIKE lower(q)` on the tag side too:
    three casings of the same query return the identical, NON-EMPTY result set.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        tag = _mk_tag(s, f"{p}-cable", f"{p} Cable", name_pl=f"{p} Kabel")
        m = _mk_model(s, f"{p}-m0", name_en=f"{p} M0")
        _assign(s, m.id, tag.id)

    seen = []
    for query in (f"{p} KABEL", f"{p} kabel", f"{p} KaBeL"):
        r = client.get("/api/models", params={"q": query})
        assert r.status_code == 200
        seen.append(_slugs(r.json()))

    assert seen[0] == {f"{p}-m0"}
    assert seen[0] == seen[1] == seen[2]


# ===========================================================================
# R-1/R-2 repair slice (2026-07-27, post-re-review) — a SECOND genuine RED.
# Authored and observed FAILING against the tree the re-review inspected, i.e.
# before the connection-level Unicode case-folding shim existed. Not a guard.
# ===========================================================================


def test_polish_diacritic_tag_names_match_in_any_casing(client):
    """AC-8, diacritic class — GENUINE RED (repair slice). Extends the ASCII-only
    corpus the AC-8 guard above certifies on, with a case derived from SHIPPED
    data: `app/core/db/seed.py`'s starter taxonomy stores the tag
    `name_pl = "Łazienka"`, so an upper-case Polish diacritic in a tag name is
    live production data, not a hypothesis.

    Before the repair, `lower()` in the emitted SQL was SQLite's built-in, which
    folds ASCII only: `lower('Łazienka')` stayed `'Łazienka'` while the LIKE
    pattern was folded by Python's full-Unicode `str.lower()`, so the row was
    unreachable by EVERY casing of its own name — including the exact one. The
    tag branch now folds through the connection-level `portal_lower` shim
    (`app/core/db/session.py`), so all three casings return the same model.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        tag = _mk_tag(s, f"{p}-bathroom", f"{p} Bathroom", name_pl=f"{p} Łazienka")
        m = _mk_model(s, f"{p}-m0", name_en=f"{p} M0")
        _assign(s, m.id, tag.id)

    seen = []
    for query in (f"{p} łazienka", f"{p} Łazienka", f"{p} ŁAZIENKA"):
        r = client.get("/api/models", params={"q": query})
        assert r.status_code == 200
        seen.append(_slugs(r.json()))

    assert seen[0] == {f"{p}-m0"}
    assert seen[0] == seen[1] == seen[2]


def test_upper_case_diacritic_tag_name_matches_on_name_en_too(client):
    """AC-8, diacritic class — GENUINE RED (repair slice). The `name_en` half of
    the disjunct folds identically: a tag whose ENGLISH name carries a
    non-ASCII upper-case letter is reachable by its lower-cased form. Pins that
    the shim was applied to BOTH tag columns, not only `name_pl`.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        tag = _mk_tag(s, f"{p}-en", f"{p} Łącznik")  # name_pl stays NULL
        m = _mk_model(s, f"{p}-men", name_en=f"{p} M-EN")
        _assign(s, m.id, tag.id)

    body = client.get("/api/models", params={"q": f"{p} łącznik"}).json()
    assert _slugs(body) == {f"{p}-men"}
    assert body["total"] == 1


# ===========================================================================
# T3 — union correctness. STRUCTURAL GUARDS, not REDs: authored after the T2
# production change was green, so they pass on first run. Their load-bearing
# character is established by the T5.2 mutation battery, not by a RED.
# ===========================================================================


def test_model_matching_both_its_name_and_a_tag_appears_once(client):
    """AC-3(a) — GUARD, not a RED. A model matching on BOTH its own name and an
    assigned tag name is returned exactly once and counted once in `total`.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        tag = _mk_tag(s, f"{p}-cable", f"{p} Cable", name_pl=f"{p} Kabel")
        m = _mk_model(s, f"{p}-both", name_en=f"{p} Kabel Both")
        _assign(s, m.id, tag.id)

    body = client.get("/api/models", params={"q": f"{p} kabel"}).json()
    returned = [item["slug"] for item in body["items"]]
    assert returned == [f"{p}-both"]
    assert body["total"] == 1


def test_model_with_three_matching_tags_appears_once(client):
    """AC-3(b)/(c) — GUARD, not a RED. A model carrying N=3 tags that each match
    the query appears exactly once on the page and contributes exactly 1 to
    `total`. This is the case a SQL JOIN onto `base` would inflate to three rows
    (§6 F-4); T5.2 mutation (a) demonstrates that failure.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        m = _mk_model(s, f"{p}-multi", name_en=f"{p} Multi")
        for i in range(3):
            tag = _mk_tag(s, f"{p}-cable{i}", f"{p} Cable {i}", name_pl=f"{p} Kabel {i}")
            _assign(s, m.id, tag.id)

    body = client.get("/api/models", params={"q": f"{p} kabel"}).json()
    returned = [item["slug"] for item in body["items"]]
    assert returned == [f"{p}-multi"]
    assert len(returned) == 1
    assert body["total"] == 1


def test_total_is_the_distinct_model_count_across_pages(client):
    """AC-4 — GUARD, not a RED. `total` is the distinct model count, independent
    of the page window; paging the whole result set yields each model exactly
    once with no repeats across pages.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        tag_a = _mk_tag(s, f"{p}-cable-a", f"{p} Cable A", name_pl=f"{p} Kabel A")
        tag_b = _mk_tag(s, f"{p}-cable-b", f"{p} Cable B", name_pl=f"{p} Kabel B")
        for i in range(5):
            m = _mk_model(s, f"{p}-m{i}", name_en=f"{p} M{i}")
            _assign(s, m.id, tag_a.id)
            if i % 2 == 0:
                # Several matching tags on the same model must not inflate total.
                _assign(s, m.id, tag_b.id)

    seen: list[str] = []
    for offset in (0, 2, 4):
        body = client.get(
            "/api/models",
            params={"q": f"{p} kabel", "sort": "name_asc", "offset": offset, "limit": 2},
        ).json()
        assert body["total"] == 5
        seen.extend(item["slug"] for item in body["items"])

    assert len(seen) == 5
    assert sorted(seen) == sorted({f"{p}-m{i}" for i in range(5)})


def test_tag_slug_is_not_matched(client):
    """AC-6 — NEGATIVE GUARD, not a RED (it is green at baseline too, by
    construction). A query equal to a tag's slug that matches neither that tag's
    name_pl/name_en nor any model field returns no rows for that tag's models.
    T5.2 mutation (c) proves this guard is load-bearing.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        tag = _mk_tag(s, f"{p}-hiddenslug", f"{p} Visible", name_pl=f"{p} Widoczny")
        m = _mk_model(s, f"{p}-m0", name_en=f"{p} M0")
        _assign(s, m.id, tag.id)

    by_slug = client.get("/api/models", params={"q": f"{p}-hiddenslug"}).json()
    assert by_slug["items"] == []
    assert by_slug["total"] == 0

    # Control: the very same model IS reachable through the tag's NAME.
    by_name = client.get("/api/models", params={"q": f"{p} visible"}).json()
    assert _slugs(by_name) == {f"{p}-m0"}


def test_matching_tag_assigned_to_nothing_widens_no_model(client):
    """§6 F-8 / R-5 — GUARD, not a RED. The disjunct is an ASSIGNMENT membership
    test: a tag whose name matches the query but which is assigned to no model
    widens the result set by nothing. This is the exact invariant the story's
    zero-shipped-test-breakage argument rests on — the unassigned `Articulated`
    tags at test_sot_tags.py:32,47 cannot reach test_sot_models_list.py:135 — and
    it is distinct from the two adjacent cases already covered: a zero-tag model
    not being matched (AC-12) and an assigned NON-matching tag not matching
    (AC-7). A predicate that matched tag names without going through `model_tag`
    would turn both seeded models below into hits.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        # Matching name, deliberately never assigned to anything.
        orphan = _mk_tag(s, f"{p}-orphan", f"{p} Cable", name_pl=f"{p} Kabel")
        # A zero-tag model, and a model carrying only a NON-matching tag.
        no_tag = _mk_model(s, f"{p}-notag", name_en=f"{p} NOTAG")
        other = _mk_tag(s, f"{p}-other", f"{p} Zzz", name_pl=f"{p} Zzz")
        m_other = _mk_model(s, f"{p}-othertag", name_en=f"{p} OTHERTAG")
        _assign(s, m_other.id, other.id)
        orphan_id, no_tag_id = orphan.id, no_tag.id

    for query in (f"{p} kabel", f"{p} cable"):
        body = client.get("/api/models", params={"q": query}).json()
        assert body["items"] == []
        assert body["total"] == 0

    # Control: the same tag name DOES widen once it is actually assigned.
    with Session(get_engine()) as s:
        _assign(s, no_tag_id, orphan_id)

    widened = client.get("/api/models", params={"q": f"{p} kabel"}).json()
    assert _slugs(widened) == {f"{p}-notag"}
    assert widened["total"] == 1


# ===========================================================================
# T4 — composition matrix (AC-9..AC-14). ALL STRUCTURAL GUARDS, explicitly NOT
# REDs: every one of them is green on first run against the T2 code.
# ===========================================================================


def test_composes_with_category_scope(client):
    """AC-10 — GUARD, not a RED. `?category=<slug>&q=<s>` is a pure AND: the
    tag-aware q narrows WITHIN the category scope, and a tag match outside the
    scope does not widen it.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        cat_in = BrowseCategory(slug=f"{p}-in", name_en=f"{p}-IN")
        cat_out = BrowseCategory(slug=f"{p}-out", name_en=f"{p}-OUT")
        s.add(cat_in)
        s.add(cat_out)
        s.commit()
        s.refresh(cat_in)
        s.refresh(cat_out)
        tag = _mk_tag(s, f"{p}-cable", f"{p} Cable", name_pl=f"{p} Kabel")
        m_in = _mk_model(s, f"{p}-in-m", name_en=f"{p} IN M")
        m_out = _mk_model(s, f"{p}-out-m", name_en=f"{p} OUT M")
        m_in_untagged = _mk_model(s, f"{p}-in-plain", name_en=f"{p} IN PLAIN")
        for m in (m_in, m_out):
            _assign(s, m.id, tag.id)
        s.add(ModelBrowseCategory(model_id=m_in.id, category_id=cat_in.id))
        s.add(ModelBrowseCategory(model_id=m_in_untagged.id, category_id=cat_in.id))
        s.add(ModelBrowseCategory(model_id=m_out.id, category_id=cat_out.id))
        s.commit()

    scoped = client.get("/api/models", params={"category": f"{p}-in", "q": f"{p} kabel"}).json()
    assert _slugs(scoped) == {f"{p}-in-m"}
    assert scoped["total"] == 1

    # The out-of-scope tag match is absent, and the category scope itself is
    # untouched by the tag-name branch.
    unfiltered_scope = client.get("/api/models", params={"category": f"{p}-in"}).json()
    assert _slugs(unfiltered_scope) == {f"{p}-in-m", f"{p}-in-plain"}


def test_composes_with_tag_ids_and_tag_match(client):
    """AC-11 — GUARD, not a RED. `tag_ids` + `tag_match=all|any` AND-s with the
    q or_(); the tag-NAME match never enters a `tag_match` bucket and never
    partitions by `Tag.group_id`.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        g1 = TagGroup(slug=f"{p}-g1", name_en=f"{p}-G1")
        g2 = TagGroup(slug=f"{p}-g2", name_en=f"{p}-G2")
        s.add(g1)
        s.add(g2)
        s.commit()
        s.refresh(g1)
        s.refresh(g2)
        t_name = _mk_tag(s, f"{p}-cable", f"{p} Cable", name_pl=f"{p} Kabel")
        t_g1 = _mk_tag(s, f"{p}-g1a", f"{p} G1A", group_id=g1.id)
        t_g2 = _mk_tag(s, f"{p}-g2a", f"{p} G2A", group_id=g2.id)
        m_both = _mk_model(s, f"{p}-both", name_en=f"{p} BOTH")
        m_g1_only = _mk_model(s, f"{p}-g1only", name_en=f"{p} G1ONLY")
        m_name_only = _mk_model(s, f"{p}-nameonly", name_en=f"{p} NAMEONLY")
        for tid in (t_name.id, t_g1.id, t_g2.id):
            _assign(s, m_both.id, tid)
        _assign(s, m_g1_only.id, t_g1.id)
        _assign(s, m_name_only.id, t_name.id)
        ids = [str(t_g1.id), str(t_g2.id)]

    all_body = client.get(
        "/api/models", params={"tag_ids": ids, "tag_match": "all", "q": f"{p} kabel"}
    ).json()
    assert _slugs(all_body) == {f"{p}-both"}
    assert all_body["total"] == 1

    any_body = client.get(
        "/api/models", params={"tag_ids": ids, "tag_match": "any", "q": f"{p} kabel"}
    ).json()
    # m_g1_only satisfies tag_ids but not q; m_name_only satisfies q but not
    # tag_ids. Neither is returned — the two predicates AND.
    assert _slugs(any_body) == {f"{p}-both"}
    assert any_body["total"] == 1


def test_composes_with_untagged(client):
    """AC-12 — GUARD, not a RED. A zero-tag model can never satisfy the
    membership disjunct, so `untagged=true` + a tag-name-only q is empty, while
    `untagged=true` + a model-name q returns the zero-tag model.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        tag = _mk_tag(s, f"{p}-cable", f"{p} Cable", name_pl=f"{p} Kabel")
        tagged = _mk_model(s, f"{p}-tagged", name_en=f"{p} TAGGED")
        _assign(s, tagged.id, tag.id)
        _mk_model(s, f"{p}-solo", name_en=f"{p} Kabel Solo")
        tag_id = str(tag.id)

    tag_only = client.get("/api/models", params={"untagged": "true", "q": f"{p} cable"}).json()
    assert tag_only["items"] == []
    assert tag_only["total"] == 0

    by_name = client.get("/api/models", params={"untagged": "true", "q": f"{p} kabel"}).json()
    assert _slugs(by_name) == {f"{p}-solo"}

    union = client.get(
        "/api/models",
        params={"untagged": "true", "tag_ids": [tag_id], "q": f"{p} kabel"},
    ).json()
    # tag_ids OR untagged, AND-ed with q: the tagged model matches q only via
    # its tag name, the solo model via its own name — both belong.
    assert _slugs(union) == {f"{p}-solo", f"{p}-tagged"}


def test_composes_with_soft_delete(client):
    """AC-13 — GUARD, not a RED. A soft-deleted model carrying a matching tag is
    absent and uncounted by default and reappears with include_deleted=true:
    liveness stays owned by the outer query, the subquery adds none of its own.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        tag = _mk_tag(s, f"{p}-cable", f"{p} Cable", name_pl=f"{p} Kabel")
        live = _mk_model(s, f"{p}-live", name_en=f"{p} LIVE")
        gone = _mk_model(
            s,
            f"{p}-gone",
            name_en=f"{p} GONE",
            deleted_at=datetime.datetime.now(datetime.UTC),
        )
        _assign(s, live.id, tag.id)
        _assign(s, gone.id, tag.id)

    default = client.get("/api/models", params={"q": f"{p} kabel"}).json()
    assert _slugs(default) == {f"{p}-live"}
    assert default["total"] == 1

    with_deleted = client.get(
        "/api/models", params={"q": f"{p} kabel", "include_deleted": "true"}
    ).json()
    assert _slugs(with_deleted) == {f"{p}-live", f"{p}-gone"}
    assert with_deleted["total"] == 2


def test_composes_with_status_source_sort_pagination_and_external_url(client):
    """AC-14 — GUARD, not a RED. `status`, `source`, `sort`, `offset`/`limit` and
    `external_url` each compose with the tag-aware q as a pure AND, with no
    change to their own semantics.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        tag = _mk_tag(s, f"{p}-cable", f"{p} Cable", name_pl=f"{p} Kabel")
        a = _mk_model(
            s,
            f"{p}-a",
            name_en=f"{p} A",
            status=ModelStatus.printed,
            # Deliberately NOT `printables`: that value is the one source
            # carrying an UNSCOPED exact-set assertion in a byte-unmodified
            # AC-20 witness (test_sot_models_list.py::test_list_filter_by_source),
            # and the session-scoped DB would leak this row into it under any
            # collection order. `thangs` is only ever asserted category-scoped.
            source=ModelSource.thangs,
        )
        b = _mk_model(
            s,
            f"{p}-b",
            name_en=f"{p} B",
            status=ModelStatus.not_printed,
            source=ModelSource.own,
        )
        c = _mk_model(
            s,
            f"{p}-c",
            name_en=f"{p} C",
            status=ModelStatus.printed,
            source=ModelSource.own,
        )
        for m in (a, b, c):
            _assign(s, m.id, tag.id)
        s.add(
            ModelExternalLink(
                model_id=b.id,
                source=ExternalSource.printables,
                url=f"https://example.invalid/{p}/b",
            )
        )
        s.commit()

    q = f"{p} kabel"

    by_status = client.get("/api/models", params={"q": q, "status": "printed"}).json()
    assert _slugs(by_status) == {f"{p}-a", f"{p}-c"}
    assert by_status["total"] == 2

    by_source = client.get("/api/models", params={"q": q, "source": "own"}).json()
    assert _slugs(by_source) == {f"{p}-b", f"{p}-c"}

    asc = client.get("/api/models", params={"q": q, "sort": "name_asc"}).json()
    assert [item["slug"] for item in asc["items"]] == [f"{p}-a", f"{p}-b", f"{p}-c"]

    recent = client.get("/api/models", params={"q": q, "sort": "recent"}).json()
    # ORDER, not just membership: `recent` is created_at desc and a, b, c were
    # created in that sequence, so the newest row must come first. Asserting a
    # set here would stay green under a reversed or dropped ORDER BY.
    assert [item["slug"] for item in recent["items"]] == [f"{p}-c", f"{p}-b", f"{p}-a"]

    page = client.get(
        "/api/models", params={"q": q, "sort": "name_asc", "offset": 1, "limit": 1}
    ).json()
    assert [item["slug"] for item in page["items"]] == [f"{p}-b"]
    assert page["total"] == 3

    by_url = client.get(
        "/api/models", params={"q": q, "external_url": f"https://example.invalid/{p}/b"}
    ).json()
    assert _slugs(by_url) == {f"{p}-b"}
    assert by_url["total"] == 1


def test_q_none_and_empty_string_change_nothing(client):
    """AC-9 — GUARD, not a RED. With q omitted or empty the `if q:` guard is
    falsy, so no subquery is built. Assertions are scoped to a category unique
    to this test rather than to a DB-global count.
    """
    p = _prefix()
    with Session(get_engine()) as s:
        cat = BrowseCategory(slug=f"{p}-scope", name_en=f"{p}-SCOPE")
        s.add(cat)
        s.commit()
        s.refresh(cat)
        tag = _mk_tag(s, f"{p}-cable", f"{p} Cable", name_pl=f"{p} Kabel")
        tagged = _mk_model(s, f"{p}-tagged", name_en=f"{p} TAGGED")
        plain = _mk_model(s, f"{p}-plain", name_en=f"{p} PLAIN")
        _assign(s, tagged.id, tag.id)
        for m in (tagged, plain):
            s.add(ModelBrowseCategory(model_id=m.id, category_id=cat.id))
        s.commit()

    no_q = client.get("/api/models", params={"category": f"{p}-scope"}).json()
    empty_q = client.get("/api/models", params={"category": f"{p}-scope", "q": ""}).json()
    assert _slugs(no_q) == {f"{p}-tagged", f"{p}-plain"}
    assert _slugs(empty_q) == _slugs(no_q)
    assert empty_q["total"] == no_q["total"] == 2

    with_q = client.get("/api/models", params={"category": f"{p}-scope", "q": f"{p} kabel"}).json()
    assert _slugs(with_q) == {f"{p}-tagged"}

    engine = get_engine()
    with Session(engine) as s, _count_selects(engine) as counter:
        result = list_models(s, q=None, category=f"{p}-scope", limit=4)
    # Scoped to this test's own category, never to a DB-global page fill: the
    # page is non-empty (so both `if model_ids:` hydration blocks fire and the
    # 4-SELECT baseline applies) and holds exactly the two rows seeded above.
    # The counted 4 is therefore the CATEGORY-SCOPED baseline — `category` builds
    # its own IN-subquery inside the same statement, which costs no extra SELECT,
    # so it equals the unscoped baseline measured at T0.2. What this pins is
    # AC-9's claim that `q=None` adds nothing on top of it; a category-side
    # regression would break it too, which is why the behavioural half above
    # (envelope equality between no-q and empty-q) is the primary AC-9 evidence.
    assert {item.slug for item in result.items} == {f"{p}-tagged", f"{p}-plain"}
    assert counter["n"] == 4


# ===========================================================================
# T5.1 — NFR26-PERF-1 query-count evidence (AC-15..AC-18). COVERAGE GUARDS,
# explicitly NOT REDs: authored after T2 landed the code they measure. Counted
# at the SERVICE layer (list_models called directly) so auth/session overhead
# does not pollute the count. Every compared call returns a NON-EMPTY page. The
# SAME-row-count precondition holds where it is meaningful — AC-16's two
# fan-out fixtures (3 rows each) and AC-17's absolute 4 — but NOT for AC-15,
# whose own text mandates varying the page size, so its two calls return 2 and
# 4 rows by construction. A 2-vs-4 SELECT delta would mean a compared page came
# back empty, never that the `if model_ids:` eager-hydration guards should be
# weakened.
# ===========================================================================


def _seed_fan_out(session, p, tag_count, tags_per_model, model_count):
    tags = [
        _mk_tag(session, f"{p}-cable{i}", f"{p} Cable {i}", name_pl=f"{p} Kabel {i}")
        for i in range(tag_count)
    ]
    for i in range(model_count):
        m = _mk_model(session, f"{p}-m{i}", name_en=f"{p} M{i}")
        for j in range(tags_per_model):
            _assign(session, m.id, tags[(i + j) % tag_count].id)


def test_select_count_is_constant_across_page_size(client):
    """AC-15 — GUARD, not a RED. A tag-matching q issues the same number of SQL
    statements at limit=k and limit=2k, both pages non-empty.
    """
    p = _prefix()
    engine = get_engine()
    with Session(engine) as s:
        _seed_fan_out(s, p, tag_count=2, tags_per_model=1, model_count=6)

    counts = {}
    for limit in (2, 4):
        with Session(engine) as s, _count_selects(engine) as counter:
            result = list_models(s, q=f"{p} kabel", limit=limit)
        assert len(result.items) == limit  # non-empty page, as AC-17 requires
        assert result.total == 6
        counts[limit] = counter["n"]

    assert counts[2] == counts[4]


def test_select_count_is_constant_across_tag_fan_out(client):
    """AC-16 — GUARD, not a RED. Two fixtures with very different matching-tag
    fan-out, sized so both return the SAME non-empty row count on the SAME page,
    issue the same number of SQL statements (the equal-result-count comparison
    NFR26-PERF-1 prescribes).
    """
    low_p, high_p = _prefix(), _prefix()
    engine = get_engine()
    with Session(engine) as s:
        _seed_fan_out(s, low_p, tag_count=1, tags_per_model=1, model_count=3)
        _seed_fan_out(s, high_p, tag_count=5, tags_per_model=3, model_count=3)

    results = {}
    for label, p in (("low", low_p), ("high", high_p)):
        with Session(engine) as s, _count_selects(engine) as counter:
            result = list_models(s, q=f"{p} kabel", limit=10)
        results[label] = (counter["n"], len(result.items), result.total)

    assert results["low"][1] == results["high"][1] == 3  # equal, non-empty
    assert results["low"][2] == results["high"][2] == 3
    assert results["low"][0] == results["high"][0]


def test_tag_aware_q_issues_exactly_four_selects(client):
    """AC-17/AC-18 — GUARD, not a RED. The absolute baseline: a tag-aware q on a
    non-empty page costs 4 SELECTs — identical to the shipped q measured at
    baseline — because the membership branch is a subquery inside the SAME
    statement, not a Python pre-query. Contrast tag_match=all, which legitimately
    costs 5 by resolving Tag.group_id first. An empty page costs 2, since both
    eager-hydration blocks are `if model_ids:`-guarded.
    """
    p = _prefix()
    engine = get_engine()
    with Session(engine) as s:
        _seed_fan_out(s, p, tag_count=3, tags_per_model=2, model_count=4)

    with Session(engine) as s, _count_selects(engine) as counter:
        result = list_models(s, q=f"{p} kabel", limit=4)
    assert len(result.items) == 4
    assert result.total == 4
    assert counter["n"] == 4

    with Session(engine) as s, _count_selects(engine) as empty_counter:
        empty = list_models(s, q=f"{p} kabel zzz-no-such-thing", limit=4)
    assert empty.items == []
    assert empty_counter["n"] == 2


# ===========================================================================
# M-1 repair slice (2026-07-27) — GUARD, not a RED. The tag disjunct folds
# through `portal_lower`, which `create_engine_for_url` registers on every new
# SQLite connection. That makes the canonical engine factory a real dependency
# of `list_models(q=...)`: a Session bound to a bare `create_engine(...)` raises
# `OperationalError: no such function: portal_lower` instead of degrading to an
# ASCII-only match. Latent today — `list_models` has one caller and every
# shipped engine path uses the factory — but until now nothing pinned it. This
# guard pins the positive half (the factory does provide the function); the
# negative half is documented in `app/core/db/session.py` and in
# `deferred-work.md` rather than frozen into an assertion.
# ===========================================================================


def test_factory_built_engine_resolves_the_unicode_lower_shim(tmp_path):
    """M-1 — GUARD, not a RED. An engine built by `create_engine_for_url`
    resolves `portal_lower` and folds non-ASCII, and `unicode_lower` routes a
    SQLite session to that shim rather than to the built-in ASCII-only
    `lower()`. Runs against its own throwaway SQLite file, so it seeds nothing
    into the session-scoped shared DB and adds no pressure to any shared window.
    """
    engine = create_engine_for_url(f"sqlite:///{tmp_path / 'shim-probe.db'}")
    try:
        with Session(engine) as s:
            # The helper routes SQLite through the shim, not the built-in lower().
            assert "portal_lower" in str(unicode_lower(s)(Tag.name_pl))
            # ...and a connection this factory built actually provides it.
            assert s.exec(text("SELECT portal_lower('ŁAZIENKA')")).one()[0] == "łazienka"
    finally:
        # Release the pooled connection and its file handle; tmp_path cleanup
        # blocks on an open handle under Windows. Matches the disposal the
        # nearest in-tree raw-engine tests already do.
        engine.dispose()


# ===========================================================================
# N-6 repair slice (2026-07-27) — GENUINE RED. `unicode_lower` resolved the
# dialect through an ARGUMENT-LESS `session.get_bind()`, which raises
# `UnboundExecutionError` on a Session bound per mapper (`Session(binds=...)`)
# — a shape that ran `list_models(q=...)` fine before Story 49.4, because bind
# resolution then happened per statement. Latent in-tree (nothing uses
# `binds=`), but it is a second coupling from the same helper, so it is pinned
# rather than only documented. The fix is one token: resolve the bind through
# the mapper the predicate actually targets, `session.get_bind(Tag)`.
# ===========================================================================


def test_per_mapper_bound_session_still_folds_tag_names(tmp_path):
    """N-6 — GENUINE RED, observed failing before `session.get_bind(Tag)` with
    `UnboundExecutionError`. A Session bound per mapper instead of to a single
    Engine still runs `list_models(q=...)` and still folds non-ASCII tag names.
    Runs against its own throwaway SQLite file, so it seeds nothing into the
    session-scoped shared DB and adds no pressure to any shared window.
    """
    # Imported here, not at module scope, so this append leaves every line
    # anchor the story record already quotes for this file exactly where it is.
    from app.core.db.models import ModelFile

    p = _prefix()
    engine = create_engine_for_url(f"sqlite:///{tmp_path / 'binds-probe.db'}")
    try:
        init_schema(engine)
        binds = {Model: engine, ModelTag: engine, Tag: engine, ModelFile: engine}
        with Session(binds=binds) as s:
            tag = _mk_tag(s, f"{p}-bath", f"{p} Bathroom", name_pl=f"{p} Łazienka")
            m = _mk_model(s, f"{p}-m0", name_en=f"{p} M0")
            _assign(s, m.id, tag.id)
            result = list_models(s, q=f"{p} ŁAZIENKA")
        assert [item.slug for item in result.items] == [f"{p}-m0"]
        assert result.total == 1
    finally:
        engine.dispose()
