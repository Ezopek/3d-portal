import { createFileRoute, useNavigate, useSearch } from "@tanstack/react-router";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";

interface LoginSearch {
  next?: string;
}

function Login() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const navigate = useNavigate();
  const search = useSearch({ from: "/login" });
  const qc = useQueryClient();
  const emailId = useId();
  const passwordId = useId();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      await qc.invalidateQueries({ queryKey: ["auth", "me"] });
      const next = search.next ? decodeURIComponent(search.next) : "/";
      await navigate({ to: next as "/" });
    } catch {
      setError(t("auth.error.invalid_credentials"));
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto mt-12 grid w-full max-w-sm gap-4 p-4">
      <h1 className="text-xl font-semibold">{t("auth.login")}</h1>
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
    return typeof raw.next === "string" && raw.next.length > 0
      ? { next: raw.next }
      : {};
  },
});
