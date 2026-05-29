import type { Route } from "@playwright/test";

import { expect, test } from "./_test";
import { waitForReady } from "./helpers";

const FIXED_NOW_ISO = "2026-05-29T10:01:00Z";
const LAST_SUCCESS_ISO = "2026-05-29T10:00:00Z";

// Brainstorm B5 demoable signal: PLA Speed Matt White 138.9g + PCTG Army
// Green 163.2g are the two real low-stock spools at session start. Fixture
// mirrors that state plus 2 well-stocked spools above the 200g threshold.
function fixturePayload() {
  return {
    spools: [
      {
        id: 1,
        filament_id: 10,
        price: 99.9,
        remaining_weight: 138.9,
        initial_weight: 1000,
        used_weight: 861.1,
        spool_weight: 200,
        first_used: null,
        last_used: null,
        archived: false,
        lot_nr: "PLA-1",
      },
      {
        id: 2,
        filament_id: 11,
        price: 140,
        remaining_weight: 163.2,
        initial_weight: 1000,
        used_weight: 836.8,
        spool_weight: 200,
        first_used: null,
        last_used: null,
        archived: false,
        lot_nr: "PCTG-1",
      },
      {
        id: 3,
        filament_id: 12,
        price: null,
        remaining_weight: 850,
        initial_weight: 1000,
        used_weight: 150,
        spool_weight: 200,
        first_used: null,
        last_used: null,
        archived: false,
        lot_nr: null,
      },
      {
        id: 4,
        filament_id: 13,
        price: null,
        remaining_weight: 950,
        initial_weight: 1000,
        used_weight: 50,
        spool_weight: 200,
        first_used: null,
        last_used: null,
        archived: false,
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
      {
        id: 12,
        name: "PETG Black",
        vendor_id: 101,
        vendor_name: "Polymaker",
        material: "PETG",
        color_hex: "000000",
        price: 110,
        weight: 1000,
        spool_weight: 200,
      },
      {
        id: 13,
        name: "PLA Galaxy Blue",
        vendor_id: 100,
        vendor_name: "Bambu Lab",
        material: "PLA",
        color_hex: "1C3D72",
        price: 100,
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

test("/ renders the landing dashboard with the LowStockCard listing two low-stock spools", async ({
  page,
}) => {
  await page.clock.install({ time: new Date(FIXED_NOW_ISO) });
  await page.route("**/api/spools/summary", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(fixturePayload()),
    }),
  );
  await page.goto("/");
  await waitForReady(page);
  await expect(page).toHaveScreenshot("landing-low-stock-happy.png", { fullPage: true });
});
