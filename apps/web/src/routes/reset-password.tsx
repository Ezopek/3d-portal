import { createFileRoute, useNavigate, useSearch } from "@tanstack/react-router";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, api } from "@/lib/api";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";

interface ResetPasswordSearch {
  token?: string;
}

type FullPageError = "token_missing" | "token_invalid";

function ResetPassword() {
  const { t } = useTranslation();
  const search = useSearch({ from: "/reset-password" });
  const navigate = useNavigate();
  const passwordId = useId();

  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [fullPageError, setFullPageError] = useState<FullPageError | null>(
    search.token ? null : "token_missing",
  );

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!search.token) return;
    setPasswordError(null);
    setPending(true);
    try {
      await api<void>("/auth/password-reset", {
        method: "POST",
        body: JSON.stringify({ token: search.token, new_password: password }),
      });
      await navigate({ to: "/login", search: { reset: "success" } });
    } catch (err) {
      const apiErr = err instanceof ApiError ? err : null;
      const rawDetail = ((apiErr?.body as { detail?: unknown }) ?? {}).detail;
      const detail = typeof rawDetail === "string" ? rawDetail : "";
      if (apiErr?.status === 404) {
        setFullPageError("token_invalid");
      } else if (apiErr?.status === 422) {
        setPasswordError(detail || t("auth.reset_password.error.unexpected"));
      } else {
        setPasswordError(t("auth.reset_password.error.unexpected"));
      }
      setPending(false);
    }
  }

  if (fullPageError) {
    return (
      <div className="mx-auto mt-12 grid w-full max-w-sm gap-4 p-4 text-center">
        <h1 className="text-xl font-semibold">{t("auth.reset_password.title")}</h1>
        <p className="text-sm text-destructive" role="alert">
          {t(`auth.reset_password.error.${fullPageError}`)}
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="mx-auto mt-12 grid w-full max-w-sm gap-4 p-4">
      <h1 className="text-xl font-semibold">{t("auth.reset_password.title")}</h1>
      <div className="grid gap-1.5">
        <label htmlFor={passwordId} className="text-sm font-medium">
          {t("auth.password")}
        </label>
        <Input
          id={passwordId}
          name="new_password"
          type="password"
          autoComplete="new-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={pending}
        />
        {passwordError !== null && (
          <p className="text-sm text-destructive" role="alert">
            {passwordError}
          </p>
        )}
      </div>
      <Button type="submit" disabled={pending}>
        {pending
          ? t("auth.reset_password.setting_password")
          : t("auth.reset_password.title")}
      </Button>
    </form>
  );
}

export const Route = createFileRoute("/reset-password")({
  component: ResetPassword,
  validateSearch: (raw: Record<string, unknown>): ResetPasswordSearch =>
    typeof raw.token === "string" && raw.token.length > 0
      ? { token: raw.token }
      : {},
});
