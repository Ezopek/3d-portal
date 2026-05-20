import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import type {
  AdminInvitesListResponse,
  GenerateInviteRequest,
  GenerateInviteResponse,
  InviteStatus,
} from "@/lib/api-types";

export interface UseAdminInvitesParams {
  page: number;
  page_size: number;
  status?: InviteStatus;
}

function buildQueryString(params: UseAdminInvitesParams): string {
  const usp = new URLSearchParams();
  usp.set("page", String(params.page));
  usp.set("page_size", String(params.page_size));
  if (params.status) usp.set("status", params.status);
  return usp.toString();
}

export function useAdminInvites(params: UseAdminInvitesParams) {
  return useQuery<AdminInvitesListResponse>({
    queryKey: ["admin", "invites", params],
    queryFn: () =>
      api<AdminInvitesListResponse>(`/admin/invites?${buildQueryString(params)}`),
    staleTime: 30 * 1000,
  });
}

export function useGenerateInvite() {
  const queryClient = useQueryClient();
  return useMutation<GenerateInviteResponse, ApiError, GenerateInviteRequest>({
    mutationFn: (body) =>
      api<GenerateInviteResponse>("/admin/invites", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "invites"] });
    },
  });
}

export function useRevokeInvite() {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: (invite_id) =>
      api<void>(`/admin/invites/${invite_id}/revoke`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "invites"] });
    },
  });
}
