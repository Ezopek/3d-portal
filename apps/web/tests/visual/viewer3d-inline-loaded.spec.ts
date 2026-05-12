import { expect, test } from "@playwright/test";

import { stubSotList, stubViewerModelDetail, stubViewerStl } from "./api-stubs";
import { waitForReady } from "./helpers";

const MODEL_ID = "33333333-3333-3333-3333-333333333333";
const STL_ID = "44444444-4444-4444-4444-444444444444";

test.describe("viewer3d — inline row with mounted canvas", () => {
  test("expanding a small STL row auto-loads the canvas", async ({ page }) => {
    await stubSotList(page);
    await stubViewerModelDetail(page, {
      modelId: MODEL_ID,
      stlFileId: STL_ID,
      thumbnailFileId: null,
    });
    // Register STL-specific route LAST so it wins the LIFO match against the
    // catch-all in stubViewerModelDetail.
    await stubViewerStl(page, MODEL_ID, STL_ID);
    await page.goto(`/catalog/${MODEL_ID}`);
    await waitForReady(page);
    // Locale-dependent: SecondaryTabs renders 3-5 sibling tabs, so role-only
    // is ambiguous; match the PL render under playwright.config.ts locale="pl-PL".
    await page.getByRole("tab", { name: /^pliki\b/i }).click();
    await page
      .getByRole("button", { name: /toggle 3d preview for cube\.stl/i })
      .click();
    await page.locator("canvas").first().waitFor({ state: "visible" });
    await page.waitForTimeout(500);
    await expect(page).toHaveScreenshot("viewer3d-inline-loaded.png", {
      maxDiffPixelRatio: 0.05,
    });
  });
});
