import type { Route } from "@playwright/test";

import { expect, test } from "./_test";
import { waitForReady } from "./helpers";

// Story 32.6 (AC-8, NFR20-VISUAL-VERIFICATION-1) — estimate display visual states.
//
// Each state is driven by a MOCKED `/api/estimates` response with a PINNED `computed_at`
// and a pinned wall clock (page.clock), so the soft-fail "Last estimated HH:MM (Xm ago)"
// label and every number are pixel-stable across the 4 visual projects
// (desktop-light/desktop-dark/mobile-light/mobile-dark). No real slice/Orca/worker runs.
//
// NOTE (baseline status): these specs are authored under Story 32.6; the `__snapshots__`
// baselines are generated + `baseline-reviewed:` signed off in the controller-owned visual
// pass (the dev environment for this continuation had no browser/dev-server budget). See the
// story File List / Dev Agent Record for the deferred-baseline note.

const STL_HASH = "a".repeat(64);
const FIXED_NOW_ISO = "2026-06-02T10:05:00Z";
const COMPUTED_AT = "2026-06-02T10:00:00Z"; // 5 minutes before FIXED_NOW

const CONTEXT = {
  material_class: "PLA",
  quality_tier: "standard",
  pinned_filament_name: null,
  custom_overrides_applied: false,
  purchase_url: null,
};

function estimate(overrides: Record<string, unknown> = {}) {
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

async function stubEstimate(
  route: (pattern: string, handler: (r: Route) => void) => Promise<unknown>,
  body: Record<string, unknown>,
) {
  // Empty spools summary so the selector's pin list is deterministic (no pins).
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

const STATES: Array<{ name: string; body: Record<string, unknown> }> = [
  { name: "fresh", body: estimate({ status: "fresh" }) },
  { name: "stale", body: estimate({ status: "stale" }) },
  { name: "queued", body: estimate({ status: "queued" }) },
  {
    name: "failed",
    body: estimate({
      status: "failed",
      failure_reason: "unparseable_time",
      time_seconds: null,
      filament_g: null,
      filament_mm: null,
      filament_cm3: null,
      filament_cost: null,
      computed_at: COMPUTED_AT,
    }),
  },
  {
    name: "absent",
    body: estimate({
      status: "absent",
      time_seconds: null,
      filament_g: null,
      filament_mm: null,
      filament_cm3: null,
      filament_cost: null,
      computed_at: null,
    }),
  },
];

for (const state of STATES) {
  test(`/estimates renders the ${state.name} state`, async ({ page }) => {
    await page.clock.install({ time: new Date(FIXED_NOW_ISO) });
    await stubEstimate(
      (pattern, handler) => page.route(pattern, handler),
      state.body,
    );
    await page.goto(`/estimates?stl_hash=${STL_HASH}`);
    await waitForReady(page);
    await expect(page).toHaveScreenshot(`estimates-${state.name}.png`, {
      fullPage: true,
    });
  });
}
