import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { BrowseCategoryRead } from "@/lib/api-types";

// Initiative 26 (Story 50.1) — the flat, ordered browse-category list.
// staleTime 5 min: browse categories are admin-governed reference data
// (FR26-CAT-1), mutated only through the Story 49.5 admin endpoints and never
// on the member browse path, so a ≤5-minute window between an admin edit and a
// member's automatic refetch is the accepted staleness budget for a navigation
// rail. The key is a PREFIX of useCategoryBySlug's, so a single future
// invalidateQueries({ queryKey: ["sot", "categories"] }) refreshes both.
export function useCategories() {
  return useQuery<BrowseCategoryRead[]>({
    queryKey: ["sot", "categories"],
    queryFn: () => api<BrowseCategoryRead[]>("/categories"),
    staleTime: 5 * 60 * 1000,
  });
}
