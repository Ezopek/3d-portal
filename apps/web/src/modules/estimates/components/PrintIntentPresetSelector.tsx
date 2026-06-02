import { useTranslation } from "react-i18next";

import type { MaterialClass, QualityTier } from "@/lib/api-types";
import {
  MATERIAL_CLASSES,
  QUALITY_TIERS,
  filamentRef,
  type PrintIntentPresetInput,
} from "@/modules/estimates/lib/preset";
import { useSpoolsSummary } from "@/modules/spools/hooks/useSpoolsSummary";

interface Props {
  value: PrintIntentPresetInput;
  onChange: (next: PrintIntentPresetInput) => void;
}

/**
 * Story 32.6 (AC-2) — the `PrintIntentPreset` selector.
 *
 * Selects a material class ∈ {PLA,PETG,PCTG,TPU} (names UNtranslated, AC-7), a portal
 * quality tier, and an OPTIONAL pinned Spoolman filament (by its churn-stable
 * `filamentRef`, NOT the integer id). It emits a `PrintIntentPreset`-shaped object and
 * NEVER exposes/accepts a raw Orca key — the bundle resolution is server-side (FR20-PRESET-1).
 *
 * Native labelled `<select>`s: keyboard-navigable and accessible by construction; every
 * control has a `<label htmlFor>`.
 */
export function PrintIntentPresetSelector({ value, onChange }: Props) {
  const { t } = useTranslation();
  const spools = useSpoolsSummary();
  const filaments = spools.data?.filaments ?? [];

  return (
    <fieldset className="flex flex-col gap-4 rounded-lg border p-4">
      <legend className="px-1 text-sm font-medium">
        {t("modules.estimates.selector.title")}
      </legend>

      <div className="flex flex-col gap-1">
        <label
          htmlFor="estimate-material-class"
          className="text-sm text-muted-foreground"
        >
          {t("modules.estimates.selector.material_class_label")}
        </label>
        <select
          id="estimate-material-class"
          className="rounded-md border bg-background px-3 py-2 text-sm"
          value={value.material_class}
          onChange={(e) =>
            onChange({
              ...value,
              material_class: e.target.value as MaterialClass,
            })
          }
        >
          {/* Material names render verbatim in every locale (NFR20-I18N-PARITY-1). */}
          {MATERIAL_CLASSES.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label
          htmlFor="estimate-quality-tier"
          className="text-sm text-muted-foreground"
        >
          {t("modules.estimates.selector.quality_tier_label")}
        </label>
        <select
          id="estimate-quality-tier"
          className="rounded-md border bg-background px-3 py-2 text-sm"
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

      <div className="flex flex-col gap-1">
        <label
          htmlFor="estimate-spool-pin"
          className="text-sm text-muted-foreground"
        >
          {t("modules.estimates.selector.spool_pin_label")}
        </label>
        <select
          id="estimate-spool-pin"
          className="rounded-md border bg-background px-3 py-2 text-sm"
          value={value.spoolman_filament_ref ?? ""}
          onChange={(e) =>
            onChange({
              ...value,
              spoolman_filament_ref:
                e.target.value === "" ? null : e.target.value,
            })
          }
        >
          {/* The empty value is the no-pin (material-default) path. */}
          <option value="">
            {t("modules.estimates.selector.spool_pin_none")}
          </option>
          {filaments.map((f) => {
            // The option VALUE is the stable profile-style ref — never `.id` (AC-2).
            const ref = filamentRef(f);
            return (
              <option key={ref} value={ref}>
                {f.name}
              </option>
            );
          })}
        </select>
      </div>
    </fieldset>
  );
}
