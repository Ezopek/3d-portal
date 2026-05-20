import uuid

import pytest
from sqlmodel import Session

from app.core.auth.cookies import ACCESS_COOKIE
from app.core.auth.jwt import encode_token
from app.core.db.models import Tag
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
