"""Story 36.1 — member-accessible published-offer list endpoint.

TDD tests for ``GET /api/profiles/offers/published``.

Auth surface: anonymous → 401; authenticated member → 200; not in _PUBLIC_ROUTES.
Filter: only published offers returned; ?material=<key> filter by compatible categories.
Leak fence: serialized response must not contain bundle_hash, raw Orca refs, chain/block
body, sidecar paths/internals, publish-state internals, or filesystem paths.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session

from app.core.auth.jwt import encode_token
from app.core.db.models import User, UserRole
from app.main import _PUBLIC_ROUTES, create_app
from app.modules.slicer import profile_offer

JWT_SECRET = "x" * 32

# Forbidden field names / value substrings the leak fence asserts must NOT appear
# in the serialized member response.
_FORBIDDEN_FIELDS = (
    "bundle_hash",
    "source_snapshot_ref",
    "published_bundle_hash",
    "published_stl_hash",
    "published_at",
    "published_by",
    "publish_state",
    "chain",
    "machine_block_id",
    "process_block_id",
    "filament_block_id",
    "validation_state",
    "reasons",
    "visibility",
    "is_default",
    "description",
    "created_at",
    "created_by",
    "updated_at",
    "original_filename",
    "manifest_version",
    "offer_manifest_version",
)

# A valid-looking fake sha256 hex digest (64 chars) used for test publish metadata.
_FAKE_HASH = "a" * 64
_FAKE_HASH2 = "b" * 64
_FAKE_HASH3 = "c" * 64


def _token(role: str, subject: str | None = None) -> str:
    return encode_token(
        subject=subject or str(uuid.uuid4()),
        role=role,
        secret=JWT_SECRET,
        ttl_minutes=30,
    )


def _make_published_sidecar(
    *,
    label: str = "K1 Max Standard PLA",
    categories: list[str] | None = None,
    offer_id: str | None = None,
) -> dict:
    """Build a sidecar dict with publish_state=published, using fake block IDs."""
    oid = offer_id or profile_offer.mint_offer_id()
    sidecar = profile_offer.build_offer_record(
        offer_id=oid,
        label=label,
        description=None,
        chain=profile_offer.ProfileChain(
            machine_block_id="a" * 32,
            process_block_id="b" * 32,
            filament_block_id="c" * 32,
        ),
        visibility="visible",
        is_default=False,
        compatible_material_categories=categories if categories is not None else ["PLA"],
        validation_state="usable",
        reasons=[],
        created_at="2026-06-13T00:00:00+00:00",
        created_by=str(uuid.uuid4()),
        updated_at="2026-06-13T00:00:00+00:00",
    )
    # Stamp publish metadata directly — bypasses resolve/bundle, test-only shortcut.
    sidecar["publish_state"] = "published"
    sidecar["published_bundle_hash"] = _FAKE_HASH
    sidecar["published_at"] = "2026-06-13T01:00:00+00:00"
    sidecar["published_by"] = str(uuid.uuid4())
    sidecar["source_snapshot_ref"] = _FAKE_HASH2
    sidecar["published_stl_hash"] = _FAKE_HASH3
    return sidecar


def _make_unpublished_sidecar(
    *,
    label: str = "Unpublished Offer",
    categories: list[str] | None = None,
) -> dict:
    return profile_offer.build_offer_record(
        offer_id=profile_offer.mint_offer_id(),
        label=label,
        description=None,
        chain=profile_offer.ProfileChain(
            machine_block_id="d" * 32,
            process_block_id="e" * 32,
            filament_block_id="f" * 32,
        ),
        visibility="visible",
        is_default=False,
        compatible_material_categories=categories if categories is not None else ["PLA"],
        validation_state="usable",
        reasons=[],
        created_at="2026-06-13T00:00:00+00:00",
        created_by=str(uuid.uuid4()),
        updated_at="2026-06-13T00:00:00+00:00",
    )
    # publish_state remains "unpublished" (the default from build_offer_record)


@pytest_asyncio.fixture
async def seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[AsyncClient, Path, uuid.UUID]]:
    """Real app wired at a tmp vendored root; creates one member user."""
    vendored_root = tmp_path / "vendored"
    vendored_root.mkdir()

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
    monkeypatch.setenv("TOTP_FERNET_KEY", "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM=")
    monkeypatch.setenv("SLICER_VENDORED_PROFILES_DIR", str(vendored_root))

    from app.core.config import get_settings
    from app.core.db.session import get_engine, init_schema

    get_settings.cache_clear()
    get_engine.cache_clear()

    app = create_app()
    engine = get_engine()
    init_schema(engine)

    with Session(engine) as session:
        member = User(
            email="member@localhost.localdomain",
            display_name="Member",
            role=UserRole.member,
            password_hash="x",
        )
        session.add(member)
        session.commit()
        session.refresh(member)
        member_id = member.id

    fake_redis = fakeredis.aioredis.FakeRedis()
    factory_mock = type(
        "_FakeFactory",
        (),
        {"get": staticmethod(lambda: fake_redis), "aclose": staticmethod(lambda: None)},
    )()
    app.state.redis = factory_mock

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"X-Portal-Client": "web"},
    ) as ac:
        yield ac, vendored_root, member_id

    get_settings.cache_clear()
    get_engine.cache_clear()


# === auth surface (AC-2, AC-3, AC-4) =========================================


@pytest.mark.asyncio
async def test_anonymous_returns_401(seam) -> None:
    """AC-3 — anonymous request returns 401."""
    ac, _root, _member_id = seam
    r = await ac.get("/api/profiles/offers/published")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_member_returns_200_empty(seam) -> None:
    """AC-2 — authenticated member gets 200; empty list when no published offers."""
    ac, _root, member_id = seam
    ac.cookies.set("portal_access", _token("member", str(member_id)))
    r = await ac.get("/api/profiles/offers/published")
    assert r.status_code == 200
    body = r.json()
    assert "offers" in body
    assert body["offers"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["admin"])
async def test_admin_role_also_allowed(seam, role: str) -> None:
    """current_user accepts admin role too (any authenticated user)."""
    ac, _root, _member_id = seam
    ac.cookies.set("portal_access", _token(role))
    r = await ac.get("/api/profiles/offers/published")
    assert r.status_code == 200


def test_route_not_in_public_allowlist() -> None:
    """AC-4 — the new route must NOT appear in _PUBLIC_ROUTES."""
    assert "/api/profiles/offers/published" not in _PUBLIC_ROUTES


# === published-only filter (AC-6, AC-7) ======================================


@pytest.mark.asyncio
async def test_returns_only_published_offers(seam) -> None:
    """AC-6/AC-7 — only published offers returned; unpublished are omitted."""
    ac, root, member_id = seam
    # Seed one published and one unpublished offer directly on disk.
    published = _make_published_sidecar(label="Published PLA Offer")
    unpublished = _make_unpublished_sidecar(label="Unpublished PLA Offer")
    profile_offer.store_offer(root, published)
    profile_offer.store_offer(root, unpublished)

    ac.cookies.set("portal_access", _token("member", str(member_id)))
    r = await ac.get("/api/profiles/offers/published")
    assert r.status_code == 200
    body = r.json()
    offer_ids = [o["offer_id"] for o in body["offers"]]
    assert published["offer_id"] in offer_ids
    assert unpublished["offer_id"] not in offer_ids
    assert len(body["offers"]) == 1


@pytest.mark.asyncio
async def test_multiple_published_offers_returned(seam) -> None:
    """AC-9 — all published offers returned without material filter."""
    ac, root, member_id = seam
    offer_a = _make_published_sidecar(label="PLA Offer", categories=["PLA"])
    offer_b = _make_published_sidecar(label="TPU Offer", categories=["TPU"])
    profile_offer.store_offer(root, offer_a)
    profile_offer.store_offer(root, offer_b)

    ac.cookies.set("portal_access", _token("member", str(member_id)))
    r = await ac.get("/api/profiles/offers/published")
    assert r.status_code == 200
    ids = {o["offer_id"] for o in r.json()["offers"]}
    assert offer_a["offer_id"] in ids
    assert offer_b["offer_id"] in ids


# === ?material filter (AC-8) =================================================


@pytest.mark.asyncio
async def test_material_filter_returns_matching_offers(seam) -> None:
    """AC-8 — ?material=PLA returns only PLA-compatible published offers."""
    ac, root, member_id = seam
    pla_offer = _make_published_sidecar(label="PLA Offer", categories=["PLA"])
    tpu_offer = _make_published_sidecar(label="TPU Offer", categories=["TPU"])
    profile_offer.store_offer(root, pla_offer)
    profile_offer.store_offer(root, tpu_offer)

    ac.cookies.set("portal_access", _token("member", str(member_id)))
    r = await ac.get("/api/profiles/offers/published", params={"material": "PLA"})
    assert r.status_code == 200
    ids = {o["offer_id"] for o in r.json()["offers"]}
    assert pla_offer["offer_id"] in ids
    assert tpu_offer["offer_id"] not in ids


@pytest.mark.asyncio
async def test_material_filter_case_insensitive(seam) -> None:
    """AC-8 — ?material=pla (lowercase) is normalized to PLA."""
    ac, root, member_id = seam
    pla_offer = _make_published_sidecar(label="PLA Offer", categories=["PLA"])
    profile_offer.store_offer(root, pla_offer)

    ac.cookies.set("portal_access", _token("member", str(member_id)))
    r = await ac.get("/api/profiles/offers/published", params={"material": "pla"})
    assert r.status_code == 200
    assert len(r.json()["offers"]) == 1


@pytest.mark.asyncio
async def test_blank_material_filter_returns_empty(seam) -> None:
    """AC-8 — blank ?material filter is normalized as invalid and returns empty."""
    ac, root, member_id = seam
    pla_offer = _make_published_sidecar(label="PLA Offer", categories=["PLA"])
    profile_offer.store_offer(root, pla_offer)

    ac.cookies.set("portal_access", _token("member", str(member_id)))
    r = await ac.get("/api/profiles/offers/published", params={"material": "   "})
    assert r.status_code == 200
    assert r.json()["offers"] == []


@pytest.mark.asyncio
async def test_material_filter_no_match_returns_empty(seam) -> None:
    """AC-8 — ?material=PETG returns empty list when only PLA offers exist."""
    ac, root, member_id = seam
    pla_offer = _make_published_sidecar(label="PLA Offer", categories=["PLA"])
    profile_offer.store_offer(root, pla_offer)

    ac.cookies.set("portal_access", _token("member", str(member_id)))
    r = await ac.get("/api/profiles/offers/published", params={"material": "PETG"})
    assert r.status_code == 200
    assert r.json()["offers"] == []


@pytest.mark.asyncio
async def test_material_filter_not_applied_without_param(seam) -> None:
    """AC-9 — no ?material param → all published offers returned."""
    ac, root, member_id = seam
    for cat in ["PLA", "TPU", "PETG"]:
        profile_offer.store_offer(root, _make_published_sidecar(categories=[cat]))

    ac.cookies.set("portal_access", _token("member", str(member_id)))
    r = await ac.get("/api/profiles/offers/published")
    assert r.status_code == 200
    assert len(r.json()["offers"]) == 3


# === safe member DTO fields (AC-11) ==========================================


@pytest.mark.asyncio
async def test_response_contains_required_safe_fields(seam) -> None:
    """AC-11 — each item exposes offer_id, portal_label, quality_tier,
    compatible_material_categories, printer_name."""
    ac, root, member_id = seam
    published = _make_published_sidecar(label="Test Offer", categories=["PLA"])
    profile_offer.store_offer(root, published)

    ac.cookies.set("portal_access", _token("member", str(member_id)))
    r = await ac.get("/api/profiles/offers/published")
    assert r.status_code == 200
    items = r.json()["offers"]
    assert len(items) == 1
    item = items[0]
    assert item["offer_id"] == published["offer_id"]
    assert item["portal_label"] == "Test Offer"
    assert "quality_tier" in item  # may be null when blocks unavailable
    assert "compatible_material_categories" in item
    assert item["compatible_material_categories"] == ["PLA"]
    assert "printer_name" in item  # may be null when blocks unavailable


# === negative leak-fence (AC-12, AC-13) =====================================


@pytest.mark.asyncio
async def test_leak_fence_no_forbidden_fields_in_response(seam) -> None:
    """AC-12/AC-13 — serialized member response must NOT contain internal field names
    (bundle_hash, raw Orca refs, chain/block internals, publish-state internals, paths)."""
    ac, root, member_id = seam
    published = _make_published_sidecar(label="Fence Offer", categories=["PLA"])
    profile_offer.store_offer(root, published)

    ac.cookies.set("portal_access", _token("member", str(member_id)))
    r = await ac.get("/api/profiles/offers/published")
    assert r.status_code == 200

    raw_json = r.text
    for forbidden in _FORBIDDEN_FIELDS:
        assert forbidden not in raw_json, (
            f"Leak fence violated: forbidden field/key '{forbidden}' found in member response. "
            f"Response body: {raw_json[:500]}"
        )


@pytest.mark.asyncio
async def test_leak_fence_fake_hash_values_not_in_response(seam) -> None:
    """AC-12 — the fake published_bundle_hash value must not appear in the response."""
    ac, root, member_id = seam
    published = _make_published_sidecar(label="Hash Fence Offer", categories=["PLA"])
    profile_offer.store_offer(root, published)

    ac.cookies.set("portal_access", _token("member", str(member_id)))
    r = await ac.get("/api/profiles/offers/published")
    assert r.status_code == 200

    raw_json = r.text
    # The fake hash values (64 'a', 64 'b', 64 'c') must not appear in the JSON body.
    assert _FAKE_HASH not in raw_json
    assert _FAKE_HASH2 not in raw_json
    assert _FAKE_HASH3 not in raw_json


# === admin offer routes unchanged (AC-5) =====================================


@pytest.mark.asyncio
async def test_admin_offer_routes_still_require_admin(seam) -> None:
    """AC-5 — admin endpoints remain unchanged; a member token gets 403."""
    ac, _root, member_id = seam
    ac.cookies.set("portal_access", _token("member", str(member_id)))
    # List endpoint (GET /api/admin/profiles/offers) must still 403 a member.
    r = await ac.get("/api/admin/profiles/offers")
    assert r.status_code == 403
