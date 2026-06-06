import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";

import { api } from "@/lib/api";

// ADMIN-JOBS-1 (Story 34.1) — read-only admin queue snapshot DTO. These mirror the
// backend field-allowlist schemas in apps/api/app/modules/queue/schemas.py exactly; the
// console NEVER receives raw args/kwargs/result (NFR22-LEAK-FENCE-1).

export type QueueRole = "api" | "render" | "slicer";
export type Liveness = "alive" | "idle" | "unknown";
export type Outcome = "success" | "failed";

export interface JobContext {
  kind: string;
  ref: string | null;
}

export interface QueueCounters {
  complete: number;
  failed: number;
  retried: number;
  ongoing: number;
  queued: number;
}

export interface WorkerLiveness {
  liveness: Liveness;
  heartbeat_at: string | null;
  heartbeat_age_s: number | null;
  interval_s: number;
  counters: QueueCounters | null;
}

export interface RunningJob {
  queue: string;
  function: string;
  job_id: string;
  started_age_s: number;
  context: JobContext | null;
}

export interface RecentJob {
  queue: string;
  function: string;
  outcome: Outcome;
  finished_at: string;
  duration_s: number;
  job_id: string;
  context: JobContext | null;
  error_class: string | null;
}

export interface QueueEntry {
  name: string;
  role: QueueRole;
  queued: number;
  running: number;
  worker: WorkerLiveness;
}

export interface QueueSnapshot {
  generated_at: string;
  queues: QueueEntry[];
  running_jobs: RunningJob[];
  recent: RecentJob[];
  retention_note: string;
}

// Contract: the panel's purpose is to WATCH work start/finish (UC1/UC2); the operator's
// own UC2 cites a 5-minute wait, so few-second resolution is ample — and it is bounded
// BELOW by "must not hammer the homelab single Redis": one poll = 3 zcard + 2 small SCANs
// (NFR22-REDIS-LOAD-1). Arbitrary-but-bounded MVP default; replace if perf telemetry or
// operator preference pins it (TB-016 lesson: not "feels right").
export const QUEUES_POLL_INTERVAL_MS = 4000;

/**
 * ADMIN-JOBS-1 (AC-19) — focus-gated polling of the live queue snapshot.
 *
 * Cache topology (per the story's enumeration): `staleTime: 0` because the panel's whole
 * purpose is LIVE state (UC1/UC2) — any staleness defeats it. The key `["admin","queues"]`
 * reads infra state no other surface owns, so there is no cross-surface coherence concern
 * (read-only; no mutations exist in this MVP).
 *
 * Polling is paused while the tab/document is hidden (`refetchInterval` returns `false`
 * when `document.hidden`, and `refetchIntervalInBackground: false`); a `visibilitychange`
 * listener re-arms it with an immediate refetch on return to visible.
 */
export function useAdminQueues() {
  const query = useQuery<QueueSnapshot>({
    queryKey: ["admin", "queues"],
    queryFn: () => api<QueueSnapshot>("/admin/queues"),
    staleTime: 0,
    refetchInterval: () => (document.hidden ? false : QUEUES_POLL_INTERVAL_MS),
    refetchIntervalInBackground: false,
  });

  const { refetch } = query;
  useEffect(() => {
    function onVisibility() {
      if (!document.hidden) void refetch();
    }
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, [refetch]);

  return query;
}
