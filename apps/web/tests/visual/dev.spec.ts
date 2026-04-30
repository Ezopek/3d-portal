import { expect, test } from "@playwright/test";

import { waitForReady } from "./helpers";

test("dev/components matches baseline", async ({ page }) => {
  await page.goto("/dev/components");
  await waitForReady(page);
  await expect(page).toHaveScreenshot("dev-components.png", { fullPage: true });
});
