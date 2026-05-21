import { useNavigate, useSearch } from "@tanstack/react-router";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "@/lib/api";
import type {
  AdminInviteRow,
  GenerateInviteResponse,
  InviteStatus,
} from "@/lib/api-types";
import { AdminTabs } from "@/modules/admin/AdminTabs";
import { GenerateInviteModal } from "@/modules/admin/GenerateInviteModal";
import { InviteTokenDisplayModal } from "@/modules/admin/InviteTokenDisplayModal";
import {
  useAdminInvites,
  useGenerateInvite,
  useRevokeInvite,
} from "@/modules/admin/hooks/useAdminInvites";
import { Button } from "@/ui/button";
import { ConfirmDialog } from "@/ui/custom/ConfirmDialog";
import { LoadingState } from "@/ui/custom/LoadingState";

const PAGE_SIZE_OPTIONS = [25, 50, 100, 200] as const;
const STATUS_OPTIONS: InviteStatus[] = ["active", "used", "expired", "revoked"];

const KNOWN_ERROR_CODES = new Set([
  "invite_not_found",
  "invite_already_resolved",
]);

const STATUS_BADGE_CLASSES: Record<InviteStatus, string> = {
  active: "bg-success/10 text-success-foreground",
  used: "bg-muted text-muted-foreground",
  expired: "bg-warning/10 text-warning-foreground",
  revoked: "bg-destructive/10 text-destructive",
};

function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("pl-PL");
}

function detailFromApiError(err: unknown): string | null {
  if (!(err instanceof ApiError)) return null;
  const body = err.body as { detail?: unknown } | null | undefined;
  if (body && typeof body.detail === "string") return body.detail;
  return null;
}

export function InvitesPage() {
  const { t } = useTranslation();
  const search = useSearch({ from: "/admin/invites" });
  const navigate = useNavigate();
  const statusId = useId();
  const pageSizeId = useId();

  const page = search.page ?? 1;
  const pageSize = search.page_size ?? 50;
  const statusFilter = search.status;

  const query = useAdminInvites({
    page,
    page_size: pageSize,
    status: statusFilter,
  });

  const generateInvite = useGenerateInvite();
  const revokeInvite = useRevokeInvite();

  const [generateModalOpen, setGenerateModalOpen] = useState(false);
  const [confirmRevokeTarget, setConfirmRevokeTarget] =
    useState<AdminInviteRow | null>(null);
  const [displayedToken, setDisplayedToken] =
    useState<GenerateInviteResponse | null>(null);
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

  function updateSearchParams(
    next: Partial<{
      page: number;
      page_size: number;
      status: InviteStatus | undefined;
    }>,
  ) {
    void navigate({
      to: "/admin/invites",
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

  function handleGenerateConfirm(payload: {
    role: "member" | "admin";
    ttl_preset: "ONE_DAY" | "THREE_DAYS" | "SEVEN_DAYS" | "THIRTY_DAYS";
  }) {
    clearError();
    generateInvite.mutate(payload, {
      onSuccess: (resp) => {
        setGenerateModalOpen(false);
        setDisplayedToken(resp);
      },
      onError: handleMutationError,
    });
  }

  function handleRevokeConfirm() {
    const target = confirmRevokeTarget;
    if (!target) return;
    clearError();
    revokeInvite.mutate(target.invite_id, {
      onSuccess: () => setConfirmRevokeTarget(null),
      onError: handleMutationError,
    });
  }

  if (query.isLoading) {
    return <LoadingState variant="spinner" className="p-6" />;
  }

  const data = query.data;
  const total = data?.total ?? 0;
  const items = data?.items ?? [];
  const first = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);
  const pending = generateInvite.isPending || revokeInvite.isPending;

  return (
    <div className="mx-auto max-w-7xl space-y-4 p-6">
      <header className="space-y-1">
        <h1 className="text-xl font-semibold">{t("admin.invites.title")}</h1>
        <p className="text-sm text-muted-foreground">
          {t("admin.invites.description")}
        </p>
      </header>

      <AdminTabs activeTab="invites" />

      {errorCode !== null && (
        <p role="alert" className="text-sm text-destructive">
          {t(`admin.invites.errors.${errorCode}`)}
        </p>
      )}

      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-wrap items-end gap-3">
          <div className="grid gap-1.5">
            <label htmlFor={statusId} className="text-sm font-medium">
              {t("admin.invites.filter_label")}
            </label>
            <select
              id={statusId}
              value={statusFilter ?? ""}
              className="rounded border border-border bg-background px-3 py-1.5 text-sm"
              onChange={(e) => {
                const v = e.target.value;
                updateSearchParams({
                  status: v ? (v as InviteStatus) : undefined,
                  page: 1,
                });
              }}
            >
              <option value="">{t("admin.invites.filter_all")}</option>
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {t(`admin.invites.filter_${opt}`)}
                </option>
              ))}
            </select>
          </div>
          <div className="grid gap-1.5">
            <label htmlFor={pageSizeId} className="text-sm font-medium">
              {t("admin.invites.page_size_label")}
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
        <Button
          onClick={() => {
            clearError();
            setGenerateModalOpen(true);
          }}
        >
          {t("admin.invites.actions.generate")}
        </Button>
      </div>

      {query.isError ? (
        <p role="alert" className="text-sm text-destructive">
          {t("admin.invites.error_loading")}
        </p>
      ) : (
        <div className="rounded border border-border overflow-x-auto">
          <table className="w-full min-w-[1200px] text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-3 py-2 text-left">
                  {t("admin.invites.column_role")}
                </th>
                <th className="px-3 py-2 text-left">
                  {t("admin.invites.column_generated_by")}
                </th>
                <th className="px-3 py-2 text-left">
                  {t("admin.invites.column_generated_at")}
                </th>
                <th className="px-3 py-2 text-left">
                  {t("admin.invites.column_expires_at")}
                </th>
                <th className="px-3 py-2 text-left">
                  {t("admin.invites.column_used_by")}
                </th>
                <th className="px-3 py-2 text-left">
                  {t("admin.invites.column_used_at")}
                </th>
                <th className="px-3 py-2 text-left">
                  {t("admin.invites.column_used_from_ip")}
                </th>
                <th className="px-3 py-2 text-left">
                  {t("admin.invites.column_revoked_at")}
                </th>
                <th className="px-3 py-2 text-left">
                  {t("admin.invites.column_status")}
                </th>
                <th className="px-3 py-2 text-left">
                  {t("admin.invites.column_actions")}
                </th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr>
                  <td
                    colSpan={10}
                    className="px-3 py-6 text-center text-muted-foreground"
                  >
                    {t("admin.invites.empty")}
                  </td>
                </tr>
              ) : (
                items.map((invite) => {
                  const isActive = invite.status === "active";
                  return (
                    <tr
                      key={invite.invite_id}
                      className="border-t border-border"
                    >
                      <td className="px-3 py-2">{invite.role}</td>
                      <td className="px-3 py-2">
                        {invite.generated_by_user_id ?? "—"}
                      </td>
                      <td className="px-3 py-2" title={invite.generated_at}>
                        {formatDateTime(invite.generated_at)}
                      </td>
                      <td className="px-3 py-2" title={invite.expires_at}>
                        {formatDateTime(invite.expires_at)}
                      </td>
                      <td className="px-3 py-2">
                        {invite.used_by_user_id ?? "—"}
                      </td>
                      <td
                        className="px-3 py-2"
                        title={invite.used_at ?? ""}
                      >
                        {formatDateTime(invite.used_at)}
                      </td>
                      <td className="px-3 py-2">
                        {invite.used_from_ip ?? "—"}
                      </td>
                      <td
                        className="px-3 py-2"
                        title={invite.revoked_at ?? ""}
                      >
                        {formatDateTime(invite.revoked_at)}
                      </td>
                      <td className="px-3 py-2">
                        <span
                          className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${STATUS_BADGE_CLASSES[invite.status]}`}
                        >
                          {t(`admin.invites.status.${invite.status}`)}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        {isActive ? (
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => {
                              clearError();
                              setConfirmRevokeTarget(invite);
                            }}
                          >
                            {t("admin.invites.actions.revoke")}
                          </Button>
                        ) : (
                          <span
                            aria-disabled="true"
                            className="text-muted-foreground"
                          >
                            —
                          </span>
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
          {t("admin.invites.pagination_label", { first, last, total })}
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={page <= 1}
            className="rounded border border-border px-3 py-1.5 text-sm disabled:opacity-50"
            onClick={() => updateSearchParams({ page: page - 1 })}
          >
            {t("admin.invites.pagination_previous")}
          </button>
          <button
            type="button"
            disabled={page * pageSize >= total}
            className="rounded border border-border px-3 py-1.5 text-sm disabled:opacity-50"
            onClick={() => updateSearchParams({ page: page + 1 })}
          >
            {t("admin.invites.pagination_next")}
          </button>
        </div>
      </footer>

      <GenerateInviteModal
        open={generateModalOpen}
        onOpenChange={(next) => {
          if (!next) setGenerateModalOpen(false);
        }}
        pending={generateInvite.isPending}
        onConfirm={handleGenerateConfirm}
      />

      <ConfirmDialog
        open={confirmRevokeTarget !== null}
        onOpenChange={(next) => {
          if (!next) setConfirmRevokeTarget(null);
        }}
        title={t("admin.invites.confirm.revoke_title", {
          role: confirmRevokeTarget?.role ?? "",
        })}
        description={t("admin.invites.confirm.revoke_description")}
        destructive
        pending={pending}
        onConfirm={handleRevokeConfirm}
      />

      {displayedToken && (
        <InviteTokenDisplayModal
          open
          onOpenChange={(next) => {
            if (!next) setDisplayedToken(null);
          }}
          role={displayedToken.role}
          registrationUrl={displayedToken.registration_url}
          expiresAt={displayedToken.expires_at}
        />
      )}
    </div>
  );
}
