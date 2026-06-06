import { AlertTriangle, CheckCircle2, HelpCircle, type LucideIcon } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";
import { Button } from "@/ui/button";

import { AdminTabs } from "./AdminTabs";
import {
  type Liveness,
  type Outcome,
  type QueueEntry,
  type RecentJob,
  type RunningJob,
  useAdminQueues,
} from "./hooks/useAdminQueues";

const LIVENESS_META: Record<Liveness, { icon: LucideIcon; className: string }> = {
  // Status conveyed by icon + text + color, never color alone (WCAG 1.4.1, AC-20).
  alive: { icon: CheckCircle2, className: "text-success" },
  idle: { icon: AlertTriangle, className: "text-warning" },
  unknown: { icon: HelpCircle, className: "text-muted-foreground" },
};

function useDurationFormatter() {
  const { t } = useTranslation();
  return (seconds: number | null | undefined): string => {
    if (seconds === null || seconds === undefined) return "—";
    const s = Math.max(0, Math.round(seconds));
    if (s >= 3600) return t("modules.admin.queues.unit_hours", { n: Math.round(s / 3600) });
    if (s >= 60) return t("modules.admin.queues.unit_minutes", { n: Math.round(s / 60) });
    return t("modules.admin.queues.unit_seconds", { n: s });
  };
}

function LivenessChip({ worker }: { worker: QueueEntry["worker"] }) {
  const { t } = useTranslation();
  const fmt = useDurationFormatter();
  const meta = LIVENESS_META[worker.liveness];
  const Icon = meta.icon;
  return (
    <div className="flex flex-col gap-0.5">
      <span className={cn("inline-flex items-center gap-1 text-sm font-medium", meta.className)}>
        <Icon className="h-4 w-4" aria-hidden="true" />
        {t(`modules.admin.queues.liveness.${worker.liveness}`)}
      </span>
      {/* Surface heartbeat age + interval so the coarse (~1h) granularity is honest (AC-15). */}
      <span className="text-xs text-muted-foreground">
        {t("modules.admin.queues.heartbeat", {
          age: fmt(worker.heartbeat_age_s),
          interval: fmt(worker.interval_s),
        })}
      </span>
    </div>
  );
}

function QueueCard({ entry }: { entry: QueueEntry }) {
  const { t } = useTranslation();
  const counters = entry.worker.counters;
  return (
    <div className="flex flex-col gap-3 rounded-md border border-border bg-card p-4">
      <header className="flex flex-col gap-0.5">
        <h2 className="text-sm font-semibold text-card-foreground">
          {t(`modules.admin.queues.role.${entry.role}`)}
        </h2>
        {/* Technical queue id stays untranslated (AC-21). */}
        <code className="text-xs text-muted-foreground">{entry.name}</code>
      </header>

      <div className="flex gap-6">
        <div className="flex flex-col">
          <span className="text-2xl font-bold tabular-nums text-foreground">{entry.queued}</span>
          <span className="text-xs text-muted-foreground">
            {t("modules.admin.queues.queued")}
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-2xl font-bold tabular-nums text-foreground">{entry.running}</span>
          <span className="text-xs text-muted-foreground">
            {t("modules.admin.queues.running")}
          </span>
        </div>
      </div>

      <LivenessChip worker={entry.worker} />

      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        <div className="flex justify-between">
          <dt className="text-muted-foreground">{t("modules.admin.queues.counters.complete")}</dt>
          <dd className="tabular-nums text-foreground">{counters ? counters.complete : "—"}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-muted-foreground">{t("modules.admin.queues.counters.failed")}</dt>
          <dd
            className={cn(
              "tabular-nums",
              counters && counters.failed > 0
                ? "font-semibold text-destructive"
                : "text-foreground",
            )}
          >
            {counters ? counters.failed : "—"}
          </dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-muted-foreground">{t("modules.admin.queues.counters.retried")}</dt>
          <dd className="tabular-nums text-foreground">{counters ? counters.retried : "—"}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-muted-foreground">{t("modules.admin.queues.counters.ongoing")}</dt>
          <dd className="tabular-nums text-foreground">{counters ? counters.ongoing : "—"}</dd>
        </div>
      </dl>
    </div>
  );
}

function ContextLabel({ context }: { context: RunningJob["context"] }) {
  if (!context) return null;
  return (
    <span className="text-xs text-muted-foreground">
      {context.kind}
      {context.ref ? ` · ${context.ref}` : ""}
    </span>
  );
}

function RunningStrip({ jobs }: { jobs: RunningJob[] }) {
  const { t } = useTranslation();
  const fmt = useDurationFormatter();
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-sm font-semibold text-foreground">
        {t("modules.admin.queues.running_now")}
      </h2>
      {jobs.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("modules.admin.queues.nothing_running")}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {jobs.map((job) => (
            <li
              key={job.job_id}
              className="flex items-center justify-between rounded-md border border-border bg-card px-3 py-2"
            >
              <div className="flex flex-col gap-0.5">
                <span className="text-sm text-card-foreground">
                  <code>{job.function}</code>
                  <span className="text-muted-foreground"> · {job.queue}</span>
                </span>
                <ContextLabel context={job.context} />
              </div>
              <span className="text-xs tabular-nums text-muted-foreground">
                {t("modules.admin.queues.running_for", { age: fmt(job.started_age_s) })}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function RecentRow({ job }: { job: RecentJob }) {
  const { t } = useTranslation();
  const fmt = useDurationFormatter();
  const failed = job.outcome === "failed";
  const Icon = failed ? AlertTriangle : CheckCircle2;
  return (
    <li
      className={cn(
        "flex items-center justify-between rounded-md border px-3 py-2",
        failed ? "border-destructive/40 bg-destructive/10" : "border-border bg-card",
      )}
    >
      <div className="flex flex-col gap-0.5">
        <span className="inline-flex items-center gap-1 text-sm text-card-foreground">
          <Icon
            className={cn("h-4 w-4", failed ? "text-destructive" : "text-success")}
            aria-hidden="true"
          />
          <code>{job.function}</code>
          <span className="text-muted-foreground"> · {job.queue}</span>
        </span>
        <span className="flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
          <span>{t(`modules.admin.queues.outcome.${job.outcome}`)}</span>
          <span>· {t("modules.admin.queues.took", { duration: fmt(job.duration_s) })}</span>
          {job.context ? (
            <span>
              · {job.context.kind}
              {job.context.ref ? ` · ${job.context.ref}` : ""}
            </span>
          ) : null}
          {failed && job.error_class ? (
            <span className="font-medium text-destructive">· {job.error_class}</span>
          ) : null}
        </span>
      </div>
    </li>
  );
}

function RecentList({ jobs }: { jobs: RecentJob[] }) {
  const { t } = useTranslation();
  const [queueFilter, setQueueFilter] = useState<string>("all");
  const [outcomeFilter, setOutcomeFilter] = useState<"all" | Outcome>("all");

  const queues = useMemo(() => Array.from(new Set(jobs.map((j) => j.queue))).sort(), [jobs]);
  const filtered = useMemo(
    () =>
      jobs.filter(
        (j) =>
          (queueFilter === "all" || j.queue === queueFilter) &&
          (outcomeFilter === "all" || j.outcome === outcomeFilter),
      ),
    [jobs, queueFilter, outcomeFilter],
  );

  const selectClass =
    "rounded-md border border-border bg-card px-2 py-1 text-xs text-card-foreground";

  return (
    <section className="flex flex-col gap-2">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-foreground">
          {t("modules.admin.queues.recent")}
        </h2>
        {/* Honest retention caveat: a vanished failure is expired, not resolved (AC-17). */}
        <span className="text-xs text-muted-foreground">{t("modules.admin.queues.retention")}</span>
      </div>

      <div className="flex flex-wrap gap-2">
        <label className="flex items-center gap-1 text-xs text-muted-foreground">
          {t("modules.admin.queues.filter_queue")}
          <select
            className={selectClass}
            value={queueFilter}
            onChange={(e) => setQueueFilter(e.target.value)}
            aria-label={t("modules.admin.queues.filter_queue")}
          >
            <option value="all">{t("modules.admin.queues.filter_all")}</option>
            {queues.map((q) => (
              <option key={q} value={q}>
                {q}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-1 text-xs text-muted-foreground">
          {t("modules.admin.queues.filter_outcome")}
          <select
            className={selectClass}
            value={outcomeFilter}
            onChange={(e) => setOutcomeFilter(e.target.value as "all" | Outcome)}
            aria-label={t("modules.admin.queues.filter_outcome")}
          >
            <option value="all">{t("modules.admin.queues.filter_all")}</option>
            <option value="success">{t("modules.admin.queues.outcome.success")}</option>
            <option value="failed">{t("modules.admin.queues.outcome.failed")}</option>
          </select>
        </label>
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("modules.admin.queues.recent_empty")}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {filtered.map((job) => (
            <RecentRow key={job.job_id} job={job} />
          ))}
        </ul>
      )}
    </section>
  );
}

export function QueuesPage() {
  const { t } = useTranslation();
  const snapshot = useAdminQueues();

  return (
    <div className="flex flex-col gap-4 p-4">
      <AdminTabs activeTab="queues" />

      <header className="flex flex-col gap-1">
        <h1 className="text-lg font-semibold text-foreground">{t("modules.admin.queues.title")}</h1>
        <p className="text-xs text-muted-foreground">{t("modules.admin.queues.description")}</p>
      </header>

      {snapshot.isError ? (
        // Fails-closed: never fabricate a green/empty state on a failed read (AC-18).
        <div className="flex flex-col items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-4">
          <p className="text-sm font-medium text-destructive">
            {t("modules.admin.queues.error_title")}
          </p>
          <Button variant="outline" size="sm" onClick={() => void snapshot.refetch()}>
            {t("modules.admin.queues.retry")}
          </Button>
        </div>
      ) : snapshot.isLoading ? (
        <div className="flex flex-col gap-4" aria-hidden="true" data-testid="queues-skeleton">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-40 animate-pulse rounded-md bg-muted" />
            ))}
          </div>
          <div className="h-20 animate-pulse rounded-md bg-muted" />
        </div>
      ) : snapshot.data ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {snapshot.data.queues.map((entry) => (
              <QueueCard key={entry.name} entry={entry} />
            ))}
          </div>
          <RunningStrip jobs={snapshot.data.running_jobs} />
          <RecentList jobs={snapshot.data.recent} />
        </>
      ) : null}
    </div>
  );
}
