import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import en from "@/locales/en.json";
import i18n from "@/locales/i18n";
import pl from "@/locales/pl.json";
import { QueuesPage } from "@/modules/admin/QueuesPage";
import type { QueueSnapshot } from "@/modules/admin/hooks/useAdminQueues";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.useRealTimers();
});

beforeAll(async () => {
  await i18n.changeLanguage("en");
});

function snapshot(overrides: Partial<QueueSnapshot> = {}): QueueSnapshot {
  return {
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
          counters: { complete: 10, failed: 0, retried: 1, ongoing: 0, queued: 2 },
        },
      },
      {
        name: "arq:queue",
        role: "render",
        queued: 0,
        running: 1,
        worker: {
          liveness: "idle",
          heartbeat_at: "2026-06-06T09:00:00+00:00",
          heartbeat_age_s: 3600,
          interval_s: 3600,
          counters: { complete: 3, failed: 2, retried: 0, ongoing: 1, queued: 0 },
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
        started_age_s: 12,
        context: { kind: "render", ref: null },
      },
      {
        queue: "arq:slicer",
        function: "slice_estimate",
        job_id: "slice:deadbeef:cafe",
        started_age_s: 3,
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
    ...overrides,
  };
}

function installFetch(opts: { snap?: QueueSnapshot; error?: boolean; pending?: boolean } = {}) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    if (url.includes("/api/admin/queues")) {
      if (opts.pending) return new Promise<Response>(() => {}); // never resolves → loading
      if (opts.error) {
        return new Response(JSON.stringify({ detail: "boom" }), {
          status: 500,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response(JSON.stringify(opts.snap ?? snapshot()), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function setHidden(hidden: boolean) {
  Object.defineProperty(document, "hidden", { configurable: true, get: () => hidden });
  Object.defineProperty(document, "visibilityState", {
    configurable: true,
    get: () => (hidden ? "hidden" : "visible"),
  });
}

function mount(node: ReactNode) {
  const root = createRootRoute();
  const route = createRoute({
    getParentRoute: () => root,
    path: "/admin/queues",
    component: () => <>{node}</>,
  });
  const fallback = createRoute({
    getParentRoute: () => root,
    path: "/",
    component: () => <div>home</div>,
  });
  const router = createRouter({
    routeTree: root.addChildren([route, fallback]),
    history: createMemoryHistory({ initialEntries: ["/admin/queues"] }),
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("QueuesPage (ADMIN-JOBS-1)", () => {
  beforeEach(() => {
    void i18n.changeLanguage("en");
    setHidden(false);
  });

  it("renders three per-queue cards with mixed liveness + counters (AC-15)", async () => {
    installFetch();
    mount(<QueuesPage />);
    // friendly roles + untranslated technical queue ids
    expect(await screen.findByText("API")).toBeTruthy();
    expect(screen.getByText("Render")).toBeTruthy();
    expect(screen.getByText("Slicer")).toBeTruthy();
    expect(screen.getAllByText("arq:api").length).toBeGreaterThan(0);
    expect(screen.getAllByText("arq:slicer").length).toBeGreaterThan(0);
    // tri-state liveness conveyed by text (icon + color also present, not asserted here)
    expect(screen.getByText("Alive")).toBeTruthy();
    expect(screen.getByText("Idle")).toBeTruthy();
    expect(screen.getByText("Unknown")).toBeTruthy();
  });

  it("renders the running-now strip with curated context (AC-16)", async () => {
    installFetch();
    mount(<QueuesPage />);
    expect(await screen.findByText("Running now")).toBeTruthy();
    expect(screen.getAllByText("render_model").length).toBeGreaterThan(0);
    expect(screen.getByText("slice_estimate")).toBeTruthy();
    // slicer context.ref is a hash prefix, never a path
    expect(screen.getByText(/deadbeef/)).toBeTruthy();
  });

  it("renders the recent list with the retention caveat + curated error_class (AC-17)", async () => {
    installFetch();
    mount(<QueuesPage />);
    expect(await screen.findByText("Recent (~last hour)")).toBeTruthy();
    // honest retention label (unique to the recent panel, not the page description)
    expect(screen.getByText(/vanished entry expired/)).toBeTruthy();
    // failed job surfaces the curated exception class only
    expect(screen.getByText(/ValueError/)).toBeTruthy();
  });

  it("shows a skeleton while loading, not a bare spinner (AC-18)", async () => {
    installFetch({ pending: true });
    mount(<QueuesPage />);
    expect(await screen.findByTestId("queues-skeleton")).toBeTruthy();
  });

  it("shows neutral empty states, not errors, when idle (AC-16/AC-18)", async () => {
    installFetch({
      snap: snapshot({ running_jobs: [], recent: [] }),
    });
    mount(<QueuesPage />);
    expect(await screen.findByText("Nothing running.")).toBeTruthy();
    expect(screen.getByText("No recent results.")).toBeTruthy();
  });

  it("fails closed on a read error: error panel + Retry, never a fake-green state (AC-18)", async () => {
    const fetchMock = installFetch({ error: true });
    mount(<QueuesPage />);
    expect(await screen.findByText("Couldn't load the queue snapshot")).toBeTruthy();
    const retry = screen.getByRole("button", { name: "Retry" });
    expect(retry).toBeTruthy();
    // must NOT fabricate cards/empty-success copy on failure
    expect(screen.queryByText("Nothing running.")).toBeNull();
    const before = fetchMock.mock.calls.length;
    fireEvent.click(retry);
    await waitFor(() => expect(fetchMock.mock.calls.length).toBeGreaterThan(before));
  });

  it("re-arms polling with a refetch when the tab becomes visible (AC-19)", async () => {
    const fetchMock = installFetch();
    mount(<QueuesPage />);
    await screen.findByText("API");
    const after_initial = fetchMock.mock.calls.length;
    setHidden(false);
    fireEvent(document, new Event("visibilitychange"));
    await waitFor(() => expect(fetchMock.mock.calls.length).toBeGreaterThan(after_initial));
  });

  it("does NOT refetch on visibilitychange while the tab is hidden (AC-19)", async () => {
    const fetchMock = installFetch();
    mount(<QueuesPage />);
    await screen.findByText("API");
    const after_initial = fetchMock.mock.calls.length;
    setHidden(true);
    fireEvent(document, new Event("visibilitychange"));
    // give any erroneous refetch a tick to fire
    await new Promise((r) => setTimeout(r, 50));
    expect(fetchMock.mock.calls.length).toBe(after_initial);
  });
});

describe("queues i18n parity (AC-21)", () => {
  const enKeys = Object.keys(en).filter(
    (k) => k.startsWith("modules.admin.queues.") || k === "admin.tabs.queues",
  );
  const plKeys = Object.keys(pl).filter(
    (k) => k.startsWith("modules.admin.queues.") || k === "admin.tabs.queues",
  );

  it("has identical en/pl key sets for the queues namespace", () => {
    expect(new Set(plKeys)).toEqual(new Set(enKeys));
    expect(enKeys.length).toBeGreaterThan(20);
  });

  it("keeps technical queue role ids untranslated and Polish copy diacritic-correct", () => {
    const enMap = en as Record<string, string>;
    const plMap = pl as Record<string, string>;
    // friendly role labels for api stay the technical "API" in both languages
    expect(plMap["modules.admin.queues.role.api"]).toBe("API");
    // a translated string actually differs + carries Polish diacritics
    expect(plMap["modules.admin.queues.queued"]).not.toBe(enMap["modules.admin.queues.queued"]);
    expect(plMap["modules.admin.queues.description"]).toMatch(/[ąćęłńóśźż]/i);
  });
});
