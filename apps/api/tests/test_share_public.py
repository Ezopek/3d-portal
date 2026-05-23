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
        c.headers.update({"X-Portal-Client": "web"})
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
    # Initiative 6 Decision N — share-resolve emits share-scoped URLs
    # (/api/share/{token}/files/{file_id}/content) instead of legacy
    # /api/models/{id}/files/{file_id}/content URLs. The legacy SoT content
    # endpoint is post-Story-11.1 current_user-gated; anonymous share
    # recipients reach assets exclusively via the share-scoped path.
    expected_img = f"/api/share/{created['token']}/files/{ids['img']}/content"
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
    # Initiative 6 Decision N — share-resolve emits share-scoped URL.
    assert body["stl_url"] == f"/api/share/{created['token']}/files/{ids['stl']}/content?download=1"


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


# ---------------------------------------------------------------------------
# Initiative 12 Story 19.4 (Decision T) — share file list endpoint
# ---------------------------------------------------------------------------


def test_share_files_list_unknown_token_returns_404(client):
    c, _, _ids = client
    r = c.get("/api/share/no-such-token/files")
    assert r.status_code == 404


def test_share_files_list_returns_files_with_share_scoped_urls(client):
    c, token, ids = client
    c.cookies.set("portal_access", token)
    created = c.post(
        "/api/admin/share",
        json={"model_id": str(ids["full"]), "expires_in_hours": 1},
    ).json()
    # Clear admin cookie — share list MUST work anonymous
    c.cookies.clear()
    r = c.get(f"/api/share/{created['token']}/files")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 2  # 1 image + 1 stl
    assert body["page"] == 1
    assert body["page_size"] == 50
    assert len(body["items"]) == 2

    items_by_id = {it["id"]: it for it in body["items"]}
    img_entry = items_by_id[str(ids["img"])]
    stl_entry = items_by_id[str(ids["stl"])]

    # Decision N — share-scoped content URLs.
    assert (
        img_entry["content_url"]
        == f"/api/share/{created['token']}/files/{ids['img']}/content"
    )
    assert (
        stl_entry["content_url"]
        == f"/api/share/{created['token']}/files/{ids['stl']}/content"
    )
    assert img_entry["kind"] == "image"
    assert img_entry["original_name"] == "hero.png"
    assert stl_entry["kind"] == "stl"
    assert stl_entry["original_name"] == "Dragon.stl"


def test_share_files_list_pagination_clamps_to_total(client):
    c, token, ids = client
    c.cookies.set("portal_access", token)
    created = c.post(
        "/api/admin/share",
        json={"model_id": str(ids["full"]), "expires_in_hours": 1},
    ).json()
    c.cookies.clear()
    r = c.get(f"/api/share/{created['token']}/files?page=2&page_size=1")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert body["page"] == 2
    assert body["page_size"] == 1
    assert len(body["items"]) == 1


def test_share_files_list_filters_disallowed_kinds(client, tmp_path):
    """source + archive_3mf MUST NOT surface in the share file list."""
    c, token, ids = client
    # Seed a source-kind file on the full model directly
    from app.core.db.session import get_engine

    engine = get_engine()
    with Session(engine) as s:
        src = ModelFile(
            model_id=ids["full"],
            kind=ModelFileKind.source,
            original_name="secret.f3d",
            storage_path=f"{ids['full']}/secret.f3d",
            sha256="c" * 64,
            size_bytes=100,
            mime_type="application/octet-stream",
        )
        s.add(src)
        s.commit()
    c.cookies.set("portal_access", token)
    created = c.post(
        "/api/admin/share",
        json={"model_id": str(ids["full"]), "expires_in_hours": 1},
    ).json()
    c.cookies.clear()
    body = c.get(f"/api/share/{created['token']}/files").json()
    kinds = {it["kind"] for it in body["items"]}
    assert "source" not in kinds
    assert "archive_3mf" not in kinds
    # Total reflects filtered count, not raw DB count (3 rows; 2 surfaced)
    assert body["total"] == 2


def test_share_files_list_returns_no_set_cookie_header(client):
    """Anonymous share endpoint MUST NOT set cookies on the response.

    Security invariant per Init 12 Story 19.3 § Threat vectors enumerated:
    no cookie response on /api/share/<token>/* endpoints. Maszynowo verified
    by TB-023 fixture in Init 14 Story 21.2; this is an early smoke version.
    """
    c, token, ids = client
    c.cookies.set("portal_access", token)
    created = c.post(
        "/api/admin/share",
        json={"model_id": str(ids["full"]), "expires_in_hours": 1},
    ).json()
    c.cookies.clear()
    r = c.get(f"/api/share/{created['token']}/files")
    assert r.status_code == 200
    assert "set-cookie" not in {k.lower() for k in r.headers}


# ---------------------------------------------------------------------------
# Initiative 14 Story 21.2 (TB-023) — credentialless contract maszynowo
# ---------------------------------------------------------------------------


def test_share_resolve_credentialless_contract(client):
    """Resolve endpoint MUST work without auth + emit no Set-Cookie.

    Uses make_anonymous_client helper (Story 21.2) to strip cookies + auth
    headers from the existing client BEFORE exercising the share endpoint.
    Locks the credentialless contract maszynowo for the bound endpoint.
    """
    from tests.conftest import assert_no_set_cookie_in_response, make_anonymous_client

    c, token, ids = client
    c.cookies.set("portal_access", token)
    created = c.post(
        "/api/admin/share",
        json={"model_id": str(ids["full"]), "expires_in_hours": 1},
    ).json()
    share_token = created["token"]

    # Strip cookies / auth headers — share view fetched as truly anonymous.
    c_anon = make_anonymous_client(c)
    assert len(c_anon.cookies) == 0
    r = c_anon.get(f"/api/share/{share_token}")
    assert r.status_code == 200, r.text
    assert_no_set_cookie_in_response(r)


def test_share_file_list_credentialless_contract(client):
    """File-list endpoint (Story 19.4) MUST work without auth + no Set-Cookie."""
    from tests.conftest import assert_no_set_cookie_in_response, make_anonymous_client

    c, token, ids = client
    c.cookies.set("portal_access", token)
    created = c.post(
        "/api/admin/share",
        json={"model_id": str(ids["full"]), "expires_in_hours": 1},
    ).json()
    share_token = created["token"]

    c_anon = make_anonymous_client(c)
    r = c_anon.get(f"/api/share/{share_token}/files")
    assert r.status_code == 200
    assert_no_set_cookie_in_response(r)
    body = r.json()
    assert "items" in body
    assert body["total"] >= 1


def test_share_invalid_token_credentialless_contract(client):
    """Even on 404 the share-resolve endpoint MUST NOT leak Set-Cookie."""
    from tests.conftest import assert_no_set_cookie_in_response, make_anonymous_client

    c, _token, _ids = client
    c_anon = make_anonymous_client(c)
    r = c_anon.get("/api/share/clearly-not-a-valid-token")
    assert r.status_code == 404
    assert_no_set_cookie_in_response(r)
