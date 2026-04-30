import { expect, test } from "@playwright/test";

import { stubCatalog } from "./api-stubs";
import { waitForReady } from "./helpers";

test("share view matches baseline", async ({ page }) => {
  await stubCatalog(page);
  await page.goto("/share/test-token");
  await waitForReady(page);
  await expect(page).toHaveScreenshot("share.png", { fullPage: true });
});
