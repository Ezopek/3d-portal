import { Navigate, createFileRoute } from "@tanstack/react-router";

import type { AdminUserSortBy, AdminUserSortOrder } from "@/lib/api-types";
import { UsersPage } from "@/modules/admin/UsersPage";
import { AuthGate } from "@/shell/AuthGate";
import { useAuth } from "@/shell/AuthContext";

interface AdminUsersSearch {
  page?: number;
  page_size?: number;
  search?: string;
  sort_by?: AdminUserSortBy;
  sort_order?: AdminUserSortOrder;
}

function AdminUsersRoute() {
  const { isAdmin, isLoading } = useAuth();
  if (isLoading) return null;
  if (!isAdmin) return <Navigate to="/" replace />;
  return <UsersPage />;
}

const SORT_COLUMNS: AdminUserSortBy[] = [
  "email",
  "role",
  "created_at",
  "last_active_at",
];

export const Route = createFileRoute("/admin/users")({
  component: () => (
    <AuthGate>
      <AdminUsersRoute />
    </AuthGate>
  ),
  validateSearch: (raw: Record<string, unknown>): AdminUsersSearch => {
    const out: AdminUsersSearch = {};
    if (typeof raw.page === "number" && raw.page >= 1) out.page = raw.page;
    else if (typeof raw.page === "string" && /^\d+$/.test(raw.page))
      out.page = Number(raw.page);
    if (typeof raw.page_size === "number") out.page_size = raw.page_size;
    else if (typeof raw.page_size === "string" && /^\d+$/.test(raw.page_size))
      out.page_size = Number(raw.page_size);
    if (typeof raw.search === "string" && raw.search.length > 0)
      out.search = raw.search;
    if (
      typeof raw.sort_by === "string" &&
      (SORT_COLUMNS as readonly string[]).includes(raw.sort_by)
    ) {
      out.sort_by = raw.sort_by as AdminUserSortBy;
    }
    if (raw.sort_order === "asc" || raw.sort_order === "desc") {
      out.sort_order = raw.sort_order;
    }
    return out;
  },
});
