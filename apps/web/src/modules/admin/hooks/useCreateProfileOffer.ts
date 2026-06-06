import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import type { PrintProfileOffer, PrintProfileOfferCreate } from "@/lib/api-types";
import type { ProfileImportRejection } from "@/lib/api-types";

/**
 * PROFILE-OFFER-1 (AC-18) — compose a new PrintProfileOffer.
 *
 * POSTs `/admin/profiles/offers` (201 + the created offer DTO). NO auto-retry on the write
 * (NFR21-OBS-1 one-audit-event + admin-fails-closed; the admin re-submits explicitly). On
 * success it invalidates the `["admin","profile-offers"]` subtree so the list reconciles from
 * the server (no optimistic insert). It does NOT touch the library cache.
 */
export function useCreateProfileOffer() {
  const qc = useQueryClient();
  return useMutation<PrintProfileOffer, ApiError, PrintProfileOfferCreate>({
    mutationFn: (body) =>
      api<PrintProfileOffer>("/admin/profiles/offers", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    retry: false,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "profile-offers"] });
    },
  });
}

/**
 * Extract the structured `reason_category` from a rejected offer mutation, or `null`.
 *
 * Mirrors `libraryRejectionCategory` / `importRejectionCategory`: the backend returns
 * `{detail: {reason_category}}` on a 4xx (e.g. `invalid_chain`, `unsupported_material_category`,
 * `invalid_offer`, `not_found`) so the FE can localize *why* an op was rejected (fails
 * closed/visible).
 */
export function offerRejectionCategory(error: unknown): string | null {
  if (error instanceof ApiError) {
    const detail = (error.body as { detail?: Partial<ProfileImportRejection> } | null)?.detail;
    if (detail && typeof detail.reason_category === "string") {
      return detail.reason_category;
    }
  }
  return null;
}
