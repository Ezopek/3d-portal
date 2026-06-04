import { useId } from "react";
import { useTranslation } from "react-i18next";

import type { MaterialClass, QualityTier } from "@/lib/api-types";
import { cn } from "@/lib/utils";
import type { QualityTierAvailability } from "@/modules/estimates/hooks/useQualityTierAvailability";
import {
  MATERIAL_CLASSES,
  QUALITY_TIERS,
  isTierCompatible,
  type PrintIntentPresetInput,
} from "@/modules/estimates/lib/preset";

interface Props {
  value: PrintIntentPresetInput;
  onChange: (next: PrintIntentPresetInput) => void;
  /**
   * EST-TIERS-1: when supplied by the Catalog Files/STL surface, unavailable tiers are
   * rendered disabled and cannot re-key estimate reads into a resolver 422. Omitted keeps the
   * standalone/pure unit-test behavior: all portal tiers (for the chosen material) selectable.
   */
  availability?: readonly QualityTierAvailability[];
}

/**
 * ===== Material-exposure reversal (Story 33.1 / Init 21 Q1 = Path B) =====
 *
 * EST-DISPLAY-1 (shipped) deliberately exposed ONLY `quality_tier`, holding `material_class`
 * at the PLA default and INTERNAL (`CatalogEstimateProfileSelector` original :22-34), to keep
 * this catalog Files/STL surface an orientational per-STL gram ESTIMATE preview — NOT ordering,
 * NOT spool availability — and to avoid re-opening spool/quote semantics here.
 *
 * Init 21 Q1 (operator/controller, 2026-06-04) REVERSES that decision so the member selects
 * `material_class` and the TPU compatibility directive ("only ever offer compatible process
 * choices") is live on the surface members actually use. Documented per the repo's
 * NFR-carve-out-reversal recipe (`[[feedback_share_view_scope_boundary]]` adjacency):
 *   1. Old rationale — EST-DISPLAY-1: material internal/PLA-pinned; estimate-preview-only.
 *   2. New requirement — Init 21 Path B: surface material for per-material compatibility (TPU).
 *   3. Preserved invariant — the surface stays an estimate PREVIEW: no ordering, no quote, no
 *      spool semantics; `spoolman_filament_ref` STAYS `null` here (filament/spool selection
 *      remains exclusive to `/estimates`); no incompatible/unofferable slot is ever selectable
 *      (NFR21-NO-422-1).
 *   4. Mechanism — the "no ordering/spool" property is now held by the BOUNDED estimate-read
 *      contract (`material_class` is a resolve INPUT only; no spool pin, no quote field), NOT
 *      by material-pinning. Compatibility filtering rides the backend projection + the FE
 *      compatibility mirror (`preset.ts MATERIAL_TIER_COMPATIBILITY`), with a vitest parity
 *      test asserting agreement.
 *
 * Hybrid disabled-vs-hidden (AC-19): incompatible tiers for the chosen material are HIDDEN
 * (never teased); compatible-but-unavailable tiers are VISIBLE but disabled-with-explanation.
 * Fail-OPEN preserved (AC-20): a transient availability error keeps tiers selectable; Standard
 * is never locked out.
 * =======================================================================
 */
export function CatalogEstimateProfileSelector({
  value,
  onChange,
  availability,
}: Props) {
  const { t } = useTranslation();
  const materialId = useId();
  const reasonIdBase = useId();
  const availabilityByTier = new Map(
    availability?.map((tier) => [tier.quality_tier, tier]) ?? [],
  );

  // Fail OPEN: a tier is unavailable only when the backend explicitly reports
  // `available: false`. An omitted/undefined availability prop (standalone use), an empty list
  // (still loading), or a missing row (availability fetch errored) all leave the tier
  // SELECTABLE — Standard is never locked out (EST-TIERS-1 invariant, AC-20).
  const isAvailable = (tier: QualityTier) =>
    availabilityByTier.get(tier)?.available !== false;

  // Compatibility HIDES incompatible tiers for the chosen material (AC-19). The FE mirror of
  // the backend projection — never render an option the projection marks incompatible.
  const compatibleTiers = QUALITY_TIERS.filter((tier) =>
    isTierCompatible(value.material_class, tier),
  );

  const selectMaterial = (material_class: MaterialClass) => {
    const tiers = QUALITY_TIERS.filter((tier) =>
      isTierCompatible(material_class, tier),
    );
    // Keep the current tier if it stays compatible; otherwise fall to the first compatible
    // tier so the preset never carries an incompatible (material, tier) pair.
    const quality_tier = tiers.includes(value.quality_tier)
      ? value.quality_tier
      : (tiers[0] ?? value.quality_tier);
    // `spoolman_filament_ref` STAYS null — this surface never pins a spool (preserved invariant
    // #3 of the reversal): material is a resolve input only, not a spool/order control.
    onChange({ ...value, material_class, quality_tier, spoolman_filament_ref: null });
  };

  const selectTier = (tier: QualityTier) => {
    // A member can NEVER select a non-offerable slot: incompatible tiers are not rendered;
    // unavailable tiers are guarded here. NFR21-NO-422-1 holds structurally.
    if (!isTierCompatible(value.material_class, tier)) return;
    if (!isAvailable(tier)) return;
    onChange({ ...value, quality_tier: tier });
  };

  return (
    <div className="flex flex-wrap items-center justify-end gap-3 text-xs text-muted-foreground">
      <div className="flex items-center gap-2">
        <label htmlFor={materialId} className="shrink-0">
          {t("modules.estimates.selector.material_class_label")}
        </label>
        <select
          id={materialId}
          className="rounded-md border bg-background px-2 py-1 text-xs text-foreground"
          value={value.material_class}
          onChange={(e) => selectMaterial(e.target.value as MaterialClass)}
        >
          {MATERIAL_CLASSES.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-2">
        <span className="shrink-0">
          {t("modules.estimates.selector.quality_tier_label")}
        </span>
        <div
          role="radiogroup"
          aria-label={t("modules.estimates.selector.quality_tier_label")}
          className="flex flex-wrap gap-1"
        >
          {compatibleTiers.map((tier) => {
            const available = isAvailable(tier);
            const selected = value.quality_tier === tier;
            const reasonKey = available
              ? null
              : availabilityByTier.get(tier)?.reason === "profile_not_imported"
                ? "reason_not_imported"
                : "reason_unavailable";
            const describedBy = reasonKey ? `${reasonIdBase}-${tier}` : undefined;
            const label = t(`modules.estimates.quality.${tier}`);
            return (
              <button
                key={tier}
                type="button"
                role="radio"
                aria-checked={selected}
                aria-describedby={describedBy}
                disabled={!available}
                onClick={() => selectTier(tier)}
                className={cn(
                  "rounded-md border px-2 py-1 text-xs transition-colors",
                  selected
                    ? "border-primary text-foreground"
                    : "border-border text-muted-foreground hover:text-foreground",
                  !available && "cursor-not-allowed opacity-60 hover:text-muted-foreground",
                )}
              >
                {available
                  ? label
                  : `${label} · ${t(`modules.estimates.selector.${reasonKey}`)}`}
                {reasonKey ? (
                  <span id={describedBy} className="sr-only">
                    {t(`modules.estimates.selector.${reasonKey}_tooltip`, {
                      material: value.material_class,
                    })}
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
