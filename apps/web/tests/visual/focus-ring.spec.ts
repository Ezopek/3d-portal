import { expect, test } from "@playwright/test";

import { stubSotList } from "./api-stubs";
import { waitForReady } from "./helpers";

test("focus ring is visible on first nav link", async ({ page }) => {
  await stubSotList(page);
  await page.goto("/catalog");
  await waitForReady(page);
  // Tab once — first focusable is the first visible nav link (desktop rail
  // on lg+, mobile bottom bar on smaller). The outline-2 outline-offset-2
  // outline-ring rule must produce a clearly visible focus indicator
  // distinct from the active-state background tint.
  await page.keyboard.press("Tab");
  await expect(page).toHaveScreenshot("rail-focus.png");
});
