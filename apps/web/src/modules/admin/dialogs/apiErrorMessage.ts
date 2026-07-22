import type { TFunction } from "i18next";

import { ApiError } from "@/lib/api";

// Shared inline-error mapping for the tag-groups write dialogs (Story 46.2):
// 409 → slug/name conflict, 400 → target group no longer exists, everything
// else → a generic retry message. Non-ApiError failures also fall through to
// generic so the dialog never surfaces a raw stack.
export function mapApiError(err: unknown, t: TFunction): string {
  if (err instanceof ApiError) {
    if (err.status === 409) return t("modules.admin.tagGroups.errors.conflict");
    if (err.status === 400) return t("modules.admin.tagGroups.errors.group_not_found");
  }
  return t("modules.admin.tagGroups.errors.generic");
}
