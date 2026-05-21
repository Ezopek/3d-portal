import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { SessionsListParams, SessionsResponse } from "@/lib/api-types";

/**
 * Story 12.5: list active session families for the current user.
 *
 * Defaults to page=1, page_size=20, sort_by=last_used_at, sort_order=desc
 * (matches the backend's own defaults — passing them explicitly is harmless
 * but lets the query key disambiguate so each page is cached independently).
 */
export function useSessions(params: SessionsListParams = {}) {
  const search = new URLSearchParams();
  if (params.page !== undefined) search.set("page", String(params.page));
  if (params.page_size !== undefined)
    search.set("page_size", String(params.page_size));
  if (params.sort_by !== undefined) search.set("sort_by", params.sort_by);
  if (params.sort_order !== undefined) search.set("sort_order", params.sort_order);
  const qs = search.toString();
  const url = qs ? `/auth/sessions?${qs}` : "/auth/sessions";
  return useQuery<SessionsResponse>({
    queryKey: ["auth", "sessions", params],
    queryFn: () => api<SessionsResponse>(url),
    staleTime: 30 * 1000,
  });
}

export function useRevokeSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (familyId: string) =>
      api<void>(`/auth/sessions/${familyId}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["auth", "sessions"] }),
  });
}

export function useLogoutOthers() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api<void>("/auth/logout-others", { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["auth", "sessions"] }),
  });
}
