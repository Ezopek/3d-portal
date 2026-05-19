import { useQueryClient } from "@tanstack/react-query";
import { createFileRoute, useNavigate, useSearch } from "@tanstack/react-router";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, api } from "@/lib/api";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";

interface RegisterSearch {
  token?: string;
}

type FullPageError = "token_missing" | "token_invalid" | "token_consumed";

interface RegisterResponse {
  user: {
    id: string;
    email: string;
    display_name: string;
    role: string;
  };
}

function Register() {
  const { t } = useTranslation();
  const search = useSearch({ from: "/register" });
  const navigate = useNavigate();
  const qc = useQueryClient();
  const emailId = useId();
  const passwordId = useId();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [fullPageError, setFullPageError] = useState<FullPageError | null>(
    search.token ? null : "token_missing",
  );

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!search.token) return;
    setEmailError(null);
    setPasswordError(null);
    setPending(true);
    try {
      const res = await api<RegisterResponse>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ token: search.token, email, password }),
      });
      await qc.invalidateQueries({ queryKey: ["auth", "me"] });
      // Story 7.4 Codex P1 follow-up: when ENFORCE_2FA_FOR_ROLES contains
      // the invite-bound role, the backend surfaces totp_enroll_required;
      // mirror the login flow's redirect so first session does not bypass
      // enforcement by landing in /catalog before enrollment.
      if (res && (res as { totp_enroll_required?: boolean }).totp_enroll_required) {
        await navigate({ to: "/settings/2fa" });
      } else {
        await navigate({ to: "/catalog" });
      }
    } catch (err) {
      const apiErr = err instanceof ApiError ? err : null;
      const rawDetail = ((apiErr?.body as { detail?: unknown }) ?? {}).detail;
      const detail = typeof rawDetail === "string" ? rawDetail : "";
      if (apiErr?.status === 404) {
        setFullPageError("token_invalid");
      } else if (apiErr?.status === 410) {
        setFullPageError("token_consumed");
      } else if (apiErr?.status === 409) {
        setEmailError(t("auth.register.error.email_taken"));
      } else if (apiErr?.status === 422) {
        // FastAPI emits string detail for our explicit weak_password reasons,
        // but pydantic body-validation surfaces detail as an array of objects.
        // Only the string form is safe to render directly.
        setPasswordError(detail || t("auth.register.error.validation_failed"));
      } else {
        setPasswordError(t("auth.register.error.unexpected"));
      }
      setPending(false);
    }
  }

  if (fullPageError) {
    return (
      <div className="mx-auto mt-12 grid w-full max-w-sm gap-4 p-4 text-center">
        <h1 className="text-xl font-semibold">{t("auth.register.title")}</h1>
        <p className="text-sm text-destructive" role="alert">
          {t(`auth.register.error.${fullPageError}`)}
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="mx-auto mt-12 grid w-full max-w-sm gap-4 p-4">
      <h1 className="text-xl font-semibold">{t("auth.register.title")}</h1>
      <div className="grid gap-1.5">
        <label htmlFor={emailId} className="text-sm font-medium">
          {t("auth.email")}
        </label>
        <Input
          id={emailId}
          name="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={pending}
        />
        {emailError !== null && (
          <p className="text-sm text-destructive" role="alert">
            {emailError}
          </p>
        )}
      </div>
      <div className="grid gap-1.5">
        <label htmlFor={passwordId} className="text-sm font-medium">
          {t("auth.password")}
        </label>
        <Input
          id={passwordId}
          name="password"
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
        {pending ? t("auth.register.signing_up") : t("auth.register.title")}
      </Button>
    </form>
  );
}

export const Route = createFileRoute("/register")({
  component: Register,
  validateSearch: (raw: Record<string, unknown>): RegisterSearch =>
    typeof raw.token === "string" && raw.token.length > 0 ? { token: raw.token } : {},
});
