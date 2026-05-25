import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { ModelDetail } from "@/lib/api-types";

// Initiative 18 Story 30.2 round-5 (Codex P2 chain — round-3 + round-4
// trade-off resolution) — MemberShareView needs to:
//
//   (a) Surface a fresh authoritative model state on each share visit
//       (round-2 + round-3 P2: don't reuse stale cached data; surface
//       deletes/revokes promptly).
//   (b) Stay coherent with admin mutations performed from /catalog/$id
//       OR from the share view itself (round-4 P2: mutations invalidate
//       the canonical key, share view should re-render).
//
// The two constraints are in tension: (a) wants a private cache, (b)
// wants the shared catalog cache. Resolution: use the CANONICAL key
// (`['sot', 'models', id]`) so mutations propagate, BUT override the
// observer options (staleTime: 0 + refetchOnMount: "always" + retry:
// false) so every share-page mount triggers a fresh GET that
// supersedes any cached value. The cached value is briefly served
// during the in-flight refetch (React Query stale-while-revalidate
// semantics) — accepted trade-off; the flash is bounded to one
// network round-trip and is rare in practice (requires the recipient
// to have visited /catalog/$id within the last 30s AND the model to
// have been deleted in between, on the same browser tab).
export function useShareModelProbe(modelId: string) {
  return useQuery<ModelDetail>({
    queryKey: ["sot", "models", modelId],
    queryFn: () => api<ModelDetail>(`/models/${modelId}`),
    enabled: modelId.length > 0,
    staleTime: 0,
    refetchOnMount: "always",
    retry: false,
  });
}
