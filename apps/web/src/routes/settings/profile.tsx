import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { ApiError, api } from "@/lib/api";
import type { MeResponse } from "@/lib/api-types";
import { useAuth } from "@/shell/AuthContext";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";
import { LoadingState } from "@/ui/custom/LoadingState";

function ProfilePage() {
  const { t } = useTranslation();
  const { user, isLoading } = useAuth();
  const qc = useQueryClient();
  const displayNameId = useId();
  const emailId = useId();
  const hintId = useId();

  const [displayName, setDisplayName] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);

  // Seed the input from the authenticated user's persisted display_name on
  // first render (and re-seed if the cached /me response changes — e.g.
  // after an invalidate from elsewhere in the app).
  useEffect(() => {
    if (user?.display_name) {
      setDisplayName(user.display_name);
    }
  }, [user?.display_name]);

  const mutation = useMutation<MeResponse, Error, string>({
    mutationFn: (value: string) =>
      api<MeResponse>("/auth/me/display-name", {
        method: "PATCH",
        body: JSON.stringify({ display_name: value }),
      }),
    onSuccess: async (data) => {
      // Optimistic + canonical refresh: write the server response into the
      // ["auth","me"] cache so the user menu + any other consumer reflects
      // the new value immediately, then invalidate so background refetch
      // re-confirms against the server.
      qc.setQueryData(["auth", "me"], data);
      await qc.invalidateQueries({ queryKey: ["auth", "me"] });
      toast.success(t("settings.profile.saved_toast"));
    },
    onError: (err) => {
      const apiErr = err instanceof ApiError ? err : null;
      if (apiErr?.status === 422) {
        setFieldError(t("settings.profile.error.blank"));
      } else {
        setFieldError(t("settings.profile.error.unexpected"));
      }
    },
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setFieldError(null);
    const trimmed = displayName.trim();
    if (trimmed.length === 0) {
      setFieldError(t("settings.profile.error.blank"));
      return;
    }
    if (trimmed.length > 120) {
      setFieldError(t("settings.profile.error.too_long"));
      return;
    }
    mutation.mutate(trimmed);
  }

  if (isLoading || !user) {
    return <LoadingState variant="spinner" className="p-6" />;
  }

  const pending = mutation.isPending;
  const trimmed = displayName.trim();
  const unchanged = trimmed === user.display_name;
  const disabled = pending || unchanged || trimmed.length === 0;

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <header className="space-y-2">
        <h1 className="text-xl font-semibold">{t("settings.profile.title")}</h1>
        <p className="text-sm text-muted-foreground">
          {t("settings.profile.description")}
        </p>
      </header>

      <form onSubmit={submit} className="grid gap-4">
        <div className="grid gap-1.5">
          <label htmlFor={emailId} className="text-sm font-medium">
            {t("settings.profile.email_label")}
          </label>
          <Input
            id={emailId}
            type="email"
            value={user.email}
            readOnly
            disabled
            aria-readonly="true"
          />
        </div>
        <div className="grid gap-1.5">
          <label htmlFor={displayNameId} className="text-sm font-medium">
            {t("settings.profile.display_name_label")}
          </label>
          <Input
            id={displayNameId}
            name="display_name"
            type="text"
            autoComplete="nickname"
            aria-label={t("settings.profile.display_name_label")}
            aria-describedby={hintId}
            maxLength={120}
            required
            value={displayName}
            onChange={(e) => {
              setDisplayName(e.target.value);
              if (fieldError !== null) setFieldError(null);
            }}
            disabled={pending}
          />
          <p id={hintId} className="text-xs text-muted-foreground">
            {t("settings.profile.display_name_hint")}
          </p>
          {fieldError !== null && (
            <p className="text-sm text-destructive" role="alert">
              {fieldError}
            </p>
          )}
        </div>
        <div>
          <Button type="submit" disabled={disabled}>
            {pending
              ? t("settings.profile.submitting")
              : t("settings.profile.submit")}
          </Button>
        </div>
      </form>
    </div>
  );
}

export const Route = createFileRoute("/settings/profile")({
  // Shell-level AuthGate (AppShell.tsx Decision O) handles the anonymous
  // redirect; per-route wrapper is not needed.
  component: ProfilePage,
});
