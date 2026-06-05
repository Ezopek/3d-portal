"""Story 33.1 (PROFILE-ADMIN-1) — tests for the read-only admin profile inventory.

Covers: auth surface (403 member/agent, 401 anonymous — AC-1); route-enforcement gate
green without a ``_PUBLIC_ROUTES`` edit (AC-2); the per-slot DTO + status precedence for
all four statuses (AC-3/AC-4); the import-vs-resolve distinction (AC-5); resolvability
parity with ``GET /api/estimates/quality-tiers`` (AC-6); incompatible-is-never-offerable
+ the selector projection excluding incompatible slots (AC-8); the provenance no-leak
fence (AC-9). The fake resolver + fake source let every status be exercised
deterministically without a real vendored tree on disk.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import MagicMock

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.auth.jwt import encode_token
from app.main import _PUBLIC_ROUTES, create_app
from app.modules.slicer.admin_router import (
    NOT_IMPORTED_REASON,
    NOT_RESOLVABLE_REASON,
    build_slot,
    derive_status_and_reason,
    get_admin_profile_resolver,
    get_profile_inventory_source,
    member_selector_tiers,
)
from app.modules.slicer.compatibility import INCOMPATIBLE_REASON, is_compatible
from app.modules.slicer.estimate_read import PresetResolveError, ResolvedPreset
from app.modules.slicer.models import PrintIntentPreset
from app.modules.slicer.router import QUALITY_TIER_ORDER, get_estimate_resolver
from app.modules.slicer.schemas import AdminProfileProvenance, AdminProfileSlot

PRINTER_REF = "creality-k1-max-microswiss-hf"
JWT_SECRET = "test"
TREE_HASH = "treehash0123456789"

# Allowlisted top-level slot field set (AC-9). Any extra field is a leak.
_ALLOWED_SLOT_FIELDS = frozenset(
    {
        "material_class",
        "quality_tier",
        "imported",
        "resolvable",
        "compatible",
        "offerable",
        "status",
        "reason",
        "portal_label",
        "provenance",
    }
)
_ALLOWED_PROVENANCE_FIELDS = frozenset({"source_system_tree_hash", "orca_version"})
# Substrings that would betray an Orca-internal / path / g-code leak in the serialized body.
_FORBIDDEN_SUBSTRINGS = (
    "/intents/",
    "/system/",
    ".json",
    "gcode",
    "g-code",
    "settings_id",
    "bundle_hash",
    "snapshot_hash",
    "source_user_partial",
    "filament_max_volumetric_speed",
    "nozzle_temperature",
)


# === fakes ===================================================================


class _FakeResolver:
    """Injected resolver: resolves every intent EXCEPT the configured failing slots."""

    def __init__(self) -> None:
        self.fail_slots: set[tuple[str, str]] = set()
        self.seen: list[PrintIntentPreset] = []

    async def resolve_preset(self, intent: PrintIntentPreset) -> ResolvedPreset:
        self.seen.append(intent)
        if (intent.material_class, intent.quality_tier) in self.fail_slots:
            raise PresetResolveError("profile_not_imported")
        return ResolvedPreset(bundle_hash="bh", pinned_filament=None)


class _FakeSource:
    """Injected source: controllable file-presence + a fixed provenance tree hash."""

    def __init__(self) -> None:
        self.imported_slots: set[tuple[str, str]] = set()
        # Story 33.2 (AC-14): controllable manifest labels per slot (default: none).
        self.manifest_labels: dict[tuple[str, str], str] = {}

    def has_intent(self, intent: PrintIntentPreset) -> bool:
        return (intent.material_class, intent.quality_tier) in self.imported_slots

    def system_tree_hash(self) -> str:
        return TREE_HASH

    def manifest_label(self, intent: PrintIntentPreset) -> str | None:
        return self.manifest_labels.get((intent.material_class, intent.quality_tier))


# === fixture =================================================================


@pytest_asyncio.fixture
async def seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[AsyncClient, _FakeResolver, _FakeSource]]:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
    monkeypatch.setenv("TOTP_FERNET_KEY", "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM=")

    from app.core.config import get_settings
    from app.core.db.session import get_engine, init_schema

    get_settings.cache_clear()
    get_engine.cache_clear()

    app = create_app()
    init_schema(get_engine())

    fake_redis = fakeredis.aioredis.FakeRedis()
    factory = MagicMock()
    factory.get = MagicMock(return_value=fake_redis)

    async def _aclose() -> None:
        return None

    factory.aclose = _aclose
    app.state.redis = factory

    resolver = _FakeResolver()
    source = _FakeSource()
    app.dependency_overrides[get_admin_profile_resolver] = lambda: resolver
    app.dependency_overrides[get_estimate_resolver] = lambda: resolver
    app.dependency_overrides[get_profile_inventory_source] = lambda: source

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"X-Portal-Client": "web"},
    ) as ac:
        yield ac, resolver, source

    app.dependency_overrides.clear()
    get_settings.cache_clear()
    get_engine.cache_clear()


def _token(role: str) -> str:
    return encode_token(subject=str(uuid.uuid4()), role=role, secret=JWT_SECRET, ttl_minutes=30)


def _inventory_url(printer_ref: str = PRINTER_REF) -> str:
    return f"/api/admin/profiles?printer_ref={printer_ref}"


def _slot(body: dict, material: str, tier: str) -> dict:
    for slot in body["slots"]:
        if slot["material_class"] == material and slot["quality_tier"] == tier:
            return slot
    raise AssertionError(f"slot {material}/{tier} missing from inventory")


# === pure unit tests (no HTTP) ===============================================


def test_derive_status_precedence_incompatible_wins_over_everything() -> None:
    # Incompatible is evaluated first and independently — even a fully imported+resolvable
    # slot reads incompatible when its compatibility is false (AC-4).
    assert derive_status_and_reason(compatible=False, imported=True, resolvable=True) == (
        "incompatible",
        INCOMPATIBLE_REASON,
    )


def test_derive_status_precedence_orders_the_three_compatible_states() -> None:
    assert derive_status_and_reason(compatible=True, imported=False, resolvable=True) == (
        "not_imported",
        NOT_IMPORTED_REASON,
    )
    assert derive_status_and_reason(compatible=True, imported=True, resolvable=False) == (
        "not_resolvable",
        NOT_RESOLVABLE_REASON,
    )
    assert derive_status_and_reason(compatible=True, imported=True, resolvable=True) == (
        "offerable",
        None,
    )


def test_build_slot_resolvable_incompatible_is_not_offerable() -> None:
    # The TPU worked example: a slot that imports + resolves but is structurally
    # incompatible is NEVER offerable (AC-4).
    incompatible = next(
        (m, t)
        for m in ("PLA", "PETG", "PCTG", "TPU")
        for t in QUALITY_TIER_ORDER
        if not is_compatible(m, t)
    )
    slot = build_slot(
        incompatible[0],
        incompatible[1],
        imported=True,
        resolvable=True,
        provenance=AdminProfileProvenance(),
    )
    assert slot.compatible is False
    assert slot.offerable is False
    assert slot.status == "incompatible"
    assert slot.reason == INCOMPATIBLE_REASON


def test_member_selector_projection_never_surfaces_incompatible() -> None:
    # AC-8: build the full grid with every slot imported+resolvable, then assert the
    # member-selector projection HIDES every incompatible (material, tier) — the structural
    # guard that the member selector and admin grid cannot drift.
    slots: list[AdminProfileSlot] = [
        build_slot(m, t, imported=True, resolvable=True, provenance=AdminProfileProvenance())
        for m in ("PLA", "PETG", "PCTG", "TPU")
        for t in QUALITY_TIER_ORDER
    ]
    projection = member_selector_tiers(slots)
    for material, tiers in projection.items():
        for entry in tiers:
            assert is_compatible(material, entry["quality_tier"]), (
                f"projection surfaced incompatible {material}/{entry['quality_tier']}"
            )
    # And every incompatible slot is genuinely absent (hidden, not merely unavailable).
    for slot in slots:
        if not slot.compatible:
            surfaced = {e["quality_tier"] for e in projection.get(slot.material_class, [])}
            assert slot.quality_tier not in surfaced


# === auth surface (AC-1, AC-2) ===============================================


@pytest.mark.asyncio
async def test_inventory_requires_admin_member_is_403(seam) -> None:
    ac, _resolver, _source = seam
    ac.cookies.set("portal_access", _token("member"))
    r = await ac.get(_inventory_url())
    assert r.status_code == 403
    assert r.json()["detail"] == "admin_required"


@pytest.mark.asyncio
async def test_inventory_requires_admin_agent_is_403(seam) -> None:
    ac, _resolver, _source = seam
    ac.cookies.set("portal_access", _token("agent"))
    r = await ac.get(_inventory_url())
    assert r.status_code == 403
    assert r.json()["detail"] == "admin_required"


@pytest.mark.asyncio
async def test_inventory_anonymous_is_401(seam) -> None:
    ac, _resolver, _source = seam
    r = await ac.get(_inventory_url())
    assert r.status_code == 401


def test_inventory_route_not_in_public_allowlist() -> None:
    # AC-2: the admin gate (not an allowlist entry) is what keeps the route private.
    assert "/api/admin/profiles" not in _PUBLIC_ROUTES


# === DTO shape, precedence, import-vs-resolve (AC-3, AC-4, AC-5) ==============


@pytest.mark.asyncio
async def test_inventory_enumerates_full_grid_with_all_four_statuses(seam) -> None:
    ac, resolver, source = seam
    # offerable: PLA/standard (imported + resolvable + compatible)
    # not_imported: PLA/aesthetic (not imported)
    # not_resolvable: PLA/strong (imported + present-but-malformed → resolve fails)
    # incompatible: TPU/aesthetic (structurally invalid — compat map placeholder)
    source.imported_slots = {("PLA", "standard"), ("PLA", "strong")}
    resolver.fail_slots = {("PLA", "strong")}
    ac.cookies.set("portal_access", _token("admin"))

    r = await ac.get(_inventory_url())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["printer_ref"] == PRINTER_REF
    # Full 4x3 grid enumerated.
    assert len(body["slots"]) == 4 * len(QUALITY_TIER_ORDER)

    offerable = _slot(body, "PLA", "standard")
    assert offerable["status"] == "offerable"
    assert offerable["offerable"] is True
    assert offerable["reason"] is None
    assert (offerable["imported"], offerable["resolvable"], offerable["compatible"]) == (
        True,
        True,
        True,
    )

    not_imported = _slot(body, "PLA", "aesthetic")
    assert not_imported["status"] == "not_imported"
    assert not_imported["imported"] is False
    assert not_imported["reason"] == NOT_IMPORTED_REASON
    assert not_imported["offerable"] is False

    # AC-5: present-but-unresolvable → imported True, resolvable False (distinct dimensions).
    not_resolvable = _slot(body, "PLA", "strong")
    assert not_resolvable["status"] == "not_resolvable"
    assert not_resolvable["imported"] is True
    assert not_resolvable["resolvable"] is False
    assert not_resolvable["reason"] == NOT_RESOLVABLE_REASON
    assert not_resolvable["offerable"] is False

    incompatible = _slot(body, "TPU", "aesthetic")
    assert incompatible["status"] == "incompatible"
    assert incompatible["compatible"] is False
    assert incompatible["offerable"] is False
    assert incompatible["reason"] == INCOMPATIBLE_REASON


@pytest.mark.asyncio
async def test_inventory_provenance_only_on_resolvable_slots(seam) -> None:
    ac, resolver, source = seam
    source.imported_slots = {("PLA", "standard")}
    resolver.fail_slots = {("PLA", "aesthetic")}
    ac.cookies.set("portal_access", _token("admin"))

    body = (await ac.get(_inventory_url())).json()

    resolvable_slot = _slot(body, "PLA", "standard")
    assert resolvable_slot["provenance"]["source_system_tree_hash"] == TREE_HASH
    assert isinstance(resolvable_slot["provenance"]["orca_version"], str)

    unresolvable_slot = _slot(body, "PLA", "aesthetic")
    assert unresolvable_slot["provenance"]["source_system_tree_hash"] is None
    assert unresolvable_slot["provenance"]["orca_version"] is None


# === resolvability parity with quality-tiers (AC-6) ==========================


@pytest.mark.asyncio
async def test_resolvability_parity_with_quality_tiers(seam) -> None:
    """AC-6: the inventory's ``resolvable`` agrees with quality-tiers ``available`` for
    every slot, because both consume the identical injected resolve seam."""
    ac, resolver, _source = seam
    resolver.fail_slots = {("PLA", "aesthetic"), ("PLA", "strong")}
    ac.cookies.set("portal_access", _token("admin"))

    inv = (await ac.get(_inventory_url())).json()
    qt = (
        await ac.get(f"/api/estimates/quality-tiers?material_class=PLA&printer_ref={PRINTER_REF}")
    ).json()

    available_by_tier = {t["quality_tier"]: t["available"] for t in qt["tiers"]}
    for tier in QUALITY_TIER_ORDER:
        inv_resolvable = _slot(inv, "PLA", tier)["resolvable"]
        assert inv_resolvable == available_by_tier[tier], (
            f"resolvable/available drift on PLA/{tier}"
        )


# === no-internal-leak fence (AC-9) ===========================================


@pytest.mark.asyncio
async def test_inventory_response_has_no_internal_leak(seam) -> None:
    ac, _resolver, source = seam
    source.imported_slots = {("PLA", "standard")}
    ac.cookies.set("portal_access", _token("admin"))

    response = await ac.get(_inventory_url())
    body = response.json()

    for slot in body["slots"]:
        assert set(slot) <= _ALLOWED_SLOT_FIELDS, (
            f"leaked field(s): {set(slot) - _ALLOWED_SLOT_FIELDS}"
        )
        assert set(slot["provenance"]) <= _ALLOWED_PROVENANCE_FIELDS

    raw = response.text.lower()
    for needle in _FORBIDDEN_SUBSTRINGS:
        assert needle not in raw, f"response leaked forbidden substring: {needle!r}"
