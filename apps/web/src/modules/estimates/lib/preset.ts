// Story 32.6 (AC-2, AC-11) — the `PrintIntentPreset`-shaped selector contract.
//
// The two enum sets here are NAMED CONTRACTS (AC-11), not UI-local re-spellings:
// they mirror the backend resolver's `MaterialClass` / `QualityTier` literals
// (`apps/api/app/modules/slicer/models.py`) — the selector emits a preset the server
// resolves to a `SlicerProfileBundle`; it NEVER carries a raw Orca key (layer height,
// `filament_max_volumetric_speed`, temps). That is FR20-PRESET-1 enforced at the edge.

import type { FilamentView, MaterialClass, QualityTier } from "@/lib/api-types";

// because "the FR20 supported material-class set (Decision AH resolver inputs); material
// names are an untranslated portal↔Orca naming convention per NFR20-I18N-PARITY-1, not UI
// copy" — the same four classes the backend `MaterialClass` literal admits, in resolve order.
export const MATERIAL_CLASSES: readonly MaterialClass[] = [
  "PLA",
  "PETG",
  "PCTG",
  "TPU",
];

// because "the portal-defined quality tier set the resolver maps to Orca process profiles
// (Decision AH); the UI selects a tier, the server resolves it to a bundle — the tier names
// are the portal contract, not Orca process-profile names" — mirrors the backend
// `QualityTier` literal.
export const QUALITY_TIERS: readonly QualityTier[] = [
  "aesthetic",
  "standard",
  "strong",
];

export const DEFAULT_MATERIAL_CLASS: MaterialClass = "PLA";
export const DEFAULT_QUALITY_TIER: QualityTier = "standard";

// because "the catalog estimate chip MUST read the SAME printer bundle EST-INGEST-1 sliced
// against, or every read is permanently `absent`" — EST-INGEST-1 ingests catalog STL parts
// using the backend `slicer_default_printer_ref` (apps/api/app/core/config.py:185), so the
// FilesTab chip/panel resolve must pass this exact ref as `printer_ref`. This is the FE half
// of that magic-constant contract; it is NOT the standalone `/estimates` demo route's "p1s"
// placeholder. Arbitrary-until-multi-printer: replace when a printer registry / per-model
// printer selection lands (mirrors the backend `slicer_default_printer_ref` note).
export const CATALOG_ESTIMATE_PRINTER_REF = "creality-k1-max-microswiss-hf";

/** The selector's output: a `PrintIntentPreset`-shaped object (NO Orca keys). */
export interface PrintIntentPresetInput {
  material_class: MaterialClass;
  quality_tier: QualityTier;
  // The Story 32.5 pin — the churn-stable PROFILE-STYLE reference, NOT the integer id.
  spoolman_filament_ref: string | null;
}

export function defaultPreset(): PrintIntentPresetInput {
  return {
    material_class: DEFAULT_MATERIAL_CLASS,
    quality_tier: DEFAULT_QUALITY_TIER,
    spoolman_filament_ref: null,
  };
}

// The unit-separator delimiter the backend `spoolman_filament_ref` joins on
// (`overrides.py:_REF_DELIMITER`). ONE derivation on each side so the build-side map key
// and the lookup-side intent key cannot silently diverge (Init 19 B2).
const REF_DELIMITER = "\x1f";

/**
 * Derive the churn-stable profile-style reference for a Spoolman filament — the EXACT
 * `vendor∥material∥name` composite the backend `spoolman_filament_ref` produces. The pin
 * stores this string, NEVER `filament.id` (the integer re-keys on inventory edits).
 */
export function filamentRef(filament: FilamentView): string {
  return [
    filament.vendor_name ?? "",
    filament.material ?? "",
    filament.name,
  ].join(REF_DELIMITER);
}

/**
 * Stable query-cache discriminator for a preset (AC-3): any selector change MUST produce a
 * new key so a stale key never shows a *different* preset's estimate. A pinned filament
 * (a different bundle) re-keys via its ref.
 */
export function presetKey(preset: PrintIntentPresetInput): string {
  return [
    preset.material_class,
    preset.quality_tier,
    preset.spoolman_filament_ref ?? "",
  ].join("|");
}
