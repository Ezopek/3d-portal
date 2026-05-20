import { useNavigate, useSearch } from "@tanstack/react-router";
import { useId } from "react";
import { useTranslation } from "react-i18next";

import type { AdminUserSortBy, AdminUserSortOrder } from "@/lib/api-types";
import { AdminTabs } from "@/modules/admin/AdminTabs";
import { useAdminUsers } from "@/modules/admin/hooks/useAdminUsers";
import { LoadingState } from "@/ui/custom/LoadingState";

const PAGE_SIZE_OPTIONS = [25, 50, 100, 200] as const;
const SORTABLE_COLUMNS: AdminUserSortBy[] = [
  "email",
  "role",
  "created_at",
  "last_active_at",
];

function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("pl-PL");
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pl-PL");
}

function nextSortOrder(
  current: { sort_by?: AdminUserSortBy; sort_order?: AdminUserSortOrder },
  column: AdminUserSortBy,
): { sort_by: AdminUserSortBy | undefined; sort_order: AdminUserSortOrder | undefined } {
  if (current.sort_by !== column) return { sort_by: column, sort_order: "asc" };
  if (current.sort_order === "asc") return { sort_by: column, sort_order: "desc" };
  return { sort_by: undefined, sort_order: undefined };
}

export function UsersPage() {
  const { t } = useTranslation();
  const search = useSearch({ from: "/admin/users" });
  const navigate = useNavigate();
  const searchId = useId();
  const pageSizeId = useId();

  const page = search.page ?? 1;
  const pageSize = search.page_size ?? 50;
  const searchValue = search.search ?? "";

  const query = useAdminUsers({
    page,
    page_size: pageSize,
    search: searchValue || undefined,
    sort_by: search.sort_by,
    sort_order: search.sort_order,
  });

  function updateSearchParams(
    next: Partial<{
      page: number;
      page_size: number;
      search: string;
      sort_by: AdminUserSortBy | undefined;
      sort_order: AdminUserSortOrder | undefined;
    }>,
  ) {
    void navigate({
      to: "/admin/users",
      search: (prev) => {
        const merged: Record<string, unknown> = { ...prev, ...next };
        for (const key of Object.keys(merged)) {
          if (merged[key] === undefined || merged[key] === "") {
            delete merged[key];
          }
        }
        return merged;
      },
      replace: true,
    });
  }

  function onHeaderClick(column: AdminUserSortBy) {
    const { sort_by, sort_order } = nextSortOrder(
      { sort_by: search.sort_by, sort_order: search.sort_order },
      column,
    );
    updateSearchParams({ sort_by, sort_order, page: 1 });
  }

  function sortIndicator(column: AdminUserSortBy): string {
    if (search.sort_by !== column) return "";
    return search.sort_order === "asc" ? " ↑" : " ↓";
  }

  if (query.isLoading) {
    return <LoadingState variant="spinner" className="p-6" />;
  }

  const data = query.data;
  const total = data?.total ?? 0;
  const items = data?.items ?? [];
  const first = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-6">
      <header className="space-y-1">
        <h1 className="text-xl font-semibold">{t("admin.users.title")}</h1>
        <p className="text-sm text-muted-foreground">
          {t("admin.users.description")}
        </p>
      </header>

      <AdminTabs activeTab="users" />

      <div className="flex flex-wrap items-end gap-3">
        <div className="grid gap-1.5">
          <label htmlFor={searchId} className="text-sm font-medium">
            {t("admin.users.search_placeholder")}
          </label>
          <input
            id={searchId}
            type="search"
            value={searchValue}
            placeholder={t("admin.users.search_placeholder")}
            className="rounded border border-border bg-background px-3 py-1.5 text-sm"
            onChange={(e) =>
              updateSearchParams({ search: e.target.value, page: 1 })
            }
          />
        </div>
        <div className="grid gap-1.5">
          <label htmlFor={pageSizeId} className="text-sm font-medium">
            {t("admin.users.page_size_label")}
          </label>
          <select
            id={pageSizeId}
            value={pageSize}
            className="rounded border border-border bg-background px-3 py-1.5 text-sm"
            onChange={(e) =>
              updateSearchParams({
                page_size: Number(e.target.value),
                page: 1,
              })
            }
          >
            {PAGE_SIZE_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>
      </div>

      {query.isError ? (
        <p role="alert" className="text-sm text-destructive">
          {t("admin.users.error_loading")}
        </p>
      ) : (
        <div className="rounded border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th
                  className="px-3 py-2 text-left cursor-pointer select-none"
                  onClick={() => onHeaderClick("email")}
                >
                  {t("admin.users.column_email")}
                  {sortIndicator("email")}
                </th>
                <th className="px-3 py-2 text-left">
                  {t("admin.users.column_display_name")}
                </th>
                <th
                  className="px-3 py-2 text-left cursor-pointer select-none"
                  onClick={() => onHeaderClick("role")}
                >
                  {t("admin.users.column_role")}
                  {sortIndicator("role")}
                </th>
                <th className="px-3 py-2 text-left">
                  {t("admin.users.column_totp")}
                </th>
                <th className="px-3 py-2 text-left">
                  {t("admin.users.column_active")}
                </th>
                <th
                  className="px-3 py-2 text-left cursor-pointer select-none"
                  onClick={() => onHeaderClick("created_at")}
                >
                  {t("admin.users.column_created_at")}
                  {sortIndicator("created_at")}
                </th>
                <th
                  className="px-3 py-2 text-left cursor-pointer select-none"
                  onClick={() => onHeaderClick("last_active_at")}
                >
                  {t("admin.users.column_last_active_at")}
                  {sortIndicator("last_active_at")}
                </th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr>
                  <td
                    colSpan={SORTABLE_COLUMNS.length + 3}
                    className="px-3 py-6 text-center text-muted-foreground"
                  >
                    {t("admin.users.empty")}
                  </td>
                </tr>
              ) : (
                items.map((user) => (
                  <tr key={user.id} className="border-t border-border">
                    <td className="px-3 py-2">{user.email}</td>
                    <td className="px-3 py-2">{user.display_name}</td>
                    <td className="px-3 py-2">{user.role}</td>
                    <td className="px-3 py-2">
                      {user.totp_enabled
                        ? t("admin.users.totp_enabled_short")
                        : t("admin.users.totp_disabled_short")}
                    </td>
                    <td className="px-3 py-2">
                      {user.is_active
                        ? t("admin.users.active_yes")
                        : t("admin.users.active_no")}
                    </td>
                    <td className="px-3 py-2" title={user.created_at}>
                      {formatDate(user.created_at)}
                    </td>
                    <td className="px-3 py-2" title={user.last_active_at ?? ""}>
                      {formatDateTime(user.last_active_at)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      <footer className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          {t("admin.users.pagination_label", { first, last, total })}
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={page <= 1}
            className="rounded border border-border px-3 py-1.5 text-sm disabled:opacity-50"
            onClick={() => updateSearchParams({ page: page - 1 })}
          >
            {t("admin.users.pagination_previous")}
          </button>
          <button
            type="button"
            disabled={page * pageSize >= total}
            className="rounded border border-border px-3 py-1.5 text-sm disabled:opacity-50"
            onClick={() => updateSearchParams({ page: page + 1 })}
          >
            {t("admin.users.pagination_next")}
          </button>
        </div>
      </footer>
    </div>
  );
}
