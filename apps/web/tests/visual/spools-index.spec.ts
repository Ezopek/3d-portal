import type { Route } from "@playwright/test";

import { expect, test } from "./_test";
import { waitForReady } from "./helpers";

const FIXED_NOW_ISO = "2026-05-29T10:01:00Z";
const LAST_SUCCESS_ISO = "2026-05-29T10:00:00Z"; // exactly 1 minute behind FIXED_NOW

function fixturePayload() {
  return {
    spools: [
      {
        id: 1,
        filament_id: 10,
        price: 42.5,
        remaining_weight: 850,
        initial_weight: 1000,
        used_weight: 150,
        spool_weight: 200,
        first_used: "2026-05-01T12:00:00Z",
        last_used: "2026-05-28T14:30:00Z",
        archived: false,
        lot_nr: "ABC123",
      },
      {
        id: 2,
        filament_id: 11,
        price: null,
        remaining_weight: 138.9,
        initial_weight: 1000,
        used_weight: 861.1,
        spool_weight: 200,
        first_used: null,
        last_used: null,
        archived: true,
        lot_nr: null,
      },
    ],
    filaments: [
      {
        id: 10,
        name: "PLA Speed Matt White",
        vendor_id: 100,
        vendor_name: "Bambu Lab",
        material: "PLA",
        color_hex: "FFFFFF",
        price: 99.9,
        weight: 1000,
        spool_weight: 200,
      },
      {
        id: 11,
        name: "PCTG Army Green",
        vendor_id: 101,
        vendor_name: "Polymaker",
        material: "PCTG",
        color_hex: "4B5320",
        price: 140,
        weight: 1000,
        spool_weight: 200,
      },
    ],
    vendors: [
      { id: 100, name: "Bambu Lab" },
      { id: 101, name: "Polymaker" },
    ],
    fetched_at: LAST_SUCCESS_ISO,
    last_success_ts: LAST_SUCCESS_ISO,
  };
}

test("/spools renders the warm-cache happy path", async ({ page }) => {
  // Pin Date so formatLastUpdated returns the deterministic "HH:MM (1m ago)"
  // suffix across project runs (4 baselines) — visual baselines need pixel-
  // stable timestamps. Timezone is pinned via playwright.config.ts to
  // Europe/Warsaw → 11:00 (CEST), so the leading HH:MM is "11:00".
  await page.clock.install({ time: new Date(FIXED_NOW_ISO) });
  await page.route("**/api/spools/summary", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(fixturePayload()),
    }),
  );
  await page.goto("/spools");
  await waitForReady(page);
  await expect(page).toHaveScreenshot("spools-index-happy.png", { fullPage: true });
});
