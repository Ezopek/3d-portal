import { expect, test } from "@playwright/test";

import { stubCatalog } from "./api-stubs";
import { waitForReady } from "./helpers";

test("catalog list matches baseline", async ({ page }) => {
  await stubCatalog(page);
  await page.goto("/catalog");
  await waitForReady(page);
  await expect(page).toHaveScreenshot("catalog-list.png", { fullPage: true });
});
