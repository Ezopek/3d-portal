import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import {
  useLogoutOthers,
  useRevokeSession,
  useSessions,
} from "@/modules/catalog/hooks/useSessions";
import { AuthGate } from "@/shell/AuthGate";
import { Button } from "@/ui/button";
import { ConfirmDialog } from "@/ui/custom/ConfirmDialog";
import { LoadingState } from "@/ui/custom/LoadingState";
import { useState } from "react";

function Sessions() {
  const { data, isLoading } = useSessions();
  const revoke = useRevokeSession();
  const logoutOthers = useLogoutOthers();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [pendingCurrentRevoke, setPendingCurrentRevoke] = useState<string | null>(null);

  if (isLoading) return <LoadingState variant="spinner" className="p-6" />;

  const items = data?.items ?? [];
  const hasOthers = items.some((i) => !i.is_current);

  async function onRevoke(familyId: string, isCurrent: boolean) {
    if (isCurrent) {
      // Defer to the ConfirmDialog and let it call performCurrentRevoke().
      setPendingCurrentRevoke(familyId);
      return;
    }
    await revoke.mutateAsync(familyId);
  }

  async function performCurrentRevoke() {
    if (pendingCurrentRevoke === null) return;
    const familyId = pendingCurrentRevoke;
    setPendingCurrentRevoke(null);
    await revoke.mutateAsync(familyId);
    await navigate({ to: "/login", replace: true });
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-6">
      <h1 className="text-xl font-semibold">{t("auth.sessions.title")}</h1>
      <p className="text-sm text-muted-foreground">
        {t("auth.sessions.description")}
      </p>

      <Button
        variant="secondary"
        disabled={!hasOthers || logoutOthers.isPending}
        onClick={() => logoutOthers.mutate()}
      >
        {t("auth.sessions.logout_others")}
      </Button>

      {/* Desktop: table */}
      <div className="hidden rounded border border-border sm:block">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-3 py-2 text-left">
                {t("auth.sessions.device")}
              </th>
              <th className="px-3 py-2 text-left">{t("auth.sessions.ip")}</th>
              <th className="px-3 py-2 text-left">
                {t("auth.sessions.last_used")}
              </th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {items.map((s) => (
              <tr key={s.family_id} className="border-t border-border">
                <td className="px-3 py-2">
                  {s.user_agent || t("auth.sessions.unknown_device")}
                  {s.is_current && (
                    <span className="ml-2 rounded bg-primary/15 px-1.5 py-0.5 text-xs">
                      {t("auth.sessions.current")}
                    </span>
                  )}
                </td>
                <td className="px-3 py-2">
                  {s.ip || t("auth.sessions.unknown_ip")}
                </td>
                <td className="px-3 py-2" title={s.last_used_at ?? ""}>
                  {s.last_used_at
                    ? new Date(s.last_used_at).toLocaleString()
                    : "—"}
                </td>
                <td className="px-3 py-2 text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => void onRevoke(s.family_id, s.is_current)}
                  >
                    {t("auth.sessions.revoke")}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile: cards */}
      <div className="space-y-2 sm:hidden">
        {items.map((s) => (
          <div
            key={s.family_id}
            className="rounded border border-border p-3 text-sm"
          >
            <div className="flex items-center justify-between">
              <span className="font-medium">
                {s.user_agent || t("auth.sessions.unknown_device")}
              </span>
              {s.is_current && (
                <span className="rounded bg-primary/15 px-1.5 py-0.5 text-xs">
                  {t("auth.sessions.current")}
                </span>
              )}
            </div>
            <div className="mt-1 text-muted-foreground">
              {s.ip || t("auth.sessions.unknown_ip")} &middot;{" "}
              {s.last_used_at
                ? new Date(s.last_used_at).toLocaleString()
                : "—"}
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="mt-2"
              onClick={() => void onRevoke(s.family_id, s.is_current)}
            >
              {t("auth.sessions.revoke")}
            </Button>
          </div>
        ))}
      </div>
      <ConfirmDialog
        open={pendingCurrentRevoke !== null}
        onOpenChange={(next) => {
          if (!next) setPendingCurrentRevoke(null);
        }}
        title={t("auth.sessions.confirm_revoke_current")}
        confirmLabel={t("auth.sessions.revoke")}
        destructive
        pending={revoke.isPending}
        onConfirm={() => void performCurrentRevoke()}
      />
    </div>
  );
}

export const Route = createFileRoute("/settings/sessions")({
  component: () => (
    <AuthGate>
      <Sessions />
    </AuthGate>
  ),
});
