import { useId } from "react";
import { useTranslation } from "react-i18next";

import type { QualityTier } from "@/lib/api-types";
import {
  QUALITY_TIERS,
  type PrintIntentPresetInput,
} from "@/modules/estimates/lib/preset";

interface Props {
  value: PrintIntentPresetInput;
  onChange: (next: PrintIntentPresetInput) => void;
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
export function CatalogEstimateProfileSelector({ value, onChange }: Props) {
  const { t } = useTranslation();
  const selectId = useId();

  return (
    <div className="flex items-center justify-end gap-2 text-xs text-muted-foreground">
      <label htmlFor={selectId} className="shrink-0">
        {t("modules.estimates.selector.profile_label")}
      </label>
      <select
        id={selectId}
        className="rounded-md border bg-background px-2 py-1 text-xs text-foreground"
        value={value.quality_tier}
        onChange={(e) =>
          onChange({ ...value, quality_tier: e.target.value as QualityTier })
        }
      >
        {QUALITY_TIERS.map((q) => (
          <option key={q} value={q}>
            {t(`modules.estimates.quality.${q}`)}
          </option>
        ))}
      </select>
    </div>
  );
}
