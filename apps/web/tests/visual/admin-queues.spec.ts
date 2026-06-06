import { expect, test } from "./_test";
import { stubAdminQueues } from "./api-stubs";
import { waitForReady } from "./helpers";

// ADMIN-JOBS-1 (AC-22, NFR22-VISUAL-VERIFICATION-1) — read-only admin queue console states.
//
// Each state is driven by a MOCKED `/api/admin/queues` response (curated allowlist DTO only —
// never raw args/kwargs/result), so the four projects (desktop-light/dark, mobile-light/dark)
// are pixel-stable. The payload carries no rendered timestamp; the focus-gated poll re-fetches
// the identical body, so screenshots are deterministic.
//
// NOTE (baseline status): the `__snapshots__` PNGs are generated + `baseline-reviewed:` signed
// off in the controller-owned visual pass. Each screenshot call below carries the sign-off
// marker for that review. See the story Dev Agent Record for any deferred-baseline note.

const POPULATED = {
  generated_at: "2026-06-06T10:00:00+00:00",
  queues: [
    {
      name: "arq:api",
      role: "api",
      queued: 2,
      running: 0,
      worker: {
        liveness: "alive",
        heartbeat_at: "2026-06-06T09:59:55+00:00",
        heartbeat_age_s: 5,
        interval_s: 3600,
        counters: { complete: 124, failed: 0, retried: 2, ongoing: 0, queued: 2 },
      },
    },
    {
      name: "arq:queue",
      role: "render",
      queued: 1,
      running: 1,
      worker: {
        liveness: "idle",
        heartbeat_at: "2026-06-06T09:00:00+00:00",
        heartbeat_age_s: 3600,
        interval_s: 3600,
        counters: { complete: 18, failed: 3, retried: 1, ongoing: 1, queued: 1 },
      },
    },
    {
      name: "arq:slicer",
      role: "slicer",
      queued: 0,
      running: 1,
      worker: {
        liveness: "unknown",
        heartbeat_at: null,
        heartbeat_age_s: null,
        interval_s: 3600,
        counters: null,
      },
    },
  ],
  running_jobs: [
    {
      queue: "arq:queue",
      function: "render_model",
      job_id: "r1",
      started_age_s: 42,
      context: { kind: "render", ref: null },
    },
    {
      queue: "arq:slicer",
      function: "slice_estimate",
      job_id: "slice:deadbeef:cafe1234",
      started_age_s: 7,
      context: { kind: "estimate", ref: "deadbeef" },
    },
  ],
  recent: [
    {
      queue: "arq:api",
      function: "generate_thumbnail",
      outcome: "success",
      finished_at: "2026-06-06T09:59:00+00:00",
      duration_s: 4,
      job_id: "ok1",
      context: { kind: "thumbnail", ref: null },
      error_class: null,
    },
    {
      queue: "arq:queue",
      function: "render_model",
      outcome: "failed",
      finished_at: "2026-06-06T09:58:00+00:00",
      duration_s: 2,
      job_id: "bad1",
      context: { kind: "render", ref: null },
      error_class: "ValueError",
    },
  ],
  retention_note: "redis-resident ~1h",
};

const EMPTY = {
  generated_at: "2026-06-06T10:00:00+00:00",
  queues: [
    {
      name: "arq:api",
      role: "api",
      queued: 0,
      running: 0,
      worker: {
        liveness: "alive",
        heartbeat_at: "2026-06-06T09:59:55+00:00",
        heartbeat_age_s: 5,
        interval_s: 3600,
        counters: { complete: 0, failed: 0, retried: 0, ongoing: 0, queued: 0 },
      },
    },
    {
      name: "arq:queue",
      role: "render",
      queued: 0,
      running: 0,
      worker: {
        liveness: "unknown",
        heartbeat_at: null,
        heartbeat_age_s: null,
        interval_s: 3600,
        counters: null,
      },
    },
    {
      name: "arq:slicer",
      role: "slicer",
      queued: 0,
      running: 0,
      worker: {
        liveness: "unknown",
        heartbeat_at: null,
        heartbeat_age_s: null,
        interval_s: 3600,
        counters: null,
      },
    },
  ],
  running_jobs: [],
  recent: [],
  retention_note: "redis-resident ~1h",
};

test.describe("/admin/queues baselines", () => {
  test("populated — mixed liveness + running strip + failed recent", async ({ page }) => {
    await stubAdminQueues(page, { snapshot: POPULATED });
    await page.goto("/admin/queues");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("queues-populated.png", { fullPage: true });
  });

  test("empty — idle pools, nothing running, empty recent", async ({ page }) => {
    await stubAdminQueues(page, { snapshot: EMPTY });
    await page.goto("/admin/queues");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("queues-empty.png", { fullPage: true });
  });

  test("error — fails-closed error panel + retry", async ({ page }) => {
    await stubAdminQueues(page, { error: true });
    await page.goto("/admin/queues");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("queues-error.png", { fullPage: true });
  });
});
