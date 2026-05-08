import uuid
from unittest.mock import MagicMock

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.auth.jwt import encode_token
from app.core.db.models import (
    Category,
    Model,
    ModelFile,
    ModelFileKind,
)
from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/p.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    from app.core.config import get_settings
    from app.core.db.session import get_engine

    get_settings.cache_clear()
    get_engine.cache_clear()
    app = create_app()
    fake = fakeredis.aioredis.FakeRedis()
    factory = MagicMock()
    factory.get = MagicMock(return_value=fake)

    async def _aclose():
        return None

    factory.aclose = _aclose

    with TestClient(app) as c:
        app.state.redis = factory
        from sqlmodel import select

        from app.core.db.models import User

        engine = get_engine()
        with Session(engine) as s:
            user = s.exec(select(User).where(User.email == "admin@localhost.localdomain")).first()
            user_id = user.id
            cat = Category(slug=f"share-cat-{uuid.uuid4().hex[:6]}", name_en="Decorum")
            s.add(cat)
            s.flush()

            # Model 1: has both image and STL files
            m_full = Model(
                slug=f"share-full-{uuid.uuid4().hex[:6]}",
                name_en="Full Model",
                name_pl="Pełny model",
                category_id=cat.id,
            )
            s.add(m_full)
            s.flush()
            img = ModelFile(
                model_id=m_full.id,
                kind=ModelFileKind.image,
                original_name="hero.png",
                storage_path=f"{m_full.id}/hero.png",
                sha256="a" * 64,
                size_bytes=10,
                mime_type="image/png",
                position=1,
            )
            stl = ModelFile(
                model_id=m_full.id,
                kind=ModelFileKind.stl,
                original_name="Dragon.stl",
                storage_path=f"{m_full.id}/Dragon.stl",
                sha256="b" * 64,
                size_bytes=20,
                mime_type="model/stl",
            )
            s.add(img)
            s.add(stl)
            s.flush()
            m_full.thumbnail_file_id = img.id
            s.add(m_full)

            # Model 2: no files at all
            m_bare = Model(
                slug=f"share-bare-{uuid.uuid4().hex[:6]}",
                name_en="Bare Model",
                category_id=cat.id,
            )
            s.add(m_bare)
            s.commit()
            ids = {
                "full": m_full.id,
                "bare": m_bare.id,
                "img": img.id,
                "stl": stl.id,
                "category_slug": cat.slug,
            }
        token = encode_token(subject=str(user_id), role="admin", secret="test", ttl_minutes=30)
        yield c, token, ids
    get_settings.cache_clear()
    get_engine.cache_clear()


def test_resolve_unknown_token_returns_404(client):
    c, _, _ids = client
    r = c.get("/api/share/nope")
    assert r.status_code == 404


def test_resolve_returns_subset_projection(client):
    c, token, ids = client
    c.cookies.set("portal_access", token)
    created = c.post(
        "/api/admin/share",
        json={"model_id": str(ids["full"]), "expires_in_hours": 1},
    ).json()
    r = c.get(f"/api/share/{created['token']}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == str(ids["full"])
    assert body["name_pl"] == "Pełny model"
    assert body["category"] == ids["category_slug"]
    assert "rating" not in body  # subset, not full Model
    assert "source_url" not in body
    assert isinstance(body["images"], list)


def test_resolve_returns_image_and_thumbnail_urls(client):
    c, token, ids = client
    c.cookies.set("portal_access", token)
    created = c.post(
        "/api/admin/share",
        json={"model_id": str(ids["full"]), "expires_in_hours": 1},
    ).json()
    body = c.get(f"/api/share/{created['token']}").json()
    expected_img = f"/api/models/{ids['full']}/files/{ids['img']}/content"
    assert body["images"] == [expected_img]
    assert body["thumbnail_url"] == expected_img


def test_resolve_returns_stl_url_when_stl_present(client):
    c, token, ids = client
    c.cookies.set("portal_access", token)
    created = c.post(
        "/api/admin/share",
        json={"model_id": str(ids["full"]), "expires_in_hours": 1},
    ).json()
    body = c.get(f"/api/share/{created['token']}").json()
    assert body["has_3d"] is True
    assert (
        body["stl_url"]
        == f"/api/models/{ids['full']}/files/{ids['stl']}/content?download=1"
    )


def test_resolve_no_files_returns_empty(client):
    c, token, ids = client
    c.cookies.set("portal_access", token)
    created = c.post(
        "/api/admin/share",
        json={"model_id": str(ids["bare"]), "expires_in_hours": 1},
    ).json()
    body = c.get(f"/api/share/{created['token']}").json()
    assert body["has_3d"] is False
    assert body["stl_url"] is None
    assert body["images"] == []
    assert body["thumbnail_url"] is None
