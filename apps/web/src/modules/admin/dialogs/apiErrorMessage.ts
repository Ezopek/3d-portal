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

// Sibling for the Story 52.2 category surface. A separate function rather than
// a parameterised namespace on the one above, because the status meanings
// genuinely differ: on the category write paths 409 is a slug collision, 422 is
// the service-layer depth-2 ceiling, 404 is a vanished category or model, and
// 400 is a duplicate id inside a replace-set payload. Copying the tag-group
// wording onto those would tell the admin the wrong thing.
export function mapCategoryApiError(err: unknown, t: TFunction): string {
  if (err instanceof ApiError) {
    if (err.status === 409) return t("modules.admin.categories.errors.slug_conflict");
    if (err.status === 422) return t("modules.admin.categories.errors.invalid");
    if (err.status === 404) return t("modules.admin.categories.errors.not_found");
    if (err.status === 400) return t("modules.admin.categories.errors.bad_request");
  }
  return t("modules.admin.categories.errors.generic");
}
