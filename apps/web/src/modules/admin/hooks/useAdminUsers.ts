import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  AdminUserSortBy,
  AdminUserSortOrder,
  AdminUsersListResponse,
} from "@/lib/api-types";

export interface UseAdminUsersParams {
  page: number;
  page_size: number;
  search?: string;
  sort_by?: AdminUserSortBy;
  sort_order?: AdminUserSortOrder;
}

function buildQueryString(params: UseAdminUsersParams): string {
  const usp = new URLSearchParams();
  usp.set("page", String(params.page));
  usp.set("page_size", String(params.page_size));
  if (params.search && params.search.length > 0) usp.set("search", params.search);
  if (params.sort_by) usp.set("sort_by", params.sort_by);
  if (params.sort_order) usp.set("sort_order", params.sort_order);
  return usp.toString();
}

export function useAdminUsers(params: UseAdminUsersParams) {
  return useQuery<AdminUsersListResponse>({
    queryKey: ["admin", "users", params],
    queryFn: () =>
      api<AdminUsersListResponse>(`/admin/users?${buildQueryString(params)}`),
    staleTime: 30 * 1000,
  });
}
