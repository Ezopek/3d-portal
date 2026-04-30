import { expect, test } from "@playwright/test";

import { stubCatalog } from "./api-stubs";
import { loginAsAdmin } from "./helpers";

// Admin star overlay is only reachable on desktop (mobile sticky header
// physically covers the absolute-positioned star button at top-2).
test.skip(({ isMobile }) => isMobile, "desktop-only: star button covered by sticky header on mobile");

test("admin star click PUTs to the override endpoint", async ({ page }) => {
  await loginAsAdmin(page);
  await stubCatalog(page);

  let putBody: { path?: string } | null = null;
  await page.route("**/api/admin/models/001/thumbnail", async (route) => {
    if (route.request().method() === "PUT") {
      putBody = JSON.parse(route.request().postData() ?? "{}");
      await route.fulfill({ status: 204, body: "" });
    } else {
      await route.fallback();
    }
  });

  await page.goto("/catalog/001");
  await page.waitForLoadState("networkidle");

  // Active main image is the first candidate (Dragon.png — also the current default).
  // Click a different thumbnail strip tile (the prints entry) so the active image
  // changes to a non-default; then the star turns into "Set as default".
  await page.locator('button:has(img[src*="prints/2026-04-30-dragon.jpg"])').first().click();

  // Polish locale → "Ustaw jako domyślną"
  await page.locator('button[title="Ustaw jako domyślną"]').click();

  await expect.poll(() => putBody !== null).toBe(true);
  expect(putBody!.path).toBe("prints/2026-04-30-dragon.jpg");

  // Toast appears (sonner renders each toast as [data-sonner-toast]).
  await expect(page.locator('[data-sonner-toast]').first()).toBeVisible();
});

test("admin star-on-current click DELETEs to clear", async ({ page }) => {
  await loginAsAdmin(page);
  await stubCatalog(page);

  let deleteCalled = false;
  await page.route("**/api/admin/models/001/thumbnail", async (route) => {
    if (route.request().method() === "DELETE") {
      deleteCalled = true;
      await route.fulfill({ status: 204, body: "" });
    } else {
      await route.fallback();
    }
  });

  await page.goto("/catalog/001");
  await page.waitForLoadState("networkidle");

  // Dragon.png is the current default per the stub thumbnail_url.
  // The star is "filled" → tooltip is "Domyślna miniaturka". Clicking clears.
  await page.locator('button[title="Domyślna miniaturka"]').click();
  await expect.poll(() => deleteCalled).toBe(true);
});
