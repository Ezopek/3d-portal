import datetime
import uuid

from sqlmodel import Session

from app.core.db.models import (
    Category,
    Model,
    ModelStatus,
    ModelTag,
    Tag,
)
from app.core.db.session import get_engine


def _seed_model(session, slug, *, category_id, status=None, tags=()):
    m = Model(
        slug=slug,
        name_en=slug,
        category_id=category_id,
    )
    if status is not None:
        m.status = status
    session.add(m)
    session.commit()
    session.refresh(m)
    for t in tags:
        session.add(ModelTag(model_id=m.id, tag_id=t.id))
    session.commit()
    session.refresh(m)
    return m


def _seed_cat(session, slug):
    c = Category(slug=slug, name_en=slug)
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


def _seed_tag(session, slug):
    t = Tag(slug=slug, name_en=slug)
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


def test_list_models_returns_envelope(client):
    r = client.get("/api/models")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert "offset" in body
    assert "limit" in body
    assert body["limit"] == 50  # default


def test_list_models_includes_seeded_model_with_tags(client):
    engine = get_engine()
    with Session(engine) as s:
        cat = _seed_cat(s, "cat-4-decorum")
        tag = _seed_tag(s, "tag-4-dragon")
        m = _seed_model(s, "model-4-x", category_id=cat.id, tags=[tag])
        cat_id: uuid.UUID = cat.id
        model_id: uuid.UUID = m.id

    r = client.get(f"/api/models?category={cat_id}")
    body = r.json()
    items = [i for i in body["items"] if i["id"] == str(model_id)]
    assert len(items) == 1
    item = items[0]
    assert item["slug"] == "model-4-x"
    assert {t["slug"] for t in item["tags"]} == {"tag-4-dragon"}


def test_list_models_filter_by_category(client):
    engine = get_engine()
    with Session(engine) as s:
        cat_a = _seed_cat(s, "cat-4-cat-a")
        cat_b = _seed_cat(s, "cat-4-cat-b")
        m_a = _seed_model(s, "model-4-cat-a", category_id=cat_a.id)
        m_b = _seed_model(s, "model-4-cat-b", category_id=cat_b.id)
        cat_a_id: uuid.UUID = cat_a.id
        m_a_id: uuid.UUID = m_a.id
        m_b_id: uuid.UUID = m_b.id

    r = client.get(f"/api/models?category={cat_a_id}")
    ids = {item["id"] for item in r.json()["items"]}
    assert str(m_a_id) in ids
    assert str(m_b_id) not in ids


def test_list_models_filter_by_status(client):
    engine = get_engine()
    with Session(engine) as s:
        cat = _seed_cat(s, "cat-4-status-cat")
        m_p = _seed_model(s, "model-4-printed", category_id=cat.id, status=ModelStatus.printed)
        m_n = _seed_model(
            s, "model-4-not-printed", category_id=cat.id, status=ModelStatus.not_printed
        )
        m_p_id: uuid.UUID = m_p.id
        m_n_id: uuid.UUID = m_n.id

    r = client.get("/api/models?status=printed&limit=200")
    ids = {item["id"] for item in r.json()["items"]}
    assert str(m_p_id) in ids
    assert str(m_n_id) not in ids


def test_list_models_filter_by_tag(client):
    engine = get_engine()
    with Session(engine) as s:
        cat = _seed_cat(s, "cat-4-tag-cat")
        t = _seed_tag(s, "tag-4-only")
        with_tag = _seed_model(s, "model-4-with-tag", category_id=cat.id, tags=[t])
        without_tag = _seed_model(s, "model-4-without-tag", category_id=cat.id)
        t_id: uuid.UUID = t.id
        with_tag_id: uuid.UUID = with_tag.id
        without_tag_id: uuid.UUID = without_tag.id

    r = client.get(f"/api/models?tag={t_id}&limit=200")
    ids = {item["id"] for item in r.json()["items"]}
    assert str(with_tag_id) in ids
    assert str(without_tag_id) not in ids


def test_list_models_filter_by_q_matches_name_en(client):
    engine = get_engine()
    with Session(engine) as s:
        cat = _seed_cat(s, "cat-4-q-cat")
        # Using slug values that include the search target so name_en (which
        # we set = slug for test brevity) contains it too.
        match = _seed_model(s, "model-4-q-articulated-x", category_id=cat.id)
        nope = _seed_model(s, "model-4-q-other-y", category_id=cat.id)
        match_id: uuid.UUID = match.id
        nope_id: uuid.UUID = nope.id

    r = client.get("/api/models?q=articulated&limit=200")
    ids = {item["id"] for item in r.json()["items"]}
    assert str(match_id) in ids
    assert str(nope_id) not in ids


def test_list_models_excludes_soft_deleted_by_default(client):
    engine = get_engine()
    with Session(engine) as s:
        cat = _seed_cat(s, "cat-4-soft-cat")
        deleted = _seed_model(s, "model-4-soft-deleted", category_id=cat.id)
        deleted.deleted_at = datetime.datetime.now(datetime.UTC)
        s.add(deleted)
        s.commit()
        alive = _seed_model(s, "model-4-soft-alive", category_id=cat.id)
        deleted_id: uuid.UUID = deleted.id
        alive_id: uuid.UUID = alive.id

    r = client.get("/api/models?limit=200")
    ids = {item["id"] for item in r.json()["items"]}
    assert str(alive_id) in ids
    assert str(deleted_id) not in ids


def test_list_models_include_deleted_returns_soft_deleted(client):
    engine = get_engine()
    with Session(engine) as s:
        cat = _seed_cat(s, "cat-4-incl-cat")
        deleted = _seed_model(s, "model-4-incl-deleted", category_id=cat.id)
        deleted.deleted_at = datetime.datetime.now(datetime.UTC)
        s.add(deleted)
        s.commit()
        deleted_id: uuid.UUID = deleted.id

    r = client.get("/api/models?include_deleted=true&limit=200")
    ids = {item["id"] for item in r.json()["items"]}
    assert str(deleted_id) in ids


def test_list_models_pagination(client):
    engine = get_engine()
    with Session(engine) as s:
        cat = _seed_cat(s, "cat-4-page-cat")
        for i in range(5):
            _seed_model(s, f"model-4-page-{i:02d}", category_id=cat.id)
        cat_id: uuid.UUID = cat.id

    r = client.get(f"/api/models?category={cat_id}&limit=2&offset=0")
    body = r.json()
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert len(body["items"]) == 2
    assert body["total"] == 5

    r2 = client.get(f"/api/models?category={cat_id}&limit=2&offset=2")
    body2 = r2.json()
    assert len(body2["items"]) == 2
    # No overlap with first page
    page1_ids = {item["id"] for item in body["items"]}
    page2_ids = {item["id"] for item in body2["items"]}
    assert page1_ids.isdisjoint(page2_ids)
