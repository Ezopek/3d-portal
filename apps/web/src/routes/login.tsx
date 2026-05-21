import { createFileRoute, useNavigate, useSearch } from "@tanstack/react-router";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";

import { ApiError, api } from "@/lib/api";
import type { LoginResponse, PartialAuthResponse } from "@/lib/api-types";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";

interface LoginSearch {
  next?: string;
  reset?: "success";
}

type SubState = "email_password" | "second_factor";

function Login() {
  const { t } = useTranslation();
  const [subState, setSubState] = useState<SubState>("email_password");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [partialToken, setPartialToken] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const navigate = useNavigate();
  const search = useSearch({ from: "/login" });
  const qc = useQueryClient();
  const emailId = useId();
  const passwordId = useId();
  const codeId = useId();

  async function submitEmailPassword(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      const resp = await api<LoginResponse | PartialAuthResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      if (resp.partial_auth === true) {
        setPartialToken(resp.partial_token);
        setSubState("second_factor");
        setPending(false);
        return;
      }
      // Story 7.4 — forced-enrollment for Decision F roles (totp_enroll_required).
      // Cookies ARE set by this branch; the user is single-factor authenticated.
      // Navigate to /settings/2fa carrying the original `next` so the page can
      // hand them back after enrollment completes.
      if (resp.totp_enroll_required === true) {
        await qc.invalidateQueries({ queryKey: ["auth", "me"] });
        // Initiative 6 Story 11.3 / Codex P2 round-2 (2026-05-21) — `search.next`
        // arrives already decoded once by TanStack Router's URLSearchParams
        // handling. The producer (AppShell.tsx / AuthGate.tsx) now passes the
        // raw `pathname + searchStr` to navigate() so the router can encode
        // it once; the consumer must NOT decodeURIComponent again or
        // percent-sequences in the original URL get double-decoded
        // (e.g. /catalog?discount=50%25 would break or 50% literal escape).
        const next = search.next || "/";
        await navigate({ to: "/settings/2fa", search: { next } });
        return;
      }
      await qc.invalidateQueries({ queryKey: ["auth", "me"] });
      const next = search.next ? decodeURIComponent(search.next) : "/";
      await navigate({ to: next as "/" });
    } catch {
      setError(t("auth.error.invalid_credentials"));
      setPending(false);
    }
  }

  async function submitSecondFactor(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      await api<LoginResponse>("/auth/2fa/verify", {
        method: "POST",
        body: JSON.stringify({ partial_token: partialToken, code }),
      });
      await qc.invalidateQueries({ queryKey: ["auth", "me"] });
      const next = search.next ? decodeURIComponent(search.next) : "/";
      await navigate({ to: next as "/" });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        const detail = (err.body as { detail?: string })?.detail;
        if (detail === "partial_token_invalid") {
          setError(t("auth.2fa.verify.error.session_expired"));
        } else {
          setError(t("auth.2fa.verify.error.invalid_code"));
        }
      } else {
        setError(t("auth.2fa.verify.error.network"));
      }
      setPending(false);
    }
  }

  function backToEmailPassword() {
    setSubState("email_password");
    setPartialToken(null);
    setCode("");
    setError(null);
    setPending(false);
  }

  if (subState === "second_factor") {
    return (
      <form onSubmit={submitSecondFactor} className="mx-auto mt-12 grid w-full max-w-sm gap-4 p-4">
        <h1 className="text-xl font-semibold">{t("auth.2fa.verify.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("auth.2fa.verify.description")}</p>
        <div className="grid gap-1.5">
          <label htmlFor={codeId} className="text-sm font-medium">
            {t("auth.2fa.verify.code_label")}
          </label>
          <Input
            id={codeId}
            name="code"
            type="text"
            inputMode="text"
            pattern="(\d{6})|([0-9a-f]{8})"
            autoComplete="one-time-code"
            maxLength={8}
            required
            value={code}
            onChange={(e) => setCode(e.target.value)}
            disabled={pending}
            autoFocus
          />
        </div>
        {error !== null && (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        )}
        <Button type="submit" disabled={pending || code.length === 0}>
          {pending ? t("auth.signing_in") : t("auth.2fa.verify.submit_button")}
        </Button>
        <Button type="button" variant="ghost" onClick={backToEmailPassword} disabled={pending}>
          {t("auth.2fa.verify.back_button")}
        </Button>
      </form>
    );
  }

  return (
    <form onSubmit={submitEmailPassword} className="mx-auto mt-12 grid w-full max-w-sm gap-4 p-4">
      <h1 className="text-xl font-semibold">{t("auth.login")}</h1>
      {search.reset === "success" && (
        <p className="text-sm text-success" role="status">
          {t("auth.login.reset_success_banner")}
        </p>
      )}
      <div className="grid gap-1.5">
        <label htmlFor={emailId} className="text-sm font-medium">
          {t("auth.email")}
        </label>
        <Input
          id={emailId}
          name="email"
          type="email"
          autoComplete="username"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={pending}
        />
      </div>
      <div className="grid gap-1.5">
        <label htmlFor={passwordId} className="text-sm font-medium">
          {t("auth.password")}
        </label>
        <Input
          id={passwordId}
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={pending}
        />
      </div>
      {error !== null && <p className="text-sm text-destructive">{error}</p>}
      <Button type="submit" disabled={pending}>
        {pending ? t("auth.signing_in") : t("auth.login")}
      </Button>
    </form>
  );
}

export const Route = createFileRoute("/login")({
  component: Login,
  validateSearch: (raw: Record<string, unknown>): LoginSearch => {
    const out: LoginSearch = {};
    if (typeof raw.next === "string" && raw.next.length > 0) out.next = raw.next;
    if (raw.reset === "success") out.reset = "success";
    return out;
  },
});
