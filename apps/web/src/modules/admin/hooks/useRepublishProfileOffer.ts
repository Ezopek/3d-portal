import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import type { OfferPublishResult } from "@/lib/api-types";

export interface RepublishProfileOfferVars {
  offerId: string;
  stlHash: string;
}

/**
 * Story 38.2 — explicit admin republish/resync for stale published offers.
 *
 * Reuses the existing publish endpoint. The caller must provide the already-published STL hash;
 * this hook does not guess or auto-select an STL. On success it invalidates the admin offer list
 * so `sync_state` reconciles from the server.
 */
export function useRepublishProfileOffer() {
  const qc = useQueryClient();
  return useMutation<OfferPublishResult, ApiError, RepublishProfileOfferVars>({
    mutationFn: ({ offerId, stlHash }) =>
      api<OfferPublishResult>(`/admin/profiles/offers/${offerId}/publish`, {
        method: "POST",
        body: JSON.stringify({ stl_hash: stlHash }),
      }),
    retry: false,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "profile-offers"] });
    },
  });
}
