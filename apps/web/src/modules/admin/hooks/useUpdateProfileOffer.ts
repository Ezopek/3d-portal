import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import type { PrintProfileOffer, PrintProfileOfferUpdate } from "@/lib/api-types";

export interface UpdateProfileOfferVars {
  offerId: string;
  patch: PrintProfileOfferUpdate;
}

/**
 * PROFILE-OFFER-1 (AC-18) — edit a PrintProfileOffer's label/visibility/default/categories.
 *
 * PATCHes `/admin/profiles/offers/{offer_id}` (200 + the updated DTO). The chain (block refs)
 * is IMMUTABLE on PATCH — changing the blocks means delete + re-create. NO auto-retry; on
 * success it invalidates the `["admin","profile-offers"]` subtree so the list reconciles from
 * the server (no optimistic mutate).
 */
export function useUpdateProfileOffer() {
  const qc = useQueryClient();
  return useMutation<PrintProfileOffer, ApiError, UpdateProfileOfferVars>({
    mutationFn: ({ offerId, patch }) =>
      api<PrintProfileOffer>(`/admin/profiles/offers/${offerId}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      }),
    retry: false,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "profile-offers"] });
    },
  });
}
