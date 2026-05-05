import { expect, test } from "@playwright/test";

import { stubSotDetail } from "./api-stubs";
import { waitForReady } from "./helpers";

test("catalog detail matches baseline", async ({ page }) => {
  await stubSotDetail(page);
  await page.goto("/catalog/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
  await waitForReady(page);
  await expect(page).toHaveScreenshot("catalog-detail.png", { fullPage: true });
});
