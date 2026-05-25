import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { ModelDetail } from "@/lib/api-types";

// Initiative 18 Story 30.2 round-2 — `options.enabled` lets MemberShareView
// probe the model-detail status only after the share-resolve roundtrip
// hands us a model_id. Existing /catalog/$id callers omit the second arg
// and continue to fire unconditionally (backwards-compatible default).
export function useModel(id: string, options?: { enabled?: boolean }) {
  return useQuery<ModelDetail>({
    queryKey: ["sot", "models", id],
    queryFn: () => api<ModelDetail>(`/models/${id}`),
    staleTime: 30 * 1000,
    enabled: options?.enabled ?? true,
  });
}
