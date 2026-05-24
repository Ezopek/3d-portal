"""Tests for Initiative 6 Story 11.1 — default-deny auth boundary on SoT GET endpoints.

Covers (per Story 11.1 acceptance criteria AC-2 / AC-3 / AC-4):

- AC-3: anonymous requests to each of the 6 SoT GET endpoints return 401
- AC-2: agent-role cookie authentication returns 200 (NFR6-INT-1 — agent
  service-account ingestion preservation; this is the EXPLICIT regression
  test for hot-fix 64447ff's P1-2 codex finding where `current_member_or_admin`
  rejected agent role and broke the hydrate_local_tree.py runbook)
- AC-4: member-role cookie authentication returns 200

The architecture intent (architecture.md § Initiative 5 Decision C lines
1489-1490) was always `current_user` (any authenticated role: admin / member
/ agent — see apps/api/app/core/auth/dependencies.py:12 `_ALLOWED_ROLES`).
Story 11.1 ships that intent and adds these mechanical tests to prevent
regression to the 64447ff P1-2 pattern.
"""

import contextlib
import hashlib
import uuid

import pytest
from sqlmodel import Session

from app.core.auth.cookies import ACCESS_COOKIE
from app.core.auth.jwt import encode_token
from app.core.config import get_settings
from app.core.db.models import Category, Model, ModelFile, ModelFileKind, ModelStatus
from app.core.db.session import get_engine
from tests._test_helpers import admin_token, agent_token, member_token


def _mint_cookie(client, role):
    user_id = uuid.uuid4()
    if role == "admin":
        token = admin_token(user_id)
    elif role == "agent":
        token = agent_token(user_id)
    elif role == "member":
        token = member_token(user_id)
    else:
        # Fallback for unsupported roles (e.g. the "rogue" test below) —
        # source secret from settings to match the centralized helper shape.
        token = encode_token(
            subject=str(user_id),
            role=role,
            secret=get_settings().jwt_secret,
            ttl_minutes=30,
        )
    client.cookies.set(ACCESS_COOKIE, token)


def _clear_cookie(client):
    # Defensive — TestClient cookies persist across calls within a test; tests
    # that need anonymous behaviour explicitly clear before the request.
    client.cookies.delete(ACCESS_COOKIE)


@pytest.fixture
def seeded_model(client) -> tuple[uuid.UUID, uuid.UUID]:
    """Seed one model + one image file row backed by an on-disk blob.

    Returns (model_id, file_id). The blob lives under settings.portal_content_dir
    so /content endpoint can stream it without 404'ing on missing-on-disk.
    """
    engine = get_engine()
    settings = get_settings()
    storage = settings.portal_content_dir.resolve()
    storage.mkdir(parents=True, exist_ok=True)
    blob_name = f"sot-auth-boundary-{uuid.uuid4().hex[:8]}.bin"
    blob_path = storage / blob_name
    blob_path.write_bytes(b"x" * 16)

    with Session(engine) as s:
        cat_slug = f"cat-sot-auth-{uuid.uuid4().hex[:6]}"
        cat = Category(slug=cat_slug, name_en="AuthBoundary")
        s.add(cat)
        s.commit()
        s.refresh(cat)

        model_slug = f"model-sot-auth-{uuid.uuid4().hex[:6]}"
        model = Model(
            slug=model_slug,
            name_en="AuthBoundary",
            category_id=cat.id,
            status=ModelStatus.not_printed,
        )
        s.add(model)
        s.commit()
        s.refresh(model)

        file_row = ModelFile(
            model_id=model.id,
            kind=ModelFileKind.image,
            original_name=blob_name,
            storage_path=blob_name,
            sha256=hashlib.sha256(blob_path.read_bytes()).hexdigest(),
            mime_type="application/octet-stream",
            size_bytes=blob_path.stat().st_size,
        )
        s.add(file_row)
        s.commit()
        s.refresh(file_row)

        yield model.id, file_row.id

    # Cleanup
    with contextlib.suppress(OSError):
        blob_path.unlink()


# ---------------------------------------------------------------------------
# Anonymous-rejection tests (AC-3) — 6 endpoints
# ---------------------------------------------------------------------------


def test_sot_categories_anonymous_returns_401(client):
    _clear_cookie(client)
    r = client.get("/api/categories")
    assert r.status_code == 401


def test_sot_tags_anonymous_returns_401(client):
    _clear_cookie(client)
    r = client.get("/api/tags")
    assert r.status_code == 401


def test_sot_models_list_anonymous_returns_401(client):
    _clear_cookie(client)
    r = client.get("/api/models")
    assert r.status_code == 401


def test_sot_models_detail_anonymous_returns_401(client, seeded_model):
    model_id, _file_id = seeded_model
    _clear_cookie(client)
    r = client.get(f"/api/models/{model_id}")
    assert r.status_code == 401


def test_sot_model_files_anonymous_returns_401(client, seeded_model):
    model_id, _file_id = seeded_model
    _clear_cookie(client)
    r = client.get(f"/api/models/{model_id}/files")
    assert r.status_code == 401


def test_sot_model_file_content_anonymous_returns_401(client, seeded_model):
    model_id, file_id = seeded_model
    _clear_cookie(client)
    r = client.get(f"/api/models/{model_id}/files/{file_id}/content")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Agent-authenticated tests (AC-2 — NFR6-INT-1 / hot-fix 64447ff P1-2 regression)
# ---------------------------------------------------------------------------


def test_sot_categories_agent_authenticated_returns_200(client):
    _mint_cookie(client, "agent")
    r = client.get("/api/categories")
    assert r.status_code == 200, r.text


def test_sot_tags_agent_authenticated_returns_200(client):
    _mint_cookie(client, "agent")
    r = client.get("/api/tags")
    assert r.status_code == 200, r.text


def test_sot_models_list_agent_authenticated_returns_200(client):
    _mint_cookie(client, "agent")
    r = client.get("/api/models")
    assert r.status_code == 200, r.text


def test_sot_models_detail_agent_authenticated_returns_200(client, seeded_model):
    model_id, _file_id = seeded_model
    _mint_cookie(client, "agent")
    r = client.get(f"/api/models/{model_id}")
    assert r.status_code == 200, r.text


def test_sot_model_files_agent_authenticated_returns_200(client, seeded_model):
    model_id, _file_id = seeded_model
    _mint_cookie(client, "agent")
    r = client.get(f"/api/models/{model_id}/files")
    assert r.status_code == 200, r.text


def test_sot_model_file_content_agent_authenticated_returns_200(client, seeded_model):
    model_id, file_id = seeded_model
    _mint_cookie(client, "agent")
    r = client.get(f"/api/models/{model_id}/files/{file_id}/content")
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# Member-authenticated tests (AC-4)
# ---------------------------------------------------------------------------


def test_sot_categories_member_authenticated_returns_200(client):
    _mint_cookie(client, "member")
    r = client.get("/api/categories")
    assert r.status_code == 200, r.text


def test_sot_tags_member_authenticated_returns_200(client):
    _mint_cookie(client, "member")
    r = client.get("/api/tags")
    assert r.status_code == 200, r.text


def test_sot_models_list_member_authenticated_returns_200(client):
    _mint_cookie(client, "member")
    r = client.get("/api/models")
    assert r.status_code == 200, r.text


def test_sot_models_detail_member_authenticated_returns_200(client, seeded_model):
    model_id, _file_id = seeded_model
    _mint_cookie(client, "member")
    r = client.get(f"/api/models/{model_id}")
    assert r.status_code == 200, r.text


def test_sot_model_files_member_authenticated_returns_200(client, seeded_model):
    model_id, _file_id = seeded_model
    _mint_cookie(client, "member")
    r = client.get(f"/api/models/{model_id}/files")
    assert r.status_code == 200, r.text


def test_sot_model_file_content_member_authenticated_returns_200(client, seeded_model):
    model_id, file_id = seeded_model
    _mint_cookie(client, "member")
    r = client.get(f"/api/models/{model_id}/files/{file_id}/content")
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# Admin-authenticated tests (AC-5 regression — admin path stays open)
# ---------------------------------------------------------------------------


def test_sot_categories_admin_authenticated_returns_200(client):
    _mint_cookie(client, "admin")
    r = client.get("/api/categories")
    assert r.status_code == 200, r.text


def test_sot_models_list_admin_authenticated_returns_200(client):
    _mint_cookie(client, "admin")
    r = client.get("/api/models")
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# Defensive: forbidden role rejection (currently no role outside {admin,
# member, agent} can exist via legitimate paths, but the dependency check
# is the canonical defense — codify the contract)
# ---------------------------------------------------------------------------


def test_sot_categories_unknown_role_returns_403(client):
    # Forge a token with an unsupported role. _resolve_user raises 403
    # forbidden_role per apps/api/app/core/auth/dependencies.py:39.
    token = encode_token(
        subject=str(uuid.uuid4()),
        role="rogue",
        secret=get_settings().jwt_secret,
        ttl_minutes=30,
    )
    client.cookies.set(ACCESS_COOKIE, token)
    r = client.get("/api/categories")
    assert r.status_code == 403, r.text
    assert "forbidden_role" in r.text
