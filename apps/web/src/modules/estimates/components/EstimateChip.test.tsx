import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import "@/locales/i18n";
import type { EstimateView, ProfileSelectionContextView } from "@/lib/api-types";

import { EstimateChip } from "./EstimateChip";
import { defaultPreset } from "@/modules/estimates/lib/preset";

const mockUseEstimate = vi.fn();
vi.mock("@/modules/estimates/hooks/useEstimate", () => ({
  useEstimate: (...args: unknown[]) => mockUseEstimate(...args),
}));

const HASH = "a".repeat(64);
const PRINTER = "creality-k1-max-microswiss-hf";

function view(overrides: Partial<EstimateView> = {}): EstimateView {
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

function ok(data: EstimateView) {
  return { isPending: false, isError: false, data, refetch: vi.fn() };
}

function chip(stlHash = HASH, props: Partial<React.ComponentProps<typeof EstimateChip>> = {}) {
  return (
    <EstimateChip
      stlHash={stlHash}
      preset={defaultPreset()}
      printerRef={PRINTER}
      {...props}
    />
  );
}

beforeEach(() => {
  mockUseEstimate.mockReset();
});

afterEach(() => cleanup());

describe("EstimateChip", () => {
  it("no hash → em-dash, no_hash title, and never engages the read (hook stays disabled)", () => {
    mockUseEstimate.mockReturnValue(ok(view()));
    render(chip(""));
    // The hook is still invoked with the EMPTY hash so it self-disables (enabled guard);
    // the chip must not show grams for a hashless file.
    expect(mockUseEstimate).toHaveBeenCalledWith(
      "",
      expect.anything(),
      PRINTER,
      { enabled: true },
    );
    const el = screen.getByTitle("No estimate available for this file.");
    expect(el.textContent).toContain("—");
    expect(el.textContent).not.toContain("42");
  });

  it("passes the parent availability gate to the estimate hook", () => {
    mockUseEstimate.mockReturnValue(ok(view()));
    render(chip(HASH, { enabled: false }));
    expect(mockUseEstimate).toHaveBeenCalledWith(
      HASH,
      expect.anything(),
      PRINTER,
      { enabled: false },
    );
  });

  it("loading → aria-busy status, no value flashed", () => {
    mockUseEstimate.mockReturnValue({
      isPending: true,
      isError: false,
      data: undefined,
      refetch: vi.fn(),
    });
    render(chip());
    const el = screen.getByLabelText("Loading estimate…");
    expect(el.getAttribute("aria-busy")).toBe("true");
  });

  it("network error → em-dash + error title (distinct from absent/failed)", () => {
    mockUseEstimate.mockReturnValue({
      isPending: false,
      isError: true,
      data: undefined,
      refetch: vi.fn(),
    });
    render(chip());
    const el = screen.getByTitle("Couldn't load the estimate.");
    expect(el.textContent).toContain("—");
  });

  it("absent → em-dash + absent title, never 0 g", () => {
    mockUseEstimate.mockReturnValue(
      ok(view({ status: "absent", filament_g: null })),
    );
    render(chip());
    const el = screen.getByTitle("No estimate yet.");
    expect(el.textContent).toContain("—");
    expect(el.textContent).not.toContain("0 g");
  });

  it("failed → em-dash + failed title", () => {
    mockUseEstimate.mockReturnValue(
      ok(view({ status: "failed", filament_g: null, failure_reason: "parse_failure" })),
    );
    render(chip());
    const el = screen.getByTitle("Couldn't estimate this file.");
    expect(el.textContent).toContain("—");
  });

  it("fresh → grams value + fresh title, non-interactive (not a button)", () => {
    mockUseEstimate.mockReturnValue(ok(view({ status: "fresh", filament_g: 42 })));
    render(chip());
    const el = screen.getByTitle("Estimated filament 42 g.");
    expect(el.textContent).toContain("42 g");
    expect(el.tagName.toLowerCase()).toBe("span");
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("stale → grams + stale title (color paired with a glyph, not color-only)", () => {
    mockUseEstimate.mockReturnValue(ok(view({ status: "stale", filament_g: 42 })));
    render(chip());
    const el = screen.getByTitle("Estimated filament 42 g — may be out of date.");
    expect(el.textContent).toContain("42 g");
  });

  it("queued with last-known grams → grams + queued title", () => {
    mockUseEstimate.mockReturnValue(ok(view({ status: "queued", filament_g: 42 })));
    render(chip());
    const el = screen.getByTitle("Estimated filament 42 g — recomputing…");
    expect(el.textContent).toContain("42 g");
  });

  it("queued with no last-known value → em-dash + queued_no_value title", () => {
    mockUseEstimate.mockReturnValue(
      ok(view({ status: "queued", filament_g: null })),
    );
    render(chip());
    const el = screen.getByTitle("Recomputing estimate…");
    expect(el.textContent).toContain("—");
  });
});

// AC-7 — absent chip title swaps for unavailable_no_profile
describe("EstimateChip — AC-7 absent_no_profile title (35.5)", () => {
  it("absent + unavailable_no_profile → distinct no-profile title, still em-dash", () => {
    mockUseEstimate.mockReturnValue(
      ok(
        view({
          status: "absent",
          filament_g: null,
          profile_selection_context: {
            estimate_profile_source: "unavailable_no_profile",
            selected_material: "PLA",
            selected_spoolman_filament_ref: null,
            selected_filament_name: null,
            orca_filament_profile_name: null,
          },
        }),
      ),
    );
    render(chip());
    const el = screen.getByTitle("No filament profile — estimate unavailable.");
    expect(el.textContent).toContain("—");
  });
});

// AC-8 — _default i18n key variants for default_material_profile chip states
describe("EstimateChip — AC-8 _default title variants (35.5)", () => {
  function defaultCtx(): ProfileSelectionContextView {
    return {
      estimate_profile_source: "default_material_profile",
      selected_material: "PLA",
      selected_spoolman_filament_ref: null,
      selected_filament_name: "Bambu PLA Basic",
      orca_filament_profile_name: "Bambu PLA Basic @BBL X1C",
    };
  }

  it("fresh + default_material_profile → fresh_default title with mass", () => {
    mockUseEstimate.mockReturnValue(
      ok(view({ status: "fresh", filament_g: 42, profile_selection_context: defaultCtx() })),
    );
    render(chip());
    expect(
      screen.getByTitle("Estimated filament 42 g (default profile)."),
    ).toBeTruthy();
  });

  it("stale + default_material_profile → stale_default title with mass", () => {
    mockUseEstimate.mockReturnValue(
      ok(view({ status: "stale", filament_g: 42, profile_selection_context: defaultCtx() })),
    );
    render(chip());
    expect(
      screen.getByTitle(
        "Estimated filament 42 g — may be out of date (default profile).",
      ),
    ).toBeTruthy();
  });

  it("queued with value + default_material_profile → queued_default title", () => {
    mockUseEstimate.mockReturnValue(
      ok(view({ status: "queued", filament_g: 42, profile_selection_context: defaultCtx() })),
    );
    render(chip());
    expect(
      screen.getByTitle(
        "Estimated filament 42 g — recomputing… (default profile).",
      ),
    ).toBeTruthy();
  });

  it("queued with no value + default_material_profile → queued_no_value_default title", () => {
    mockUseEstimate.mockReturnValue(
      ok(
        view({
          status: "queued",
          filament_g: null,
          profile_selection_context: defaultCtx(),
        }),
      ),
    );
    render(chip());
    expect(screen.getByTitle("Recomputing estimate (default profile)…")).toBeTruthy();
  });
});
