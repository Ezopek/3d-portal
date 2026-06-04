"""Story 33.1 (AC-7, OD-7) — unit tests for the per-material process-tier
compatibility map (the backend source of truth).

These assert the *structure and behaviour* of the map (every material is keyed;
``is_compatible`` agrees with the table; ``incompatibility_reason`` is the structured
category for incompatible cells and ``None`` for compatible ones), including the
operator-confirmed Q5 TPU row (TPU exposes only ``standard`` for this read-only slice).
The map still declares structurally-incompatible cells so the ``incompatible`` status
path is exercised end-to-end.
"""

from __future__ import annotations

import pytest

from app.modules.slicer.compatibility import (
    INCOMPATIBLE_REASON,
    MATERIAL_TIER_COMPATIBILITY,
    incompatibility_reason,
    is_compatible,
)
from app.modules.slicer.models import MaterialClass, QualityTier
from app.modules.slicer.router import QUALITY_TIER_ORDER

# The named FE↔BE grid axes (mirror of MaterialClass / QualityTier literals).
_MATERIAL_CLASSES: tuple[MaterialClass, ...] = ("PLA", "PETG", "PCTG", "TPU")


def test_every_material_class_is_keyed_in_the_map() -> None:
    # The map is a total declaration over the named MaterialClass set — a missing key
    # would silently make a whole material read as all-incompatible.
    assert set(MATERIAL_TIER_COMPATIBILITY) == set(_MATERIAL_CLASSES)


def test_compatible_tiers_are_a_subset_of_the_named_quality_tiers() -> None:
    # Every declared-compatible tier must be a real QualityTier (no typo'd tier that can
    # never match a slot).
    valid = set(QUALITY_TIER_ORDER)
    for material, tiers in MATERIAL_TIER_COMPATIBILITY.items():
        assert tiers <= valid, f"{material} declares an unknown tier: {tiers - valid}"


@pytest.mark.parametrize("material", _MATERIAL_CLASSES)
@pytest.mark.parametrize("tier", QUALITY_TIER_ORDER)
def test_is_compatible_agrees_with_the_table(material: MaterialClass, tier: QualityTier) -> None:
    expected = tier in MATERIAL_TIER_COMPATIBILITY[material]
    assert is_compatible(material, tier) is expected


@pytest.mark.parametrize("material", _MATERIAL_CLASSES)
@pytest.mark.parametrize("tier", QUALITY_TIER_ORDER)
def test_incompatibility_reason_matches_compatibility(
    material: MaterialClass, tier: QualityTier
) -> None:
    if is_compatible(material, tier):
        assert incompatibility_reason(material, tier) is None
    else:
        # A non-null *structured* category (not human copy) for every incompatible cell.
        assert incompatibility_reason(material, tier) == INCOMPATIBLE_REASON


def test_tpu_is_standard_only_per_q5_operator_decision() -> None:
    # Q5 operator decision: TPU-specific Orca profiles will be imported later; until the
    # management UI exists, the portal exposes TPU only through the standard slot.
    assert MATERIAL_TIER_COMPATIBILITY["TPU"] == {"standard"}


def test_map_declares_at_least_one_incompatible_cell() -> None:
    # The operator-confirmed map MUST contain at least one structurally-incompatible
    # (material, tier) so the `incompatible` status path is genuinely exercised by the
    # grid/selector tests.
    incompatible = [
        (m, t) for m in _MATERIAL_CLASSES for t in QUALITY_TIER_ORDER if not is_compatible(m, t)
    ]
    assert incompatible, "the compatibility map declares no incompatible cell"
