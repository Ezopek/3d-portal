import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { EstimateView } from "@/lib/api-types";

// because "match useEstimate — estimates change no faster than the slicer worker cadence."
// (UX §D.5)
const OFFER_ESTIMATE_STALE_TIME_MS = 60_000;
const OFFER_ESTIMATE_GC_TIME_MS = 5 * 60_000;

/**
 * Story 36.3 (AC-3) — offer-based estimate read hook.
 *
 * Cache key: ["estimates", stlHash, { offerId }]
 * Deliberately DIFFERENT from preset key (["estimates", stlHash, presetKey(preset), printerRef])
 * so switching between "None" and an offer is always an independent read, not a stale preset.
 *
 * OD-2: spoolman_filament_ref is NOT sent; backend resolves via material-default policy.
 * NFR24-NO-422-1: backend guarantees no 422 on the offer path; no availability pre-check needed.
 */
export function useOfferEstimate(stlHash: string, offerId: string) {
  return useQuery<EstimateView>({
    queryKey: ["estimates", stlHash, { offerId }],
    queryFn: () => {
      const params = new URLSearchParams({
        stl_hash: stlHash,
        offer_id: offerId,
      });
      // OD-2: spoolman_filament_ref deliberately omitted
      return api<EstimateView>(`/estimates?${params.toString()}`);
    },
    staleTime: OFFER_ESTIMATE_STALE_TIME_MS,
    gcTime: OFFER_ESTIMATE_GC_TIME_MS,
    retry: false,
    enabled: offerId.length > 0 && stlHash.length > 0,
  });
}
