import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { PrintProfileOfferListResponse, ProfileOffersFilters } from "@/lib/api-types";

/**
 * PROFILE-OFFER-1 (AC-18) — the admin PrintProfileOffer list.
 *
 * Cache topology (per the story's enumeration): `staleTime: 0` + `refetchOnMount: "always"`
 * because the admin must see the TRUE current offer state on entry — especially because
 * validation is RECOMPUTED server-side at read time (AC-10) and can flip after a referenced
 * block changes (e.g. a deleted block ⇒ `invalid · unknown_block`). The key namespace
 * (`["admin","profile-offers", …]`) is deliberately DISJOINT from the library's
 * `["admin","profile-library"]` and the grid's `["admin","profiles"]`: offer mutations never
 * cross-invalidate the library cache (offers reference blocks, they do not mutate them).
 */
export function useProfileOffers(filters?: ProfileOffersFilters) {
  return useQuery<PrintProfileOfferListResponse>({
    queryKey: ["admin", "profile-offers", filters ?? "all"],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filters?.material_category) params.set("material_category", filters.material_category);
      if (filters?.visibility) params.set("visibility", filters.visibility);
      const qs = params.toString();
      return api<PrintProfileOfferListResponse>(`/admin/profiles/offers${qs ? `?${qs}` : ""}`);
    },
    staleTime: 0,
    refetchOnMount: "always",
  });
}
