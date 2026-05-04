import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "@/lib/api";
import { writeToken } from "@/lib/auth";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";

interface LoginResponse {
  access_token: string;
  expires_in: number;
}

function Login() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const r = await api<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      writeToken(r.access_token, r.expires_in);
      // Full page navigation: AuthProvider reads localStorage synchronously at
      // its top-level render, so soft-nav (TanStack Router) leaves the auth
      // context stale until a reload. Router-aware refresh lands in a later
      // slice; for now hard-load is the minimal correct behavior.
      window.location.assign("/");
    } catch {
      setError(t("errors.not_found"));
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto mt-12 grid w-full max-w-sm gap-4 p-4">
      <h1 className="text-xl font-semibold">{t("auth.login")}</h1>
      <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder={t("auth.email")} type="email" />
      <Input value={password} onChange={(e) => setPassword(e.target.value)} placeholder={t("auth.password")} type="password" />
      {error !== null && <p className="text-sm text-destructive">{error}</p>}
      <Button type="submit">{t("auth.login")}</Button>
    </form>
  );
}

export const Route = createFileRoute("/login")({ component: Login });
