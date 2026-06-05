import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import type {
  AdminProfileSlot,
  MaterialClass,
  ProfileImportRejection,
  QualityTier,
} from "@/lib/api-types";

export interface ImportProfileVars {
  file: File;
  material_class: MaterialClass;
  quality_tier: QualityTier;
  portal_label?: string;
}

/**
 * Story 33.2 (FR21-PROFILE-IMPORT-1, AC-17) — the admin profile-import mutation.
 *
 * Posts the multipart `{file, printer_ref, material_class, quality_tier, portal_label?}`
 * through `api()` (which adds the `X-Portal-Client: web` CSRF header and never stamps a
 * JSON content-type on a `FormData` body). On success it invalidates the exact
 * `["admin","profiles"]` key the 33.1 `useAdminProfiles` hook reserved, so the inventory
 * grid refetches and the cell flips from Not imported → Offerable.
 *
 * Cache topology (per the story's enumeration): NO auto-retry on the write — a mutation must
 * not silently re-fire (NFR21-OBS-1 one-audit-event-per-import + admin-fails-closed). The
 * admin re-submits explicitly. The grid is never optimistically flipped before the server
 * confirms (AC-18).
 */
export function useImportProfile(printerRef: string) {
  const qc = useQueryClient();
  return useMutation<AdminProfileSlot, Error, ImportProfileVars>({
    mutationFn: ({ file, material_class, quality_tier, portal_label }) => {
      const form = new FormData();
      form.append("file", file);
      form.append("printer_ref", printerRef);
      form.append("material_class", material_class);
      form.append("quality_tier", quality_tier);
      if (portal_label) form.append("portal_label", portal_label);
      return api<AdminProfileSlot>("/admin/profiles/import", {
        method: "POST",
        body: form,
      });
    },
    retry: false,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "profiles"] });
    },
  });
}

/**
 * Extract the structured `reason_category` from a rejected import, or `null`.
 *
 * The backend returns `{detail: {reason_category, message}}` on a 413/422; the FE keys a
 * localized message off the category (admin sees *why* — AC-18). Anything else (a network
 * error, an unexpected shape) yields `null` so the caller can fall back to a generic message.
 */
export function importRejectionCategory(error: unknown): string | null {
  if (error instanceof ApiError) {
    const detail = (error.body as { detail?: Partial<ProfileImportRejection> } | null)?.detail;
    if (detail && typeof detail.reason_category === "string") {
      return detail.reason_category;
    }
  }
  return null;
}
