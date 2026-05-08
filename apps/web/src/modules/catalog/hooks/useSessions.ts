import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { SessionsResponse } from "@/lib/api-types";

export function useSessions() {
  return useQuery<SessionsResponse>({
    queryKey: ["auth", "sessions"],
    queryFn: () => api<SessionsResponse>("/auth/sessions"),
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
