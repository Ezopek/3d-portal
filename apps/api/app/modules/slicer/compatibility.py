"""Story 33.1 (AC-7, OD-7) — per-material process-tier compatibility map.

This module is the **single backend source of truth** for the OD-7 compatibility
contract: which ``quality_tier`` process slots are structurally valid for a given
``material_class``. It realises the ``compatible`` dimension of Decision AK's
``offerable = imported ∧ resolvable ∧ compatible``.

**Resolvability is necessary but NOT sufficient.** A slot whose vendored profile happens
to resolve is still ``compatible=false`` (and therefore not offerable) when its tier is
not in its material's allowed set — e.g. a PLA-class process profile dropped into a TPU
slot. This map encodes the structural rule INDEPENDENTLY of "what resolves"; the two
dimensions are deliberately orthogonal (FR21-COMPAT-1).

**Magic-constant discipline (per [[feedback_scp_pre_enumeration_phase]] § C):** every
entry points to the OD-7 *operator-confirmed* compatibility contract — NOT to "what the
resolver happens to accept." The concrete per-material compatible-slot set is operator
data confirmed at the data phase (Q5).

Q5 operator decision (2026-06-04): the **TPU row** is intentionally restricted to the
``standard`` process slot for this read-only slice. The operator uses separate TPU-specific
Orca profiles in practice; until the import/manage UI exists, exposing only ``standard``
keeps the portal grid honest without pretending TPU supports the PLA/PETG/PCTG tier spread.
Authoring/editing this map (the import-time enforcement) belongs to Stories 33.2/33.3; it
is consumed read-only here.

[Source: architecture.md § Initiative 21 Decision AK + OD-7; PRD FR21-COMPAT-1]
"""

from __future__ import annotations

from app.modules.slicer.models import MaterialClass, QualityTier

# The structured reason CATEGORY (not human copy) emitted for a structurally-incompatible
# slot. The frontend maps this category to a localized string (NFR21-I18N-PARITY-1); the
# backend never ships display text. Mirrors the AC-4 reason taxonomy alongside the
# status-derived `profile_not_imported` / `not_resolvable` categories.
INCOMPATIBLE_REASON = "incompatible_for_material"

# OD-7 compatibility contract — material_class → frozenset of structurally-valid tiers.
# PLA/PETG/PCTG declare all three portal tiers. TPU is intentionally standard-only per the
# Q5 operator decision documented in the module docstring. frozenset → the SoT cannot be
# mutated at runtime by a consumer.
MATERIAL_TIER_COMPATIBILITY: dict[MaterialClass, frozenset[QualityTier]] = {
    "PLA": frozenset({"aesthetic", "standard", "strong"}),
    "PETG": frozenset({"aesthetic", "standard", "strong"}),
    "PCTG": frozenset({"aesthetic", "standard", "strong"}),
    # Q5 operator decision — TPU is currently exposed only through the standard slot.
    "TPU": frozenset({"standard"}),
}


def is_compatible(material_class: MaterialClass, quality_tier: QualityTier) -> bool:
    """True when ``quality_tier`` is a structurally-valid process slot for ``material_class``.

    An unknown ``material_class`` (outside the named set) yields ``False`` for every tier —
    a fail-closed default: an unmodelled material offers nothing rather than everything.
    """
    return quality_tier in MATERIAL_TIER_COMPATIBILITY.get(material_class, frozenset())


def incompatibility_reason(material_class: MaterialClass, quality_tier: QualityTier) -> str | None:
    """The structured incompatibility category for a slot, or ``None`` when compatible.

    Returns the machine-readable :data:`INCOMPATIBLE_REASON` category for an incompatible
    slot (the FE localizes it); ``None`` when the slot is compatible (its non-offerability,
    if any, then comes from the import/resolve dimensions, not from compatibility).
    """
    if is_compatible(material_class, quality_tier):
        return None
    return INCOMPATIBLE_REASON
