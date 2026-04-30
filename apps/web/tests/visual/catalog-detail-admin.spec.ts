import { expect, test } from "@playwright/test";

import { stubCatalog } from "./api-stubs";
import { loginAsAdmin, waitForReady } from "./helpers";

test("catalog detail with admin thumbnail controls", async ({ page }) => {
  await loginAsAdmin(page);
  await stubCatalog(page);
  await page.goto("/catalog/001");
  await waitForReady(page);
  await expect(page).toHaveScreenshot("catalog-detail-admin.png", {
    fullPage: true,
  });
});
