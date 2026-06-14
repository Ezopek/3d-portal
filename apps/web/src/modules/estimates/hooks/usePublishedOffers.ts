import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { MemberPublishedOfferListResponse } from "@/lib/api-types";

// because "offer list changes only when admin publishes; 30s freshness avoids hammering
// the backend on every tab visit while still picking up new offers after refocus."
// (UX §D.5, cache-coherence: staleness budget covers infrequent admin-side mutations)
const OFFERS_STALE_TIME_MS = 30_000;
// because "keep warm across tab switches — match useEstimate GC budget (Decision AD)."
const OFFERS_GC_TIME_MS = 5 * 60_000;

/**
 * Story 36.3 (AC-2) / Story 38.3 (AC-2) — member-facing published offer list hook.
 *
 * Cache key: ["member", "offers", "published", { material }]
 * Deliberately different from the preset estimate key family so clearing the offer
 * cache on material switch does not evict preset estimate cache entries.
 *
 * Disabled when !isAuthenticated (AuthGate discipline, NFR24-AUTHGATE-1) or when
 * there are no STL files (no offer picker needed).
 *
 * material is optional (Story 38.3): when undefined, lists ALL published offers
 * (no ?material param sent). Backend already supports omitted material (returns all).
 */
export function usePublishedOffers(
  material: string | undefined,
  options: { isAuthenticated: boolean; hasStlFiles: boolean },
) {
  return useQuery<MemberPublishedOfferListResponse>({
    queryKey: ["member", "offers", "published", { material }],
    queryFn: () => {
      const params = new URLSearchParams();
      if (material) params.set("material", material);
      const query = params.toString();
      return api<MemberPublishedOfferListResponse>(
        `/profiles/offers/published${query ? `?${query}` : ""}`,
      );
    },
    staleTime: OFFERS_STALE_TIME_MS,
    gcTime: OFFERS_GC_TIME_MS,
    refetchOnWindowFocus: true,
    // retry: false per UX §D.5 — transport error shows Retry affordance, not auto-retry
    retry: false,
    enabled: options.isAuthenticated && options.hasStlFiles,
  });
}
