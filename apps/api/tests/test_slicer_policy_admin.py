"""Story 35.4 (POLICY-ADMIN-1, FR23-ADMIN-1) — admin policy management surface.

Tests the admin read + write endpoints for the portal's filament-profile-selection policy:
  - GET /api/admin/policy (AC-1/AC-2/AC-3)
  - PUT /api/admin/policy/material-defaults/{material} (AC-4/AC-6/AC-9/AC-10/AC-11/AC-12)
  - DELETE /api/admin/policy/material-defaults/{material} (AC-5/AC-12)
  - POST /api/admin/policy/filament-overrides (AC-7/AC-9/AC-10/AC-11/AC-12)
  - DELETE /api/admin/policy/filament-overrides (AC-8/AC-12)

All external dependencies (store, Spoolman snapshot, profile source) are faked so tests run
without real Redis, Spoolman, or a vendored profile tree on disk.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.auth.jwt import encode_token
from app.core.db.session import get_engine
from app.modules.slicer.profile_policy import (
    FilamentOverride,
    MaterialDefault,
    ProfilePolicy,
    ProfilePolicyStore,
)
from app.modules.spools.models import SpoolmanFilament, SpoolmanSnapshot

JWT_SECRET = "test-secret-not-real"  # matches conftest _isolated_db
SEEDED_ADMIN_EMAIL = "admin@localhost.localdomain"

# Churn-stable ref for the fixture filament: Bambu∥PLA∥Bambu PLA Basic
_US = "\x1f"
BAMBU_PLA_REF = _US.join(("Bambu", "PLA", "Bambu PLA Basic"))

# Fake profile names — the "known" vendored filament profile set
_KNOWN_PROFILES = {"Generic PLA", "Generic PETG"}


# === _FakeSource — protocol stub for VendoredProfileSource ==================


class _FakeSource:
    """Minimal stub that satisfies the system_tree() seam used by the policy admin routes."""

    def __init__(self, filament_profile_names: set[str] | None = None) -> None:
        self._names = filament_profile_names or _KNOWN_PROFILES

    def system_tree(self) -> dict[str, dict]:
        # Return minimal bodies that classify_profile() tags as "filament"
        return {name: {"filament_type": "PLA", "name": name} for name in self._names}


# === fixtures ================================================================


def _make_snapshot(filaments: list[SpoolmanFilament] | None = None) -> SpoolmanSnapshot:
    if filaments is None:
        filaments = [
            SpoolmanFilament(id=1, name="Bambu PLA Basic", vendor_name="Bambu", material="PLA")
        ]
    return SpoolmanSnapshot(
        spools=[], vendors=[], filaments=filaments, fetched_at=datetime.now(UTC)
    )


@pytest.fixture()
def client_with_policy(tmp_path, monkeypatch):
    """TestClient wired with fake store, snapshot, and profile source.

    Auth is NOT bypassed — callers set portal_access cookie using _admin_cookie().
    """
    from app.core.config import get_settings
    from app.main import create_app
    from app.modules.slicer.admin_router import (
        get_policy_profile_source,
        get_policy_store,
        get_snapshot,
    )

    get_settings.cache_clear()
    get_engine.cache_clear()

    policy_store = ProfilePolicyStore(tmp_path)
    fake_snap = _make_snapshot()
    fake_source = _FakeSource()

    app = create_app()
    app.dependency_overrides[get_policy_store] = lambda: policy_store
    app.dependency_overrides[get_snapshot] = lambda: fake_snap
    app.dependency_overrides[get_policy_profile_source] = lambda: fake_source

    with TestClient(app) as c:
        c.headers.update({"X-Portal-Client": "web"})
        yield c, policy_store

    app.dependency_overrides.clear()
    get_settings.cache_clear()
    get_engine.cache_clear()


@pytest.fixture()
def client_no_snapshot(tmp_path, monkeypatch):
    """Client where the Spoolman snapshot is unavailable (None) — AC-2 cold-cache path."""
    from app.core.config import get_settings
    from app.main import create_app
    from app.modules.slicer.admin_router import (
        get_policy_profile_source,
        get_policy_store,
        get_snapshot,
    )

    get_settings.cache_clear()
    get_engine.cache_clear()

    policy_store = ProfilePolicyStore(tmp_path)
    fake_source = _FakeSource()

    app = create_app()
    app.dependency_overrides[get_policy_store] = lambda: policy_store
    app.dependency_overrides[get_snapshot] = lambda: None  # cold-cache / Spoolman down
    app.dependency_overrides[get_policy_profile_source] = lambda: fake_source

    with TestClient(app) as c:
        c.headers.update({"X-Portal-Client": "web"})
        yield c

    app.dependency_overrides.clear()
    get_settings.cache_clear()
    get_engine.cache_clear()


def _admin_cookie() -> dict[str, str]:
    """Mint an admin JWT cookie using the seeded admin from _isolated_db."""
    with Session(get_engine()) as s:
        from app.core.db.models import User

        admin = s.exec(select(User).where(User.email == SEEDED_ADMIN_EMAIL)).first()
        assert admin is not None, "Seeded admin missing — conftest bootstrap regressed"
        admin_id = admin.id
    token = encode_token(subject=str(admin_id), role="admin", secret=JWT_SECRET, ttl_minutes=30)
    return {"portal_access": token}


# === AC-1/AC-3 — GET /api/admin/policy returns 200 with PolicyAdminView ======


def test_read_policy_returns_200_with_full_view(client_with_policy):
    c, _ = client_with_policy
    r = c.get("/api/admin/policy", cookies=_admin_cookie())
    assert r.status_code == 200, r.text
    body = r.json()
    assert "policy" in body
    assert "spoolman_materials" in body
    assert "spoolman_filaments" in body
    assert "orca_filament_profile_names" in body
    # orca_filament_profile_names is sorted from the FakeSource
    assert body["orca_filament_profile_names"] == sorted(_KNOWN_PROFILES)


def test_read_policy_projects_spoolman_materials(client_with_policy):
    c, _ = client_with_policy
    r = c.get("/api/admin/policy", cookies=_admin_cookie())
    assert r.status_code == 200
    materials = r.json()["spoolman_materials"]
    assert len(materials) == 1
    mat = materials[0]
    assert mat["material"] == "PLA"
    assert mat["configured"] is False  # no default configured yet
    assert mat["enabled"] is None


def test_read_policy_projects_spoolman_filaments(client_with_policy):
    c, _ = client_with_policy
    r = c.get("/api/admin/policy", cookies=_admin_cookie())
    assert r.status_code == 200
    filaments = r.json()["spoolman_filaments"]
    assert len(filaments) == 1
    fil = filaments[0]
    assert fil["ref"] == BAMBU_PLA_REF
    assert fil["name"] == "Bambu PLA Basic"
    assert fil["vendor_name"] == "Bambu"
    assert fil["material"] == "PLA"
    assert fil["has_override"] is False
    assert fil["override"] is None


def test_read_policy_no_leak_in_response(client_with_policy):
    c, _ = client_with_policy
    r = c.get("/api/admin/policy", cookies=_admin_cookie())
    assert r.status_code == 200
    body_str = r.text
    # No internal fields should appear
    for leaked in ("bundle_hash", "stl_hash", "gcode", "settings_ids"):
        assert leaked not in body_str


# === AC-2 — snapshot unavailable → 200 with empty lists =====================


def test_read_policy_snapshot_unavailable_returns_empty_lists(client_no_snapshot):
    c = client_no_snapshot
    r = c.get("/api/admin/policy", cookies=_admin_cookie())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["spoolman_materials"] == []
    assert body["spoolman_filaments"] == []
    # policy and orca names should still be present
    assert "policy" in body
    assert "orca_filament_profile_names" in body


# === AC-3 — unauthenticated → 401 ============================================


def test_read_policy_unauthenticated_is_401(client_with_policy):
    c, _ = client_with_policy
    r = c.get("/api/admin/policy")
    assert r.status_code == 401


def test_put_material_default_unauthenticated_is_401(client_with_policy):
    c, _ = client_with_policy
    r = c.put(
        "/api/admin/policy/material-defaults/PLA",
        json={"orca_filament_profile_ref": "Generic PLA"},
    )
    assert r.status_code == 401


def test_delete_material_default_unauthenticated_is_401(client_with_policy):
    c, _ = client_with_policy
    r = c.delete("/api/admin/policy/material-defaults/PLA")
    assert r.status_code == 401


def test_post_filament_override_unauthenticated_is_401(client_with_policy):
    c, _ = client_with_policy
    r = c.post(
        "/api/admin/policy/filament-overrides",
        json={"spoolman_filament_ref": BAMBU_PLA_REF, "orca_filament_profile_ref": "Generic PLA"},
    )
    assert r.status_code == 401


def test_delete_filament_override_unauthenticated_is_401(client_with_policy):
    c, _ = client_with_policy
    r = c.request(
        "DELETE",
        "/api/admin/policy/filament-overrides",
        content=json.dumps({"spoolman_filament_ref": BAMBU_PLA_REF}),
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 401


# === AC-4 — PUT material-defaults happy path / validation ====================


def test_put_material_default_happy_path_returns_200_with_view(client_with_policy):
    c, _store = client_with_policy
    r = c.put(
        "/api/admin/policy/material-defaults/PLA",
        json={"orca_filament_profile_ref": "Generic PLA", "enabled": True},
        cookies=_admin_cookie(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # The upserted default should be reflected in the response
    assert body["policy"]["material_defaults"]["PLA"]["orca_filament_profile_ref"] == "Generic PLA"
    assert body["policy"]["material_defaults"]["PLA"]["enabled"] is True


def test_put_material_default_normalizes_path_param(client_with_policy):
    c, _ = client_with_policy
    r = c.put(
        "/api/admin/policy/material-defaults/pla",  # lowercase input
        json={"orca_filament_profile_ref": "Generic PLA"},
        cookies=_admin_cookie(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Key must be normalized to uppercase
    assert "PLA" in body["policy"]["material_defaults"]
    assert "pla" not in body["policy"]["material_defaults"]


def test_put_material_default_empty_material_is_422(client_with_policy):
    c, _ = client_with_policy
    # Leading/trailing whitespace only collapses to blank after normalize_material
    r = c.put(
        "/api/admin/policy/material-defaults/   ",
        json={"orca_filament_profile_ref": "Generic PLA"},
        cookies=_admin_cookie(),
    )
    assert r.status_code == 422, r.text
    body = r.json()
    assert body["detail"]["reason_category"] == "invalid_material"


def test_put_material_default_unknown_profile_ref_is_422(client_with_policy):
    c, _ = client_with_policy
    r = c.put(
        "/api/admin/policy/material-defaults/PLA",
        json={"orca_filament_profile_ref": "NonExistent Profile XYZ"},
        cookies=_admin_cookie(),
    )
    assert r.status_code == 422, r.text
    body = r.json()
    assert body["detail"]["reason_category"] == "unknown_profile_ref"


# === AC-5 — DELETE material-defaults =========================================


def test_delete_material_default_204_on_remove(client_with_policy):
    c, store = client_with_policy
    # First add a default
    policy = ProfilePolicy(
        material_defaults={"PLA": MaterialDefault(orca_filament_profile_ref="Generic PLA")}
    )
    store.save(policy)

    r = c.delete("/api/admin/policy/material-defaults/PLA", cookies=_admin_cookie())
    assert r.status_code == 204, r.text

    # Verify it was removed
    loaded = store.load()
    assert "PLA" not in loaded.material_defaults


def test_delete_material_default_404_when_absent(client_with_policy):
    c, _ = client_with_policy
    r = c.delete("/api/admin/policy/material-defaults/NONEXISTENT", cookies=_admin_cookie())
    assert r.status_code == 404, r.text
    body = r.json()
    assert body["detail"]["reason_category"] == "not_found"


def test_delete_material_default_normalizes_path_param(client_with_policy):
    c, store = client_with_policy
    policy = ProfilePolicy(
        material_defaults={"PLA": MaterialDefault(orca_filament_profile_ref="Generic PLA")}
    )
    store.save(policy)

    r = c.delete("/api/admin/policy/material-defaults/pla", cookies=_admin_cookie())
    assert r.status_code == 204, r.text


# === AC-7 — POST filament-overrides happy path ================================


def test_post_filament_override_happy_path_returns_200(client_with_policy):
    c, _ = client_with_policy
    r = c.post(
        "/api/admin/policy/filament-overrides",
        json={
            "spoolman_filament_ref": BAMBU_PLA_REF,
            "orca_filament_profile_ref": "Generic PLA",
            "enabled": True,
        },
        cookies=_admin_cookie(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert BAMBU_PLA_REF in body["policy"]["filament_overrides"]
    override = body["policy"]["filament_overrides"][BAMBU_PLA_REF]
    assert override["orca_filament_profile_ref"] == "Generic PLA"


def test_post_filament_override_unknown_profile_ref_is_422(client_with_policy):
    c, _ = client_with_policy
    r = c.post(
        "/api/admin/policy/filament-overrides",
        json={
            "spoolman_filament_ref": BAMBU_PLA_REF,
            "orca_filament_profile_ref": "NonExistent Profile XYZ",
        },
        cookies=_admin_cookie(),
    )
    assert r.status_code == 422, r.text
    body = r.json()
    assert body["detail"]["reason_category"] == "unknown_profile_ref"


# === AC-8 — DELETE filament-overrides =========================================


def test_delete_filament_override_204_on_remove(client_with_policy):
    c, store = client_with_policy
    policy = ProfilePolicy(
        filament_overrides={
            BAMBU_PLA_REF: FilamentOverride(orca_filament_profile_ref="Generic PLA")
        }
    )
    store.save(policy)

    r = c.request(
        "DELETE",
        "/api/admin/policy/filament-overrides",
        content=json.dumps({"spoolman_filament_ref": BAMBU_PLA_REF}),
        headers={"Content-Type": "application/json"},
        cookies=_admin_cookie(),
    )
    assert r.status_code == 204, r.text

    loaded = store.load()
    assert BAMBU_PLA_REF not in loaded.filament_overrides


def test_delete_filament_override_404_when_absent(client_with_policy):
    c, _ = client_with_policy
    r = c.request(
        "DELETE",
        "/api/admin/policy/filament-overrides",
        content=json.dumps({"spoolman_filament_ref": "NonExistent\x1fRef\x1fFilament"}),
        headers={"Content-Type": "application/json"},
        cookies=_admin_cookie(),
    )
    assert r.status_code == 404, r.text
    body = r.json()
    assert body["detail"]["reason_category"] == "not_found"


# === AC-9 — unknown_profile_refs fires before save ===========================


def test_put_material_default_no_save_on_422(client_with_policy):
    c, store = client_with_policy
    # Ensure store is empty before the call
    initial_policy = store.load()
    assert initial_policy.material_defaults == {}

    r = c.put(
        "/api/admin/policy/material-defaults/PLA",
        json={"orca_filament_profile_ref": "BadProfile"},
        cookies=_admin_cookie(),
    )
    assert r.status_code == 422

    # Store must be unchanged (no partial save)
    reloaded = store.load()
    assert reloaded.material_defaults == {}


def test_post_filament_override_no_save_on_422(client_with_policy):
    c, store = client_with_policy
    initial_policy = store.load()
    assert initial_policy.filament_overrides == {}

    r = c.post(
        "/api/admin/policy/filament-overrides",
        json={"spoolman_filament_ref": BAMBU_PLA_REF, "orca_filament_profile_ref": "BadProfile"},
        cookies=_admin_cookie(),
    )
    assert r.status_code == 422

    reloaded = store.load()
    assert reloaded.filament_overrides == {}


# === AC-1 extended — configured=True and orca_ref reflected ==================


def test_read_policy_configured_true_when_enabled_default_exists(client_with_policy):
    """SpoolmanMaterialInfo.configured is True and orca_filament_profile_ref is populated
    when an enabled material default exists for that normalized material (AC-1)."""
    c, store = client_with_policy
    policy = ProfilePolicy(
        material_defaults={
            "PLA": MaterialDefault(orca_filament_profile_ref="Generic PLA", enabled=True)
        }
    )
    store.save(policy)

    r = c.get("/api/admin/policy", cookies=_admin_cookie())
    assert r.status_code == 200
    materials = r.json()["spoolman_materials"]
    assert len(materials) == 1
    mat = materials[0]
    assert mat["material"] == "PLA"
    assert mat["configured"] is True
    assert mat["enabled"] is True
    assert mat["orca_filament_profile_ref"] == "Generic PLA"


def test_read_policy_filament_has_override_true_when_override_exists(client_with_policy):
    """SpoolmanFilamentPolicyInfo.has_override is True and override is populated
    when a filament override exists for that ref (AC-1)."""
    c, store = client_with_policy
    policy = ProfilePolicy(
        filament_overrides={
            BAMBU_PLA_REF: FilamentOverride(orca_filament_profile_ref="Generic PLA")
        }
    )
    store.save(policy)

    r = c.get("/api/admin/policy", cookies=_admin_cookie())
    assert r.status_code == 200
    filaments = r.json()["spoolman_filaments"]
    assert len(filaments) == 1
    fil = filaments[0]
    assert fil["ref"] == BAMBU_PLA_REF
    assert fil["has_override"] is True
    assert fil["override"] is not None
    assert fil["override"]["orca_filament_profile_ref"] == "Generic PLA"


# === AC-4 — enabled=False upsert ==============================================


def test_put_material_default_enabled_false(client_with_policy):
    """PUT with enabled=False persists the disabled state and configured=False in view (AC-4)."""
    c, _ = client_with_policy
    r = c.put(
        "/api/admin/policy/material-defaults/PLA",
        json={"orca_filament_profile_ref": "Generic PLA", "enabled": False},
        cookies=_admin_cookie(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    default = body["policy"]["material_defaults"]["PLA"]
    assert default["enabled"] is False
    # configured is False when enabled=False (AC-1 definition)
    materials = body["spoolman_materials"]
    pla_mat = next((m for m in materials if m["material"] == "PLA"), None)
    assert pla_mat is not None
    assert pla_mat["configured"] is False
    assert pla_mat["enabled"] is False


# === AC-7 — enabled=False filament override ==================================


def test_post_filament_override_enabled_false(client_with_policy):
    """POST with enabled=False persists the disabled override (AC-7)."""
    c, _ = client_with_policy
    r = c.post(
        "/api/admin/policy/filament-overrides",
        json={
            "spoolman_filament_ref": BAMBU_PLA_REF,
            "orca_filament_profile_ref": "Generic PLA",
            "enabled": False,
        },
        cookies=_admin_cookie(),
    )
    assert r.status_code == 200, r.text
    override = r.json()["policy"]["filament_overrides"][BAMBU_PLA_REF]
    assert override["enabled"] is False


# === AC-12 — audit events written on mutations ================================


_RECORD_EVENT = "app.modules.slicer.admin_router.record_event"


def test_put_material_default_emits_audit_event(client_with_policy, monkeypatch):
    """record_event called with action=slicer_policy.material_default_upsert (AC-12)."""
    from unittest.mock import patch

    c, _ = client_with_policy
    calls: list[dict] = []
    with patch(_RECORD_EVENT, side_effect=lambda *a, **kw: calls.append(kw)):
        r = c.put(
            "/api/admin/policy/material-defaults/PLA",
            json={"orca_filament_profile_ref": "Generic PLA"},
            cookies=_admin_cookie(),
        )
    assert r.status_code == 200
    assert len(calls) == 1
    assert calls[0]["action"] == "slicer_policy.material_default_upsert"
    assert calls[0]["after"]["material_or_ref"] == "PLA"
    assert calls[0]["after"]["orca_filament_profile_ref"] == "Generic PLA"


def test_delete_material_default_emits_audit_event(client_with_policy):
    """record_event called with action=slicer_policy.material_default_delete (AC-12)."""
    from unittest.mock import patch

    c, store = client_with_policy
    store.save(
        ProfilePolicy(
            material_defaults={"PLA": MaterialDefault(orca_filament_profile_ref="Generic PLA")}
        )
    )

    calls: list[dict] = []
    with patch(_RECORD_EVENT, side_effect=lambda *a, **kw: calls.append(kw)):
        r = c.delete("/api/admin/policy/material-defaults/PLA", cookies=_admin_cookie())
    assert r.status_code == 204
    assert len(calls) == 1
    assert calls[0]["action"] == "slicer_policy.material_default_delete"
    assert calls[0]["after"]["material_or_ref"] == "PLA"


def test_post_filament_override_emits_audit_event(client_with_policy):
    """record_event called with action=slicer_policy.filament_override_upsert (AC-12)."""
    from unittest.mock import patch

    c, _ = client_with_policy
    calls: list[dict] = []
    with patch(_RECORD_EVENT, side_effect=lambda *a, **kw: calls.append(kw)):
        r = c.post(
            "/api/admin/policy/filament-overrides",
            json={
                "spoolman_filament_ref": BAMBU_PLA_REF,
                "orca_filament_profile_ref": "Generic PLA",
            },
            cookies=_admin_cookie(),
        )
    assert r.status_code == 200
    assert len(calls) == 1
    assert calls[0]["action"] == "slicer_policy.filament_override_upsert"
    assert calls[0]["after"]["material_or_ref"] == BAMBU_PLA_REF


def test_delete_filament_override_emits_audit_event(client_with_policy):
    """record_event called with action=slicer_policy.filament_override_delete (AC-12)."""
    from unittest.mock import patch

    c, store = client_with_policy
    store.save(
        ProfilePolicy(
            filament_overrides={
                BAMBU_PLA_REF: FilamentOverride(orca_filament_profile_ref="Generic PLA")
            }
        )
    )

    calls: list[dict] = []
    with patch(_RECORD_EVENT, side_effect=lambda *a, **kw: calls.append(kw)):
        r = c.request(
            "DELETE",
            "/api/admin/policy/filament-overrides",
            content=json.dumps({"spoolman_filament_ref": BAMBU_PLA_REF}),
            headers={"Content-Type": "application/json"},
            cookies=_admin_cookie(),
        )
    assert r.status_code == 204
    assert len(calls) == 1
    assert calls[0]["action"] == "slicer_policy.filament_override_delete"
    assert calls[0]["after"]["material_or_ref"] == BAMBU_PLA_REF


# === Story 35.6 — material-default change matrix hook (AC-10) ================


def test_put_material_default_matrix_hook_fires_on_new_entry(client_with_policy, monkeypatch, tmp_path):
    """AC-10 (35.6): adding a brand-new enabled material default triggers enumerate_matrix_cells."""
    enumerate_calls: list = []

    def _fake_enumerate(offers, policy):
        enumerate_calls.append((offers, policy))
        return []

    # _FakeSource has no `root` — add it temporarily so source.root works in the hook
    monkeypatch.setattr(_FakeSource, "root", tmp_path, raising=False)
    monkeypatch.setattr("app.modules.slicer.profile_offer.list_offers", lambda root: [])
    monkeypatch.setattr("app.modules.slicer.matrix_backfill.enumerate_matrix_cells", _fake_enumerate)

    c, _ = client_with_policy
    r = c.put(
        "/api/admin/policy/material-defaults/PLA",
        json={"orca_filament_profile_ref": "Generic PLA", "enabled": True},
        cookies=_admin_cookie(),
    )
    assert r.status_code == 200, r.text
    assert len(enumerate_calls) == 1, "enumerate_matrix_cells must be called for a new enabled default"


def test_put_material_default_matrix_hook_not_fired_when_ref_unchanged(client_with_policy, monkeypatch):
    """AC-10 (35.6): if the orca_filament_profile_ref is unchanged, hook does NOT fire."""
    enumerate_calls: list = []

    def _fake_enumerate(offers, policy):
        enumerate_calls.append((offers, policy))
        return []

    monkeypatch.setattr("app.modules.slicer.profile_offer.list_offers", lambda root: [])
    monkeypatch.setattr("app.modules.slicer.matrix_backfill.enumerate_matrix_cells", _fake_enumerate)

    c, store = client_with_policy
    # Pre-seed the default so the first PUT below has the same ref
    store.save(ProfilePolicy(
        material_defaults={"PETG": MaterialDefault(orca_filament_profile_ref="Generic PETG")},
    ))

    # PUT with the same ref — ref is unchanged, hook must NOT fire
    r = c.put(
        "/api/admin/policy/material-defaults/PETG",
        json={"orca_filament_profile_ref": "Generic PETG", "enabled": True},
        cookies=_admin_cookie(),
    )
    assert r.status_code == 200, r.text
    assert enumerate_calls == [], "enumerate_matrix_cells must NOT be called when ref is unchanged"


def test_put_material_default_matrix_hook_not_fired_when_disabled(client_with_policy, monkeypatch):
    """AC-10 (35.6): a disabled material default does NOT trigger the matrix hook."""
    enumerate_calls: list = []

    def _fake_enumerate(offers, policy):
        enumerate_calls.append((offers, policy))
        return []

    monkeypatch.setattr("app.modules.slicer.profile_offer.list_offers", lambda root: [])
    monkeypatch.setattr("app.modules.slicer.matrix_backfill.enumerate_matrix_cells", _fake_enumerate)

    c, _ = client_with_policy
    r = c.put(
        "/api/admin/policy/material-defaults/TPU",
        json={"orca_filament_profile_ref": "Generic PLA", "enabled": False},
        cookies=_admin_cookie(),
    )
    assert r.status_code == 200, r.text
    assert enumerate_calls == [], "enumerate_matrix_cells must NOT be called for a disabled default"


def test_put_material_default_matrix_hook_exception_does_not_prevent_200(client_with_policy, monkeypatch):
    """AC-10 (35.6): a hook exception is swallowed — the policy save and 200 response succeed."""
    def _raise(*args, **kwargs):
        raise RuntimeError("matrix hook exploded")

    monkeypatch.setattr("app.modules.slicer.matrix_backfill.enumerate_matrix_cells", _raise)
    monkeypatch.setattr("app.modules.slicer.profile_offer.list_offers", lambda root: [{"dummy": True}])

    c, _ = client_with_policy
    r = c.put(
        "/api/admin/policy/material-defaults/PLA",
        json={"orca_filament_profile_ref": "Generic PLA", "enabled": True},
        cookies=_admin_cookie(),
    )
    assert r.status_code == 200, r.text
