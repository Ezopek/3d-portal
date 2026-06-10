import type { Route } from "@playwright/test";

import { expect, test } from "./_test";
import { waitForReady } from "./helpers";

// Story 35.5 (AC-11) — estimate display with profile_selection_context visual states.
//
// 4 scenarios × 4 visual projects (desktop-light/desktop-dark/mobile-light/mobile-dark)
// = 16 snapshots total.
//
// Each scenario stubs /api/estimates with a fixed profile_selection_context payload
// and a pinned clock for pixel-stable numbers across all projects.

const STL_HASH = "a".repeat(64);
const FIXED_NOW_ISO = "2026-06-02T10:05:00Z";
const COMPUTED_AT = "2026-06-02T10:00:00Z";

const OVERRIDE_CONTEXT = {
  material_class: "PLA",
  quality_tier: "standard",
  pinned_filament_name: "Bambu PLA Basic",
  custom_overrides_applied: false,
  purchase_url: null,
};

function estimateWithSource(
  status: string,
  source: "exact_filament_mapping" | "default_material_profile" | "unavailable_no_profile",
  numericOverrides: Record<string, unknown> = {},
) {
  return {
    status,
    time_seconds: 12947,
    filament_g: 76.76,
    filament_mm: 25735.79,
    filament_cm3: 61.9,
    filament_cost: 4.6,
    currency: "PLN",
    computed_at: COMPUTED_AT,
    warnings: [],
    failure_reason: null,
    override_context: OVERRIDE_CONTEXT,
    profile_selection_context: {
      estimate_profile_source: source,
      selected_material: "PLA",
      selected_spoolman_filament_ref:
        source === "exact_filament_mapping"
          ? "Bambu\x1fPLA\x1fPLA Basic"
          : null,
      selected_filament_name: "Bambu PLA Basic",
      orca_filament_profile_name:
        source !== "unavailable_no_profile"
          ? "Bambu PLA Basic @BBL X1C"
          : null,
    },
    ...numericOverrides,
  };
}

async function stubEstimate(
  route: (pattern: string, handler: (r: Route) => void) => Promise<unknown>,
  body: Record<string, unknown>,
) {
  await route("**/api/spools/summary**", (r) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        spools: [],
        filaments: [],
        vendors: [],
        fetched_at: null,
        last_success_ts: null,
      }),
    }),
  );
  await route("**/api/estimates**", (r) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    }),
  );
}

const SCENARIOS: Array<{ name: string; body: Record<string, unknown> }> = [
  {
    name: "fresh-exact",
    body: estimateWithSource("fresh", "exact_filament_mapping"),
  },
  {
    name: "fresh-default",
    body: estimateWithSource("fresh", "default_material_profile"),
  },
  {
    name: "absent-unavailable",
    body: estimateWithSource("absent", "unavailable_no_profile", {
      time_seconds: null,
      filament_g: null,
      filament_mm: null,
      filament_cm3: null,
      filament_cost: null,
      computed_at: null,
    }),
  },
  {
    name: "stale-default",
    body: estimateWithSource("stale", "default_material_profile"),
  },
];

for (const scenario of SCENARIOS) {
  test(`/estimates renders ${scenario.name}`, async ({ page }) => {
    await page.clock.install({ time: new Date(FIXED_NOW_ISO) });
    await stubEstimate(
      (pattern, handler) => page.route(pattern, handler),
      scenario.body,
    );
    await page.goto(`/estimates?stl_hash=${STL_HASH}`);
    await waitForReady(page);
    await expect(page).toHaveScreenshot(
      `estimate-profile-source-${scenario.name}.png`,
      { fullPage: true },
    );
  });
}
