import { expect, test } from "@playwright/test";

import { stubSotList } from "./api-stubs";
import { waitForReady } from "./helpers";
import type { Page, Route } from "@playwright/test";

async function stubAdminAuth(page: Page) {
  await page.route("**/api/auth/me", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "u-admin",
        email: "ezop@example.com",
        display_name: "Ezop",
        role: "admin",
      }),
    }),
  );
}

// Catalog/SoT endpoints fire on `/` (which redirects through to the catalog
// route). Without stubs the visual test would either time out on networkidle
// or — if a real backend is reachable — fetch live data and violate the
// no-real-network contract (project-context.md). The dialog/menu screenshots
// are scoped to the popup/dialog locator so the catalog payload itself does
// not affect baselines; the stub is purely about determinism.
async function stubVisualEnvironment(page: Page) {
  await stubAdminAuth(page);
  await stubSotList(page);
}

test.describe("UserMenu — TB-006 admin agents entry", () => {
  test("user menu open with 'For agents' item visible", async ({ page }) => {
    await stubVisualEnvironment(page);
    await page.goto("/");
    await page.waitForSelector("text=Ezop", { state: "visible" });
    await waitForReady(page);
    await page.getByRole("button", { name: "Ezop" }).click();
    // Scope to the open dropdown popup so background catalog rendering
    // (which is NOT stubbed in this spec) doesn't introduce non-determinism.
    const popup = page.locator("[data-slot='dropdown-menu-content']");
    await popup.waitFor({ state: "visible" });
    await expect(popup).toHaveScreenshot("agents-menu-open.png");
  });

  test("agents dialog renders with three copy blocks + two external links", async ({ page }) => {
    await stubVisualEnvironment(page);
    await page.goto("/");
    await page.waitForSelector("text=Ezop", { state: "visible" });
    await waitForReady(page);
    await page.getByRole("button", { name: "Ezop" }).click();
    await page.getByText(/For agents|Dla agentów/).click();
    const dialog = page.locator("[data-slot='dialog-content']");
    await dialog.waitFor({ state: "visible" });
    // Wait one frame for the open-animation transform/zoom to settle
    // (the global helper already disables animation/transition durations).
    await page.waitForTimeout(50);
    await expect(dialog).toHaveScreenshot("agents-dialog.png");
  });
});
