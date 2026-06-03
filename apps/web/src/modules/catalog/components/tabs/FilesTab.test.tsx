import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, cleanup, fireEvent, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import "@/locales/i18n";
import type { EstimateView, ModelFileRead } from "@/lib/api-types";

import { FilesTab } from "./FilesTab";

const mockUseAuth = vi.fn();
vi.mock("@/shell/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

const EMPTY_SUMMARY = {
  spools: [],
  filaments: [],
  vendors: [],
  fetched_at: null,
  last_success_ts: null,
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function estimateView(overrides: Partial<EstimateView> = {}): EstimateView {
  return {
    status: "fresh",
    time_seconds: 3600,
    filament_g: 42,
    filament_mm: 14000,
    filament_cm3: 36,
    filament_cost: 5,
    currency: "PLN",
    computed_at: "2026-06-02T10:00:00Z",
    warnings: [],
    failure_reason: null,
    override_context: {
      material_class: "PLA",
      quality_tier: "standard",
      pinned_filament_name: null,
      custom_overrides_applied: false,
      purchase_url: null,
    },
    ...overrides,
  };
}

interface RouterOpts {
  estimate?: EstimateView;
  estimateError?: boolean;
}

// Route fetch by URL so the order of the (always-mounted) preset-bar `/spools/summary` read,
// the per-row `/estimates` reads, and any admin mutation does not make assertions
// order-dependent (Story 32.6's selector + EST-DISPLAY-1's chip both fetch on mount).
function installRouter(opts: RouterOpts = {}) {
  fetchMock.mockImplementation((input: unknown) => {
    const url = String(input);
    if (url.includes("/spools/summary")) return Promise.resolve(json(EMPTY_SUMMARY));
    if (url.includes("/estimates")) {
      if (opts.estimateError) return Promise.resolve(json({ detail: "boom" }, 500));
      return Promise.resolve(json(opts.estimate ?? estimateView({ status: "absent" })));
    }
    return Promise.resolve(json({}, 200));
  });
}

function estimateCalls(): string[] {
  return fetchMock.mock.calls
    .map((c) => String(c[0]))
    .filter((u) => u.includes("/estimates"));
}

function findCall(predicate: (url: string, init: RequestInit) => boolean) {
  return fetchMock.mock.calls.find((c) =>
    predicate(String(c[0]), (c[1] ?? {}) as RequestInit),
  );
}

beforeEach(() => {
  mockUseAuth.mockReturnValue({ isAdmin: false });
  installRouter();
});

afterEach(() => {
  cleanup();
  fetchMock.mockReset();
});

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

const MODEL_ID = "m1";
const HASH_A = "a".repeat(64);
const HASH_B = "b".repeat(64);

function file(over: Partial<ModelFileRead> & Pick<ModelFileRead, "id" | "kind" | "original_name">): ModelFileRead {
  return {
    model_id: MODEL_ID,
    storage_path: "",
    sha256: "",
    size_bytes: 1024,
    mime_type: "",
    position: null,
    selected_for_render: false,
    created_at: "",
    ...over,
  };
}

// Default fixture: STL parts carry NO sha256 (mirrors a not-yet-ingested catalog) so the
// honesty path is the default; hash-bearing fixtures are opted into per test.
const FILES: ModelFileRead[] = [
  file({ id: "fa", kind: "stl", original_name: "a.stl", selected_for_render: true }),
  file({ id: "fb", kind: "stl", original_name: "b.stl", size_bytes: 2048 }),
  file({ id: "fc", kind: "source", original_name: "c.f3d", size_bytes: 4096 }),
  file({ id: "fd", kind: "archive_3mf", original_name: "d.3mf", size_bytes: 8192 }),
  file({ id: "fe", kind: "image", original_name: "e.png", size_bytes: 512 }),
];

const FILES_WITH_HASH: ModelFileRead[] = [
  file({ id: "fa", kind: "stl", original_name: "a.stl", sha256: HASH_A }),
  file({ id: "fb", kind: "stl", original_name: "b.stl", sha256: HASH_B, size_bytes: 2048 }),
];

describe("FilesTab — file listing", () => {
  it("defaults to STL kind and lists STL files only", () => {
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    expect(screen.getByText("a.stl")).toBeTruthy();
    expect(screen.getByText("b.stl")).toBeTruthy();
    expect(screen.queryByText("c.f3d")).toBeNull();
    expect(screen.queryByText("e.png")).toBeNull();
  });

  it("clicking Source chip switches to source files", () => {
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    fireEvent.click(screen.getByRole("button", { name: /source/i }));
    expect(screen.getByText("c.f3d")).toBeTruthy();
    expect(screen.queryByText("a.stl")).toBeNull();
  });

  it("download link points at the content endpoint", () => {
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    const link = screen
      .getAllByRole("link")
      .find((a) => a.getAttribute("href")?.includes("fa"));
    expect(link?.getAttribute("href")).toBe(
      `/api/models/${MODEL_ID}/files/fa/content?download=1`,
    );
  });

  it("renders an empty state when no files of the active kind", () => {
    render(<FilesTab modelId={MODEL_ID} files={[FILES[4]!]} />, { wrapper: wrap() });
    expect(document.body.textContent?.toLowerCase()).toContain("no files");
  });
});

describe("FilesTab — admin render controls (unchanged, separate from estimates)", () => {
  it("non-admin sees no render-selection checkboxes", () => {
    mockUseAuth.mockReturnValue({ isAdmin: false });
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    expect(screen.queryByLabelText(/include .* in renders/i)).toBeNull();
  });

  it("admin sees a checkbox per STL reflecting selected_for_render", () => {
    mockUseAuth.mockReturnValue({ isAdmin: true });
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    const a = screen.getByLabelText("include a.stl in renders") as HTMLInputElement;
    const b = screen.getByLabelText("include b.stl in renders") as HTMLInputElement;
    expect(a.checked).toBe(true);
    expect(b.checked).toBe(false);
  });

  it("toggling the admin checkbox PATCHes selected_for_render", async () => {
    mockUseAuth.mockReturnValue({ isAdmin: true });
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    fireEvent.click(screen.getByLabelText("include b.stl in renders"));
    await waitFor(() =>
      expect(
        findCall((u, i) => u.endsWith(`/admin/models/${MODEL_ID}/files/fb`) && i.method === "PATCH"),
      ).toBeTruthy(),
    );
    const call = findCall(
      (u, i) => u.endsWith(`/admin/models/${MODEL_ID}/files/fb`) && i.method === "PATCH",
    )!;
    expect((call[1] as RequestInit).body).toBe(
      JSON.stringify({ selected_for_render: true }),
    );
  });

  it("admin sees a Re-render preview button when STLs are present", () => {
    mockUseAuth.mockReturnValue({ isAdmin: true });
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    expect(screen.getByRole("button", { name: /re-render preview/i })).toBeTruthy();
  });

  it("non-admin does not see the Re-render button (but DOES see the estimate selector)", () => {
    mockUseAuth.mockReturnValue({ isAdmin: false });
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    expect(screen.queryByRole("button", { name: /re-render preview/i })).toBeNull();
    // The estimate-profile selector is member-visible (not admin-gated).
    expect(screen.getByText("Print preset")).toBeTruthy();
  });

  it("clicking Re-render posts an empty selection so the worker uses persisted flags", async () => {
    mockUseAuth.mockReturnValue({ isAdmin: true });
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    fireEvent.click(screen.getByRole("button", { name: /re-render preview/i }));
    await waitFor(() =>
      expect(
        findCall((u, i) => u.endsWith(`/admin/models/${MODEL_ID}/render`) && i.method === "POST"),
      ).toBeTruthy(),
    );
    const call = findCall(
      (u, i) => u.endsWith(`/admin/models/${MODEL_ID}/render`) && i.method === "POST",
    )!;
    expect((call[1] as RequestInit).body).toBe(
      JSON.stringify({ selected_stl_file_ids: [] }),
    );
  });
});

describe("FilesTab — EST-DISPLAY-1 estimate surface", () => {
  it("shows the member-visible estimate-profile selector on the STL tab only", () => {
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    expect(screen.getByText("Print preset")).toBeTruthy();
    // Switch to the Source tab → the estimate selector is gone (STL-only surface).
    fireEvent.click(screen.getByRole("button", { name: /source/i }));
    expect(screen.queryByText("Print preset")).toBeNull();
  });

  it("does not render the selector when there are no STL files", () => {
    render(<FilesTab modelId={MODEL_ID} files={[FILES[2]!]} />, { wrapper: wrap() });
    expect(screen.queryByText("Print preset")).toBeNull();
  });

  it("reads GET /api/estimates keyed by sha256 + preset + the catalog printer ref", async () => {
    render(<FilesTab modelId={MODEL_ID} files={FILES_WITH_HASH} />, { wrapper: wrap() });
    await waitFor(() => expect(estimateCalls().length).toBeGreaterThanOrEqual(2));
    const urls = estimateCalls();
    const a = urls.find((u) => u.includes(`stl_hash=${HASH_A}`))!;
    expect(a).toBeTruthy();
    expect(a).toContain("material_class=PLA");
    expect(a).toContain("quality_tier=standard");
    expect(a).toContain("printer_ref=creality-k1-max-microswiss-hf");
    expect(urls.some((u) => u.includes(`stl_hash=${HASH_B}`))).toBe(true);
  });

  it("renders a fresh grams chip for a hash-bearing row", async () => {
    installRouter({ estimate: estimateView({ status: "fresh", filament_g: 42 }) });
    render(<FilesTab modelId={MODEL_ID} files={FILES_WITH_HASH} />, { wrapper: wrap() });
    await waitFor(() =>
      expect(screen.getAllByTitle("Estimated filament 42 g.").length).toBeGreaterThan(0),
    );
  });

  it("missing-hash STL row fires NO estimate read and shows the honest no-hash chip", async () => {
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    // Let any mount effects flush.
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(estimateCalls()).toEqual([]);
    expect(
      screen.getAllByTitle("No estimate available for this file.").length,
    ).toBeGreaterThanOrEqual(2);
  });

  it("network error → quiet error chip, distinct from absent", async () => {
    installRouter({ estimateError: true });
    render(<FilesTab modelId={MODEL_ID} files={FILES_WITH_HASH} />, { wrapper: wrap() });
    await waitFor(() =>
      expect(screen.getAllByTitle("Couldn't load the estimate.").length).toBeGreaterThan(0),
    );
  });

  it("stale state → grams chip with the stale title", async () => {
    installRouter({ estimate: estimateView({ status: "stale", filament_g: 42 }) });
    render(<FilesTab modelId={MODEL_ID} files={FILES_WITH_HASH} />, { wrapper: wrap() });
    await waitFor(() =>
      expect(
        screen.getAllByTitle("Estimated filament 42 g — may be out of date.").length,
      ).toBeGreaterThan(0),
    );
  });

  it("expanding a hash-bearing row reuses the shipped EstimateDisplay breakdown", async () => {
    installRouter({ estimate: estimateView({ status: "fresh", filament_g: 42 }) });
    render(<FilesTab modelId={MODEL_ID} files={FILES_WITH_HASH} />, { wrapper: wrap() });
    fireEvent.click(
      screen.getByRole("button", { name: /Toggle 3D preview for a\.stl/i }),
    );
    // The full EstimateDisplay <dl> labels appear (Print time / Length / Volume) — the chip
    // alone never shows these.
    await waitFor(() => expect(screen.getByText("Print time")).toBeTruthy());
    expect(screen.getByText("Length")).toBeTruthy();
    expect(screen.getByText("Volume")).toBeTruthy();
    expect(screen.getByText("Informational only — not a quote.")).toBeTruthy();
  });

  it("has no recompute/enqueue affordance on the estimate surface", () => {
    render(<FilesTab modelId={MODEL_ID} files={FILES_WITH_HASH} />, { wrapper: wrap() });
    expect(screen.queryByRole("button", { name: /recompute|recalculate|re-estimate/i })).toBeNull();
  });
});
