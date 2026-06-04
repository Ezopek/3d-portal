import { useId } from "react";
import { useTranslation } from "react-i18next";

import type { QualityTier } from "@/lib/api-types";
import type { QualityTierAvailability } from "@/modules/estimates/hooks/useQualityTierAvailability";
import {
  QUALITY_TIERS,
  type PrintIntentPresetInput,
} from "@/modules/estimates/lib/preset";

interface Props {
  value: PrintIntentPresetInput;
  onChange: (next: PrintIntentPresetInput) => void;
  /**
   * EST-TIERS-1: when supplied by the Catalog Files/STL surface, unavailable tiers are
   * rendered disabled and cannot re-key estimate reads into a resolver 422. Omitted keeps the
   * standalone/pure unit-test behavior: all portal tiers are selectable.
   */
  availability?: readonly QualityTierAvailability[];
}

/**
 * EST-DISPLAY-1 product correction — the Catalog detail → Files → STL tab is an orientational
 * per-STL gram ESTIMATE preview surface, NOT print ordering and NOT spool availability. The only
 * high-leverage choice here is the print process / quality profile, so this compact, inline
 * selector exposes ONLY `quality_tier`.
 *
 * Material class is held at the EST-INGEST-1 default (PLA) and the Spoolman pin stays `null` — both
 * carried as INTERNAL preset defaults (never surfaced here) so the estimate query keys
 * (`sha256 + preset + printerRef`) and the chip/panel re-render behaviour are unchanged. Material
 * and pinned-filament selection live only on the standalone `/estimates` surface
 * (`EstimatesPanel` + `PrintIntentPresetSelector`); ordering / spool semantics are deliberately
 * NOT exposed on this surface.
 */
export function CatalogEstimateProfileSelector({
  value,
  onChange,
  availability,
}: Props) {
  const { t } = useTranslation();
  const selectId = useId();
  const availabilityByTier = new Map(
    availability?.map((tier) => [tier.quality_tier, tier]) ?? [],
  );

  // Fail OPEN: a tier is unavailable only when the backend explicitly reports
  // `available: false`. An omitted/undefined availability prop (standalone use), an empty list
  // (still loading), or a missing row (availability fetch errored) all leave the tier
  // SELECTABLE. This guarantees the product invariant that Standard is never locked out — a
  // disabled-everything selector on a transient fetch error would be worse than the 422 this
  // gate closes. Disabling only happens once the backend has positively said a tier is missing.
  const isAvailable = (tier: QualityTier) =>
    availabilityByTier.get(tier)?.available !== false;

  return (
    <div className="flex items-center justify-end gap-2 text-xs text-muted-foreground">
      <label htmlFor={selectId} className="shrink-0">
        {t("modules.estimates.selector.profile_label")}
      </label>
      <select
        id={selectId}
        className="rounded-md border bg-background px-2 py-1 text-xs text-foreground disabled:cursor-not-allowed disabled:opacity-60"
        value={value.quality_tier}
        onChange={(e) => {
          const quality_tier = e.target.value as QualityTier;
          if (!isAvailable(quality_tier)) return;
          onChange({ ...value, quality_tier });
        }}
      >
        {QUALITY_TIERS.map((q) => {
          const available = isAvailable(q);
          const label = t(`modules.estimates.quality.${q}`);
          return (
            <option key={q} value={q} disabled={!available}>
              {available
                ? label
                : t("modules.estimates.selector.profile_unavailable_option", {
                    profile: label,
                  })}
            </option>
          );
        })}
      </select>
    </div>
  );
}
