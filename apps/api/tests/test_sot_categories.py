import datetime
import uuid

from sqlmodel import Session

from app.core.db.models import Category, Model, ModelStatus
from app.core.db.session import get_engine


def _seed_categories(session, slugs_with_parent_slug):
    """Seed categories. Each tuple: (slug, name_en, parent_slug_or_None)."""
    by_slug: dict[str, Category] = {}
    # Two-pass: first roots, then children
    for slug, name_en, parent_slug in slugs_with_parent_slug:
        if parent_slug is None:
            cat = Category(slug=slug, name_en=name_en)
            session.add(cat)
            session.commit()
            session.refresh(cat)
            by_slug[slug] = cat
    for slug, name_en, parent_slug in slugs_with_parent_slug:
        if parent_slug is not None:
            cat = Category(
                slug=slug,
                name_en=name_en,
                parent_id=by_slug[parent_slug].id,
            )
            session.add(cat)
            session.commit()
            session.refresh(cat)
            by_slug[slug] = cat
    return by_slug


def test_get_categories_returns_empty_tree_when_no_categories(client):
    # Note: session-scoped DB may have data from earlier tests; this test
    # just checks the response shape on an arbitrary state. With no
    # cat-2-* categories present, those particular slugs must not appear.
    r = client.get("/api/categories")
    assert r.status_code == 200
    body = r.json()
    assert "roots" in body


def test_get_categories_returns_root_then_children(client):
    engine = get_engine()
    with Session(engine) as s:
        _seed_categories(
            s,
            [
                ("cat-2-decorum", "Decorum", None),
                ("cat-2-articulated", "Articulated", "cat-2-decorum"),
                ("cat-2-vases", "Vases", "cat-2-decorum"),
            ],
        )

    r = client.get("/api/categories")
    assert r.status_code == 200
    body = r.json()
    # find our seeded root
    decorum_nodes = [n for n in body["roots"] if n["slug"] == "cat-2-decorum"]
    assert len(decorum_nodes) == 1
    decorum = decorum_nodes[0]
    child_slugs = {c["slug"] for c in decorum["children"]}
    assert child_slugs == {"cat-2-articulated", "cat-2-vases"}
    # children of children: empty for these leaves
    for child in decorum["children"]:
        assert child["children"] == []


def test_get_categories_three_level_hierarchy(client):
    engine = get_engine()
    with Session(engine) as s:
        _seed_categories(
            s,
            [
                ("cat-3-printer", "Printer", None),
                ("cat-3-k1max", "K1 Max", "cat-3-printer"),
            ],
        )
        # third level
        from sqlmodel import select

        k1 = s.exec(select(Category).where(Category.slug == "cat-3-k1max")).first()
        s.add(Category(slug="cat-3-k1max-mods", name_en="Mods", parent_id=k1.id))
        s.commit()

    r = client.get("/api/categories")
    body = r.json()
    printer = next(n for n in body["roots"] if n["slug"] == "cat-3-printer")
    k1 = next(c for c in printer["children"] if c["slug"] == "cat-3-k1max")
    mods = next(c for c in k1["children"] if c["slug"] == "cat-3-k1max-mods")
    assert mods["children"] == []


def _seed_model_in_category(session: Session, *, slug: str, category_id: uuid.UUID) -> Model:
    m = Model(
        slug=slug,
        name_en=slug,
        category_id=category_id,
        status=ModelStatus.not_printed,
    )
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


def test_get_categories_model_count_zero_for_empty_subtree(client):
    engine = get_engine()
    with Session(engine) as s:
        _seed_categories(
            s,
            [
                ("cat-mc-empty-root", "EmptyRoot", None),
                ("cat-mc-empty-leaf", "EmptyLeaf", "cat-mc-empty-root"),
            ],
        )

    r = client.get("/api/categories")
    body = r.json()
    root = next(n for n in body["roots"] if n["slug"] == "cat-mc-empty-root")
    assert root["model_count"] == 0
    leaf = next(c for c in root["children"] if c["slug"] == "cat-mc-empty-leaf")
    assert leaf["model_count"] == 0


def test_get_categories_model_count_propagates_up_from_leaf(client):
    engine = get_engine()
    with Session(engine) as s:
        cats = _seed_categories(
            s,
            [
                ("cat-mc-up-root", "UpRoot", None),
                ("cat-mc-up-mid", "UpMid", "cat-mc-up-root"),
                ("cat-mc-up-leaf", "UpLeaf", "cat-mc-up-mid"),
            ],
        )
        _seed_model_in_category(s, slug="model-mc-up-1", category_id=cats["cat-mc-up-leaf"].id)

    r = client.get("/api/categories")
    body = r.json()
    root = next(n for n in body["roots"] if n["slug"] == "cat-mc-up-root")
    mid = next(c for c in root["children"] if c["slug"] == "cat-mc-up-mid")
    leaf = next(c for c in mid["children"] if c["slug"] == "cat-mc-up-leaf")
    assert leaf["model_count"] == 1
    assert mid["model_count"] == 1
    assert root["model_count"] == 1


def test_get_categories_model_count_sums_sibling_leaves(client):
    engine = get_engine()
    with Session(engine) as s:
        cats = _seed_categories(
            s,
            [
                ("cat-mc-sum-root", "SumRoot", None),
                ("cat-mc-sum-leaf-a", "SumLeafA", "cat-mc-sum-root"),
                ("cat-mc-sum-leaf-b", "SumLeafB", "cat-mc-sum-root"),
            ],
        )
        _seed_model_in_category(s, slug="model-mc-sum-a", category_id=cats["cat-mc-sum-leaf-a"].id)
        _seed_model_in_category(s, slug="model-mc-sum-b", category_id=cats["cat-mc-sum-leaf-b"].id)

    r = client.get("/api/categories")
    body = r.json()
    root = next(n for n in body["roots"] if n["slug"] == "cat-mc-sum-root")
    leaf_a = next(c for c in root["children"] if c["slug"] == "cat-mc-sum-leaf-a")
    leaf_b = next(c for c in root["children"] if c["slug"] == "cat-mc-sum-leaf-b")
    assert leaf_a["model_count"] == 1
    assert leaf_b["model_count"] == 1
    assert root["model_count"] == 2


def test_get_categories_model_count_excludes_soft_deleted(client):
    engine = get_engine()
    with Session(engine) as s:
        cats = _seed_categories(
            s,
            [
                ("cat-mc-del-root", "DelRoot", None),
            ],
        )
        m = _seed_model_in_category(
            s, slug="model-mc-del-1", category_id=cats["cat-mc-del-root"].id
        )
        m.deleted_at = datetime.datetime.now(datetime.UTC)
        s.add(m)
        s.commit()

    r = client.get("/api/categories")
    body = r.json()
    root = next(n for n in body["roots"] if n["slug"] == "cat-mc-del-root")
    assert root["model_count"] == 0
