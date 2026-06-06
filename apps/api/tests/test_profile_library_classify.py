"""PROFILE-LIB-1 (T1) — classifier + curated-metadata + validation-state engine tests.

Grounded in the bench-derived fixtures (heuristic branch, AC-2b) AND the real Orca block
exports (the G-DATA explicit-``type`` branch + the user-process governance shape, AC-2a/AC-5)
copied into ``tests/fixtures/slicer/library/`` (sanitized — no print_host/agent/gcode).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.modules.slicer.profile_library import (
    classify_profile,
    declared_inherit,
    derive_validation_state,
    extract_curated_metadata,
    resolve_inherit_chain,
)

LIBRARY_FIXTURES = Path(__file__).parent / "fixtures" / "slicer" / "library"


def _load(name: str) -> dict:
    return json.loads((LIBRARY_FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def system_tree() -> dict[str, dict]:
    """A name-keyed system tree carrying the system parents the user blocks inherit."""
    tree: dict[str, dict] = {}
    for name in (
        "system_filament_generic_tpu.json",
        "system_process_020_standard.json",
        "system_machine_k1max.json",
    ):
        profile = _load(name)
        tree[profile["name"]] = profile
    return tree


# === AC-2: classification ======================================================


def test_classify_user_process_by_heuristic_print_settings_id() -> None:
    # Real user process: no explicit `type`, `from: User`, `print_settings_id` discriminator.
    assert classify_profile(_load("user_process_tpu_flowtech.json")) == "process"


def test_classify_user_filament_by_heuristic_filament_type() -> None:
    assert classify_profile(_load("user_filament_rosa_flex.json")) == "filament"


def test_classify_user_machine_by_heuristic_printer_settings_id() -> None:
    assert classify_profile(_load("user_machine_k1max_microswiss.json")) == "machine"


def test_classify_bench_system_profiles_by_heuristic() -> None:
    # The EXISTING bench fixtures (singular `inherit`, no explicit `type`) still classify.
    system_dir = LIBRARY_FIXTURES.parent / "system"
    assert classify_profile(json.loads((system_dir / "rosa3d_flex_96a.json").read_text())) == (
        "filament"
    )
    assert (
        classify_profile(
            json.loads((system_dir / "creality_k1_max_microswiss_hf.json").read_text())
        )
        == "machine"
    )
    assert (
        classify_profile(json.loads((system_dir / "process_0_20mm_standard.json").read_text()))
        == "process"
    )


def test_classify_system_blocks_by_explicit_type_field() -> None:
    # G-DATA: real Orca SYSTEM exports carry an explicit `type` ∈ {filament,process,machine}.
    assert classify_profile(_load("system_filament_generic_tpu.json")) == "filament"
    assert classify_profile(_load("system_process_020_standard.json")) == "process"
    assert classify_profile(_load("system_machine_k1max.json")) == "machine"


def test_explicit_type_precedence_over_heuristic() -> None:
    # An explicit `type: machine` wins even if a (contradictory) filament key is present.
    body = {"type": "machine", "name": "x", "filament_type": ["PLA"]}
    assert classify_profile(body) == "machine"


def test_explicit_type_synonyms_normalized() -> None:
    assert classify_profile({"type": "printer", "name": "x"}) == "machine"
    assert classify_profile({"type": "print", "name": "x"}) == "process"


def test_unrecognised_explicit_type_falls_through_to_heuristic() -> None:
    assert classify_profile({"type": "weird", "name": "x", "filament_type": ["PLA"]}) == "filament"


@pytest.mark.parametrize("body", [{}, {"name": "x"}, [], None, "str", {"unrelated": 1}])
def test_unclassifiable_returns_none(body: object) -> None:
    assert classify_profile(body) is None


# === AC-3: curated-metadata extraction =========================================


def test_extract_user_filament_curated_fields(system_tree) -> None:
    body = _load("user_filament_rosa_flex.json")
    curated = extract_curated_metadata(body, profile_type="filament", system_tree=system_tree)
    assert curated.name == "AI Rosa3D Flex 96A Black"
    assert curated.profile_type == "filament"
    assert curated.source == "user"
    assert curated.is_system is False
    assert curated.inherit == "Generic TPU @System"
    assert curated.inherit_chain[0] == "Generic TPU @System"
    assert curated.settings_id == "AI Rosa3D Flex 96A Black"  # from list-valued filament id
    assert curated.material_type == "TPU"
    assert curated.compatible_printers == ["Creality K1 Max (0.4 nozzle)"]


def test_extract_system_block_marks_is_system(system_tree) -> None:
    curated = extract_curated_metadata(
        _load("system_machine_k1max.json"), profile_type="machine", system_tree=system_tree
    )
    assert curated.source == "system"
    assert curated.is_system is True
    assert curated.settings_id == "GM001"  # system `setting_id`


def test_declared_inherit_handles_plural_and_singular() -> None:
    assert declared_inherit({"inherits": "A"}) == "A"
    assert declared_inherit({"inherit": "B"}) == "B"
    assert declared_inherit({"name": "no parent"}) is None


def test_inherit_chain_truncates_on_unknown_parent_without_raising() -> None:
    tree = {"A": {"name": "A", "inherits": "B"}}  # B is absent from the tree
    chain, direct_known = resolve_inherit_chain("A", tree)
    assert chain == ["A", "B"]  # walked into A, then truncated at unknown B
    assert direct_known is True


def test_inherit_chain_flags_unknown_direct_parent() -> None:
    chain, direct_known = resolve_inherit_chain("Ghost", {})
    assert chain == ["Ghost"]
    assert direct_known is False


def test_inherit_chain_is_cycle_safe() -> None:
    tree = {"A": {"name": "A", "inherits": "B"}, "B": {"name": "B", "inherits": "A"}}
    chain, _ = resolve_inherit_chain("A", tree)
    assert chain == ["A", "B"]  # cycle halts, never loops forever


def test_curated_metadata_carries_no_raw_orca_keys(system_tree) -> None:
    # Leak fence: the curated dataclass exposes none of the raw process/filament keys.
    from dataclasses import asdict

    curated = extract_curated_metadata(
        _load("user_filament_rosa_flex.json"), profile_type="filament", system_tree=system_tree
    )
    serialized = json.dumps(asdict(curated))
    for raw_key in (
        "nozzle_temperature",
        "filament_density",
        "filament_max_volumetric_speed",
        "filament_flow_ratio",
        "layer_height",
        "gcode",
    ):
        assert raw_key not in serialized


# === AC-4 / AC-5: validation-state derivation + governance =====================


def test_usable_user_process_inheriting_system_process(system_tree) -> None:
    curated = extract_curated_metadata(
        _load("user_process_tpu_flowtech.json"), profile_type="process", system_tree=system_tree
    )
    state, reasons = derive_validation_state(curated, system_tree=system_tree)
    assert state == "usable"
    assert reasons == []


def test_user_process_invalid_inheritance_flags_requires_attention(system_tree) -> None:
    # Governance (AC-5): a user process inheriting a NON-system parent is flagged, not dropped.
    curated = extract_curated_metadata(
        _load("user_process_invalid_inherit.json"), profile_type="process", system_tree=system_tree
    )
    state, reasons = derive_validation_state(curated, system_tree=system_tree)
    assert state == "requires_attention"
    assert "user_process_invalid_inheritance" in reasons
    # The governance reason supersedes the generic unknown-parent reason (one reason, not two).
    assert "unknown_inherit_parent" not in reasons


def test_usable_filament_with_resolvable_parent(system_tree) -> None:
    curated = extract_curated_metadata(
        _load("user_filament_rosa_flex.json"), profile_type="filament", system_tree=system_tree
    )
    state, reasons = derive_validation_state(curated, system_tree=system_tree)
    assert state == "usable"
    assert reasons == []


def test_unknown_inherit_parent_flag_for_non_process(system_tree) -> None:
    body = {"name": "Lonely", "from": "User", "filament_type": ["PLA"], "inherits": "Ghost Parent"}
    curated = extract_curated_metadata(body, profile_type="filament", system_tree=system_tree)
    state, reasons = derive_validation_state(curated, system_tree=system_tree)
    assert state == "requires_attention"
    assert reasons == ["unknown_inherit_parent"]


def test_unknown_material_type_flag(system_tree) -> None:
    body = {
        "name": "Exotic",
        "from": "User",
        "filament_type": ["PEEK"],
        "inherits": "Generic TPU @System",
    }
    curated = extract_curated_metadata(body, profile_type="filament", system_tree=system_tree)
    assert curated.material_type is None
    state, reasons = derive_validation_state(curated, system_tree=system_tree)
    assert state == "requires_attention"
    assert reasons == ["unknown_material_type"]


def test_in_table_material_types_are_not_flagged(system_tree) -> None:
    for material in ("PLA", "PETG", "PCTG", "TPU"):
        body = {"name": f"{material} f", "from": "User", "filament_type": [material]}
        curated = extract_curated_metadata(body, profile_type="filament", system_tree=system_tree)
        assert curated.material_type == material
        assert curated.material_type_unknown is False
