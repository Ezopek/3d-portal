"""Story 35.1 — profile-selection policy model + store + precedence resolver.

Pure/standalone foundation slice of Epic E35 (Init 23). Tests the portal-owned
profile-selection policy: material normalization, the exact-override > material-default
> unavailable precedence, disabled-entry fall-through, the file-backed store
(roundtrip / missing-file / atomic / mtime-cache), and the pure profile-ref
validation seam. No resolver/API/worker coupling is exercised here.

[Source: epics.md § Initiative 23 / Story 35.1; SCP 2026-06-07 § Task 1]
"""

from __future__ import annotations

import json

import pytest

from app.modules.slicer.profile_policy import (
    EstimateProfileSource,
    FilamentOverride,
    MaterialDefault,
    ProfilePolicy,
    ProfilePolicyStore,
    normalize_material,
    unknown_profile_refs,
)

# A churn-stable Spoolman filament ref (vendor∥material∥name), built by the same
# unit-separator join overrides.spoolman_filament_ref() uses. Kept literal here so the
# test does not depend on the integer Spoolman id (NFR23-STABLE-KEY-1, AC-12).
_US = "\x1f"
PLA_MATT_REF = _US.join(("Fiberlogy", "PLA", "Fiberlogy PLA Matt"))
PLA_BASIC_REF = _US.join(("Rosa3D", "PLA", "Rosa3D PLA Starter Red"))


# --- AC-2: material normalization -------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" pla ", "PLA"),
        ("pla", "PLA"),
        ("PLA", "PLA"),
        ("  PetG\t", "PETG"),
        ("", None),
        ("   ", None),
        (None, None),
    ],
)
def test_normalize_material_trims_and_uppercases(raw: str | None, expected: str | None) -> None:
    assert normalize_material(raw) == expected


def test_normalize_material_does_not_invent_variants() -> None:
    # No alias coercion: "PLA+" stays "PLA+", it is NOT folded to "PLA".
    assert normalize_material(" pla+ ") == "PLA+"


# --- AC-1: source enum ------------------------------------------------------------


def test_estimate_profile_source_values() -> None:
    assert EstimateProfileSource.exact_filament_mapping == "exact_filament_mapping"
    assert EstimateProfileSource.default_material_profile == "default_material_profile"
    assert EstimateProfileSource.unavailable_no_profile == "unavailable_no_profile"
    assert {s.value for s in EstimateProfileSource} == {
        "exact_filament_mapping",
        "default_material_profile",
        "unavailable_no_profile",
    }


# --- AC-3/AC-4: models ------------------------------------------------------------


def test_models_forbid_extra_fields() -> None:
    with pytest.raises(ValueError):
        MaterialDefault(orca_filament_profile_ref="X", bogus=1)  # type: ignore[call-arg]
    with pytest.raises(ValueError):
        FilamentOverride(orca_filament_profile_ref="X", bogus=1)  # type: ignore[call-arg]


def test_policy_normalizes_material_default_keys() -> None:
    # AC-4: " pla " and "PLA" collapse to a single normalized "PLA" entry.
    policy = ProfilePolicy(
        material_defaults={" pla ": MaterialDefault(orca_filament_profile_ref="AI Generic PLA")},
    )
    assert "PLA" in policy.material_defaults
    assert " pla " not in policy.material_defaults


# --- AC-5..AC-9: precedence resolution --------------------------------------------


def _policy_with_default_and_override() -> ProfilePolicy:
    return ProfilePolicy(
        material_defaults={
            "PLA": MaterialDefault(orca_filament_profile_ref="AI Generic PLA"),
        },
        filament_overrides={
            PLA_MATT_REF: FilamentOverride(orca_filament_profile_ref="AI Fiberlogy PLA Matt"),
        },
    )


def test_exact_override_wins_over_material_default() -> None:
    policy = _policy_with_default_and_override()
    sel = policy.resolve_selection(material="PLA", spoolman_filament_ref=PLA_MATT_REF)
    assert sel.source == EstimateProfileSource.exact_filament_mapping
    assert sel.orca_filament_profile_ref == "AI Fiberlogy PLA Matt"
    assert sel.selected_spoolman_filament_ref == PLA_MATT_REF
    assert sel.selected_material == "PLA"


def test_material_default_used_when_no_override() -> None:
    policy = _policy_with_default_and_override()
    # A generic PLA color with no exact override resolves via the material default.
    sel = policy.resolve_selection(material=" pla ", spoolman_filament_ref=PLA_BASIC_REF)
    assert sel.source == EstimateProfileSource.default_material_profile
    assert sel.orca_filament_profile_ref == "AI Generic PLA"
    assert sel.selected_material == "PLA"
    # Not an exact mapping ⇒ no exact ref carried.
    assert sel.selected_spoolman_filament_ref is None


def test_material_default_used_when_no_filament_selected() -> None:
    policy = _policy_with_default_and_override()
    sel = policy.resolve_selection(material="PLA", spoolman_filament_ref=None)
    assert sel.source == EstimateProfileSource.default_material_profile
    assert sel.orca_filament_profile_ref == "AI Generic PLA"


def test_unavailable_when_no_override_and_no_default() -> None:
    policy = _policy_with_default_and_override()
    # ABS has neither an override nor a configured material default.
    sel = policy.resolve_selection(material="ABS", spoolman_filament_ref=None)
    assert sel.source == EstimateProfileSource.unavailable_no_profile
    assert sel.orca_filament_profile_ref is None
    assert sel.selected_material == "ABS"


def test_unavailable_when_material_unknown_none() -> None:
    policy = _policy_with_default_and_override()
    sel = policy.resolve_selection(material=None, spoolman_filament_ref=None)
    assert sel.source == EstimateProfileSource.unavailable_no_profile
    assert sel.orca_filament_profile_ref is None
    assert sel.selected_material is None


def test_disabled_override_falls_through_to_default() -> None:
    policy = ProfilePolicy(
        material_defaults={"PLA": MaterialDefault(orca_filament_profile_ref="AI Generic PLA")},
        filament_overrides={
            PLA_MATT_REF: FilamentOverride(
                orca_filament_profile_ref="AI Fiberlogy PLA Matt", enabled=False
            ),
        },
    )
    sel = policy.resolve_selection(material="PLA", spoolman_filament_ref=PLA_MATT_REF)
    assert sel.source == EstimateProfileSource.default_material_profile
    assert sel.orca_filament_profile_ref == "AI Generic PLA"
    assert sel.selected_spoolman_filament_ref is None


def test_disabled_material_default_is_unavailable() -> None:
    policy = ProfilePolicy(
        material_defaults={
            "PLA": MaterialDefault(orca_filament_profile_ref="AI Generic PLA", enabled=False)
        },
    )
    sel = policy.resolve_selection(material="PLA", spoolman_filament_ref=None)
    assert sel.source == EstimateProfileSource.unavailable_no_profile
    assert sel.orca_filament_profile_ref is None


def test_override_ref_not_in_policy_falls_through() -> None:
    policy = _policy_with_default_and_override()
    # A pinned ref with no override entry uses the material default, not unavailable.
    sel = policy.resolve_selection(material="PLA", spoolman_filament_ref=PLA_BASIC_REF)
    assert sel.source == EstimateProfileSource.default_material_profile


# --- AC-10/AC-11: store -----------------------------------------------------------


def test_store_load_missing_returns_empty_policy(tmp_path) -> None:
    store = ProfilePolicyStore(tmp_path)
    policy = store.load()
    assert isinstance(policy, ProfilePolicy)
    assert policy.material_defaults == {}
    assert policy.filament_overrides == {}


def test_store_save_then_load_roundtrip(tmp_path) -> None:
    store = ProfilePolicyStore(tmp_path)
    policy = _policy_with_default_and_override()
    store.save(policy)
    loaded = store.load()
    assert loaded == policy
    # Resolution behaves identically through a reload.
    sel = loaded.resolve_selection(material="PLA", spoolman_filament_ref=PLA_MATT_REF)
    assert sel.orca_filament_profile_ref == "AI Fiberlogy PLA Matt"


def test_store_save_is_atomic_no_temp_left(tmp_path) -> None:
    store = ProfilePolicyStore(tmp_path)
    store.save(_policy_with_default_and_override())
    # The published file exists and parses as JSON; no leftover temp/partial files remain.
    files = sorted(p.name for p in tmp_path.iterdir() if p.is_file())
    assert "profile_policy.json" in files
    assert all(".tmp" not in name for name in files)
    json.loads((tmp_path / "profile_policy.json").read_text(encoding="utf-8"))


def test_store_load_is_mtime_cached_and_reloads_after_save(tmp_path) -> None:
    store = ProfilePolicyStore(tmp_path)
    store.save(_policy_with_default_and_override())
    first = store.load()
    # Cached read returns an equal policy.
    assert store.load() == first
    # A subsequent save with new content is observed by a later load (mtime invalidation).
    new_policy = ProfilePolicy(
        material_defaults={"PETG": MaterialDefault(orca_filament_profile_ref="AI Generic PETG")},
    )
    store.save(new_policy)
    assert store.load() == new_policy


# --- AC-13: validation seam (no concrete Orca ref hard-coded) ---------------------


def test_unknown_profile_refs_flags_refs_absent_from_known_set() -> None:
    policy = _policy_with_default_and_override()
    known = {"AI Generic PLA"}  # the override ref is intentionally absent
    missing = unknown_profile_refs(policy, known)
    assert missing == {"AI Fiberlogy PLA Matt"}


def test_unknown_profile_refs_empty_when_all_known() -> None:
    policy = _policy_with_default_and_override()
    known = {"AI Generic PLA", "AI Fiberlogy PLA Matt"}
    assert unknown_profile_refs(policy, known) == set()
