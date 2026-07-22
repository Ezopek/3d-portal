"""PROFILE-OFFER-1 (T3) — CRUD endpoint tests for the PrintProfileOffer layer.

End-to-end against a REAL tmp vendored root seeded with the (sanitized) real Orca system
parents, via production wiring (settings point at the tmp dirs). The library blocks an offer
references are imported through the shipped PROFILE-LIB-1 import endpoint, so the offer layer
is exercised exactly as it runs in production. Covers the auth surface, route-enforcement (no
_PUBLIC_ROUTES edit), the create gate order, read-time revalidation, the chain-immutable PATCH,
list/get/delete round-trip, audit, and the curated leak fence.
"""

from __future__ import annotations

import hashlib as _hashlib
import json
import shutil
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import MagicMock

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session, select

from app.core.auth.jwt import encode_token
from app.core.db.models import AuditLog, User, UserRole
from app.main import _PUBLIC_ROUTES, create_app
from app.modules.slicer import profile_offer

FIXTURES = Path(__file__).parent / "fixtures" / "slicer"
LIBRARY_FIXTURES = FIXTURES / "library"
JWT_SECRET = "test"
ORCA_VERSION = "2.3.2"

_SYSTEM_PARENTS = (
    "system_filament_generic_tpu.json",
    "system_process_020_standard.json",
    "system_machine_k1max.json",
)


def _fixture_bytes(name: str) -> bytes:
    return (LIBRARY_FIXTURES / name).read_bytes()


@pytest_asyncio.fixture
async def seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[AsyncClient, Path, uuid.UUID]]:
    """A real app wired at a tmp vendored root seeded with the real system parent tree."""
    vendored_root = tmp_path / "vendored"
    system_dir = vendored_root / "system"
    system_dir.mkdir(parents=True)
    for name in _SYSTEM_PARENTS:
        shutil.copy(LIBRARY_FIXTURES / name, system_dir / name)

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
    monkeypatch.setenv("TOTP_FERNET_KEY", "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM=")
    monkeypatch.setenv("SLICER_VENDORED_PROFILES_DIR", str(vendored_root))
    monkeypatch.setenv("SLICER_BUNDLE_STORE_DIR", str(tmp_path / "bundle-store"))
    monkeypatch.setenv("ORCA_VERSION", ORCA_VERSION)

    from app.core.config import get_settings
    from app.core.db.session import get_engine, init_schema

    get_settings.cache_clear()
    get_engine.cache_clear()

    app = create_app()
    engine = get_engine()
    init_schema(engine)

    with Session(engine) as session:
        admin = User(
            email="admin@localhost.localdomain",
            display_name="Admin",
            role=UserRole.admin,
            password_hash="x",
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        admin_id = admin.id

    fake_redis = fakeredis.aioredis.FakeRedis()
    factory = MagicMock()
    factory.get = MagicMock(return_value=fake_redis)

    async def _aclose() -> None:
        return None

    factory.aclose = _aclose
    app.state.redis = factory

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"X-Portal-Client": "web"},
    ) as ac:
        yield ac, vendored_root, admin_id

    get_settings.cache_clear()
    get_engine.cache_clear()


def _token(role: str, subject: str | None = None) -> str:
    return encode_token(
        subject=subject or str(uuid.uuid4()), role=role, secret=JWT_SECRET, ttl_minutes=30
    )


async def _login_admin(ac: AsyncClient, admin_id: uuid.UUID) -> None:
    ac.cookies.set("portal_access", _token("admin", str(admin_id)))


def _block_upload(content: bytes, *, filename: str = "block.json") -> dict:
    return {"files": {"file": (filename, content, "application/json")}, "data": {}}


async def _import_block(ac: AsyncClient, fixture_name: str) -> str:
    r = await ac.post("/api/admin/profiles/library", **_block_upload(_fixture_bytes(fixture_name)))
    assert r.status_code == 201, r.text
    return r.json()["block_id"]


async def _import_chain_blocks(ac: AsyncClient) -> tuple[str, str, str]:
    """Import machine + process + filament blocks; return their (machine, process, filament) ids.

    All three are USABLE under the seeded system tree: the USER machine inherits the seeded
    system ``Creality K1 Max (0.4 nozzle)`` parent (so it is not flagged
    ``unknown_inherit_parent``), and its inherited system name is what the filament's
    ``compatible_printers`` references — so the filament↔machine identity match resolves via the
    machine's inherit chain (the pinned real-fixture shape, AC-4). Process + filament inherit
    seeded system parents too.
    """
    machine = await _import_block(ac, "user_machine_k1max_microswiss.json")
    process = await _import_block(ac, "user_process_tpu_flowtech.json")
    filament = await _import_block(ac, "user_filament_rosa_flex.json")
    return machine, process, filament


def _offer_body(
    machine: str,
    process: str,
    filament: str,
    *,
    label: str = "TPU Offer",
    visibility: str = "hidden",
    is_default: bool = False,
    categories: list[str] | None = None,
    description: str | None = None,
) -> dict:
    body: dict = {
        "label": label,
        "chain": {
            "machine_block_id": machine,
            "process_block_id": process,
            "filament_block_id": filament,
        },
        "visibility": visibility,
        "is_default": is_default,
        "compatible_material_categories": categories if categories is not None else ["TPU"],
    }
    if description is not None:
        body["description"] = description
    return body


def _snapshot_offers(root: Path) -> dict[str, bytes]:
    offers = root / "offers"
    if not offers.exists():
        return {}
    return {
        p.relative_to(root).as_posix(): p.read_bytes() for p in offers.rglob("*") if p.is_file()
    }


# === auth surface + route enforcement (AC-15) =================================


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["member", "agent"])
async def test_create_requires_admin_is_403(seam, role) -> None:
    ac, _root, _admin_id = seam
    ac.cookies.set("portal_access", _token(role))
    r = await ac.post("/api/admin/profiles/offers", json=_offer_body("0" * 32, "1" * 32, "2" * 32))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_create_anonymous_is_401(seam) -> None:
    ac, _root, _admin_id = seam
    r = await ac.post("/api/admin/profiles/offers", json=_offer_body("0" * 32, "1" * 32, "2" * 32))
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_list_requires_admin_is_403(seam) -> None:
    ac, _root, _admin_id = seam
    ac.cookies.set("portal_access", _token("member"))
    assert (await ac.get("/api/admin/profiles/offers")).status_code == 403


def test_offer_routes_not_in_public_allowlist() -> None:
    assert "/api/admin/profiles/offers" not in _PUBLIC_ROUTES
    assert "/api/admin/profiles/offers/{offer_id}" not in _PUBLIC_ROUTES


# === create gate order (AC-9) ==================================================


@pytest.mark.asyncio
async def test_create_over_cap_is_413(seam) -> None:
    ac, root, admin_id = seam
    await _login_admin(ac, admin_id)
    machine, process, filament = await _import_chain_blocks(ac)
    body = _offer_body(machine, process, filament, description="y" * (1024 * 1024 + 16))
    r = await ac.post("/api/admin/profiles/offers", json=body)
    assert r.status_code == 413
    assert r.json()["detail"]["reason_category"] == "too_large"
    assert _snapshot_offers(root) == {}


@pytest.mark.asyncio
async def test_create_invalid_json_is_422(seam) -> None:
    ac, root, admin_id = seam
    await _login_admin(ac, admin_id)
    r = await ac.post(
        "/api/admin/profiles/offers",
        content=b"not json{",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["reason_category"] == "invalid_json"
    assert _snapshot_offers(root) == {}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        {"label": "x"},  # missing chain
        {
            "label": "x",
            "chain": {
                "machine_block_id": "nothex",
                "process_block_id": "1" * 32,
                "filament_block_id": "2" * 32,
            },
        },
        {
            "label": "x",
            "chain": {
                "machine_block_id": "0" * 32,
                "process_block_id": "1" * 32,
                "filament_block_id": "2" * 32,
            },
            "unexpected": 1,
        },
    ],
)
async def test_create_invalid_offer_shape_is_422(seam, body) -> None:
    ac, root, admin_id = seam
    await _login_admin(ac, admin_id)
    r = await ac.post("/api/admin/profiles/offers", json=body)
    assert r.status_code == 422
    assert r.json()["detail"]["reason_category"] == "invalid_offer"
    assert _snapshot_offers(root) == {}


@pytest.mark.asyncio
async def test_create_unsupported_material_category_is_422(seam) -> None:
    ac, root, admin_id = seam
    await _login_admin(ac, admin_id)
    machine, process, filament = await _import_chain_blocks(ac)
    body = _offer_body(machine, process, filament, categories=["NYLON"])
    r = await ac.post("/api/admin/profiles/offers", json=body)
    assert r.status_code == 422
    assert r.json()["detail"]["reason_category"] == "unsupported_material_category"
    assert _snapshot_offers(root) == {}


@pytest.mark.asyncio
async def test_create_invalid_chain_unknown_block_is_422_not_stored(seam) -> None:
    ac, root, admin_id = seam
    await _login_admin(ac, admin_id)
    machine, process, _filament = await _import_chain_blocks(ac)
    # A syntactically-valid but never-imported filament block id ⇒ unknown_block ⇒ invalid_chain.
    ghost = uuid.uuid4().hex
    r = await ac.post("/api/admin/profiles/offers", json=_offer_body(machine, process, ghost))
    assert r.status_code == 422
    assert r.json()["detail"]["reason_category"] == "invalid_chain"
    assert _snapshot_offers(root) == {}  # nothing stored on the hard-chain reject


# === successful create + audit + leak fence (AC-9, AC-14) ======================


@pytest.mark.asyncio
async def test_create_usable_offer(seam) -> None:
    ac, root, admin_id = seam
    await _login_admin(ac, admin_id)
    machine, process, filament = await _import_chain_blocks(ac)
    r = await ac.post(
        "/api/admin/profiles/offers",
        json=_offer_body(machine, process, filament, label="K1 Max TPU", categories=["TPU"]),
    )
    assert r.status_code == 201, r.text
    offer = r.json()
    assert profile_offer.is_valid_offer_id(offer["offer_id"])
    assert offer["label"] == "K1 Max TPU"
    assert offer["validation_state"] == "usable"
    assert offer["reasons"] == []
    assert offer["chain"]["filament_block_id"] == filament
    # chain_blocks echo carries the three referenced blocks' curated metadata, no raw Orca body.
    assert [b["profile_type"] for b in offer["chain_blocks"]] == ["machine", "process", "filament"]
    for raw_key in ("nozzle_temperature", "filament_density", "outer_wall_speed"):
        assert raw_key not in json.dumps(offer)

    # Sidecar on disk under the disjoint offers/ subtree.
    sidecar = profile_offer.read_offer(root, offer["offer_id"])
    assert sidecar is not None
    assert sidecar["label"] == "K1 Max TPU"

    # Audit emitted (offer_create), leak-fenced.
    from app.core.db.session import get_engine

    with Session(get_engine()) as session:
        [event] = session.exec(
            select(AuditLog).where(AuditLog.action == "slicer_profile.offer_create")
        ).all()
    assert event.entity_type == "slicer_profile"
    assert event.entity_id == uuid.UUID(offer["offer_id"])
    assert event.actor_user_id == admin_id
    after = json.loads(event.after_json)
    assert after["machine_block_id"] == machine
    assert after["validation_state"] == "usable"
    assert "outer_wall_speed" not in event.after_json
    assert "gcode" not in event.after_json


@pytest.mark.asyncio
async def test_create_default_but_hidden_is_requires_attention_but_stored(seam) -> None:
    ac, root, admin_id = seam
    await _login_admin(ac, admin_id)
    machine, process, filament = await _import_chain_blocks(ac)
    r = await ac.post(
        "/api/admin/profiles/offers",
        json=_offer_body(machine, process, filament, is_default=True, visibility="hidden"),
    )
    assert r.status_code == 201, r.text
    offer = r.json()
    assert offer["validation_state"] == "requires_attention"
    assert "default_but_hidden" in offer["reasons"]
    assert profile_offer.read_offer(root, offer["offer_id"]) is not None


@pytest.mark.asyncio
async def test_create_material_category_mismatch_is_flagged(seam) -> None:
    ac, _root, admin_id = seam
    await _login_admin(ac, admin_id)
    machine, process, filament = await _import_chain_blocks(ac)
    # Filament material_type is TPU; declaring PLA-only ⇒ material_category_mismatch.
    r = await ac.post(
        "/api/admin/profiles/offers",
        json=_offer_body(machine, process, filament, categories=["PLA"]),
    )
    assert r.status_code == 201, r.text
    offer = r.json()
    assert offer["validation_state"] == "requires_attention"
    assert "material_category_mismatch" in offer["reasons"]


# === list / get + read-time revalidation (AC-10, AC-11) ========================


@pytest.mark.asyncio
async def test_list_empty_is_200_empty(seam) -> None:
    ac, _root, admin_id = seam
    await _login_admin(ac, admin_id)
    r = await ac.get("/api/admin/profiles/offers")
    assert r.status_code == 200
    assert r.json() == {"offers": []}


@pytest.mark.asyncio
async def test_list_filters_by_category_and_visibility(seam) -> None:
    ac, _root, admin_id = seam
    await _login_admin(ac, admin_id)
    machine, process, filament = await _import_chain_blocks(ac)
    await ac.post(
        "/api/admin/profiles/offers",
        json=_offer_body(machine, process, filament, label="hidden-tpu", visibility="hidden"),
    )
    await ac.post(
        "/api/admin/profiles/offers",
        json=_offer_body(machine, process, filament, label="visible-tpu", visibility="visible"),
    )
    visible = (await ac.get("/api/admin/profiles/offers?visibility=visible")).json()["offers"]
    assert [o["label"] for o in visible] == ["visible-tpu"]
    tpu = (await ac.get("/api/admin/profiles/offers?material_category=TPU")).json()["offers"]
    assert len(tpu) == 2
    pla = (await ac.get("/api/admin/profiles/offers?material_category=PLA")).json()["offers"]
    assert pla == []


@pytest.mark.asyncio
async def test_list_revalidates_after_referenced_block_deleted(seam) -> None:
    ac, _root, admin_id = seam
    await _login_admin(ac, admin_id)
    machine, process, filament = await _import_chain_blocks(ac)
    created = (
        await ac.post(
            "/api/admin/profiles/offers",
            json=_offer_body(machine, process, filament, categories=["TPU"]),
        )
    ).json()
    assert created["validation_state"] == "usable"

    # Delete the referenced process block out-of-band (bypassing the delete guard, which now
    # correctly returns 409 when an offer references the block). The next list must still surface
    # invalid unknown_block — NOT the stale usable — and the offer itself must remain.
    from app.modules.slicer import profile_library as _pl

    assert _pl.delete_block(_root, process) is True
    listed = (await ac.get("/api/admin/profiles/offers")).json()["offers"]
    assert len(listed) == 1
    assert listed[0]["validation_state"] == "invalid"
    assert "unknown_block" in listed[0]["reasons"]


@pytest.mark.asyncio
async def test_get_offer_detail_and_404(seam) -> None:
    ac, _root, admin_id = seam
    await _login_admin(ac, admin_id)
    machine, process, filament = await _import_chain_blocks(ac)
    created = (
        await ac.post("/api/admin/profiles/offers", json=_offer_body(machine, process, filament))
    ).json()
    got = await ac.get(f"/api/admin/profiles/offers/{created['offer_id']}")
    assert got.status_code == 200
    assert got.json()["offer_id"] == created["offer_id"]

    missing = await ac.get(f"/api/admin/profiles/offers/{'0' * 32}")
    assert missing.status_code == 404
    assert missing.json()["detail"]["reason_category"] == "not_found"

    bad = await ac.get("/api/admin/profiles/offers/not-a-hex-id")
    assert bad.status_code == 404


# === patch (AC-12) — label/visibility/default/categories; chain immutable ======


@pytest.mark.asyncio
async def test_patch_updates_fields_and_audits(seam) -> None:
    ac, _root, admin_id = seam
    await _login_admin(ac, admin_id)
    machine, process, filament = await _import_chain_blocks(ac)
    created = (
        await ac.post(
            "/api/admin/profiles/offers",
            json=_offer_body(machine, process, filament, label="old", visibility="hidden"),
        )
    ).json()
    offer_id = created["offer_id"]

    r = await ac.patch(
        f"/api/admin/profiles/offers/{offer_id}",
        json={"label": "new", "visibility": "visible"},
    )
    assert r.status_code == 200, r.text
    patched = r.json()
    assert patched["label"] == "new"
    assert patched["visibility"] == "visible"
    # Chain unchanged; updated_at bumped.
    assert patched["chain"]["machine_block_id"] == machine
    assert patched["updated_at"] >= created["updated_at"]

    from app.core.db.session import get_engine

    with Session(get_engine()) as session:
        events = session.exec(
            select(AuditLog).where(AuditLog.action == "slicer_profile.offer_update")
        ).all()
    assert len(events) == 1
    assert events[0].entity_id == uuid.UUID(offer_id)


@pytest.mark.asyncio
async def test_patch_chain_is_rejected_422(seam) -> None:
    ac, _root, admin_id = seam
    await _login_admin(ac, admin_id)
    machine, process, filament = await _import_chain_blocks(ac)
    created = (
        await ac.post("/api/admin/profiles/offers", json=_offer_body(machine, process, filament))
    ).json()
    # The chain field is forbidden on PATCH (extra="forbid").
    r = await ac.patch(
        f"/api/admin/profiles/offers/{created['offer_id']}",
        json={
            "chain": {
                "machine_block_id": "0" * 32,
                "process_block_id": "1" * 32,
                "filament_block_id": "2" * 32,
            }
        },
    )
    assert r.status_code == 422
    assert r.json()["detail"]["reason_category"] == "invalid_offer"


@pytest.mark.asyncio
async def test_patch_unsupported_category_is_422(seam) -> None:
    ac, _root, admin_id = seam
    await _login_admin(ac, admin_id)
    machine, process, filament = await _import_chain_blocks(ac)
    created = (
        await ac.post("/api/admin/profiles/offers", json=_offer_body(machine, process, filament))
    ).json()
    r = await ac.patch(
        f"/api/admin/profiles/offers/{created['offer_id']}",
        json={"compatible_material_categories": ["NYLON"]},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["reason_category"] == "unsupported_material_category"


@pytest.mark.asyncio
async def test_patch_absent_offer_is_404(seam) -> None:
    ac, _root, admin_id = seam
    await _login_admin(ac, admin_id)
    r = await ac.patch(f"/api/admin/profiles/offers/{'0' * 32}", json={"label": "x"})
    assert r.status_code == 404


# === delete (AC-13) — 204/404, audited, library untouched ======================


@pytest.mark.asyncio
async def test_delete_offer_204_then_404_and_library_untouched(seam) -> None:
    ac, root, admin_id = seam
    await _login_admin(ac, admin_id)
    machine, process, filament = await _import_chain_blocks(ac)
    created = (
        await ac.post("/api/admin/profiles/offers", json=_offer_body(machine, process, filament))
    ).json()
    offer_id = created["offer_id"]

    r = await ac.delete(f"/api/admin/profiles/offers/{offer_id}")
    assert r.status_code == 204
    assert profile_offer.read_offer(root, offer_id) is None
    # Re-delete is an idempotent-safe 404, not a 500.
    assert (await ac.delete(f"/api/admin/profiles/offers/{offer_id}")).status_code == 404

    # The referenced library blocks are untouched (offers reference, they do not own).
    assert (await ac.get(f"/api/admin/profiles/library/{machine}")).status_code == 200
    assert (await ac.get(f"/api/admin/profiles/library/{process}")).status_code == 200

    from app.core.db.session import get_engine

    with Session(get_engine()) as session:
        events = session.exec(
            select(AuditLog).where(AuditLog.action == "slicer_profile.offer_delete")
        ).all()
    assert len(events) == 1
    assert events[0].entity_id == uuid.UUID(offer_id)


@pytest.mark.asyncio
async def test_create_audit_failure_rolls_back(seam, monkeypatch) -> None:
    ac, root, admin_id = seam
    await _login_admin(ac, admin_id)
    machine, process, filament = await _import_chain_blocks(ac)
    before = _snapshot_offers(root)

    def boom(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("app.modules.slicer.admin_router.record_event", boom)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        await ac.post("/api/admin/profiles/offers", json=_offer_body(machine, process, filament))
    # Fresh create rolled back → offers tree byte-identical, no temp leftover.
    assert _snapshot_offers(root) == before
    assert not list((root / "offers").rglob(".*tmp*")) if (root / "offers").exists() else True


# === T5: Story 38.1 — sync_state in offer DTO ===================================


class _FakeArqPool:
    def __init__(self) -> None:
        self.calls: list = []

    async def enqueue_job(self, name: str, *args: object, **kwargs: object) -> object:
        self.calls.append((name, args, kwargs))
        return object()


_STL_BYTES = b"solid t5-stl\nendsolid t5-stl\n"
_STL_HASH = _hashlib.sha256(_STL_BYTES).hexdigest()
_PUBLISH_SYSTEM_DIR = FIXTURES / "system"
_INTENTS_FIXTURE = FIXTURES / "intents" / "creality-k1-max-microswiss-hf" / "TPU" / "standard.json"


def _store_chain_block_t5(
    root: Path, profile_type: str, name: str, body: dict, *, material_type: str | None = None
) -> str:
    """Seed a chain block directly (bypassing the import endpoint) for publish tests."""
    from app.modules.slicer.profile_library import (
        derive_block_id,
        store_block,
    )

    block_id = derive_block_id(profile_type, name)  # type: ignore[arg-type]
    from datetime import UTC, datetime

    imported_at = datetime.now(UTC).isoformat()
    manifest = {
        "manifest_version": "1",
        "block_id": block_id,
        "profile_type": profile_type,
        "name": name,
        "source": "user",
        "is_system": False,
        "inherit": body.get("inherit"),
        "inherit_chain": [body["inherit"]] if isinstance(body.get("inherit"), str) else [],
        "settings_id": None,
        "material_type": material_type,
        "compatible_printers": [],
        "validation_state": "usable",
        "reasons": [],
        "portal_label": None,
        "imported_at": imported_at,
        "imported_by": "00000000-0000-0000-0000-0000000000aa",
        "original_filename": f"{profile_type}.json",
    }
    store_block(root, profile_type=profile_type, block_id=block_id, body=body, manifest=manifest)  # type: ignore[arg-type]
    return block_id


def _seed_publish_offer(root: Path) -> str:
    """Seed a usable offer with chain blocks from the standard intent fixture."""
    import uuid as _uuid

    from app.modules.slicer.profile_offer import ProfileChain, build_offer_record, store_offer

    partials = json.loads(_INTENTS_FIXTURE.read_text(encoding="utf-8"))
    machine = _store_chain_block_t5(root, "machine", "offer-machine-t5", partials["machine"])
    process = _store_chain_block_t5(root, "process", "offer-process-t5", partials["process"])
    filament = _store_chain_block_t5(
        root, "filament", "offer-filament-t5", partials["filament"], material_type="TPU"
    )
    offer_id = _uuid.uuid4().hex
    record = build_offer_record(
        offer_id=offer_id,
        label="T5 Standard",
        description=None,
        chain=ProfileChain(
            machine_block_id=machine, process_block_id=process, filament_block_id=filament
        ),
        visibility="visible",
        is_default=False,
        compatible_material_categories=["TPU"],
        validation_state="usable",
        reasons=[],
        created_at="2026-06-14T00:00:00+00:00",
        created_by=_uuid.UUID("00000000-0000-0000-0000-0000000000aa"),
        updated_at="2026-06-14T00:00:00+00:00",
    )
    store_offer(root, record)
    return offer_id, machine, process, filament


@pytest_asyncio.fixture
async def seam_publish(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[tuple]:
    """Full publish seam: bundle_store + STL cache + arq pool + content dir."""
    from sqlmodel import Session as _Session

    from app.core.db.models import Model, ModelFile, ModelFileKind, User, UserRole

    vendored_root = tmp_path / "vendored"
    content_dir = tmp_path / "content"
    system_dir = vendored_root / "system"
    system_dir.mkdir(parents=True)

    if _PUBLISH_SYSTEM_DIR.exists():
        for source in _PUBLISH_SYSTEM_DIR.glob("*.json"):
            shutil.copy(source, system_dir / source.name)

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
    monkeypatch.setenv("TOTP_FERNET_KEY", "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM=")
    monkeypatch.setenv("PORTAL_CONTENT_DIR", str(content_dir))
    monkeypatch.setenv("SLICER_VENDORED_PROFILES_DIR", str(vendored_root))
    monkeypatch.setenv("SLICER_BUNDLE_STORE_DIR", str(tmp_path / "bundle-store"))
    monkeypatch.setenv("SLICER_ESTIMATE_STORE_DIR", str(tmp_path / "estimate-store"))
    monkeypatch.setenv("SLICER_STL_CACHE_DIR", str(tmp_path / "stl-cache"))
    monkeypatch.setenv("ORCA_VERSION", ORCA_VERSION)

    from app.core.config import get_settings
    from app.core.db.session import get_engine, init_schema

    get_settings.cache_clear()
    get_engine.cache_clear()

    app = create_app()
    engine = get_engine()
    init_schema(engine)

    with _Session(engine) as session:
        u = User(
            email="admin@localhost.localdomain",
            display_name="Admin",
            role=UserRole.admin,
            password_hash="x",
        )
        session.add(u)
        session.commit()
        session.refresh(u)
        admin_id = u.id
        model = Model(slug=f"model-{uuid.uuid4().hex[:8]}", name_en="m")
        session.add(model)
        session.commit()
        session.refresh(model)
        storage_path = f"models/{model.id}/files/part.stl"
        file_row = ModelFile(
            model_id=model.id,
            kind=ModelFileKind.stl,
            original_name="part.stl",
            storage_path=storage_path,
            sha256=_STL_HASH,
            size_bytes=len(_STL_BYTES),
            mime_type="model/stl",
        )
        session.add(file_row)
        session.commit()
        stl_path = content_dir / storage_path
        stl_path.parent.mkdir(parents=True, exist_ok=True)
        stl_path.write_bytes(_STL_BYTES)

    fake_redis = fakeredis.aioredis.FakeRedis()
    factory = MagicMock()
    factory.get = MagicMock(return_value=fake_redis)

    async def _aclose() -> None:
        return None

    factory.aclose = _aclose
    app.state.redis = factory
    pool = _FakeArqPool()
    app.state.arq = pool

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"X-Portal-Client": "web"},
    ) as ac:
        yield ac, vendored_root, admin_id, pool

    get_settings.cache_clear()
    get_engine.cache_clear()


async def _do_publish(ac, offer_id: str) -> dict:
    r = await ac.post(
        f"/api/admin/profiles/offers/{offer_id}/publish", json={"stl_hash": _STL_HASH}
    )
    assert r.status_code == 200, f"publish failed: {r.text}"
    return r.json()


@pytest.mark.asyncio
async def test_t5_1_freshly_published_offer_has_sync_state_current(seam_publish) -> None:
    ac, root, admin_id, _pool = seam_publish
    await _login_admin(ac, admin_id)
    offer_id, _machine, _process, _filament = _seed_publish_offer(root)
    await _do_publish(ac, offer_id)

    r = await ac.get(f"/api/admin/profiles/offers/{offer_id}")
    assert r.status_code == 200, r.text
    assert r.json()["sync_state"] == "current"


@pytest.mark.asyncio
async def test_t5_2_offer_becomes_stale_after_block_manifest_updated(seam_publish) -> None:
    """After re-writing a block manifest with newer imported_at, sync_state becomes stale."""
    ac, root, admin_id, _pool = seam_publish
    await _login_admin(ac, admin_id)
    offer_id, _machine, process, _filament = _seed_publish_offer(root)
    await _do_publish(ac, offer_id)

    # Bump the process block's imported_at in the manifest (simulates re-import)
    from app.modules.slicer.profile_library import block_path, manifest_path

    proc_bp = block_path(root, "process", process)
    mpath = manifest_path(proc_bp)
    data = json.loads(mpath.read_text())
    data["imported_at"] = "2026-06-15T12:00:00+00:00"
    mpath.write_text(json.dumps(data))

    r = await ac.get(f"/api/admin/profiles/offers/{offer_id}")
    assert r.status_code == 200, r.text
    assert r.json()["sync_state"] == "stale"


@pytest.mark.asyncio
async def test_t5_3_offer_without_fingerprint_is_stale(seam) -> None:
    ac, root, admin_id = seam
    await _login_admin(ac, admin_id)
    machine, process, filament = await _import_chain_blocks(ac)
    created = (
        await ac.post(
            "/api/admin/profiles/offers",
            json=_offer_body(machine, process, filament, visibility="visible", categories=["TPU"]),
        )
    ).json()
    offer_id = created["offer_id"]

    # Manually write a published sidecar without published_chain_fingerprint (pre-38.1)
    from app.modules.slicer import profile_offer as _po

    sidecar = _po.read_offer(root, offer_id)
    sidecar["publish_state"] = "published"
    sidecar["published_bundle_hash"] = "a" * 64
    sidecar["published_at"] = "2026-06-14T00:00:00+00:00"
    sidecar["published_by"] = str(admin_id)
    sidecar["source_snapshot_ref"] = "b" * 64
    sidecar["published_stl_hash"] = "c" * 64
    sidecar.pop("published_chain_fingerprint", None)
    _po.store_offer(root, sidecar)

    r = await ac.get(f"/api/admin/profiles/offers/{offer_id}")
    assert r.status_code == 200, r.text
    assert r.json()["sync_state"] == "stale"


@pytest.mark.asyncio
async def test_t5_4_unpublished_offer_has_sync_state_unknown(seam) -> None:
    ac, _root, admin_id = seam
    await _login_admin(ac, admin_id)
    machine, process, filament = await _import_chain_blocks(ac)
    created = (
        await ac.post("/api/admin/profiles/offers", json=_offer_body(machine, process, filament))
    ).json()

    r = await ac.get(f"/api/admin/profiles/offers/{created['offer_id']}")
    assert r.status_code == 200, r.text
    assert r.json()["sync_state"] == "unknown"


@pytest.mark.asyncio
async def test_t5_5_sync_state_not_in_member_dto(seam) -> None:
    ac, root, admin_id = seam
    await _login_admin(ac, admin_id)
    machine, process, filament = await _import_chain_blocks(ac)
    created = (
        await ac.post(
            "/api/admin/profiles/offers",
            json=_offer_body(machine, process, filament, visibility="visible", categories=["TPU"]),
        )
    ).json()

    from app.modules.slicer import profile_offer as _po

    sidecar = _po.read_offer(root, created["offer_id"])
    sidecar["publish_state"] = "published"
    sidecar["published_bundle_hash"] = "a" * 64
    sidecar["published_at"] = "2026-06-14T00:00:00+00:00"
    sidecar["published_by"] = str(admin_id)
    sidecar["source_snapshot_ref"] = "b" * 64
    sidecar["published_stl_hash"] = "c" * 64
    _po.store_offer(root, sidecar)

    ac.cookies.set("portal_access", _token("member"))
    r = await ac.get("/api/profiles/offers/published")
    assert r.status_code == 200, r.text
    offers = r.json()["offers"]
    assert len(offers) >= 1
    for offer in offers:
        assert "sync_state" not in offer
        assert "published_bundle_hash" not in offer
        assert "published_chain_fingerprint" not in offer


@pytest.mark.asyncio
async def test_t5_6_publish_fails_when_manifest_missing_imported_at(seam_publish) -> None:
    ac, root, admin_id, _pool = seam_publish
    await _login_admin(ac, admin_id)
    offer_id, _machine, process, _filament = _seed_publish_offer(root)

    # Corrupt the process block manifest: remove imported_at
    from app.modules.slicer.profile_library import block_path, manifest_path

    proc_bp = block_path(root, "process", process)
    mpath = manifest_path(proc_bp)
    data = json.loads(mpath.read_text())
    del data["imported_at"]
    mpath.write_text(json.dumps(data))

    # Publish should fail
    r = await ac.post(
        f"/api/admin/profiles/offers/{offer_id}/publish", json={"stl_hash": _STL_HASH}
    )
    assert r.status_code in (409, 422, 400), f"expected 4xx, got {r.status_code}: {r.text}"

    # Sidecar must remain unpublished
    from app.modules.slicer import profile_offer as _po

    sidecar = _po.read_offer(root, offer_id)
    assert sidecar["publish_state"] == "unpublished"
    assert sidecar.get("published_chain_fingerprint") is None
