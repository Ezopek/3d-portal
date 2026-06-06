"""PROFILE-LIB-1 (T3) — CRUD endpoint tests for the separate-block profile library.

End-to-end against a REAL tmp vendored root seeded with the (sanitized) real Orca system
parents, via production wiring (settings point at the tmp dirs). Covers the auth surface,
route-enforcement (no _PUBLIC_ROUTES edit), the import gate order, the AC-5 governance flag,
list/get/delete round-trip, audit, and the curated leak fence.
"""

from __future__ import annotations

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
from app.modules.slicer import profile_library

FIXTURES = Path(__file__).parent / "fixtures" / "slicer"
LIBRARY_FIXTURES = FIXTURES / "library"
JWT_SECRET = "test"
ORCA_VERSION = "2.3.2"

# System parents the user blocks inherit (seeded into <root>/system so the inherit-chain walk
# + governance resolve). These are the sanitized real Orca system exports.
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


def _upload(
    content: bytes, *, filename: str = "block.json", portal_label: str | None = None
) -> dict:
    data: dict[str, str] = {}
    if portal_label is not None:
        data["portal_label"] = portal_label
    return {"files": {"file": (filename, content, "application/json")}, "data": data}


async def _login_admin(ac: AsyncClient, admin_id: uuid.UUID) -> None:
    ac.cookies.set("portal_access", _token("admin", str(admin_id)))


def _snapshot_library(root: Path) -> dict[str, bytes]:
    lib = root / "library"
    if not lib.exists():
        return {}
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in lib.rglob("*") if p.is_file()}


# === auth surface (AC-15) ======================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["member", "agent"])
async def test_import_requires_admin_is_403(seam, role) -> None:
    ac, _root, _admin_id = seam
    ac.cookies.set("portal_access", _token(role))
    r = await ac.post(
        "/api/admin/profiles/library", **_upload(_fixture_bytes("user_process_tpu_flowtech.json"))
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_import_anonymous_is_401(seam) -> None:
    ac, _root, _admin_id = seam
    r = await ac.post(
        "/api/admin/profiles/library", **_upload(_fixture_bytes("user_process_tpu_flowtech.json"))
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_list_requires_admin_is_403(seam) -> None:
    ac, _root, _admin_id = seam
    ac.cookies.set("portal_access", _token("member"))
    assert (await ac.get("/api/admin/profiles/library")).status_code == 403


def test_library_routes_not_in_public_allowlist() -> None:
    assert "/api/admin/profiles/library" not in _PUBLIC_ROUTES


# === import gate order (AC-9) ==================================================


@pytest.mark.asyncio
async def test_import_over_cap_is_413(seam) -> None:
    ac, root, admin_id = seam
    await _login_admin(ac, admin_id)
    oversized = b'{"name":"x","print_settings_id":"x","pad":"' + b"y" * (1024 * 1024 + 16) + b'"}'
    r = await ac.post("/api/admin/profiles/library", **_upload(oversized))
    assert r.status_code == 413
    assert r.json()["detail"]["reason_category"] == "too_large"
    assert _snapshot_library(root) == {}


@pytest.mark.asyncio
async def test_import_invalid_json_is_422(seam) -> None:
    ac, root, admin_id = seam
    await _login_admin(ac, admin_id)
    r = await ac.post("/api/admin/profiles/library", **_upload(b"not json{"))
    assert r.status_code == 422
    assert r.json()["detail"]["reason_category"] == "invalid_json"
    assert _snapshot_library(root) == {}


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [b"{}", b'{"name":"orphan"}', b'{"unrelated":1}'])
async def test_import_unsupported_profile_is_422_not_stored(seam, body) -> None:
    ac, root, admin_id = seam
    await _login_admin(ac, admin_id)
    r = await ac.post("/api/admin/profiles/library", **_upload(body))
    assert r.status_code == 422
    assert r.json()["detail"]["reason_category"] == "unsupported_profile"
    assert _snapshot_library(root) == {}  # nothing stored on the reject path


# === successful import + manifest + audit (AC-9, AC-14) ========================


@pytest.mark.asyncio
async def test_import_usable_process_block(seam) -> None:
    ac, root, admin_id = seam
    await _login_admin(ac, admin_id)
    r = await ac.post(
        "/api/admin/profiles/library",
        **_upload(_fixture_bytes("user_process_tpu_flowtech.json"), portal_label="TPU FlowTech"),
    )
    assert r.status_code == 201, r.text
    block = r.json()
    assert block["profile_type"] == "process"
    assert block["name"] == "AI 0.20mm TPU - FlowTech"
    assert block["source"] == "user"
    assert block["validation_state"] == "usable"
    assert block["reasons"] == []
    assert block["inherit"] == "0.20mm Standard @Creality K1Max (0.4 nozzle)"
    assert block["portal_label"] == "TPU FlowTech"
    assert profile_library.is_valid_block_id(block["block_id"])

    # Body + curated manifest on disk under the disjoint library/ subtree.
    body_path = profile_library.block_path(root, "process", block["block_id"])
    assert body_path.exists()
    manifest = json.loads(profile_library.manifest_path(body_path).read_text())
    assert manifest["validation_state"] == "usable"
    assert manifest["original_filename"] == "block.json"

    # Audit emitted (library_import), leak-fenced.
    from app.core.db.session import get_engine

    with Session(get_engine()) as session:
        [event] = session.exec(
            select(AuditLog).where(AuditLog.action == "slicer_profile.library_import")
        ).all()
    assert event.entity_type == "slicer_profile"
    assert event.actor_user_id == admin_id
    after = json.loads(event.after_json)
    assert after["profile_type"] == "process"
    assert after["name"] == "AI 0.20mm TPU - FlowTech"
    # No raw Orca body / g-code in the audit payload.
    assert "outer_wall_speed" not in event.after_json
    assert "gcode" not in event.after_json


@pytest.mark.asyncio
async def test_import_user_process_invalid_inheritance_is_flagged_but_stored(seam) -> None:
    ac, root, admin_id = seam
    await _login_admin(ac, admin_id)
    r = await ac.post(
        "/api/admin/profiles/library",
        **_upload(_fixture_bytes("user_process_invalid_inherit.json")),
    )
    assert r.status_code == 201, r.text  # flag, NOT hard-reject (AC-5)
    block = r.json()
    assert block["validation_state"] == "requires_attention"
    assert "user_process_invalid_inheritance" in block["reasons"]
    # It IS stored (the operator can see why + fix the source).
    assert profile_library.read_block(root, block["block_id"]) is not None


@pytest.mark.asyncio
async def test_import_filament_block_extracts_material_and_compat(seam) -> None:
    ac, _root, admin_id = seam
    await _login_admin(ac, admin_id)
    r = await ac.post(
        "/api/admin/profiles/library", **_upload(_fixture_bytes("user_filament_rosa_flex.json"))
    )
    assert r.status_code == 201, r.text
    block = r.json()
    assert block["profile_type"] == "filament"
    assert block["material_type"] == "TPU"
    assert block["compatible_printers"] == ["Creality K1 Max (0.4 nozzle)"]
    assert block["validation_state"] == "usable"
    # Leak fence: no raw Orca filament key on the DTO.
    for raw_key in ("nozzle_temperature", "filament_density", "filament_max_volumetric_speed"):
        assert raw_key not in block


@pytest.mark.asyncio
async def test_import_machine_block_with_explicit_type(seam) -> None:
    ac, _root, admin_id = seam
    await _login_admin(ac, admin_id)
    r = await ac.post(
        "/api/admin/profiles/library", **_upload(_fixture_bytes("system_machine_k1max.json"))
    )
    assert r.status_code == 201, r.text
    block = r.json()
    assert block["profile_type"] == "machine"
    assert block["is_system"] is True
    assert block["source"] == "system"


@pytest.mark.asyncio
async def test_reimport_same_block_is_upsert(seam) -> None:
    ac, _root, admin_id = seam
    await _login_admin(ac, admin_id)
    body = _fixture_bytes("user_process_tpu_flowtech.json")
    r1 = await ac.post("/api/admin/profiles/library", **_upload(body, portal_label="v1"))
    r2 = await ac.post("/api/admin/profiles/library", **_upload(body, portal_label="v2"))
    assert r1.json()["block_id"] == r2.json()["block_id"]
    listing = (await ac.get("/api/admin/profiles/library")).json()["blocks"]
    assert len(listing) == 1
    assert listing[0]["portal_label"] == "v2"


# === list / get / delete round-trip (AC-10, AC-11, AC-12) ======================


@pytest.mark.asyncio
async def test_list_empty_is_200_empty(seam) -> None:
    ac, _root, admin_id = seam
    await _login_admin(ac, admin_id)
    r = await ac.get("/api/admin/profiles/library")
    assert r.status_code == 200
    assert r.json() == {"blocks": []}


@pytest.mark.asyncio
async def test_list_orders_process_first_and_filters(seam) -> None:
    ac, _root, admin_id = seam
    await _login_admin(ac, admin_id)
    await ac.post(
        "/api/admin/profiles/library",
        **_upload(_fixture_bytes("user_machine_k1max_microswiss.json")),
    )
    await ac.post(
        "/api/admin/profiles/library", **_upload(_fixture_bytes("user_filament_rosa_flex.json"))
    )
    await ac.post(
        "/api/admin/profiles/library", **_upload(_fixture_bytes("user_process_tpu_flowtech.json"))
    )

    all_blocks = (await ac.get("/api/admin/profiles/library")).json()["blocks"]
    assert [b["profile_type"] for b in all_blocks] == ["process", "filament", "machine"]

    only = (await ac.get("/api/admin/profiles/library?profile_type=process")).json()["blocks"]
    assert [b["profile_type"] for b in only] == ["process"]


@pytest.mark.asyncio
async def test_get_block_detail_and_404(seam) -> None:
    ac, _root, admin_id = seam
    await _login_admin(ac, admin_id)
    created = (
        await ac.post(
            "/api/admin/profiles/library",
            **_upload(_fixture_bytes("user_process_tpu_flowtech.json")),
        )
    ).json()
    got = await ac.get(f"/api/admin/profiles/library/{created['block_id']}")
    assert got.status_code == 200
    assert got.json()["block_id"] == created["block_id"]

    missing = await ac.get(f"/api/admin/profiles/library/{'0' * 32}")
    assert missing.status_code == 404
    assert missing.json()["detail"]["reason_category"] == "not_found"

    bad = await ac.get("/api/admin/profiles/library/not-a-hex-id")
    assert bad.status_code == 404


@pytest.mark.asyncio
async def test_delete_block_204_then_404_and_audited(seam) -> None:
    ac, root, admin_id = seam
    await _login_admin(ac, admin_id)
    created = (
        await ac.post(
            "/api/admin/profiles/library",
            **_upload(_fixture_bytes("user_process_tpu_flowtech.json")),
        )
    ).json()
    block_id = created["block_id"]

    r = await ac.delete(f"/api/admin/profiles/library/{block_id}")
    assert r.status_code == 204
    assert profile_library.read_block(root, block_id) is None

    # Re-delete is an idempotent-safe 404, not a 500.
    assert (await ac.delete(f"/api/admin/profiles/library/{block_id}")).status_code == 404

    from app.core.db.session import get_engine

    with Session(get_engine()) as session:
        events = session.exec(
            select(AuditLog).where(AuditLog.action == "slicer_profile.library_delete")
        ).all()
    assert len(events) == 1
    assert events[0].entity_id == uuid.UUID(block_id)


@pytest.mark.asyncio
async def test_import_audit_failure_rolls_back(seam, monkeypatch) -> None:
    ac, root, admin_id = seam
    await _login_admin(ac, admin_id)
    before = _snapshot_library(root)

    def boom(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("app.modules.slicer.admin_router.record_event", boom)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        await ac.post(
            "/api/admin/profiles/library",
            **_upload(_fixture_bytes("user_process_tpu_flowtech.json")),
        )
    # Fresh import rolled back → library tree byte-identical, no temp leftover.
    assert _snapshot_library(root) == before
    assert not list((root / "library").rglob(".*tmp*")) if (root / "library").exists() else True
