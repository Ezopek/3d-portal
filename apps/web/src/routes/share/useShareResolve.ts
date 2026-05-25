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
// unresolvable. `staleTime` matches AuthContext meQuery (5 min).
export interface ShareResolveResponse {
  model_id: string;
  access: "granted";
}

export function useShareResolve(token: string) {
  return useQuery<ShareResolveResponse>({
    queryKey: ["share", "resolve", token],
    queryFn: () => api<ShareResolveResponse>(`/me/share-links/${encodeURIComponent(token)}/resolve`),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}
