import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/ui/button";
import { Input } from "@/ui/input";

interface Reauth2faModalProps {
  title: string;
  submitLabel: string;
  pending: boolean;
  error: string | null;
  onSubmit: (password: string, totp_code: string) => void;
  onCancel: () => void;
}

export function Reauth2faModal({
  title,
  submitLabel,
  pending,
  error,
  onSubmit,
  onCancel,
}: Reauth2faModalProps) {
  const { t } = useTranslation();
  const passwordId = useId();
  const codeId = useId();
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");

  const submitDisabled = pending || password.length === 0 || code.length !== 6;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (submitDisabled) return;
    onSubmit(password, code);
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      data-testid="reauth-2fa-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40"
    >
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md space-y-4 rounded-md border border-border bg-background p-6 shadow-lg"
      >
        <h2 className="text-lg font-semibold">{title}</h2>
        <div className="space-y-2">
          <label htmlFor={passwordId} className="block text-sm font-medium">
            {t("auth.2fa.reauth.password_label")}
          </label>
          <Input
            id={passwordId}
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={pending}
            autoFocus
          />
        </div>
        <div className="space-y-2">
          <label htmlFor={codeId} className="block text-sm font-medium">
            {t("auth.2fa.reauth.code_label")}
          </label>
          <Input
            id={codeId}
            inputMode="numeric"
            pattern="\d{6}"
            maxLength={6}
            autoComplete="one-time-code"
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            disabled={pending}
            className="w-32 font-mono tracking-widest"
          />
        </div>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onCancel}>
            {t("auth.2fa.reauth.cancel")}
          </Button>
          <Button type="submit" disabled={submitDisabled}>
            {submitLabel}
          </Button>
        </div>
      </form>
    </div>
  );
}
