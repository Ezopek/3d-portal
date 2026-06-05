"""Story 33.2 (PROFILE-ADMIN-2) — tests for the validated import/publish write path.

Unlike the 33.1 inventory tests (pure fakes), the write path is exercised end-to-end against
a REAL tmp vendored root seeded with the bench-derived fixture system tree, via production
wiring (settings point at the tmp dirs) — so atomic publish, the sidecar manifest, provenance
byte-stability, and the live resolve are all verified against real file I/O.

Covers: auth surface (403 member/agent, 401 anonymous — AC-1); route-enforcement gate green
without a ``_PUBLIC_ROUTES`` edit (AC-2); 413 over-cap (AC-4); incompatible-slot rejection
not-written + tree byte-identical (AC-5/AC-8); malformed-triple rejection (AC-6); structural
resolve-failure rejection (AC-7); successful compatible import + manifest + audit (AC-8/9/12);
provenance invariant (AC-11); end-to-end selector projection (AC-15).

G2: the successful import uses the REAL ``Rosa3D Flex 96A`` TPU·standard triple (the operator's
"Rosa Flex" direction), NOT a synthesized guess.
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
from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.import_service import manifest_path_for
from app.modules.slicer.models import PrintIntentPreset
from app.modules.slicer.overrides import NoopOverrideProvider
from app.modules.slicer.resolver import VendoredProfileSource, resolve
from app.modules.slicer.validation import NullCliValidator

FIXTURES = Path(__file__).parent / "fixtures" / "slicer"
PRINTER_REF = "creality-k1-max-microswiss-hf"
JWT_SECRET = "test"
ORCA_VERSION = "2.3.2"

TPU_PARTIALS = (FIXTURES / "intents" / PRINTER_REF / "TPU" / "standard.json").read_bytes()
PLA_PARTIALS = (FIXTURES / "intents" / PRINTER_REF / "PLA" / "standard.json").read_bytes()


def _intent(material_class: str, quality_tier: str) -> PrintIntentPreset:
    return PrintIntentPreset(
        name=f"{material_class} {quality_tier}",
        material_class=material_class,
        quality_tier=quality_tier,
        printer_ref=PRINTER_REF,
        spoolman_filament_ref=None,
    )


@pytest_asyncio.fixture
async def seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[AsyncClient, Path, uuid.UUID]]:
    """A real app wired at a tmp vendored root seeded with the fixture system tree.

    Yields (client, vendored_root, admin_user_id). The admin user is a REAL DB row so the
    import's audit write (actor_user_id FK) succeeds.
    """
    vendored_root = tmp_path / "vendored"
    bundle_store = tmp_path / "bundle-store"
    # Seed ONLY the real system tree + one pre-existing unrelated intent (PLA·standard, the
    # "slot B" of the provenance-stability test). The import target (TPU·standard) is absent.
    shutil.copytree(FIXTURES / "system", vendored_root / "system")
    pla_dir = vendored_root / "intents" / PRINTER_REF / "PLA"
    pla_dir.mkdir(parents=True)
    (pla_dir / "standard.json").write_bytes(PLA_PARTIALS)

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
    monkeypatch.setenv("TOTP_FERNET_KEY", "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM=")
    monkeypatch.setenv("SLICER_VENDORED_PROFILES_DIR", str(vendored_root))
    monkeypatch.setenv("SLICER_BUNDLE_STORE_DIR", str(bundle_store))
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


def _multipart(
    partials: bytes,
    material_class: str,
    quality_tier: str,
    *,
    filename: str = "triple.json",
    portal_label: str | None = None,
    printer_ref: str = PRINTER_REF,
) -> dict:
    data = {
        "printer_ref": printer_ref,
        "material_class": material_class,
        "quality_tier": quality_tier,
    }
    if portal_label is not None:
        data["portal_label"] = portal_label
    return {
        "files": {"file": (filename, partials, "application/json")},
        "data": data,
    }


def _snapshot_tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _bundle_hash(root: Path, intent: PrintIntentPreset, store_dir: Path) -> str:
    out = resolve(
        intent,
        source=VendoredProfileSource(root),
        store=BundleStore(store_dir),
        override_provider=NoopOverrideProvider(),
        validator=NullCliValidator(),
        orca_version=ORCA_VERSION,
    )
    return out.bundle.bundle_hash  # type: ignore[union-attr]


# === auth surface (AC-1, AC-2) ===============================================


@pytest.mark.asyncio
async def test_import_requires_admin_member_is_403(seam) -> None:
    ac, _root, _admin_id = seam
    ac.cookies.set("portal_access", _token("member"))
    r = await ac.post("/api/admin/profiles/import", **_multipart(TPU_PARTIALS, "TPU", "standard"))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_import_requires_admin_agent_is_403(seam) -> None:
    ac, _root, _admin_id = seam
    ac.cookies.set("portal_access", _token("agent"))
    r = await ac.post("/api/admin/profiles/import", **_multipart(TPU_PARTIALS, "TPU", "standard"))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_import_anonymous_is_401(seam) -> None:
    ac, _root, _admin_id = seam
    r = await ac.post("/api/admin/profiles/import", **_multipart(TPU_PARTIALS, "TPU", "standard"))
    assert r.status_code == 401


def test_import_route_not_in_public_allowlist() -> None:
    assert "/api/admin/profiles/import" not in _PUBLIC_ROUTES


# === size cap (AC-4) =========================================================


@pytest.mark.asyncio
async def test_import_over_cap_is_413(seam) -> None:
    ac, _root, admin_id = seam
    ac.cookies.set("portal_access", _token("admin", str(admin_id)))
    pad = b"x" * (1024 * 1024 + 16)
    oversized = b'{"machine":{},"process":{},"filament":{},"pad":"' + pad + b'"}'
    r = await ac.post("/api/admin/profiles/import", **_multipart(oversized, "PLA", "standard"))
    assert r.status_code == 413
    assert r.json()["detail"]["reason_category"] == "too_large"


# === incompatible-slot rejection, not written (AC-5, AC-8) ===================


@pytest.mark.asyncio
@pytest.mark.parametrize("tier", ["aesthetic", "strong"])
async def test_import_incompatible_tpu_slot_is_422_and_unwritten(seam, tier) -> None:
    ac, root, admin_id = seam
    ac.cookies.set("portal_access", _token("admin", str(admin_id)))
    before = _snapshot_tree(root)

    r = await ac.post("/api/admin/profiles/import", **_multipart(TPU_PARTIALS, "TPU", tier))
    assert r.status_code == 422
    assert r.json()["detail"]["reason_category"] == "incompatible_for_material"

    # AC-8: tree byte-identical, no temp leftover, no TPU intent created.
    assert _snapshot_tree(root) == before
    assert not list((root / "intents" / PRINTER_REF).glob("TPU/*"))
    assert not list(root.rglob(".*tmp*"))


# === malformed-triple rejection (AC-6) =======================================


@pytest.mark.asyncio
async def test_import_non_json_is_422_invalid_partial(seam) -> None:
    ac, root, admin_id = seam
    ac.cookies.set("portal_access", _token("admin", str(admin_id)))
    before = _snapshot_tree(root)
    r = await ac.post("/api/admin/profiles/import", **_multipart(b"not json{", "PLA", "standard"))
    assert r.status_code == 422
    assert r.json()["detail"]["reason_category"] == "invalid_partial"
    assert _snapshot_tree(root) == before


@pytest.mark.asyncio
async def test_import_missing_kind_is_422_invalid_partial(seam) -> None:
    ac, _root, admin_id = seam
    ac.cookies.set("portal_access", _token("admin", str(admin_id)))
    bad = json.dumps({"machine": {}, "process": {}}).encode()  # no filament
    r = await ac.post("/api/admin/profiles/import", **_multipart(bad, "PETG", "standard"))
    assert r.status_code == 422
    assert r.json()["detail"]["reason_category"] == "invalid_partial"


# === structural resolve-failure rejection (AC-7) =============================


@pytest.mark.asyncio
async def test_import_required_key_gap_is_422_classified(seam) -> None:
    ac, root, admin_id = seam
    ac.cookies.set("portal_access", _token("admin", str(admin_id)))
    # A TPU triple whose filament drops the required filament_max_volumetric_speed.
    broken = json.dumps(
        {
            "machine": {"inherit": "Creality K1 Max MicroSwiss HF"},
            "process": {"inherit": "0.20mm Standard"},
            "filament": {"inherit": "fdm_filament_common"},
        }
    ).encode()
    before = _snapshot_tree(root)
    r = await ac.post("/api/admin/profiles/import", **_multipart(broken, "TPU", "standard"))
    assert r.status_code == 422
    assert r.json()["detail"]["reason_category"] == "invalid_partial"
    assert _snapshot_tree(root) == before  # not written


@pytest.mark.asyncio
async def test_import_invalid_form_enum_is_422(seam) -> None:
    ac, _root, admin_id = seam
    ac.cookies.set("portal_access", _token("admin", str(admin_id)))
    r = await ac.post("/api/admin/profiles/import", **_multipart(TPU_PARTIALS, "NYLON", "standard"))
    assert r.status_code == 422  # FastAPI Literal validation


# === successful compatible import (AC-8, AC-9, AC-12) ========================


@pytest.mark.asyncio
async def test_import_success_publishes_manifest_audit_and_flips_offerable(seam) -> None:
    ac, root, admin_id = seam
    ac.cookies.set("portal_access", _token("admin", str(admin_id)))

    r = await ac.post(
        "/api/admin/profiles/import",
        **_multipart(TPU_PARTIALS, "TPU", "standard", portal_label="Rosa Flex 96A"),
    )
    assert r.status_code == 201, r.text
    slot = r.json()
    assert (slot["imported"], slot["resolvable"], slot["compatible"], slot["offerable"]) == (
        True,
        True,
        True,
        True,
    )
    assert slot["status"] == "offerable"
    assert slot["portal_label"] == "Rosa Flex 96A"
    assert slot["provenance"]["orca_version"] == ORCA_VERSION

    # Intent file published with the uploaded partials (JSON-equal; canonical formatting).
    intent_path = VendoredProfileSource(root).intent_path(_intent("TPU", "standard"))
    assert intent_path.exists()
    assert json.loads(intent_path.read_text()) == json.loads(TPU_PARTIALS)
    # And the published file re-resolves cleanly (round-trip through the real resolver).
    assert VendoredProfileSource(root).has_intent(_intent("TPU", "standard"))

    # Sidecar manifest written with importer / label / compat snapshot.
    manifest = json.loads(manifest_path_for(intent_path).read_text())
    assert manifest["manifest_version"] == "1"
    assert manifest["portal_label"] == "Rosa Flex 96A"
    assert manifest["imported_by"] == str(admin_id)
    assert manifest["status"] == "published"
    assert manifest["compatibility"] == {"compatible": True, "reason": None}
    assert manifest["original_filename"] == "triple.json"

    # Audit emitted with entity_type slicer_profile and a leak-fenced payload.
    from app.core.db.session import get_engine

    with Session(get_engine()) as session:
        events = session.exec(
            select(AuditLog).where(AuditLog.action == "slicer_profile.import")
        ).all()
    assert len(events) == 1
    assert events[0].entity_type == "slicer_profile"
    assert events[0].actor_user_id == admin_id
    after = json.loads(events[0].after_json)
    assert after["material_class"] == "TPU"
    assert after["quality_tier"] == "standard"
    # No Orca profile body / g-code in the audit payload (NFR21-OBS-1 fence).
    assert "machine" not in after
    assert "filament" not in after
    assert "gcode" not in events[0].after_json


@pytest.mark.asyncio
async def test_import_then_inventory_read_surfaces_offerable_with_label(seam) -> None:
    ac, _root, admin_id = seam
    ac.cookies.set("portal_access", _token("admin", str(admin_id)))
    await ac.post(
        "/api/admin/profiles/import",
        **_multipart(TPU_PARTIALS, "TPU", "standard", portal_label="Rosa Flex"),
    )

    inv = (await ac.get(f"/api/admin/profiles?printer_ref={PRINTER_REF}")).json()
    tpu_standard = next(
        s for s in inv["slots"] if s["material_class"] == "TPU" and s["quality_tier"] == "standard"
    )
    assert tpu_standard["offerable"] is True
    assert tpu_standard["portal_label"] == "Rosa Flex"  # AC-14 manifest surfacing


# === provenance invariant (AC-11) ============================================


@pytest.mark.asyncio
async def test_import_does_not_perturb_unrelated_bundle_hash(seam, tmp_path) -> None:
    ac, root, admin_id = seam
    ac.cookies.set("portal_access", _token("admin", str(admin_id)))
    slot_b = _intent("PLA", "standard")  # pre-seeded, unrelated to the TPU import

    before = _bundle_hash(root, slot_b, tmp_path / "hash-store-1")
    r = await ac.post("/api/admin/profiles/import", **_multipart(TPU_PARTIALS, "TPU", "standard"))
    assert r.status_code == 201, r.text
    after = _bundle_hash(root, slot_b, tmp_path / "hash-store-2")
    assert before == after, "import of slot A perturbed the bundle_hash of unrelated slot B"


@pytest.mark.asyncio
async def test_import_does_not_write_the_append_only_bundle_store(seam) -> None:
    ac, _root, admin_id = seam
    ac.cookies.set("portal_access", _token("admin", str(admin_id)))
    from app.core.config import get_settings

    store_dir = get_settings().slicer_bundle_store_dir
    r = await ac.post("/api/admin/profiles/import", **_multipart(TPU_PARTIALS, "TPU", "standard"))
    assert r.status_code == 201, r.text
    # The validation path uses a no-persist store → the append-only store stays empty.
    assert not (Path(store_dir) / "bundles").exists()
    assert not (Path(store_dir) / "snapshots").exists()


# === end-to-end selector invariant (AC-15) ===================================


@pytest.mark.asyncio
async def test_end_to_end_selector_projection_after_import(seam) -> None:
    ac, _root, admin_id = seam
    ac.cookies.set("portal_access", _token("admin", str(admin_id)))
    await ac.post("/api/admin/profiles/import", **_multipart(TPU_PARTIALS, "TPU", "standard"))

    inv = (await ac.get(f"/api/admin/profiles?printer_ref={PRINTER_REF}")).json()

    from app.modules.slicer.admin_router import member_selector_tiers
    from app.modules.slicer.compatibility import is_compatible
    from app.modules.slicer.schemas import AdminProfileSlot

    slots = [AdminProfileSlot.model_validate(s) for s in inv["slots"]]
    projection = member_selector_tiers(slots)

    # (a) the just-imported compatible slot is projected available.
    tpu = {e["quality_tier"]: e["available"] for e in projection.get("TPU", [])}
    assert tpu.get("standard") is True
    # (b) no incompatible (material, tier) is ever projected.
    for material, tiers in projection.items():
        for entry in tiers:
            assert is_compatible(material, entry["quality_tier"])
    # (c) every projected-available slot is genuinely offerable in the inventory.
    offerable = {(s.material_class, s.quality_tier) for s in slots if s.offerable}
    for material, tiers in projection.items():
        for entry in tiers:
            if entry["available"]:
                assert (material, entry["quality_tier"]) in offerable


# === printer_ref path-traversal guard (fallback-review Critical) =============


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_printer_ref",
    ["../../tmp/evil", "..", "/etc/evil", "a/b", "a\\b", ".hidden", "with space"],
)
async def test_import_rejects_traversal_printer_ref_without_writing(seam, bad_printer_ref) -> None:
    ac, root, admin_id = seam
    ac.cookies.set("portal_access", _token("admin", str(admin_id)))
    before = _snapshot_tree(root)

    r = await ac.post(
        "/api/admin/profiles/import",
        **_multipart(TPU_PARTIALS, "TPU", "standard", printer_ref=bad_printer_ref),
    )
    assert r.status_code == 422
    assert r.json()["detail"]["reason_category"] == "invalid_printer_ref"

    # Nothing written anywhere: the vendored tree is byte-identical and no temp leftover.
    assert _snapshot_tree(root) == before
    assert not list(root.rglob(".*tmp*"))


@pytest.mark.asyncio
async def test_import_traversal_does_not_write_outside_the_vendored_root(seam, tmp_path) -> None:
    # The classic escape: <root>/intents/../../<escape>/PLA/standard.json. Prove no file lands
    # at the escaped location and the tree is untouched.
    ac, root, admin_id = seam
    ac.cookies.set("portal_access", _token("admin", str(admin_id)))
    escape_marker = root.parent / "escape-marker"
    before = _snapshot_tree(root)

    r = await ac.post(
        "/api/admin/profiles/import",
        **_multipart(PLA_PARTIALS, "PLA", "standard", printer_ref="../escape-marker"),
    )
    assert r.status_code == 422
    assert r.json()["detail"]["reason_category"] == "invalid_printer_ref"
    assert not escape_marker.exists()
    assert _snapshot_tree(root) == before


@pytest.mark.asyncio
async def test_import_audit_failure_rolls_back_published_pair(seam, monkeypatch) -> None:
    """Codex review fix: audit failure must not leave an unaudited profile live on disk."""
    ac, root, admin_id = seam
    ac.cookies.set("portal_access", _token("admin", str(admin_id)))
    intent_path = VendoredProfileSource(root).intent_path(_intent("TPU", "standard"))
    manifest_path = manifest_path_for(intent_path)
    before = _snapshot_tree(root)

    def boom(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("app.modules.slicer.admin_router.record_event", boom)

    with pytest.raises(RuntimeError, match="audit unavailable"):
        await ac.post(
            "/api/admin/profiles/import",
            **_multipart(TPU_PARTIALS, "TPU", "standard", portal_label="Rosa Flex"),
        )
    assert _snapshot_tree(root) == before
    assert not intent_path.exists()
    assert not manifest_path.exists()
    assert not list(root.rglob(".*tmp*"))


@pytest.mark.asyncio
async def test_import_sanitizes_original_filename_for_manifest_and_audit(seam) -> None:
    """Codex review fix: multipart filename is attacker-controlled metadata, never raw."""
    ac, root, admin_id = seam
    ac.cookies.set("portal_access", _token("admin", str(admin_id)))
    weird_filename = "../../secret\\printer\x00profile.json"

    r = await ac.post(
        "/api/admin/profiles/import",
        **_multipart(TPU_PARTIALS, "TPU", "standard", filename=weird_filename),
    )
    assert r.status_code == 201, r.text

    intent_path = VendoredProfileSource(root).intent_path(_intent("TPU", "standard"))
    manifest = json.loads(manifest_path_for(intent_path).read_text())
    assert manifest["original_filename"] == "printer_profile.json"

    from app.core.db.session import get_engine

    with Session(get_engine()) as session:
        [event] = session.exec(
            select(AuditLog).where(AuditLog.action == "slicer_profile.import")
        ).all()
    after = json.loads(event.after_json)
    assert after["original_filename"] == "printer_profile.json"
    assert ".." not in event.after_json
    assert "secret" not in event.after_json
    assert "\\" not in event.after_json
