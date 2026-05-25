import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

// Initiative 18 Story 30.2 — wraps Story 30.1's authenticated share-resolve
// endpoint (GET /api/me/share-links/<token>/resolve). The endpoint requires
// authentication (current_user dep); 401 surfaces as ApiError(status=401)
// caught by MemberShareView's defensive fallback. 404 covers
// invalid/expired/revoked tokens AND soft-deleted models (uniform 404 per
// Story 30.1 NFR18-TOKEN-ENUMERATION-1).
//
// `retry: false` because 404/401 are decisive: we don't want to thrash
// the backend retrying a token the server has already classified as
// unresolvable.
//
// Story 30.2 round-2 (Codex P1) — caching the resolve response across
// mounts would let a previously-resolved token keep MemberShareView
// rendering after the owner revoked the link OR soft-deleted the model.
// Mirror the shareBlobCache page-mount invalidation contract (Story 23.1
// TB-033 Decision X.1 policy A): always re-fetch on mount + drop the
// cache when the last subscriber unmounts. Token-state is small (one
// roundtrip) so cost is negligible; the alternative — stale cache holding
// a revoked token open for up to 5 min — violates the revocation
// contract guaranteed by Init 12 Story 19.5 + the existing route-unmount
// `clearShareBlobCache()`.
export interface ShareResolveResponse {
  model_id: string;
  access: "granted";
}

export function useShareResolve(token: string) {
  return useQuery<ShareResolveResponse>({
    queryKey: ["share", "resolve", token],
    queryFn: () => api<ShareResolveResponse>(`/me/share-links/${encodeURIComponent(token)}/resolve`),
    retry: false,
    staleTime: 0,
    gcTime: 0,
    refetchOnMount: "always",
  });
}
