import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";

/**
 * PROFILE-OFFER-1 (AC-18) — delete a PrintProfileOffer.
 *
 * DELETEs `/admin/profiles/offers/{offer_id}` (204 on success). Deleting an offer removes only
 * the offer — it never touches the referenced library blocks (offers reference, they do not
 * own). NO auto-retry on the write; on success it invalidates the `["admin","profile-offers"]`
 * subtree so the list reconciles from the server (no optimistic removal).
 */
export function useDeleteProfileOffer() {
  const qc = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: (offerId) =>
      api<void>(`/admin/profiles/offers/${offerId}`, { method: "DELETE" }),
    retry: false,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "profile-offers"] });
    },
  });
}
