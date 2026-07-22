"""Story 42.2 — GET /api/tag-groups read endpoint + no-N+1 query-count proofs.

Covers AC #4 (envelope/order/groupless/empty groups), AC #5 (cross-endpoint
count consistency), AC #8 (constant, cardinality-independent query count).

Terminology discipline (Dev Notes): a *groupless tag* (`Tag.group_id IS NULL`)
is unrelated to an *untagged model* — these tests never conflate them.

The session-scoped shared DB (conftest `_isolated_db`) persists rows across
tests in this file, so every seed uses unique slugs and every assertion is
scoped to its own seeded rows (never a DB-global membership count).
"""

import contextlib
import datetime
import uuid

import pytest
from sqlalchemy import event
from sqlmodel import Session

from app.core.auth.cookies import ACCESS_COOKIE
from app.core.auth.jwt import encode_token
from app.core.db.models import Model, ModelStatus, ModelTag, Tag, TagGroup
from app.core.db.session import get_engine
from app.modules.sot.service import list_tag_groups, list_tags


@pytest.fixture(autouse=True)
def _default_admin_cookie(client):
    """Authenticate every request — GET /api/tag-groups is default-deny (AC #6)."""
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


def _mk_group(s, slug, *, position=0, name_pl=None):
    g = TagGroup(slug=slug, name_en=slug.upper(), name_pl=name_pl, position=position)
    s.add(g)
    s.commit()
    s.refresh(g)
    return g


def _mk_tag(s, slug, *, group_id=None, group_position=0):
    t = Tag(slug=slug, name_en=slug.upper(), group_id=group_id, group_position=group_position)
    s.add(t)
    s.commit()
    s.refresh(t)
    return t


def _tag_model(s, tag_id, *, count, deleted=0):
    """Attach `count` live + `deleted` soft-deleted models to a tag."""
    for _ in range(count):
        m = Model(
            slug=f"m-{uuid.uuid4().hex[:10]}",
            name_en="M",
            status=ModelStatus.not_printed,
        )
        s.add(m)
        s.commit()
        s.refresh(m)
        s.add(ModelTag(model_id=m.id, tag_id=tag_id))
        s.commit()
    for _ in range(deleted):
        m = Model(
            slug=f"m-{uuid.uuid4().hex[:10]}",
            name_en="M",
            status=ModelStatus.not_printed,
            deleted_at=datetime.datetime.now(datetime.UTC),
        )
        s.add(m)
        s.commit()
        s.refresh(m)
        s.add(ModelTag(model_id=m.id, tag_id=tag_id))
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


# --- AC #4: envelope, ordering, groupless, empty groups --------------------


def test_tag_groups_envelope_has_groups_and_groupless_keys(client):
    r = client.get("/api/tag-groups")
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body.keys()) == {"groups", "groupless"}
    assert isinstance(body["groups"], list)
    assert isinstance(body["groupless"], list)


def test_tag_groups_group_order_position_then_slug(client):
    engine = get_engine()
    p = f"grp-order-{uuid.uuid4().hex[:6]}"
    with Session(engine) as s:
        _mk_group(s, f"{p}-zzz", position=1)
        _mk_group(s, f"{p}-aaa", position=1)
        _mk_group(s, f"{p}-mmm", position=0)

    body = client.get("/api/tag-groups").json()
    order = [g["slug"] for g in body["groups"] if g["slug"].startswith(p)]
    # position 0 first; within equal position, slug ascending
    assert order == [f"{p}-mmm", f"{p}-aaa", f"{p}-zzz"]


def test_tag_groups_intra_group_tag_order_group_position_then_slug(client):
    engine = get_engine()
    p = f"tag-order-{uuid.uuid4().hex[:6]}"
    with Session(engine) as s:
        g = _mk_group(s, f"{p}-grp")
        _mk_tag(s, f"{p}-zzz", group_id=g.id, group_position=1)
        _mk_tag(s, f"{p}-aaa", group_id=g.id, group_position=1)
        _mk_tag(s, f"{p}-mmm", group_id=g.id, group_position=0)
        gid = str(g.id)

    body = client.get("/api/tag-groups").json()
    grp = next(g for g in body["groups"] if g["id"] == gid)
    order = [t["slug"] for t in grp["tags"]]
    assert order == [f"{p}-mmm", f"{p}-aaa", f"{p}-zzz"]


def test_tag_groups_empty_group_included_with_empty_tags(client):
    engine = get_engine()
    slug = f"empty-grp-{uuid.uuid4().hex[:8]}"
    with Session(engine) as s:
        g = _mk_group(s, slug)
        gid = str(g.id)

    body = client.get("/api/tag-groups").json()
    grp = next((g for g in body["groups"] if g["id"] == gid), None)
    assert grp is not None, "empty group must still be returned"
    assert grp["tags"] == []


def test_tag_groups_groupless_tag_in_groupless_array_not_in_any_group(client):
    engine = get_engine()
    slug = f"groupless-{uuid.uuid4().hex[:8]}"
    with Session(engine) as s:
        t = _mk_tag(s, slug, group_id=None)
        tid = str(t.id)

    body = client.get("/api/tag-groups").json()
    groupless_ids = {t["id"] for t in body["groupless"]}
    assert tid in groupless_ids
    # never nested under any real group
    for g in body["groups"]:
        assert tid not in {t["id"] for t in g["tags"]}
    # groupless tag carries the enriched shape incl. null group_id
    item = next(t for t in body["groupless"] if t["id"] == tid)
    assert item["group_id"] is None
    assert "model_count" in item


def test_tag_groups_groupless_order_group_position_then_slug(client):
    engine = get_engine()
    p = f"gl-order-{uuid.uuid4().hex[:6]}"
    with Session(engine) as s:
        _mk_tag(s, f"{p}-zzz", group_position=1)
        _mk_tag(s, f"{p}-aaa", group_position=1)
        _mk_tag(s, f"{p}-mmm", group_position=0)

    body = client.get("/api/tag-groups").json()
    order = [t["slug"] for t in body["groupless"] if t["slug"].startswith(p)]
    assert order == [f"{p}-mmm", f"{p}-aaa", f"{p}-zzz"]


# --- AC #3/#4/#5: per-tag counts, non-deleted scope, consistency -----------


def test_tag_groups_model_count_excludes_soft_deleted(client):
    engine = get_engine()
    slug = f"cnt-scope-{uuid.uuid4().hex[:8]}"
    with Session(engine) as s:
        g = _mk_group(s, f"{slug}-grp")
        t = _mk_tag(s, slug, group_id=g.id)
        _tag_model(s, t.id, count=2, deleted=1)
        tid = str(t.id)

    body = client.get("/api/tag-groups").json()
    item = next(t for grp in body["groups"] for t in grp["tags"] if t["id"] == tid)
    assert item["model_count"] == 2  # 3 attached, 1 soft-deleted excluded


def test_tag_groups_count_matches_tags_endpoint(client):
    """AC #5 — same tag's model_count is identical across both endpoints."""
    engine = get_engine()
    slug = f"consistency-{uuid.uuid4().hex[:8]}"
    with Session(engine) as s:
        g = _mk_group(s, f"{slug}-grp")
        t = _mk_tag(s, slug, group_id=g.id)
        _tag_model(s, t.id, count=3)
        tid = str(t.id)

    groups_body = client.get("/api/tag-groups").json()
    from_groups = next(
        t["model_count"] for grp in groups_body["groups"] for t in grp["tags"] if t["id"] == tid
    )
    tags_body = client.get("/api/tags?with_counts=true&limit=200").json()
    from_tags = next(t["model_count"] for t in tags_body if t["id"] == tid)

    assert from_groups == from_tags == 3


# --- AC #8: no-N+1 / constant query count ----------------------------------


def test_tag_groups_query_count_is_constant_and_bounded(client):
    """AC #8 — /api/tag-groups issues a fixed, cardinality-independent query
    count. Measured at the service layer to isolate the read surface from
    auth/session overhead (per story guidance)."""
    engine = get_engine()
    p = f"qc-{uuid.uuid4().hex[:6]}"

    def _seed(prefix, n_groups, m_tags):
        with Session(engine) as s:
            for gi in range(n_groups):
                g = _mk_group(s, f"{prefix}-g{gi}", position=gi)
                for ti in range(m_tags):
                    _mk_tag(s, f"{prefix}-g{gi}-t{ti}", group_id=g.id, group_position=ti)

    _seed(f"{p}-small", 2, 2)
    with Session(engine) as s, _count_selects(engine) as c_small:
        list_tag_groups(s)

    _seed(f"{p}-large", 4, 4)  # doubled cardinality
    with Session(engine) as s, _count_selects(engine) as c_large:
        list_tag_groups(s)

    assert c_small["n"] == c_large["n"], (c_small["n"], c_large["n"])
    assert c_large["n"] <= 3, c_large["n"]  # TagGroup + Tag + counts


def test_tags_with_counts_adds_exactly_one_query(client):
    """AC #8 — with_counts=true costs exactly one extra aggregate query."""
    engine = get_engine()
    with Session(engine) as s, _count_selects(engine) as c_no:
        list_tags(s, with_counts=False)
    with Session(engine) as s, _count_selects(engine) as c_yes:
        list_tags(s, with_counts=True)

    assert c_no["n"] == 1, c_no["n"]  # select Tag
    assert c_yes["n"] == c_no["n"] + 1  # + one GROUP BY aggregate
