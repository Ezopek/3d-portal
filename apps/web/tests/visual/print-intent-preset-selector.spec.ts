import type { Route } from "@playwright/test";

import { expect, test } from "./_test";
import { waitForReady } from "./helpers";

// Story 32.6 (AC-8) — the PrintIntentPreset selector + override-context panel visual baseline.
//
// Driven by a mocked spools summary (one filament, so the pin option renders) + a `fresh`
// estimate whose override context carries a pinned filament, the custom-applied badge, and a
// purchase link — the AC-5 provenance surface. Baselines generated/sign-off in the
// controller-owned visual pass (see estimates-display.spec.ts note).

const STL_HASH = "a".repeat(64);
const FIXED_NOW_ISO = "2026-06-02T10:05:00Z";
const COMPUTED_AT = "2026-06-02T10:00:00Z";

const FILAMENT = {
  id: 10,
  name: "PLA Speed Matt White",
  vendor_id: 100,
  vendor_name: "Bambu Lab",
  material: "PLA",
  color_hex: "FFFFFF",
  price: 99.9,
  weight: 1000,
  spool_weight: 200,
};

test("/estimates renders the selector + override context (pinned filament)", async ({
  page,
}) => {
  await page.clock.install({ time: new Date(FIXED_NOW_ISO) });
  await page.route("**/api/spools/summary**", (r: Route) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        spools: [],
        filaments: [FILAMENT],
        vendors: [{ id: 100, name: "Bambu Lab" }],
        fetched_at: null,
        last_success_ts: null,
      }),
    }),
  );
  await page.route("**/api/estimates**", (r: Route) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "fresh",
        time_seconds: 12947,
        filament_g: 76.76,
        filament_mm: 25735.79,
        filament_cm3: 61.9,
        filament_cost: 4.6,
        currency: "PLN",
        computed_at: COMPUTED_AT,
        warnings: [
          { code: "slice_warning", message: "Floating cantilever detected" },
        ],
        failure_reason: null,
        override_context: {
          material_class: "PLA",
          quality_tier: "standard",
          pinned_filament_name: "PLA Speed Matt White",
          custom_overrides_applied: true,
          purchase_url: "https://shop.example.com/pla-white",
        },
      }),
    }),
  );
  await page.goto(`/estimates?stl_hash=${STL_HASH}`);
  await waitForReady(page);
  await expect(page).toHaveScreenshot("print-intent-preset-selector.png", {
    fullPage: true,
  });
});
