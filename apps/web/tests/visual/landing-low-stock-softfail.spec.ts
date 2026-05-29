import type { Route } from "@playwright/test";

import { expect, test } from "./_test";
import { waitForReady } from "./helpers";

// Cold-cache + Spoolman-down soft-fail: backend Story 31.2 returns 200
// with empty arrays + null fetched_at + null last_success_ts per
// FR19-FAILURE-1. The LandingPage renders the LowStockCard in the
// "unavailable" empty state (no Retry — cache repopulates via arq poll).
test("/ renders the LowStockCard soft-fail unavailable state", async ({ page }) => {
  await page.route("**/api/spools/summary", (route: Route) =>
    route.fulfill({
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
  await page.goto("/");
  await waitForReady(page);
  await expect(page).toHaveScreenshot("landing-low-stock-softfail.png", { fullPage: true });
});
