import datetime
import uuid

import pytest
from sqlmodel import Session

from app.core.auth.cookies import ACCESS_COOKIE
from app.core.auth.jwt import encode_token
from app.core.db.models import Category, Model, ModelStatus, ModelTag, Tag, TagGroup
from app.core.db.session import get_engine


# Initiative 6 Story 11.1 — default-deny on SoT GET endpoints. See
# test_sot_categories.py:_default_admin_cookie docstring for context.
@pytest.fixture(autouse=True)
def _default_admin_cookie(client):
    token = encode_token(
        subject=str(uuid.uuid4()),
        role="admin",
        secret="test-secret-not-real",
        ttl_minutes=30,
    )
    client.cookies.set(ACCESS_COOKIE, token)
    yield
    client.cookies.delete(ACCESS_COOKIE)


def test_get_tags_returns_seeded_tags(client):
    engine = get_engine()
    with Session(engine) as s:
        s.add(Tag(slug="tag-3-dragon", name_en="Dragon", name_pl="Smok"))
        s.add(Tag(slug="tag-3-articulated", name_en="Articulated"))
        s.commit()

    r = client.get("/api/tags")
    assert r.status_code == 200
    body = r.json()
    slugs = {t["slug"] for t in body}
    assert "tag-3-dragon" in slugs
    assert "tag-3-articulated" in slugs


def test_get_tags_filters_by_q(client):
    engine = get_engine()
    with Session(engine) as s:
        s.add(Tag(slug="tag-3q-dragonfly", name_en="Dragonfly"))
        s.add(Tag(slug="tag-3q-articulated", name_en="Articulated"))
        s.commit()

    r = client.get("/api/tags?q=dragon")
    body = r.json()
    slugs = {t["slug"] for t in body}
    assert "tag-3q-dragonfly" in slugs
    assert "tag-3q-articulated" not in slugs


def test_get_tags_q_matches_name_pl_too(client):
    engine = get_engine()
    with Session(engine) as s:
        s.add(Tag(slug="tag-3pl-egg", name_en="Egg", name_pl="Jajko"))
        s.commit()

    r = client.get("/api/tags?q=jajko")
    body = r.json()
    slugs = {t["slug"] for t in body}
    assert "tag-3pl-egg" in slugs


def test_get_tags_respects_limit(client):
    engine = get_engine()
    with Session(engine) as s:
        for i in range(5):
            s.add(Tag(slug=f"tag-3l-{i}", name_en=f"T{i}"))
        s.commit()

    r = client.get("/api/tags?limit=2")
    body = r.json()
    assert len(body) <= 2


def test_get_tags_default_limit_is_200(client):
    """Default limit is 200; sanity-check the value (boundary)."""
    r = client.get("/api/tags?limit=200")
    assert r.status_code == 200
    r2 = client.get("/api/tags?limit=201")
    assert r2.status_code == 422  # over max


# --- Story 42.2 — facet membership fields (AC #1/#2) -----------------------


def test_get_tags_includes_group_fields(client):
    """Every tag item carries group_id + group_position (additive, AC #1/#2)."""
    engine = get_engine()
    with Session(engine) as s:
        g = TagGroup(slug=f"tg-fields-grp-{uuid.uuid4().hex[:6]}", name_en="Grp", position=2)
        s.add(g)
        s.commit()
        s.refresh(g)
        grouped = Tag(
            slug=f"tg-grouped-{uuid.uuid4().hex[:6]}",
            name_en="Grouped",
            group_id=g.id,
            group_position=5,
        )
        groupless = Tag(slug=f"tg-groupless-{uuid.uuid4().hex[:6]}", name_en="Solo", name_pl=None)
        s.add(grouped)
        s.add(groupless)
        s.commit()
        gid = str(g.id)
        grouped_slug, groupless_slug = grouped.slug, groupless.slug

    body = client.get("/api/tags?limit=200").json()
    by_slug = {t["slug"]: t for t in body}

    gt = by_slug[grouped_slug]
    assert gt["group_id"] == gid
    assert gt["group_position"] == 5

    ut = by_slug[groupless_slug]
    # groupless tag: group_id present as explicit null; name_pl null preserved
    assert "group_id" in ut and ut["group_id"] is None
    assert "name_pl" in ut and ut["name_pl"] is None
    assert ut["group_position"] == 0


def test_get_tags_no_counts_omits_model_count_key(client):
    """Without with_counts, NO item carries a model_count key (AC #2)."""
    engine = get_engine()
    with Session(engine) as s:
        s.add(Tag(slug=f"tg-nocount-{uuid.uuid4().hex[:6]}", name_en="NoCount"))
        s.commit()

    body = client.get("/api/tags?limit=200").json()
    assert body, "expected at least one tag"
    for item in body:
        assert "model_count" not in item


def test_get_tags_with_counts_includes_int_model_count(client):
    """with_counts=true adds model_count = distinct non-deleted models (AC #3)."""
    engine = get_engine()
    with Session(engine) as s:
        cat = Category(slug=f"cat-tgc-{uuid.uuid4().hex[:6]}", name_en="C")
        s.add(cat)
        s.commit()
        s.refresh(cat)
        tag = Tag(slug=f"tg-wc-{uuid.uuid4().hex[:6]}", name_en="WithCount")
        s.add(tag)
        s.commit()
        s.refresh(tag)
        for _ in range(2):
            m = Model(
                slug=f"m-{uuid.uuid4().hex[:10]}",
                name_en="M",
                category_id=cat.id,
                status=ModelStatus.not_printed,
            )
            s.add(m)
            s.commit()
            s.refresh(m)
            s.add(ModelTag(model_id=m.id, tag_id=tag.id))
            s.commit()
        tag_slug = tag.slug

    body = client.get("/api/tags?with_counts=true&limit=200").json()
    item = next(t for t in body if t["slug"] == tag_slug)
    assert item["model_count"] == 2
    assert isinstance(item["model_count"], int)


def test_get_tags_with_counts_excludes_soft_deleted(client):
    engine = get_engine()
    with Session(engine) as s:
        cat = Category(slug=f"cat-tgd-{uuid.uuid4().hex[:6]}", name_en="C")
        s.add(cat)
        s.commit()
        s.refresh(cat)
        tag = Tag(slug=f"tg-del-{uuid.uuid4().hex[:6]}", name_en="Del")
        s.add(tag)
        s.commit()
        s.refresh(tag)
        live = Model(
            slug=f"m-{uuid.uuid4().hex[:10]}",
            name_en="Live",
            category_id=cat.id,
            status=ModelStatus.not_printed,
        )
        dead = Model(
            slug=f"m-{uuid.uuid4().hex[:10]}",
            name_en="Dead",
            category_id=cat.id,
            status=ModelStatus.not_printed,
            deleted_at=datetime.datetime.now(datetime.UTC),
        )
        s.add(live)
        s.add(dead)
        s.commit()
        s.refresh(live)
        s.refresh(dead)
        s.add(ModelTag(model_id=live.id, tag_id=tag.id))
        s.add(ModelTag(model_id=dead.id, tag_id=tag.id))
        s.commit()
        tag_slug = tag.slug

    body = client.get("/api/tags?with_counts=true&limit=200").json()
    item = next(t for t in body if t["slug"] == tag_slug)
    assert item["model_count"] == 1  # soft-deleted model excluded


def test_get_tags_with_counts_zero_for_unused_tag(client):
    engine = get_engine()
    with Session(engine) as s:
        tag = Tag(slug=f"tg-unused-{uuid.uuid4().hex[:6]}", name_en="Unused")
        s.add(tag)
        s.commit()
        tag_slug = tag.slug

    body = client.get("/api/tags?with_counts=true&limit=200").json()
    item = next(t for t in body if t["slug"] == tag_slug)
    assert item["model_count"] == 0


def test_get_tags_openapi_response_schema_is_honest(client):
    """AC #9 — the 200 response schema is a non-empty named component, and
    model_count is advertised as an OPTIONAL integer. Regression guard proving
    response_model=None (empty `schema: {}`) was NOT used (D-RESPONSEMODEL-1)."""
    spec = client.get("/api/openapi.json").json()
    op = spec["paths"]["/api/tags"]["get"]
    schema = op["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema != {}
    assert schema.get("type") == "array"
    ref = schema["items"].get("$ref", "")
    assert ref.endswith("/TagListItem"), ref

    comp = spec["components"]["schemas"]["TagListItem"]
    props = comp["properties"]
    assert "model_count" in props
    assert "model_count" not in comp.get("required", [])  # optional

    def _types(node):
        if "type" in node:
            return {node["type"]}
        return {sub.get("type") for sub in node.get("anyOf", [])}

    assert "integer" in _types(props["model_count"])
