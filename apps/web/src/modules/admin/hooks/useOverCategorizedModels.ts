import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { OverCategorizedResponse } from "@/lib/api-types";

// Story 52.3 (B-1 / D-9) — the curation-QA over-categorized check.
//
// The key is a CHILD of the shipped admin key `["sot","admin-categories"]`,
// which is the opposite call from 52.2's sibling decision — and for a reason
// that inverts. There, a child of the PUBLIC key would have made every member's
// browse-rail invalidation refetch an admin-only endpoint. Here the parent is
// already admin-only, and every write that can change a model's category count
// already sweeps that prefix via `invalidateCategories`, so the child is kept
// coherent for free and costs no new invalidation code.
const KEY = ["sot", "admin-categories", "over-categorized"] as const;

export function useOverCategorizedModels(minCategories: number) {
  return useQuery<OverCategorizedResponse>({
    queryKey: [...KEY, minCategories],
    queryFn: () =>
      api<OverCategorizedResponse>(
        `/admin/models/over-categorized?min_categories=${minCategories}`,
      ),
    // Pinned to `useAdminCategories`'s budget because the two render on the
    // SAME screen from the SAME admin-mutated corpus, swept by the SAME
    // invalidation — not because that hook happens to use this number. A longer
    // budget would let the panel assert "3 models are over-categorized" directly
    // above a list that has already moved on.
    staleTime: 10 * 1000,
  });
}
