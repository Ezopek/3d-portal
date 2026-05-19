import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, api } from "@/lib/api";
import type {
  ReauthRequest,
  TotpConfirmRequest,
  TotpConfirmResponse,
  TotpEnrollResponse,
  TotpStatusResponse,
} from "@/lib/api-types";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";
import { LoadingState } from "@/ui/custom/LoadingState";

import { Reauth2faModal } from "./Reauth2faModal";

type WizardStep = "status" | "enroll" | "show-codes" | "done";

type ReauthModalMode = "regenerate" | "disable" | null;

interface EnrollState {
  qr_svg: string;
  manual_secret: string;
  enrollment_token: string;
}

interface CodesState {
  recovery_codes: string[];
  batch_id: string;
  generated_at: string;
}

export function Settings2faPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const search = useSearch({ from: "/settings/2fa" });
  const forcedEnrollmentMode = Boolean(search.next && search.next.length > 0);
  const codeInputId = useId();
  const savedCheckboxId = useId();
  const manualSecretId = useId();

  const [step, setStep] = useState<WizardStep>("status");
  const [enrollState, setEnrollState] = useState<EnrollState | null>(null);
  const [codesState, setCodesState] = useState<CodesState | null>(null);
  const [codeInput, setCodeInput] = useState("");
  const [codeError, setCodeError] = useState<string | null>(null);
  const [confirmedSaved, setConfirmedSaved] = useState(false);
  const [reauthModal, setReauthModal] = useState<ReauthModalMode>(null);
  // Story 7.5 Codex P2-2: when the user clicks Cancel on the reauth modal
  // while a destructive submit is in flight, hiding the modal alone leaves
  // ``onSuccess`` free to mutate page state (show codes / disable 2FA) once
  // the request settles. These refs flag the in-flight mutation as
  // user-cancelled so its ``onSuccess`` becomes a no-op.
  const regenerateCancelledRef = useRef(false);
  const disableCancelledRef = useRef(false);

  const status = useQuery<TotpStatusResponse>({
    queryKey: ["auth", "2fa", "status"],
    queryFn: () => api<TotpStatusResponse>("/auth/2fa/status"),
  });

  const enroll = useMutation<TotpEnrollResponse>({
    mutationFn: () =>
      api<TotpEnrollResponse>("/auth/2fa/enroll", { method: "POST" }),
    onSuccess: (data) => {
      setEnrollState({
        qr_svg: data.qr_svg,
        manual_secret: data.manual_secret,
        enrollment_token: data.enrollment_token,
      });
      setCodeInput("");
      setCodeError(null);
      setStep("enroll");
    },
    onError: (err) => {
      setCodeError(mapEnrollError(err, t));
    },
  });

  const regenerate = useMutation<TotpConfirmResponse, ApiError, ReauthRequest>({
    mutationFn: (body) =>
      api<TotpConfirmResponse>("/auth/2fa/recovery-codes/regenerate", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: (data) => {
      if (regenerateCancelledRef.current) {
        regenerateCancelledRef.current = false;
        return;
      }
      setCodesState({
        recovery_codes: data.recovery_codes,
        batch_id: data.batch_id,
        generated_at: data.generated_at,
      });
      setConfirmedSaved(false);
      setReauthModal(null);
      setStep("show-codes");
    },
    // onError is intentionally NOT set — error is surfaced inside the
    // Reauth2faModal via the mutation's `error` state through mapReauthError.
  });

  const disable = useMutation<void, ApiError, ReauthRequest>({
    mutationFn: (body) =>
      api<void>("/auth/2fa/disable", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      if (disableCancelledRef.current) {
        disableCancelledRef.current = false;
        return;
      }
      setReauthModal(null);
      void qc.invalidateQueries({ queryKey: ["auth", "2fa", "status"] });
      setStep("status");
    },
    // onError handled inside Reauth2faModal via mutation state.
  });

  const confirm = useMutation<TotpConfirmResponse, ApiError, TotpConfirmRequest>({
    mutationFn: (body) =>
      api<TotpConfirmResponse>("/auth/2fa/enroll/confirm", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: (data) => {
      setCodesState({
        recovery_codes: data.recovery_codes,
        batch_id: data.batch_id,
        generated_at: data.generated_at,
      });
      setConfirmedSaved(false);
      setStep("show-codes");
    },
    onError: (err) => {
      if (err.status === 422) {
        setCodeError(t("auth.2fa.error.invalid_code"));
      } else if (err.status === 404) {
        setCodeError(t("auth.2fa.error.enrollment_expired"));
      } else if (err.status === 409) {
        // Already enrolled — refetch status to surface the enabled panel.
        setStep("status");
        void qc.invalidateQueries({ queryKey: ["auth", "2fa", "status"] });
      } else if (err.status === 500) {
        setCodeError(t("auth.2fa.error.totp_not_configured"));
      } else {
        setCodeError(t("auth.2fa.error.network"));
      }
    },
  });

  function startEnrollment() {
    setCodeError(null);
    enroll.mutate();
  }

  function submitCode(e: React.FormEvent) {
    e.preventDefault();
    if (!enrollState) return;
    setCodeError(null);
    confirm.mutate({
      enrollment_token: enrollState.enrollment_token,
      code: codeInput,
    });
  }

  function restartEnrollment() {
    // Keep enrollState in place until the new /enroll response arrives —
    // clearing it eagerly with step still "enroll" makes the next render
    // skip both the enroll branch (no state) and the show-codes branch,
    // falling through to the "2FA enabled" done panel. If /enroll is slow
    // or fails the user would then see a false success state.
    setCodeInput("");
    setCodeError(null);
    enroll.mutate();
  }

  async function copyToClipboard(text: string) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* ignore — surfaced via aria-live in a richer impl */
    }
  }

  function downloadCodes() {
    if (!codesState) return;
    const header = `# 3d-portal recovery codes — generated at ${codesState.generated_at}`;
    const body = [header, ...codesState.recovery_codes].join("\n");
    const blob = new Blob([body], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `recovery-codes-${codesState.batch_id}.txt`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  }

  function continueToDone() {
    setCodesState(null);
    void qc.invalidateQueries({ queryKey: ["auth", "2fa", "status"] });
    if (forcedEnrollmentMode && search.next) {
      const next = decodeURIComponent(search.next);
      void navigate({ to: next as "/" });
      return;
    }
    setStep("done");
  }

  if (step === "status") {
    return (
      <div className="mx-auto max-w-3xl space-y-4 p-6">
        <h1 className="text-xl font-semibold">{t("auth.2fa.title")}</h1>
        {forcedEnrollmentMode && !status.data?.enabled && (
          <div
            role="alert"
            className="rounded-md border border-warning bg-warning/10 p-3 text-sm"
          >
            {t("auth.2fa.enroll.forced_banner")}
          </div>
        )}
        {status.isLoading ? (
          <LoadingState variant="spinner" />
        ) : status.data?.enabled ? (
          <EnabledPanel
            data={status.data}
            t={t}
            onRegenerateClick={() => setReauthModal("regenerate")}
            onDisableClick={() => setReauthModal("disable")}
          />
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {t("auth.2fa.enroll.description")}
            </p>
            <Button onClick={startEnrollment} disabled={enroll.isPending}>
              {t("auth.2fa.status.disabled.cta")}
            </Button>
            {codeError && (
              <p role="alert" className="text-sm text-destructive">
                {codeError}
              </p>
            )}
          </div>
        )}
        {reauthModal && (
          <Reauth2faModal
            title={
              reauthModal === "regenerate"
                ? t("auth.2fa.reauth.regenerate_title")
                : t("auth.2fa.reauth.disable_title")
            }
            submitLabel={
              reauthModal === "regenerate"
                ? t("auth.2fa.reauth.regenerate_submit")
                : t("auth.2fa.reauth.disable_submit")
            }
            pending={
              reauthModal === "regenerate"
                ? regenerate.isPending
                : disable.isPending
            }
            error={
              reauthModal === "regenerate"
                ? mapReauthError(regenerate.error, t)
                : mapReauthError(disable.error, t)
            }
            onSubmit={(password, totp_code) => {
              if (reauthModal === "regenerate") {
                regenerateCancelledRef.current = false;
                regenerate.mutate({ password, totp_code });
              } else {
                disableCancelledRef.current = false;
                disable.mutate({ password, totp_code });
              }
            }}
            onCancel={() => {
              // Mark BOTH destructive mutations as cancelled. ``isPending``
              // read in this closure can be stale right after ``mutate()``
              // — React batches the re-render that flips it to true.
              // Unconditional set is safe because ``onSubmit`` resets the
              // ref before kicking off the next mutation.
              regenerateCancelledRef.current = true;
              disableCancelledRef.current = true;
              setReauthModal(null);
            }}
          />
        )}
      </div>
    );
  }

  if (step === "enroll" && enrollState) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 p-6">
        <h1 className="text-xl font-semibold">{t("auth.2fa.enroll.title")}</h1>
        <p className="text-sm text-muted-foreground">
          {t("auth.2fa.enroll.description")}
        </p>
        <div
          aria-label={t("auth.2fa.qr_alt")}
          data-testid="totp-qr"
          className="inline-block rounded p-4"
          style={{ background: "hsl(0 0% 100%)" }}
          dangerouslySetInnerHTML={{ __html: enrollState.qr_svg }}
        />
        <span className="sr-only">{enrollState.manual_secret}</span>
        <details className="rounded border border-border p-3">
          <summary className="cursor-pointer text-sm font-medium">
            {t("auth.2fa.enroll.cant_scan")}
          </summary>
          <div className="mt-2 flex items-center gap-2">
            <code
              id={manualSecretId}
              className="rounded bg-muted px-2 py-1 font-mono text-sm"
            >
              {enrollState.manual_secret}
            </code>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void copyToClipboard(enrollState.manual_secret)}
            >
              {t("auth.2fa.enroll.copy_secret")}
            </Button>
          </div>
        </details>
        <form onSubmit={submitCode} className="space-y-2">
          <label htmlFor={codeInputId} className="block text-sm font-medium">
            {t("auth.2fa.enroll.code_label")}
          </label>
          <Input
            id={codeInputId}
            inputMode="numeric"
            pattern="\d{6}"
            maxLength={6}
            autoComplete="one-time-code"
            value={codeInput}
            onChange={(e) => setCodeInput(e.target.value.replace(/\D/g, ""))}
            className="w-32 font-mono tracking-widest"
          />
          {codeError && (
            <p role="alert" className="text-sm text-destructive">
              {codeError}
            </p>
          )}
          <div className="flex gap-2">
            <Button
              type="submit"
              disabled={
                confirm.isPending || enroll.isPending || codeInput.length !== 6
              }
            >
              {t("auth.2fa.enroll.verify_button")}
            </Button>
            <Button
              type="button"
              variant="ghost"
              onClick={restartEnrollment}
              disabled={enroll.isPending}
            >
              {t("auth.2fa.enroll.restart_button")}
            </Button>
          </div>
        </form>
      </div>
    );
  }

  if (step === "show-codes" && codesState) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 p-6">
        <h1 className="text-xl font-semibold">
          {t("auth.2fa.show_codes.title")}
        </h1>
        <p className="text-sm text-muted-foreground">
          {t("auth.2fa.show_codes.description")}
        </p>
        <ul
          data-testid="totp-recovery-codes"
          className="grid grid-cols-1 gap-2 rounded border border-border p-4 sm:grid-cols-2"
        >
          {codesState.recovery_codes.map((c) => (
            <li
              key={c}
              className="rounded bg-muted px-2 py-1 text-center font-mono text-sm"
            >
              <code>{c}</code>
            </li>
          ))}
        </ul>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            onClick={() =>
              void copyToClipboard(codesState.recovery_codes.join("\n"))
            }
          >
            {t("auth.2fa.show_codes.copy_all")}
          </Button>
          <Button variant="secondary" onClick={downloadCodes}>
            {t("auth.2fa.show_codes.download_button")}
          </Button>
        </div>
        <label
          htmlFor={savedCheckboxId}
          className="flex items-center gap-2 text-sm"
        >
          <input
            id={savedCheckboxId}
            type="checkbox"
            checked={confirmedSaved}
            onChange={(e) => setConfirmedSaved(e.target.checked)}
          />
          {t("auth.2fa.show_codes.saved_confirm")}
        </label>
        <Button onClick={continueToDone} disabled={!confirmedSaved}>
          {t("auth.2fa.show_codes.continue_button")}
        </Button>
      </div>
    );
  }

  // done
  return (
    <div className="mx-auto max-w-3xl space-y-4 p-6">
      <h1 className="text-xl font-semibold">{t("auth.2fa.done.title")}</h1>
      <p className="text-sm text-muted-foreground">
        {t("auth.2fa.done.description")}
      </p>
      <Link to="/settings/sessions" className="text-sm text-primary underline">
        {t("auth.2fa.done.back_link")}
      </Link>
    </div>
  );
}

interface EnabledPanelProps {
  data: TotpStatusResponse;
  t: ReturnType<typeof useTranslation>["t"];
  onRegenerateClick: () => void;
  onDisableClick: () => void;
}

function EnabledPanel({
  data,
  t,
  onRegenerateClick,
  onDisableClick,
}: EnabledPanelProps) {
  const generatedText = data.generated_at
    ? new Date(data.generated_at).toLocaleString()
    : "";
  return (
    <div className="space-y-3">
      <p className="text-sm font-medium">
        {t("auth.2fa.status.enabled.title")}
      </p>
      <p className="text-sm text-muted-foreground">
        {t("auth.2fa.status.enabled.codes_remaining", {
          count: data.codes_remaining ?? 0,
        })}
      </p>
      {data.generated_at && (
        <p className="text-sm text-muted-foreground">
          {t("auth.2fa.status.enabled.generated_at", { date: generatedText })}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={onRegenerateClick}>
          {t("auth.2fa.status.enabled.regenerate_button")}
        </Button>
        <Button variant="secondary" onClick={onDisableClick}>
          {t("auth.2fa.status.enabled.disable_button")}
        </Button>
      </div>
    </div>
  );
}

function mapEnrollError(
  err: unknown,
  t: ReturnType<typeof useTranslation>["t"],
): string {
  if (err instanceof ApiError) {
    if (err.status === 500) return t("auth.2fa.error.totp_not_configured");
    if (err.status === 409) return t("auth.2fa.error.enrollment_expired");
  }
  return t("auth.2fa.error.network");
}

function mapReauthError(
  err: ApiError | null,
  t: ReturnType<typeof useTranslation>["t"],
): string | null {
  if (!err) return null;
  if (err.status === 401) return t("auth.2fa.reauth.error.invalid_credentials");
  if (err.status === 429) return t("auth.2fa.reauth.error.rate_limited");
  if (err.status === 500) return t("auth.2fa.error.totp_not_configured");
  return t("auth.2fa.error.network");
}
