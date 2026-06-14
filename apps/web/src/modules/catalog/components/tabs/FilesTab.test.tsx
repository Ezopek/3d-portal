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
  unavailableTiers?: string[];
  unavailableTiersByMaterial?: Partial<Record<string, string[]>>;
}

// Route fetch by URL so the order of the (always-mounted) preset-bar `/spools/summary` read,
// the per-row `/estimates` reads, and any admin mutation does not make assertions
// order-dependent (Story 32.6's selector + EST-DISPLAY-1's chip both fetch on mount).
function installRouter(opts: RouterOpts = {}) {
  fetchMock.mockImplementation((input: unknown) => {
    const url = String(input);
    if (url.includes("/spools/summary")) return Promise.resolve(json(EMPTY_SUMMARY));
    if (url.includes("/estimates/quality-tiers")) {
      const material = new URL(url, "http://test.local").searchParams.get("material_class") ?? "PLA";
      const unavailable = new Set(
        opts.unavailableTiersByMaterial?.[material] ?? opts.unavailableTiers ?? ["aesthetic", "strong"],
      );
      return Promise.resolve(
        json({
          printer_ref: "creality-k1-max-microswiss-hf",
          material_class: material,
          tiers: ["aesthetic", "standard", "strong"].map((quality_tier) => ({
            quality_tier,
            available: !unavailable.has(quality_tier),
            reason: unavailable.has(quality_tier) ? "profile_not_imported" : null,
          })),
        }),
      );
    }
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
    .filter((u) => u.includes("/estimates") && !u.includes("/estimates/quality-tiers"));
}

function availabilityCalls(): string[] {
  return fetchMock.mock.calls
    .map((c) => String(c[0]))
    .filter((u) => u.includes("/estimates/quality-tiers"));
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
    // The estimate selector is member-visible (not admin-gated).
    expect(screen.getByLabelText(/material/i)).toBeTruthy();
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
  it("shows the member-visible estimate selector on the STL tab only", () => {
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    expect(screen.getByLabelText(/material/i)).toBeTruthy();
    // Switch to the Source tab → the estimate selector is gone (STL-only surface).
    fireEvent.click(screen.getByRole("button", { name: /source/i }));
    expect(screen.queryByLabelText(/material/i)).toBeNull();
  });

  it("does not render the selector when there are no STL files", () => {
    render(<FilesTab modelId={MODEL_ID} files={[FILES[2]!]} />, { wrapper: wrap() });
    expect(screen.queryByLabelText(/material/i)).toBeNull();
  });

  it("surfaces material + quality (Path B reversal) but NO pinned-filament/spool control", () => {
    // Story 33.1 / Init 21 Path B: material is now surfaced so per-material compatibility (the
    // TPU directive) is live here; the surface stays an estimate preview — no Spoolman pin /
    // spool control, `spoolman_filament_ref` stays null (AC-18).
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    expect(screen.getByLabelText(/material/i)).toBeTruthy();
    // E33.1: quality is a native <select>, not a radio group.
    expect((screen.getByLabelText(/quality/i) as HTMLSelectElement).tagName).toBe("SELECT");
    expect(screen.queryByRole("radiogroup")).toBeNull();
    expect(screen.queryByLabelText(/pinned filament|spool/i)).toBeNull();
    expect(screen.queryByText("Print preset")).toBeNull();
  });

  it("changing the estimate profile re-keys the estimate read to the chosen quality tier", async () => {
    installRouter({ unavailableTiers: [] });
    render(<FilesTab modelId={MODEL_ID} files={FILES_WITH_HASH} />, { wrapper: wrap() });
    await waitFor(() => expect(estimateCalls().length).toBeGreaterThanOrEqual(2));
    await waitFor(() =>
      expect((screen.getByRole("option", { name: "Strong" }) as HTMLOptionElement).disabled).toBe(
        false,
      ),
    );
    // Default reads are PLA · standard (material defaults to PLA).
    expect(estimateCalls().every((u) => u.includes("material_class=PLA"))).toBe(true);
    fetchMock.mockClear();
    fireEvent.change(screen.getByLabelText(/quality/i), { target: { value: "strong" } });
    await waitFor(() =>
      expect(estimateCalls().some((u) => u.includes("quality_tier=strong"))).toBe(true),
    );
    // Material class is still the unchanged internal default on the re-keyed read.
    expect(
      estimateCalls()
        .filter((u) => u.includes("quality_tier=strong"))
        .every((u) => u.includes("material_class=PLA")),
    ).toBe(true);
  });

  it("disables unavailable tiers from backend availability before they can fire estimate reads", async () => {
    render(<FilesTab modelId={MODEL_ID} files={FILES_WITH_HASH} />, { wrapper: wrap() });
    await waitFor(() => expect(availabilityCalls().length).toBe(1));
    await waitFor(() =>
      expect(screen.getByRole("option", { name: /Strong.*Not available yet/i })).toBeTruthy(),
    );
    const strong = screen.getByRole("option", {
      name: /Strong.*Not available yet/i,
    }) as HTMLOptionElement;
    expect(strong.disabled).toBe(true);

    fetchMock.mockClear();
    // The selectTier guard ignores an unavailable tier even if a change event reaches the select.
    fireEvent.change(screen.getByLabelText(/quality/i), { target: { value: "strong" } });
    expect(estimateCalls()).toEqual([]);
  });

  it("does not fire an estimate read while a material switch lands on an unavailable target tier", async () => {
    installRouter({
      unavailableTiersByMaterial: {
        PLA: ["aesthetic", "strong"],
        TPU: ["standard"],
      },
    });
    render(<FilesTab modelId={MODEL_ID} files={FILES_WITH_HASH} />, { wrapper: wrap() });
    await waitFor(() => expect(availabilityCalls().some((u) => u.includes("material_class=PLA"))).toBe(true));
    await waitFor(() => expect(estimateCalls().length).toBeGreaterThan(0));

    fetchMock.mockClear();
    fireEvent.change(screen.getByLabelText(/material/i), { target: { value: "TPU" } });

    await waitFor(() => expect(availabilityCalls().some((u) => u.includes("material_class=TPU"))).toBe(true));
    await waitFor(() =>
      expect(screen.getByRole("option", { name: /Standard.*Not available yet/i })).toBeTruthy(),
    );
    expect(estimateCalls()).toEqual([]);
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
    // The honest no-hash chips render synchronously (no request); wait for them, then assert
    // that no /estimates read fired. The compact estimate-profile selector makes no network
    // call of its own, so hash-less STL rows produce zero fetches at all.
    await waitFor(() =>
      expect(
        screen.getAllByTitle("No estimate available for this file.").length,
      ).toBeGreaterThanOrEqual(2),
    );
    expect(estimateCalls()).toEqual([]);
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


describe("FilesTab — admin file delete affordance", () => {
  it("admin sees delete actions for STL/source/3MF rows, but non-admin does not", () => {
    mockUseAuth.mockReturnValue({ isAdmin: true });
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    expect(screen.getByRole("button", { name: /delete a\.stl/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /delete b\.stl/i })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /source/i }));
    expect(screen.getByRole("button", { name: /delete c\.f3d/i })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /3mf/i }));
    expect(screen.getByRole("button", { name: /delete d\.3mf/i })).toBeTruthy();

    cleanup();
    mockUseAuth.mockReturnValue({ isAdmin: false });
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    expect(screen.queryByRole("button", { name: /delete a\.stl/i })).toBeNull();
  });

  it("requires confirmation before deleting a visible file row", async () => {
    mockUseAuth.mockReturnValue({ isAdmin: true });
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });

    fireEvent.click(screen.getByRole("button", { name: /delete a\.stl/i }));
    expect(screen.getByText("Delete a.stl?")).toBeTruthy();
    expect(
      findCall((u, i) => u.endsWith("/admin/models/" + MODEL_ID + "/files/fa") && i.method === "DELETE"),
    ).toBeUndefined();

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() =>
      expect(
        findCall((u, i) => u.endsWith("/admin/models/" + MODEL_ID + "/files/fa") && i.method === "DELETE"),
      ).toBeTruthy(),
    );
  });

  it("clears a selected/expanded STL after confirming deletion so viewer state cannot target the deleted file", async () => {
    mockUseAuth.mockReturnValue({ isAdmin: true });
    render(<FilesTab modelId={MODEL_ID} files={FILES_WITH_HASH} />, { wrapper: wrap() });

    fireEvent.click(screen.getByRole("button", { name: /Toggle 3D preview for a\.stl/i }));
    expect(
      screen.getByRole("button", { name: /Toggle 3D preview for a\.stl/i }).getAttribute("aria-expanded"),
    ).toBe("true");

    fireEvent.click(screen.getByRole("button", { name: /delete a\.stl/i }));
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() =>
      expect(
        findCall((u, i) => u.endsWith("/admin/models/" + MODEL_ID + "/files/fa") && i.method === "DELETE"),
      ).toBeTruthy(),
    );
    expect(
      screen.getByRole("button", { name: /Toggle 3D preview for a\.stl/i }).getAttribute("aria-expanded"),
    ).toBe("false");
  });
});
