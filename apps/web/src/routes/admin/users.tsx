import { Navigate, createFileRoute } from "@tanstack/react-router";

import type { AdminUserSortBy, AdminUserSortOrder } from "@/lib/api-types";
import { UsersPage } from "@/modules/admin/UsersPage";
import { useAuth } from "@/shell/AuthContext";

interface AdminUsersSearch {
  page?: number;
  page_size?: number;
  search?: string;
  sort_by?: AdminUserSortBy;
  sort_order?: AdminUserSortOrder;
  // Story 12.2 — `show_inactive=1` flips the page from "active-only" (default)
  // to "show all (active + inactive)". Default behavior (param absent) hides
  // deactivated accounts. Boolean-shaped via `1` only so URLs stay shareable +
  // round-tripable through Tanstack's stringifier without quoting.
  show_inactive?: 1;
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
  // Initiative 6 Story 11.3 — shell-level AuthGate (AppShell.tsx Decision O)
  // handles the authenticated-vs-anonymous redirect. AdminUsersRoute's
  // inner `isAdmin` check remains as the role-tier gate (member-authenticated
  // user navigating here gets redirected to / per the inner Navigate).
  component: AdminUsersRoute,
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
    // Story 12.2 — accept only the literal `1` (number or string); any other
    // value is treated as absent so the page falls back to active-only.
    if (raw.show_inactive === 1 || raw.show_inactive === "1") {
      out.show_inactive = 1;
    }
    return out;
  },
});
