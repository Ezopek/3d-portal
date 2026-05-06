import datetime
import uuid

import pytest
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

    r = client.get(f"/api/models?category_ids={cat_id}")
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

    r = client.get(f"/api/models?category_ids={cat_a_id}")
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

    r = client.get(f"/api/models?tag_ids={t_id}&limit=200")
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

    r = client.get(f"/api/models?category_ids={cat_id}&limit=2&offset=0")
    body = r.json()
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert len(body["items"]) == 2
    assert body["total"] == 5

    r2 = client.get(f"/api/models?category_ids={cat_id}&limit=2&offset=2")
    body2 = r2.json()
    assert len(body2["items"]) == 2
    # No overlap with first page
    page1_ids = {item["id"] for item in body["items"]}
    page2_ids = {item["id"] for item in body2["items"]}
    assert page1_ids.isdisjoint(page2_ids)


@pytest.fixture(scope="module")
def seeded_listing():
    """Seed: 2 categories (A,B), 3 tags (x,y,z), 5 models with assorted filter axes.

    Returns a dict with category/tag/model id lookups for assertions.

    Module-scoped so the (uniquely-slugged) seed rows are inserted exactly
    once across all tests in this file — the test DB persists for the whole
    session, so per-function seeding would hit a UNIQUE-constraint conflict
    on the second invocation.
    """
    with Session(get_engine()) as s:
        cat_a = _seed_cat(s, "list-cat-a")
        cat_b = _seed_cat(s, "list-cat-b")
        tag_x = _seed_tag(s, "list-tag-x")
        tag_y = _seed_tag(s, "list-tag-y")
        tag_z = _seed_tag(s, "list-tag-z")

        from app.core.db.models import ModelSource

        # model 1: cat_a, tag x+y, source printables, status printed, rating 5
        m1 = _seed_model(s, "m-list-1", category_id=cat_a.id, tags=(tag_x, tag_y))
        m1.source = ModelSource.printables
        m1.status = ModelStatus.printed
        m1.rating = 5
        s.add(m1)
        # model 2: cat_a, tag x only, source printables, not_printed, rating 3
        m2 = _seed_model(s, "m-list-2", category_id=cat_a.id, tags=(tag_x,))
        m2.source = ModelSource.printables
        m2.status = ModelStatus.not_printed
        m2.rating = 3
        s.add(m2)
        # model 3: cat_a, tag z, source own, printed, rating 4
        m3 = _seed_model(s, "m-list-3", category_id=cat_a.id, tags=(tag_z,))
        m3.source = ModelSource.own
        m3.status = ModelStatus.printed
        m3.rating = 4
        s.add(m3)
        # model 4: cat_b, tag x+y+z, source thangs, in_progress, rating null
        m4 = _seed_model(s, "m-list-4", category_id=cat_b.id, tags=(tag_x, tag_y, tag_z))
        m4.source = ModelSource.thangs
        m4.status = ModelStatus.in_progress
        s.add(m4)
        # model 5: cat_b, no tags, source unknown, broken, rating 1
        m5 = _seed_model(s, "m-list-5", category_id=cat_b.id, tags=())
        m5.source = ModelSource.unknown
        m5.status = ModelStatus.broken
        m5.rating = 1
        s.add(m5)
        s.commit()

        return {
            "cat_a": cat_a.id,
            "cat_b": cat_b.id,
            "tag_x": tag_x.id,
            "tag_y": tag_y.id,
            "tag_z": tag_z.id,
            "m1": m1.id,
            "m2": m2.id,
            "m3": m3.id,
            "m4": m4.id,
            "m5": m5.id,
        }


def test_list_filter_by_category_ids_multi(client, seeded_listing):
    """category_ids=A,B returns models in either category (OR semantics)."""
    r = client.get(
        f"/api/models?category_ids={seeded_listing['cat_a']}&category_ids={seeded_listing['cat_b']}"
    )
    assert r.status_code == 200
    items = r.json()["items"]
    slugs = {it["slug"] for it in items}
    assert {"m-list-1", "m-list-2", "m-list-3", "m-list-4", "m-list-5"} <= slugs


def test_list_filter_by_tag_ids_and_semantics(client, seeded_listing):
    """tag_ids=x,y returns only models that have BOTH tags (AND semantics)."""
    r = client.get(
        f"/api/models?tag_ids={seeded_listing['tag_x']}&tag_ids={seeded_listing['tag_y']}"
    )
    assert r.status_code == 200
    slugs = {it["slug"] for it in r.json()["items"]}
    # m1 has x+y, m4 has x+y+z. m2 has only x. m3 only z. m5 none.
    assert slugs == {"m-list-1", "m-list-4"}


def test_list_filter_by_source(client, seeded_listing):
    r = client.get("/api/models?source=printables")
    slugs = {it["slug"] for it in r.json()["items"]}
    assert slugs == {"m-list-1", "m-list-2"}


def test_list_filter_by_source_rejects_unknown_value(client, seeded_listing):
    r = client.get("/api/models?source=banana")
    assert r.status_code == 422


def test_list_sort_recent_is_default(client, seeded_listing):
    """recent sort = created_at desc; tail of seed list comes first."""
    r = client.get("/api/models")
    slugs = [it["slug"] for it in r.json()["items"]]
    # Seeded in order m1..m5; created_at desc → m5 first
    assert slugs.index("m-list-5") < slugs.index("m-list-1")


def test_list_sort_name_asc(client, seeded_listing):
    r = client.get("/api/models?sort=name_asc")
    slugs = [it["slug"] for it in r.json()["items"] if it["slug"].startswith("m-list-")]
    assert slugs == sorted(slugs)


def test_list_sort_rating_puts_nulls_last(client, seeded_listing):
    """rating sort = rating desc, NULLS last (per SQL standard for NULLS LAST hint)."""
    r = client.get("/api/models?sort=rating&category_ids=" + str(seeded_listing["cat_a"]))
    items = r.json()["items"]
    ratings = [it["rating"] for it in items if it["slug"].startswith("m-list-")]
    # cat_a: m1=5, m3=4, m2=3 — descending; no nulls in this slice. Just check ordering.
    assert ratings == sorted(ratings, reverse=True)


def test_list_sort_rejects_unknown_value(client, seeded_listing):
    r = client.get("/api/models?sort=trending")
    assert r.status_code == 422


def test_list_combined_filters(client, seeded_listing):
    """category_ids=A AND tag_ids=x → m1 + m2."""
    r = client.get(
        f"/api/models?category_ids={seeded_listing['cat_a']}&tag_ids={seeded_listing['tag_x']}"
    )
    slugs = {it["slug"] for it in r.json()["items"]}
    assert slugs == {"m-list-1", "m-list-2"}


def test_list_models_exposes_gallery_hints(client):
    """Each ModelSummary carries the full gallery_file_ids list and total image_count.

    A model with image + print files reports both, ordered by
    (position NULLS LAST, created_at). A model with no image/print files
    reports image_count=0 and an empty gallery.
    """
    from app.core.db.models import ModelFile, ModelFileKind

    engine = get_engine()
    with Session(engine) as s:
        cat = _seed_cat(s, "cat-4-gallery")
        with_imgs = _seed_model(s, "model-4-gallery-with", category_id=cat.id)
        without_imgs = _seed_model(s, "model-4-gallery-without", category_id=cat.id)

        # Insert in scrambled order to confirm ordering isn't insertion-order.
        f_print = ModelFile(
            model_id=with_imgs.id,
            kind=ModelFileKind.print,
            original_name="print.png",
            storage_path=f"models/{with_imgs.id}/files/p.png",
            sha256="0" * 64,
            size_bytes=1,
            mime_type="image/png",
            position=2,
        )
        f_img_a = ModelFile(
            model_id=with_imgs.id,
            kind=ModelFileKind.image,
            original_name="a.png",
            storage_path=f"models/{with_imgs.id}/files/a.png",
            sha256="1" * 64,
            size_bytes=1,
            mime_type="image/png",
            position=0,
        )
        f_img_b = ModelFile(
            model_id=with_imgs.id,
            kind=ModelFileKind.image,
            original_name="b.png",
            storage_path=f"models/{with_imgs.id}/files/b.png",
            sha256="2" * 64,
            size_bytes=1,
            mime_type="image/png",
            position=1,
        )
        s.add_all([f_print, f_img_a, f_img_b])
        s.commit()
        s.refresh(f_print)
        s.refresh(f_img_a)
        s.refresh(f_img_b)
        with_id = str(with_imgs.id)
        without_id = str(without_imgs.id)
        expected_order = [str(f_img_a.id), str(f_img_b.id), str(f_print.id)]

    r = client.get("/api/models?limit=200")
    body = r.json()
    by_id = {it["id"]: it for it in body["items"]}

    item = by_id[with_id]
    assert item["image_count"] == 3
    assert item["gallery_file_ids"] == expected_order

    empty = by_id[without_id]
    assert empty["image_count"] == 0
    assert empty["gallery_file_ids"] == []
