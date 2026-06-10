import { useTranslation } from "react-i18next";

import type { ProfileSelectionContextView } from "@/lib/api-types";
import { Badge } from "@/ui/badge";

interface Props {
  context: ProfileSelectionContextView | null | undefined;
}

/**
 * Story 35.5 (AC-2) — renders a source-honesty badge for an estimate.
 *
 * exact_filament_mapping → subtle outline badge (confident path).
 * default_material_profile → muted secondary badge with material name.
 * unavailable_no_profile | null | undefined → renders nothing (absent state owns its copy).
 *
 * orca_filament_profile_name is admin-scoped and MUST NOT appear here.
 */
export function ProfileSourceBadge({ context }: Props) {
  const { t } = useTranslation();

  if (
    context == null ||
    context.estimate_profile_source === "unavailable_no_profile"
  ) {
    return null;
  }

  if (context.estimate_profile_source === "exact_filament_mapping") {
    return (
      <Badge variant="outline">
        {t("modules.estimates.profile_source.exact")}
      </Badge>
    );
  }

  // default_material_profile
  return (
    <Badge variant="secondary">
      {t("modules.estimates.profile_source.default", {
        material: context.selected_material,
      })}
    </Badge>
  );
}
