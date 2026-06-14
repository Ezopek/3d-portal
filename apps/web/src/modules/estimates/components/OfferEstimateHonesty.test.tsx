import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "@/locales/i18n";
import { EstimateDisplay } from "@/modules/estimates/components/EstimateDisplay";

// AC-21 (NFR24-HONESTY-1): rendering EstimateDisplay with
// estimate_profile_source: "default_material_profile" + status: "fresh" MUST show the badge.
// This test must FAIL if the badge is hidden or suppressed in offer mode.

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const DEFAULT_PROFILE_ESTIMATE = {
  status: "fresh" as const,
  time_seconds: 3600,
  filament_g: 50.5,
  filament_mm: 16000,
  filament_cm3: 40,
  filament_cost: 3.0,
  currency: "PLN",
  computed_at: "2026-06-14T10:00:00Z",
  warnings: [] as { code: string; message: string }[],
  failure_reason: null,
  override_context: {
    material_class: "PLA" as const,
    quality_tier: "standard" as const,
    pinned_filament_name: null,
    custom_overrides_applied: false,
    purchase_url: null,
  },
  profile_selection_context: {
    estimate_profile_source: "default_material_profile" as const,
    selected_material: "PLA",
    selected_spoolman_filament_ref: null,
    selected_filament_name: null,
    orca_filament_profile_name: null,
  },
  offer_id: "abc123",
};

describe("AC-21 NFR24-HONESTY-1: offer-mode default_material_profile badge is shown", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("renders Default PLA profile badge when estimate_profile_source is default_material_profile", () => {
    render(
      <EstimateDisplay
        isPending={false}
        isError={false}
        data={DEFAULT_PROFILE_ESTIMATE}
        onRetry={vi.fn()}
      />,
      { wrapper },
    );

    // The "Default PLA profile" badge MUST be visible (NFR24-HONESTY-1).
    // i18n key: modules.estimates.profile_source.default with material=PLA
    expect(screen.getByText("Default PLA profile")).toBeTruthy();
  });

  it("does NOT render source badge for not_computed status (§E.3)", () => {
    const NOT_COMPUTED = {
      ...DEFAULT_PROFILE_ESTIMATE,
      status: "not_computed" as const,
      time_seconds: null,
      filament_g: null,
      filament_mm: null,
      filament_cm3: null,
      filament_cost: null,
      computed_at: null,
    };

    render(
      <EstimateDisplay
        isPending={false}
        isError={false}
        data={NOT_COMPUTED}
        onRetry={vi.fn()}
      />,
      { wrapper },
    );

    // Source badge must NOT be shown for not_computed (§E.3 — misleading to show source for absent estimate)
    expect(screen.queryByText("Default PLA profile")).toBeNull();
    expect(screen.queryByText("Exact filament profile")).toBeNull();
    // But the "not yet available" notice must be shown
    expect(screen.getByText("Estimate not yet available")).toBeTruthy();
  });

  it("renders exact filament mapping badge for exact_filament_mapping source", () => {
    const EXACT_ESTIMATE = {
      ...DEFAULT_PROFILE_ESTIMATE,
      profile_selection_context: {
        ...DEFAULT_PROFILE_ESTIMATE.profile_selection_context,
        estimate_profile_source: "exact_filament_mapping" as const,
      },
    };

    render(
      <EstimateDisplay
        isPending={false}
        isError={false}
        data={EXACT_ESTIMATE}
        onRetry={vi.fn()}
      />,
      { wrapper },
    );

    expect(screen.getByText("Exact filament profile")).toBeTruthy();
  });
});
