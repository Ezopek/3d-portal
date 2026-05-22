import { useNavigate, useSearch } from "@tanstack/react-router";
import { MoreVertical } from "lucide-react";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "@/lib/api";
import type {
  AdminUser,
  AdminUserSortBy,
  AdminUserSortOrder,
  Role,
} from "@/lib/api-types";
import { AdminTabs } from "@/modules/admin/AdminTabs";
import { ChangeRoleModal } from "@/modules/admin/ChangeRoleModal";
import { ResetLinkDisplayModal } from "@/modules/admin/ResetLinkDisplayModal";
import {
  useAdminUsers,
  useForce2faEnrollmentAdminUser,
  useForceDisable2faAdminUser,
  useForceLogoutAdminUser,
  useIssuePasswordResetAdminUser,
  useUpdateAdminUser,
} from "@/modules/admin/hooks/useAdminUsers";
import { useAuth } from "@/shell/AuthContext";
import { Button } from "@/ui/button";
import { ConfirmDialog } from "@/ui/custom/ConfirmDialog";
import { LoadingState } from "@/ui/custom/LoadingState";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/ui/dropdown-menu";

const PAGE_SIZE_OPTIONS = [25, 50, 100, 200] as const;
const SORTABLE_COLUMNS: AdminUserSortBy[] = [
  "email",
  "role",
  "created_at",
  "last_active_at",
];

const KNOWN_ERROR_CODES = new Set([
  "cannot_target_self",
  "cannot_target_agent",
  "cannot_promote_to_agent",
  "no_mutation_provided",
  "user_not_found",
  "totp_already_enrolled",
  "already_force_enrolled",
  "totp_not_enrolled",
]);

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

function detailFromApiError(err: unknown): string | null {
  if (!(err instanceof ApiError)) return null;
  const body = err.body as { detail?: unknown } | null | undefined;
  if (body && typeof body.detail === "string") return body.detail;
  return null;
}

export function UsersPage() {
  const { t } = useTranslation();
  const search = useSearch({ from: "/admin/users" });
  const navigate = useNavigate();
  const searchId = useId();
  const pageSizeId = useId();
  const showInactiveId = useId();
  const auth = useAuth();
  const currentUserId = auth.user?.id ?? null;

  const page = search.page ?? 1;
  const pageSize = search.page_size ?? 50;
  const searchValue = search.search ?? "";
  // Story 12.2 — default behavior hides inactive accounts. The URL param
  // `show_inactive=1` flips the page to "show all"; absence means the API call
  // restricts to `is_active=true`. State is derived from the URL so the toggle
  // survives reloads and is shareable.
  const showInactive = search.show_inactive === 1;

  const query = useAdminUsers({
    page,
    page_size: pageSize,
    search: searchValue || undefined,
    sort_by: search.sort_by,
    sort_order: search.sort_order,
    is_active: showInactive ? undefined : true,
  });

  const updateUser = useUpdateAdminUser();
  const forceLogout = useForceLogoutAdminUser();
  const force2faEnrollment = useForce2faEnrollmentAdminUser();
  const forceDisable2fa = useForceDisable2faAdminUser();
  const issuePasswordReset = useIssuePasswordResetAdminUser();

  const [changeRoleTarget, setChangeRoleTarget] = useState<AdminUser | null>(null);
  const [confirmDeactivateTarget, setConfirmDeactivateTarget] =
    useState<AdminUser | null>(null);
  const [confirmReactivateTarget, setConfirmReactivateTarget] =
    useState<AdminUser | null>(null);
  const [confirmForceLogoutTarget, setConfirmForceLogoutTarget] =
    useState<AdminUser | null>(null);
  const [confirmForce2faEnrollmentTarget, setConfirmForce2faEnrollmentTarget] =
    useState<AdminUser | null>(null);
  const [confirmForceDisable2faTarget, setConfirmForceDisable2faTarget] =
    useState<AdminUser | null>(null);
  const [confirmIssuePasswordResetTarget, setConfirmIssuePasswordResetTarget] =
    useState<AdminUser | null>(null);
  const [displayedResetLink, setDisplayedResetLink] = useState<
    { reset_url: string; expires_at: string; email: string } | null
  >(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);

  function clearError() {
    setErrorCode(null);
  }

  function handleMutationError(err: unknown) {
    const detail = detailFromApiError(err);
    if (detail && KNOWN_ERROR_CODES.has(detail)) {
      setErrorCode(detail);
    } else {
      setErrorCode("generic");
    }
  }

  function handleChangeRoleConfirm(newRole: Role) {
    if (!changeRoleTarget) return;
    clearError();
    updateUser.mutate(
      { user_id: changeRoleTarget.id, body: { role: newRole } },
      {
        onSuccess: () => setChangeRoleTarget(null),
        onError: handleMutationError,
      },
    );
  }

  function handleDeactivateConfirm() {
    if (!confirmDeactivateTarget) return;
    clearError();
    updateUser.mutate(
      { user_id: confirmDeactivateTarget.id, body: { is_active: false } },
      {
        onSuccess: () => setConfirmDeactivateTarget(null),
        onError: handleMutationError,
      },
    );
  }

  function handleReactivateConfirm() {
    if (!confirmReactivateTarget) return;
    clearError();
    updateUser.mutate(
      { user_id: confirmReactivateTarget.id, body: { is_active: true } },
      {
        onSuccess: () => setConfirmReactivateTarget(null),
        onError: handleMutationError,
      },
    );
  }

  function handleForceLogoutConfirm() {
    if (!confirmForceLogoutTarget) return;
    clearError();
    forceLogout.mutate(confirmForceLogoutTarget.id, {
      onSuccess: () => setConfirmForceLogoutTarget(null),
      onError: handleMutationError,
    });
  }

  function handleForce2faEnrollmentConfirm() {
    if (!confirmForce2faEnrollmentTarget) return;
    clearError();
    force2faEnrollment.mutate(confirmForce2faEnrollmentTarget.id, {
      onSuccess: () => setConfirmForce2faEnrollmentTarget(null),
      onError: handleMutationError,
    });
  }

  function handleForceDisable2faConfirm() {
    if (!confirmForceDisable2faTarget) return;
    clearError();
    forceDisable2fa.mutate(confirmForceDisable2faTarget.id, {
      onSuccess: () => setConfirmForceDisable2faTarget(null),
      onError: handleMutationError,
    });
  }

  function handleIssuePasswordResetConfirm() {
    const target = confirmIssuePasswordResetTarget;
    if (!target) return;
    clearError();
    issuePasswordReset.mutate(target.id, {
      onSuccess: (resp) => {
        setConfirmIssuePasswordResetTarget(null);
        setDisplayedResetLink({
          reset_url: resp.reset_url,
          expires_at: resp.expires_at,
          email: target.email,
        });
      },
      onError: handleMutationError,
    });
  }

  function updateSearchParams(
    next: Partial<{
      page: number;
      page_size: number;
      search: string;
      sort_by: AdminUserSortBy | undefined;
      sort_order: AdminUserSortOrder | undefined;
      show_inactive: 1 | undefined;
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
  const pending =
    updateUser.isPending ||
    forceLogout.isPending ||
    force2faEnrollment.isPending ||
    forceDisable2fa.isPending ||
    issuePasswordReset.isPending;

  return (
    <div className="space-y-4 p-6">
      <header className="space-y-1">
        <h1 className="text-xl font-semibold">{t("admin.users.title")}</h1>
        <p className="text-sm text-muted-foreground">
          {t("admin.users.description")}
        </p>
      </header>

      <AdminTabs activeTab="users" />

      {errorCode !== null && (
        <p role="alert" className="text-sm text-destructive">
          {t(`admin.users.errors.${errorCode}`)}
        </p>
      )}

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
        {/* Story 12.2 — default-hide inactive accounts; checkbox reveals them. */}
        <div className="flex items-center gap-2 self-end py-1.5">
          <input
            id={showInactiveId}
            type="checkbox"
            checked={showInactive}
            aria-label={t("admin.users.filter_show_inactive")}
            className="size-4 rounded border-border"
            onChange={(e) =>
              updateSearchParams({
                show_inactive: e.target.checked ? 1 : undefined,
                page: 1,
              })
            }
          />
          <label htmlFor={showInactiveId} className="text-sm font-medium">
            {t("admin.users.filter_show_inactive")}
          </label>
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
                <th className="px-3 py-2 text-left">
                  {t("admin.users.column_force_2fa")}
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
                <th className="px-3 py-2 text-left">
                  {t("admin.users.column_actions")}
                </th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr>
                  <td
                    colSpan={SORTABLE_COLUMNS.length + 5}
                    className="px-3 py-6 text-center text-muted-foreground"
                  >
                    {t("admin.users.empty")}
                  </td>
                </tr>
              ) : (
                items.map((user) => {
                  const isSelf = currentUserId !== null && user.id === currentUserId;
                  const isAgent = user.role === "agent";
                  const actionsDisabled = isSelf || isAgent;
                  // Story 12.2 — muted styling on deactivated rows when shown.
                  const rowClassName = user.is_active
                    ? "border-t border-border"
                    : "border-t border-border bg-muted/30 text-muted-foreground";
                  return (
                    <tr key={user.id} className={rowClassName}>
                      <td className="px-3 py-2">
                        {user.is_active ? (
                          user.email
                        ) : (
                          <span className="line-through">{user.email}</span>
                        )}
                        {!user.is_active && (
                          <span className="ml-1 text-xs">
                            {t("admin.users.row_inactive_indicator")}
                          </span>
                        )}
                      </td>
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
                      <td className="px-3 py-2">
                        {user.force_2fa_enrollment
                          ? t("admin.users.totp_enabled_short")
                          : t("admin.users.totp_disabled_short")}
                      </td>
                      <td className="px-3 py-2" title={user.created_at}>
                        {formatDate(user.created_at)}
                      </td>
                      <td className="px-3 py-2" title={user.last_active_at ?? ""}>
                        {formatDateTime(user.last_active_at)}
                      </td>
                      <td className="px-3 py-2">
                        {actionsDisabled ? (
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            disabled
                            aria-disabled="true"
                            aria-label={t("admin.users.actions.menu_label", {
                              email: user.email,
                            })}
                            className="opacity-50 cursor-not-allowed"
                          >
                            <MoreVertical className="size-4" aria-hidden />
                          </Button>
                        ) : (
                          <DropdownMenu>
                            <DropdownMenuTrigger
                              render={
                                <Button
                                  variant="ghost"
                                  size="icon-sm"
                                  aria-label={t("admin.users.actions.menu_label", {
                                    email: user.email,
                                  })}
                                />
                              }
                            >
                              <MoreVertical className="size-4" aria-hidden />
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem
                                onClick={() => {
                                  clearError();
                                  setChangeRoleTarget(user);
                                }}
                              >
                                {t("admin.users.actions.change_role")}
                              </DropdownMenuItem>
                              {user.is_active ? (
                                <DropdownMenuItem
                                  variant="destructive"
                                  onClick={() => {
                                    clearError();
                                    setConfirmDeactivateTarget(user);
                                  }}
                                >
                                  {t("admin.users.actions.deactivate")}
                                </DropdownMenuItem>
                              ) : (
                                <DropdownMenuItem
                                  onClick={() => {
                                    clearError();
                                    setConfirmReactivateTarget(user);
                                  }}
                                >
                                  {t("admin.users.actions.reactivate")}
                                </DropdownMenuItem>
                              )}
                              <DropdownMenuItem
                                variant="destructive"
                                onClick={() => {
                                  clearError();
                                  setConfirmForceLogoutTarget(user);
                                }}
                              >
                                {t("admin.users.actions.force_logout")}
                              </DropdownMenuItem>
                              {!user.totp_enabled && !user.force_2fa_enrollment ? (
                                <DropdownMenuItem
                                  variant="destructive"
                                  onClick={() => {
                                    clearError();
                                    setConfirmForce2faEnrollmentTarget(user);
                                  }}
                                >
                                  {t("admin.users.actions.force_2fa_enrollment")}
                                </DropdownMenuItem>
                              ) : null}
                              {user.totp_enabled ? (
                                <DropdownMenuItem
                                  variant="destructive"
                                  onClick={() => {
                                    clearError();
                                    setConfirmForceDisable2faTarget(user);
                                  }}
                                >
                                  {t("admin.users.actions.force_disable_2fa")}
                                </DropdownMenuItem>
                              ) : null}
                              <DropdownMenuItem
                                onClick={() => {
                                  clearError();
                                  setConfirmIssuePasswordResetTarget(user);
                                }}
                              >
                                {t("admin.users.actions.issue_password_reset")}
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        )}
                      </td>
                    </tr>
                  );
                })
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

      <ChangeRoleModal
        open={changeRoleTarget !== null}
        onOpenChange={(next) => {
          if (!next) setChangeRoleTarget(null);
        }}
        target={changeRoleTarget}
        pending={pending}
        onConfirm={handleChangeRoleConfirm}
      />

      <ConfirmDialog
        open={confirmDeactivateTarget !== null}
        onOpenChange={(next) => {
          if (!next) setConfirmDeactivateTarget(null);
        }}
        title={t("admin.users.confirm.deactivate_title", {
          email: confirmDeactivateTarget?.email ?? "",
        })}
        description={t("admin.users.confirm.deactivate_description")}
        destructive
        pending={pending}
        onConfirm={handleDeactivateConfirm}
      />

      <ConfirmDialog
        open={confirmReactivateTarget !== null}
        onOpenChange={(next) => {
          if (!next) setConfirmReactivateTarget(null);
        }}
        title={t("admin.users.confirm.reactivate_title", {
          email: confirmReactivateTarget?.email ?? "",
        })}
        description={t("admin.users.confirm.reactivate_description")}
        pending={pending}
        onConfirm={handleReactivateConfirm}
      />

      <ConfirmDialog
        open={confirmForceLogoutTarget !== null}
        onOpenChange={(next) => {
          if (!next) setConfirmForceLogoutTarget(null);
        }}
        title={t("admin.users.confirm.force_logout_title", {
          email: confirmForceLogoutTarget?.email ?? "",
        })}
        description={t("admin.users.confirm.force_logout_description")}
        destructive
        pending={pending}
        onConfirm={handleForceLogoutConfirm}
      />

      <ConfirmDialog
        open={confirmForce2faEnrollmentTarget !== null}
        onOpenChange={(next) => {
          if (!next) setConfirmForce2faEnrollmentTarget(null);
        }}
        title={t("admin.users.confirm.force_2fa_enrollment_title", {
          email: confirmForce2faEnrollmentTarget?.email ?? "",
        })}
        description={t("admin.users.confirm.force_2fa_enrollment_description")}
        destructive
        pending={pending}
        onConfirm={handleForce2faEnrollmentConfirm}
      />

      <ConfirmDialog
        open={confirmForceDisable2faTarget !== null}
        onOpenChange={(next) => {
          if (!next) setConfirmForceDisable2faTarget(null);
        }}
        title={t("admin.users.confirm.force_disable_2fa_title", {
          email: confirmForceDisable2faTarget?.email ?? "",
        })}
        description={t("admin.users.confirm.force_disable_2fa_description")}
        destructive
        pending={pending}
        onConfirm={handleForceDisable2faConfirm}
      />

      <ConfirmDialog
        open={confirmIssuePasswordResetTarget !== null}
        onOpenChange={(next) => {
          if (!next) setConfirmIssuePasswordResetTarget(null);
        }}
        title={t("admin.users.confirm.issue_password_reset_title", {
          email: confirmIssuePasswordResetTarget?.email ?? "",
        })}
        description={t("admin.users.confirm.issue_password_reset_description")}
        pending={pending}
        onConfirm={handleIssuePasswordResetConfirm}
      />

      {displayedResetLink && (
        <ResetLinkDisplayModal
          open
          onOpenChange={(next) => {
            if (!next) setDisplayedResetLink(null);
          }}
          email={displayedResetLink.email}
          resetUrl={displayedResetLink.reset_url}
          expiresAt={displayedResetLink.expires_at}
        />
      )}
    </div>
  );
}
