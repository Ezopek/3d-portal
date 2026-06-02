import "@/locales/i18n";

import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { EstimateView, OverrideContextView } from "@/lib/api-types";
import { EstimateDisplay } from "./EstimateDisplay";

afterEach(cleanup);

const CONTEXT: OverrideContextView = {
  material_class: "PLA",
  quality_tier: "standard",
  pinned_filament_name: null,
  custom_overrides_applied: false,
  purchase_url: null,
};

// A fixed clock so the soft-fail "(Xm ago)" label is deterministic (AC-12).
const NOW = new Date("2026-06-02T10:05:00+00:00");
const COMPUTED_AT = "2026-06-02T10:00:00+00:00"; // 5 minutes before NOW

function view(overrides: Partial<EstimateView> = {}): EstimateView {
  return {
    status: "fresh",
    time_seconds: 12947,
    filament_g: 76.76,
    filament_mm: 25735.79,
    filament_cm3: 61.9,
    filament_cost: 4.6,
    currency: "PLN",
    computed_at: COMPUTED_AT,
    warnings: [],
    failure_reason: null,
    override_context: CONTEXT,
    ...overrides,
  };
}

function renderDisplay(
  props: Partial<Parameters<typeof EstimateDisplay>[0]> = {},
) {
  return render(
    <EstimateDisplay
      isPending={false}
      isError={false}
      data={view()}
      onRetry={() => {}}
      now={NOW}
      {...props}
    />,
  );
}

describe("EstimateDisplay — honest per-state rendering (AC-3)", () => {
  it("loading shows a busy skeleton, never a flash of absent/failed", () => {
    renderDisplay({ isPending: true, data: undefined });
    const status = screen.getByRole("status");
    expect(status.getAttribute("aria-busy")).toBe("true");
    expect(screen.queryByText(/no estimate yet/i)).toBeNull();
    expect(screen.queryByText(/couldn't estimate/i)).toBeNull();
  });

  it("fresh shows the populated values and NO staleness banner", () => {
    renderDisplay({ data: view({ status: "fresh" }) });
    expect(screen.getByText("3h 36m")).toBeTruthy();
    expect(screen.getByText("77 g")).toBeTruthy();
    expect(screen.getByText("4.60 PLN")).toBeTruthy();
    expect(screen.queryByText(/out of date/i)).toBeNull();
    expect(screen.queryByText(/recomputing/i)).toBeNull();
  });

  it("stale shows the still-servable numbers AND an out-of-date banner", () => {
    renderDisplay({ data: view({ status: "stale" }) });
    expect(screen.getByText("3h 36m")).toBeTruthy(); // servable numbers kept
    expect(screen.getByText(/out of date/i)).toBeTruthy();
  });

  it("stale does NOT claim it is being recomputed (AC-6 honesty)", () => {
    renderDisplay({ data: view({ status: "stale" }) });
    expect(screen.queryByText(/recomputing/i)).toBeNull();
  });

  it("queued shows the prior numbers AND a recomputing indicator", () => {
    renderDisplay({ data: view({ status: "queued" }) });
    expect(screen.getByText("3h 36m")).toBeTruthy();
    expect(screen.getByText(/recomputing/i)).toBeTruthy();
  });

  it("failed shows the reason and renders numerics as em-dash, never 0", () => {
    renderDisplay({
      data: view({
        status: "failed",
        failure_reason: "unparseable_time",
        time_seconds: null,
        filament_g: null,
        filament_mm: null,
        filament_cm3: null,
        filament_cost: null,
      }),
    });
    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.getByText(/print time couldn't be read/i)).toBeTruthy();
    expect(screen.queryByText(/\b0m\b|\b0 g\b/)).toBeNull();
  });

  it("absent is a distinct empty state (not failed, not transport error)", () => {
    renderDisplay({ data: view({ status: "absent" }) });
    expect(screen.getByText(/no estimate yet/i)).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("transport error is a retryable alert, distinct from absent", () => {
    const onRetry = vi.fn();
    renderDisplay({ isError: true, data: undefined, onRetry });
    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.queryByText(/no estimate yet/i)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("soft-fail label reads 'Last estimated HH:MM (Xm ago)' from an injected now", () => {
    renderDisplay({ data: view({ status: "stale" }) });
    expect(screen.getByText(/last estimated .*\(5m ago\)/i)).toBeTruthy();
  });
});

describe("EstimateDisplay — AC-6 cost-only vs mapped honesty", () => {
  it("a fresh record (incl. after a cost-only recompute) is never labelled stale", () => {
    renderDisplay({ data: view({ status: "fresh", filament_cost: 5.1 }) });
    expect(screen.getByText("5.10 PLN")).toBeTruthy();
    expect(screen.queryByText(/out of date/i)).toBeNull();
    expect(screen.queryByText(/recomputing/i)).toBeNull();
  });

  it("a stale-after-mapped-change record shows the recompute/staleness copy", () => {
    renderDisplay({ data: view({ status: "stale" }) });
    expect(screen.getByText(/out of date/i)).toBeTruthy();
  });
});

describe("EstimateDisplay — no internal labels leak into the DOM (AC-8)", () => {
  it("renders no Orca key / settings_ids / bundle_hash / g-code text", () => {
    const { container } = renderDisplay({
      data: view({ status: "fresh" }),
    });
    const text = container.textContent ?? "";
    for (const internal of [
      "settings_ids",
      "bundle_hash",
      "stl_hash",
      "filament_max_volumetric_speed",
      "nozzle_temperature",
      "filament_density",
      "gcode",
    ]) {
      expect(text).not.toContain(internal);
    }
  });
});
