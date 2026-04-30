import { expect, test } from "@playwright/test";

import { stubCatalog } from "./api-stubs";
import { waitForReady } from "./helpers";

test("catalog detail matches baseline", async ({ page }) => {
  await stubCatalog(page);
  await page.goto("/catalog/001");
  await waitForReady(page);
  await expect(page).toHaveScreenshot("catalog-detail.png", { fullPage: true });
});
