import type { Route } from "@playwright/test";

import { expect, test } from "./_test";
import { waitForReady } from "./helpers";

// Cold-cache + Spoolman-down soft-fail: backend Story 31.2 returns 200
// with empty arrays + null fetched_at + null last_success_ts per
// FR19-FAILURE-1. SpoolsIndexPage renders the "unavailable" EmptyState.
test("/spools renders the soft-fail unavailable state", async ({ page }) => {
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
  await page.goto("/spools");
  await waitForReady(page);
  await expect(page).toHaveScreenshot("spools-index-softfail.png", { fullPage: true });
});
