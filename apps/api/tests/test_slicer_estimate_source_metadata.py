"""Story 35.3 — pure-unit tests for the DTO / helper layer (AC-2, AC-13).

Scope:
- ``ProfileSelectionContextView``: field set + ``extra="forbid"`` no-leak assertion (AC-2).
- ``build_profile_selection_context`` pure function: all four input cases (AC-13).
- ``UnavailableProfileError``: carries ``profile_selection`` + ``selected_filament_name``.

No HTTP, no store, no Spoolman, no Orca — pure model/function tests that run without any
fixture scaffolding.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.slicer.profile_policy import EstimateProfileSource, ProfileSelection
from app.modules.slicer.schemas import ProfileSelectionContextView

# === AC-2 — ProfileSelectionContextView field set + no-leak ====================


def test_profile_selection_context_view_exact_fields():
    """ProfileSelectionContextView has EXACTLY the five specified fields (AC-2)."""
    expected = {
        "estimate_profile_source",
        "selected_material",
        "selected_spoolman_filament_ref",
        "selected_filament_name",
        "orca_filament_profile_name",
    }
    assert set(ProfileSelectionContextView.model_fields) == expected


def test_profile_selection_context_view_extra_forbid():
    """``extra="forbid"`` — an unexpected field is a ValidationError (AC-2 negative assertion)."""
    with pytest.raises(ValidationError):
        ProfileSelectionContextView(
            estimate_profile_source=EstimateProfileSource.unavailable_no_profile,
            selected_material=None,
            selected_spoolman_filament_ref=None,
            selected_filament_name=None,
            orca_filament_profile_name=None,
            bundle_hash="leak",  # internal field must not survive extra="forbid"
        )


def test_profile_selection_context_view_no_internal_fields():
    """No internal fields (bundle_hash, settings_ids, etc.) present on the model (AC-2)."""
    leak_fields = {
        "bundle_hash",
        "settings_ids",
        "stl_hash",
        "gcode",
        "orca_filament_profile_ref",  # internal ref name — exposed as _name instead
    }
    assert leak_fields.isdisjoint(ProfileSelectionContextView.model_fields)


def test_profile_selection_context_view_constructs_exact_filament_mapping():
    ctx = ProfileSelectionContextView(
        estimate_profile_source=EstimateProfileSource.exact_filament_mapping,
        selected_material="PLA",
        selected_spoolman_filament_ref="Bambu Lab\x1fPLA\x1fSpeed White",
        selected_filament_name="Speed White",
        orca_filament_profile_name="Bambu PLA Basic @BBL A1M 0.4 nozzle",
    )
    assert ctx.estimate_profile_source == EstimateProfileSource.exact_filament_mapping
    assert ctx.selected_material == "PLA"
    assert ctx.selected_spoolman_filament_ref == "Bambu Lab\x1fPLA\x1fSpeed White"
    assert ctx.selected_filament_name == "Speed White"
    assert ctx.orca_filament_profile_name == "Bambu PLA Basic @BBL A1M 0.4 nozzle"


def test_profile_selection_context_view_constructs_unavailable():
    ctx = ProfileSelectionContextView(
        estimate_profile_source=EstimateProfileSource.unavailable_no_profile,
        selected_material=None,
        selected_spoolman_filament_ref=None,
        selected_filament_name=None,
        orca_filament_profile_name=None,
    )
    assert ctx.estimate_profile_source == EstimateProfileSource.unavailable_no_profile
    assert ctx.orca_filament_profile_name is None


# === AC-13 — build_profile_selection_context pure function =====================


def test_build_profile_selection_context_none_input_returns_none():
    """``profile_selection=None`` → ``None`` (the no-filament path, AC-13)."""
    from app.modules.slicer.estimate_read import build_profile_selection_context

    result = build_profile_selection_context(None)
    assert result is None


def test_build_profile_selection_context_unavailable_no_profile():
    """unavailable_no_profile → correct view with all None numerics (AC-13)."""
    from app.modules.slicer.estimate_read import build_profile_selection_context

    selection = ProfileSelection(
        source=EstimateProfileSource.unavailable_no_profile,
        orca_filament_profile_ref=None,
        selected_material=None,
        selected_spoolman_filament_ref=None,
    )
    ctx = build_profile_selection_context(selection, selected_filament_name="Mystery Filament")
    assert ctx is not None
    assert ctx.estimate_profile_source == EstimateProfileSource.unavailable_no_profile
    assert ctx.orca_filament_profile_name is None
    assert ctx.selected_material is None
    assert ctx.selected_spoolman_filament_ref is None
    assert ctx.selected_filament_name == "Mystery Filament"


def test_build_profile_selection_context_exact_filament_mapping():
    """exact_filament_mapping → all fields populated (AC-13)."""
    from app.modules.slicer.estimate_read import build_profile_selection_context

    selection = ProfileSelection(
        source=EstimateProfileSource.exact_filament_mapping,
        orca_filament_profile_ref="Bambu PLA Basic @BBL A1M 0.4 nozzle",
        selected_material="PLA",
        selected_spoolman_filament_ref="Bambu Lab\x1fPLA\x1fSpeed White",
    )
    ctx = build_profile_selection_context(selection, selected_filament_name="Speed White")
    assert ctx is not None
    assert ctx.estimate_profile_source == EstimateProfileSource.exact_filament_mapping
    assert ctx.selected_material == "PLA"
    assert ctx.selected_spoolman_filament_ref == "Bambu Lab\x1fPLA\x1fSpeed White"
    assert ctx.selected_filament_name == "Speed White"
    assert ctx.orca_filament_profile_name == "Bambu PLA Basic @BBL A1M 0.4 nozzle"


def test_build_profile_selection_context_default_material_profile():
    """default_material_profile → selected_spoolman_filament_ref is None (AC-13, AC-8)."""
    from app.modules.slicer.estimate_read import build_profile_selection_context

    selection = ProfileSelection(
        source=EstimateProfileSource.default_material_profile,
        orca_filament_profile_ref="Generic PLA @BBL A1M 0.4 nozzle",
        selected_material="PLA",
        selected_spoolman_filament_ref=None,  # default is per-material, not per-filament
    )
    ctx = build_profile_selection_context(selection, selected_filament_name="Some Filament")
    assert ctx is not None
    assert ctx.estimate_profile_source == EstimateProfileSource.default_material_profile
    assert ctx.selected_spoolman_filament_ref is None
    assert ctx.selected_material == "PLA"
    assert ctx.selected_filament_name == "Some Filament"
    assert ctx.orca_filament_profile_name == "Generic PLA @BBL A1M 0.4 nozzle"


def test_build_profile_selection_context_no_filament_name():
    """selected_filament_name defaults to None (AC-13)."""
    from app.modules.slicer.estimate_read import build_profile_selection_context

    selection = ProfileSelection(
        source=EstimateProfileSource.default_material_profile,
        orca_filament_profile_ref="Generic PLA @BBL A1M 0.4 nozzle",
        selected_material="PLA",
        selected_spoolman_filament_ref=None,
    )
    ctx = build_profile_selection_context(selection)
    assert ctx is not None
    assert ctx.selected_filament_name is None


# === UnavailableProfileError carries its payload ================================


def test_unavailable_profile_error_carries_payload():
    """UnavailableProfileError carries profile_selection + selected_filament_name."""
    from app.modules.slicer.estimate_read import UnavailableProfileError

    selection = ProfileSelection(
        source=EstimateProfileSource.unavailable_no_profile,
        orca_filament_profile_ref=None,
        selected_material=None,
        selected_spoolman_filament_ref=None,
    )
    exc = UnavailableProfileError(
        profile_selection=selection,
        selected_filament_name="Test Filament",
    )
    assert exc.profile_selection is selection
    assert exc.selected_filament_name == "Test Filament"


def test_unavailable_profile_error_none_filament_name():
    """selected_filament_name may be None (filament not found in snapshot)."""
    from app.modules.slicer.estimate_read import UnavailableProfileError

    selection = ProfileSelection(
        source=EstimateProfileSource.unavailable_no_profile,
        orca_filament_profile_ref=None,
        selected_material=None,
        selected_spoolman_filament_ref=None,
    )
    exc = UnavailableProfileError(profile_selection=selection, selected_filament_name=None)
    assert exc.selected_filament_name is None


# === SettingsEstimateResolver fallback integration ==============================


@pytest.mark.asyncio
async def test_35_3_settings_resolver_uses_fallback_material_when_spoolman_down(monkeypatch):
    """SettingsEstimateResolver uses intent.material_class as fallback when Spoolman is down."""
    from app.modules.slicer.estimate_read import SettingsEstimateResolver
    from app.modules.slicer.models import (
        PrintIntentPreset,
        ResolvedTriple,
        ResolveSuccess,
        SlicerProfileBundle,
    )
    from app.modules.slicer.profile_policy import (
        EstimateProfileSource,
        MaterialDefault,
        ProfilePolicy,
    )

    # Mock policy with a default for PLA
    policy = ProfilePolicy(
        material_defaults={"PLA": MaterialDefault(orca_filament_profile_ref="Generic PLA")}
    )
    monkeypatch.setattr(
        "app.modules.slicer.profile_policy.ProfilePolicyStore.load", lambda self: policy
    )

    # Mock _filaments_by_ref to simulate Spoolman down/empty snapshot
    async def mock_filaments_by_ref(self):
        return {}

    monkeypatch.setattr(SettingsEstimateResolver, "_filaments_by_ref", mock_filaments_by_ref)

    # Mock resolve to avoid filesystem hits for vendored profiles
    mock_bundle = SlicerProfileBundle.model_construct(bundle_hash="fake-hash")
    mock_triple = ResolvedTriple.model_construct(machine={}, process={}, filament={})
    monkeypatch.setattr(
        "app.modules.slicer.estimate_read.resolve",
        lambda *args, **kwargs: ResolveSuccess.model_construct(
            bundle=mock_bundle,
            triple=mock_triple,
            from_cache=False,
            profile_selection=kwargs.get("profile_selection"),
        ),
    )

    resolver = SettingsEstimateResolver(redis_factory=None)
    intent = PrintIntentPreset(
        name="PLA standard",
        material_class="PLA",
        quality_tier="standard",
        printer_ref="p1s",
        spoolman_filament_ref="some-ref",
    )

    resolved = await resolver.resolve_preset(intent)
    assert resolved.profile_selection is not None
    # IF fallback_material was missing, this would be unavailable_no_profile.
    assert resolved.profile_selection.source == EstimateProfileSource.default_material_profile
    assert resolved.profile_selection.orca_filament_profile_ref == "Generic PLA"
