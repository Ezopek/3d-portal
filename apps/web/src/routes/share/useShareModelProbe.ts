import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { ModelDetail } from "@/lib/api-types";

// Initiative 18 Story 30.2 round-3 (Codex P2) — MemberShareView needs to
// know "does this model still exist?" without sharing cache with the
// canonical /catalog/$id useModel hook. Sharing the catalog-cache would
// let a recently-loaded-then-deleted model render as valid (cached
// success short-circuits the probe), AND default retry backoff would
// delay the 404 → AnonymousShareView fallthrough.
//
// This hook uses a share-specific queryKey so the probe is fully isolated
// from the catalog cache, runs with no caching (staleTime + gcTime 0),
// always re-fetches on mount, and disables retries so a real 404 surfaces
// immediately.
//
// Cost: one extra network round-trip per share visit (the canonical
// CatalogDetailBody fires its own useModel separately). Accepted as the
// price of full revocation-contract closure on the share path.
export function useShareModelProbe(modelId: string) {
  return useQuery<ModelDetail>({
    queryKey: ["share", "model-probe", modelId],
    queryFn: () => api<ModelDetail>(`/models/${modelId}`),
    enabled: modelId.length > 0,
    staleTime: 0,
    gcTime: 0,
    refetchOnMount: "always",
    retry: false,
  });
}
