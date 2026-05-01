import { expect, test } from "@playwright/test";

import { waitForReady } from "./helpers";

// /queue, /spools, /printer, /requests all render the same ComingSoonStub.
// Screenshotting /queue is representative for the whole set.
test("queue placeholder is vertically centered", async ({ page }) => {
  await page.goto("/queue");
  await waitForReady(page);
  await expect(page).toHaveScreenshot("queue-placeholder.png", { fullPage: true });
});
