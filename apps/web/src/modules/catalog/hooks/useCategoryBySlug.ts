import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { BrowseCategoryRead } from "@/lib/api-types";

// Initiative 26 (Story 50.1) — one browse category by its stable slug.
// Deliberately NOT seeded from the useCategories list result even though both
// return the same shape: seeding would let a 404 on an unknown slug resolve
// silently from a stale list, erasing a contract distinction Decision AY draws
// on purpose (`/categories/{slug}` 404s; `?category=<unknown>` degrades to an
// empty page). Two independent canonical keys, no cross-seeding.
// No `enabled` guard — the caller passes a non-empty slug, mirroring useModel.
export function useCategoryBySlug(slug: string) {
  return useQuery<BrowseCategoryRead>({
    queryKey: ["sot", "categories", slug],
    queryFn: () => api<BrowseCategoryRead>(`/categories/${slug}`),
    staleTime: 5 * 60 * 1000,
  });
}
