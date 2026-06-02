import { useTranslation } from "react-i18next";

import type { OverrideContextView } from "@/lib/api-types";
import { Badge } from "@/ui/badge";

interface Props {
  context: OverrideContextView;
}

/**
 * Story 32.6 (AC-5) — the material / Spoolman override-context panel.
 *
 * Surfaces the provenance the operator needs AT THE RIGHT ALTITUDE: the material class +
 * quality tier, and — when a Spoolman filament is pinned — its human name, the FACT that a
 * custom override profile is applied (a badge, never the values), and the carried
 * `filament.extra.url` purchase link (a plain `rel="noopener noreferrer"` external link).
 *
 * It NEVER renders the override VALUES (no volumetric speed / temp / density / layer height),
 * NO `settings_ids`, NO g-code, NO Orca key — the DTO simply does not carry them
 * (FR20-PRESET-1 re-enforced at the render layer; defense in depth over the API projection).
 * Material names render verbatim (NFR20-I18N-PARITY-1).
 */
export function OverrideContextPanel({ context }: Props) {
  const { t } = useTranslation();
  const pinned = context.pinned_filament_name !== null;

  return (
    <section
      aria-label={t("modules.estimates.override.title")}
      className="flex flex-col gap-2 rounded-lg border p-4 text-sm"
    >
      <h3 className="font-medium">{t("modules.estimates.override.title")}</h3>

      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
        <dt className="text-muted-foreground">
          {t("modules.estimates.override.material_class")}
        </dt>
        {/* Material class is an untranslated portal↔Orca name — render verbatim. */}
        <dd className="font-medium">{context.material_class}</dd>

        <dt className="text-muted-foreground">
          {t("modules.estimates.override.quality_tier")}
        </dt>
        <dd>{t(`modules.estimates.quality.${context.quality_tier}`)}</dd>

        {pinned && (
          <>
            <dt className="text-muted-foreground">
              {t("modules.estimates.override.pinned_filament")}
            </dt>
            <dd className="font-medium">{context.pinned_filament_name}</dd>
          </>
        )}
      </dl>

      {pinned && (
        <Badge
          variant={context.custom_overrides_applied ? "secondary" : "outline"}
        >
          {context.custom_overrides_applied
            ? t("modules.estimates.override.custom_applied")
            : t("modules.estimates.override.no_custom")}
        </Badge>
      )}

      {context.purchase_url !== null && (
        <a
          href={context.purchase_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm underline underline-offset-2"
        >
          {t("modules.estimates.override.purchase_link")}
        </a>
      )}
    </section>
  );
}
