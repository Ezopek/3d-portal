import { createFileRoute, useNavigate, useSearch } from "@tanstack/react-router";
import { useState } from "react";
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
      setError(t("errors.not_found"));
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto mt-12 grid w-full max-w-sm gap-4 p-4">
      <h1 className="text-xl font-semibold">{t("auth.login")}</h1>
      <Input
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder={t("auth.email")}
        type="email"
        disabled={pending}
      />
      <Input
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder={t("auth.password")}
        type="password"
        disabled={pending}
      />
      {error !== null && <p className="text-sm text-destructive">{error}</p>}
      <Button type="submit" disabled={pending}>
        {t("auth.login")}
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
