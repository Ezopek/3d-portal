import { expect, test } from "@playwright/test";

import { stubSotList, stubViewerModelDetail, stubViewerStl } from "./api-stubs";
import { waitForReady } from "./helpers";

const MODEL_ID = "33333333-3333-3333-3333-333333333333";
const STL_ID = "44444444-4444-4444-4444-444444444444";

test.describe("viewer3d — inline loaded", () => {
  test("inline canvas mounts and renders the cube", async ({ page }) => {
    await stubSotList(page);
    await stubViewerModelDetail(page, {
      modelId: MODEL_ID,
      stlFileId: STL_ID,
      thumbnailFileId: null,
    });
    // Register STL-specific route AFTER the model-detail stub: Playwright
    // tries route handlers LIFO, so the last-registered match wins.
    await stubViewerStl(page, MODEL_ID, STL_ID);
    await page.goto(`/catalog/${MODEL_ID}`);
    await waitForReady(page);
    await page.getByRole("tab", { name: /^files\b/i }).click();
    await page.locator("canvas").first().waitFor({ state: "visible" });
    // Allow one render frame to settle.
    await page.waitForTimeout(500);
    await expect(page).toHaveScreenshot("viewer3d-inline-loaded.png", {
      // WebGL output varies between machines; accept up to 5% pixel diff.
      maxDiffPixelRatio: 0.05,
    });
  });
});
