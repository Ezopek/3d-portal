import { expect, test } from "@playwright/test";

import { stubCatalog } from "./api-stubs";
import { waitForReady } from "./helpers";

async function loginAsAdmin(page: import("@playwright/test").Page) {
  await page.addInitScript(() => {
    localStorage.setItem("portal.token", "fake-test-token");
    localStorage.setItem(
      "portal.token.exp",
      String(Date.now() + 60 * 60 * 1000),
    );
  });
}

test("catalog detail with admin thumbnail controls", async ({ page }) => {
  await loginAsAdmin(page);
  await stubCatalog(page);
  await page.goto("/catalog/001");
  await waitForReady(page);
  await expect(page).toHaveScreenshot("catalog-detail-admin.png", {
    fullPage: true,
  });
});
