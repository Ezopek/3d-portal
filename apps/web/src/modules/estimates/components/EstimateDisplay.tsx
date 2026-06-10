import { AlertTriangle, FileQuestion, Loader2, RefreshCw } from "lucide-react";
import { useTranslation } from "react-i18next";

import type { EstimateView, UIEstimateStatus } from "@/lib/api-types";
import { ProfileSourceBadge } from "@/modules/estimates/components/ProfileSourceBadge";
import {
  formatCost,
  formatDuration,
  formatLength,
  formatMass,
  formatVolume,
} from "@/modules/estimates/lib/format";
import { OverrideContextPanel } from "@/modules/estimates/components/OverrideContextPanel";
import { formatTimeOfDay, minutesSince } from "@/modules/spools/lib/format";
import { Button } from "@/ui/button";
import { EmptyState } from "@/ui/custom/EmptyState";

interface Props {
  /** Query-level (transport) states the FE owns — never server-reported. */
  isPending: boolean;
  isError: boolean;
  /** The UI-safe estimate body once the read succeeds. */
  data: EstimateView | undefined;
  onRetry: () => void;
  /** Injected for a deterministic soft-fail label (AC-12); defaults to wall clock. */
  now?: Date;
  /**
   * EST-RECOMPUTE-1 — request a guarded re-slice. When omitted, no recompute affordance is
   * rendered (keeps the pure-display call sites unchanged). Surfaced for the absent / stale /
   * failed states; a `queued` record is already in flight, so it shows no button.
   */
  onRecompute?: () => void;
  /** The recompute mutation is in flight (button disabled + spinner). */
  isRecomputing?: boolean;
  /** The recompute mutation failed (a small inline, retryable error line). */
  isRecomputeError?: boolean;
}

/**
 * Story 32.6 (AC-3, AC-6) — the estimate display, the status-honesty chokepoint.
 *
 * Renders every state HONESTLY and mutually-exclusively: loading (query pending) / fresh /
 * stale (servable numbers + "may be out of date") / queued (numbers + "recomputing…") /
 * failed ("here's why" keyed off `failure_reason`, numerics em-dash never 0) / absent
 * ("no estimate yet") / transport-error (retryable, distinct from absent+failed).
 *
 * It renders the record's ACTUAL `status` + `computed_at` — it never invents *why* a record
 * is stale, and never claims automatic live propagation (the SPOOL-EVT-1 honesty constraint,
 * AC-6). A `fresh` record (incl. one after a cost-only `update_cost`) carries NO staleness
 * banner; only `stale`/`queued` do.
 */
export function EstimateDisplay({
  isPending,
  isError,
  data,
  onRetry,
  now,
  onRecompute,
  isRecomputing = false,
  isRecomputeError = false,
}: Props) {
  const { t } = useTranslation();

  // The recompute affordance, rendered only when a handler is wired (pure-display call sites
  // pass none). Honest copy: an absent key reads "Estimate now", everything else "Recompute".
  const recompute = (status: UIEstimateStatus) =>
    onRecompute ? (
      <RecomputeButton
        status={status}
        onRecompute={onRecompute}
        isRecomputing={isRecomputing}
        isRecomputeError={isRecomputeError}
      />
    ) : null;

  // 1) loading — never flash absent/failed.
  if (isPending) {
    return (
      <div
        role="status"
        aria-busy="true"
        className="flex items-center gap-2 rounded-lg border p-4 text-sm text-muted-foreground"
      >
        <Loader2 className="size-4 animate-spin" aria-hidden />
        {t("modules.estimates.states.loading")}
      </div>
    );
  }

  // 2) transport error — retryable, distinct from absent/failed.
  if (isError || data === undefined) {
    return (
      <div role="alert" className="rounded-lg border border-destructive/40 p-2">
        <EmptyState
          messageKey="modules.estimates.states.error"
          tone="error"
          icon={<AlertTriangle className="size-8" />}
          action={{ labelKey: "common.retry", onClick: onRetry }}
        />
      </div>
    );
  }

  // 3) absent — explicit empty state, distinct from failed and from a transport error.
  if (data.status === "absent") {
    const isUnavailable =
      data.profile_selection_context?.estimate_profile_source ===
      "unavailable_no_profile";
    return (
      <div className="flex flex-col gap-3">
        <div role="status" className="rounded-lg border p-2">
          <EmptyState
            messageKey={
              isUnavailable
                ? "modules.estimates.states.absent.no_profile"
                : "modules.estimates.states.absent.body"
            }
            tone="muted"
            icon={<FileQuestion className="size-8" />}
          />
        </div>
        <OverrideContextPanel context={data.override_context} />
        {recompute("absent")}
      </div>
    );
  }

  // 4) failed — explicit "couldn't estimate, here's why"; numerics render as em-dash.
  if (data.status === "failed") {
    return (
      <div className="flex flex-col gap-3">
        <div
          role="alert"
          className="flex flex-col gap-2 rounded-lg border border-destructive/40 p-4"
        >
          <p className="flex items-center gap-2 font-medium text-destructive">
            <AlertTriangle className="size-4" aria-hidden />
            {t("modules.estimates.states.failed.title")}
          </p>
          {data.failure_reason !== null && (
            <p className="text-sm text-muted-foreground">
              {t(`modules.estimates.failure.${data.failure_reason}`)}
            </p>
          )}
        </div>
        <OverrideContextPanel context={data.override_context} />
        {data.profile_selection_context != null && (
          <ProfileSourceBadge context={data.profile_selection_context} />
        )}
        {recompute("failed")}
      </div>
    );
  }

  // 5) fresh / stale / queued — populated (or last-known) numbers + the honest banner.
  const isStale = data.status === "stale";
  const isQueued = data.status === "queued";

  return (
    <div className="flex flex-col gap-3">
      {isStale && (
        <p
          role="status"
          className="rounded-md border border-warning/40 bg-warning/10 px-3 py-2 text-sm"
        >
          {t("modules.estimates.states.stale_banner")}
        </p>
      )}
      {isQueued && (
        <p
          role="status"
          className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm text-muted-foreground"
        >
          <Loader2 className="size-4 animate-spin" aria-hidden />
          {t("modules.estimates.states.queued_banner")}
        </p>
      )}

      <dl className="grid grid-cols-2 gap-3 rounded-lg border p-4 text-sm">
        <Field
          label={t("modules.estimates.fields.duration")}
          value={formatDuration(data.time_seconds)}
        />
        <Field
          label={t("modules.estimates.fields.mass")}
          value={formatMass(data.filament_g)}
        />
        <Field
          label={t("modules.estimates.fields.length")}
          value={formatLength(data.filament_mm)}
        />
        <Field
          label={t("modules.estimates.fields.volume")}
          value={formatVolume(data.filament_cm3)}
        />
        <div className="col-span-2 flex flex-col gap-0.5">
          <Field
            label={t("modules.estimates.fields.cost")}
            value={formatCost(data.filament_cost, data.currency)}
          />
          <span className="text-xs text-muted-foreground">
            {t("modules.estimates.cost_informational")}
          </span>
        </div>
      </dl>

      {/* Soft-fail "Last estimated HH:MM (Xm ago)" for stale/queued records carrying a time. */}
      {(isStale || isQueued) && data.computed_at !== null && (
        <LastEstimated iso={data.computed_at} now={now} />
      )}

      {data.warnings.length > 0 && (
        <section
          aria-label={t("modules.estimates.warnings.title")}
          className="flex flex-col gap-1 rounded-lg border border-warning/40 p-3 text-sm"
        >
          <h3 className="font-medium">
            {t("modules.estimates.warnings.title")}
          </h3>
          <ul className="list-disc pl-5 text-muted-foreground">
            {data.warnings.map((w, i) => (
              <li key={`${w.code}-${i}`}>{w.message}</li>
            ))}
          </ul>
        </section>
      )}

      <OverrideContextPanel context={data.override_context} />
      {data.profile_selection_context != null && (
        <ProfileSourceBadge context={data.profile_selection_context} />
      )}
      {/* A stale estimate is the user-driven recompute case; a queued one is already in flight
          (no button), and a fresh one needs no recompute affordance. */}
      {isStale && recompute("stale")}
    </div>
  );
}

function RecomputeButton({
  status,
  onRecompute,
  isRecomputing,
  isRecomputeError,
}: {
  status: UIEstimateStatus;
  onRecompute: () => void;
  isRecomputing: boolean;
  isRecomputeError: boolean;
}) {
  const { t } = useTranslation();
  const label =
    status === "absent"
      ? t("modules.estimates.recompute.action_absent")
      : t("modules.estimates.recompute.action");
  return (
    <div className="flex flex-col gap-1">
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="self-start"
        disabled={isRecomputing}
        onClick={onRecompute}
      >
        {isRecomputing ? (
          <Loader2 className="size-3.5 animate-spin" aria-hidden />
        ) : (
          <RefreshCw className="size-3.5" aria-hidden />
        )}
        {isRecomputing ? t("modules.estimates.recompute.pending") : label}
      </Button>
      {isRecomputeError && (
        <p role="alert" className="text-xs text-destructive">
          {t("modules.estimates.recompute.error")}
        </p>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="font-medium tabular-nums">{value}</dd>
    </div>
  );
}

function LastEstimated({ iso, now }: { iso: string; now?: Date }) {
  const { t } = useTranslation();
  const time = formatTimeOfDay(iso);
  // Reuse the spools soft-fail helpers (FR20-FAILURE-1; do not re-author) — `now` injected
  // for deterministic tests/snapshots.
  const minutes =
    now === undefined ? minutesSince(iso) : minutesSince(iso, now);
  const text =
    minutes < 1
      ? t("modules.estimates.last_estimated", { time })
      : t("modules.estimates.last_estimated_with_ago", { time, ago: minutes });
  return <p className="text-xs text-muted-foreground">{text}</p>;
}
