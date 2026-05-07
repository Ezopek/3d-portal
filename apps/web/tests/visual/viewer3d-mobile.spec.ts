import { expect, test } from "@playwright/test";

import { stubSotList, stubViewerModelDetail } from "./api-stubs";
import { waitForReady } from "./helpers";

const MODEL_ID = "33333333-3333-3333-3333-333333333333";
const STL_ID = "44444444-4444-4444-4444-444444444444";

test.describe("viewer3d — mobile inline", () => {
  test("phone viewport shows the file list collapsed (no inline preview)", async ({
    page,
  }, testInfo) => {
    test.skip(
      !testInfo.project.name.startsWith("mobile-"),
      "mobile-only assertion",
    );
    await stubSotList(page);
    await stubViewerModelDetail(page, {
      modelId: MODEL_ID,
      stlFileId: STL_ID,
      thumbnailFileId: "thumb-1",
    });
    await page.goto(`/catalog/${MODEL_ID}`);
    await waitForReady(page);
    await page.getByRole("tab", { name: /^files\b/i }).click();
    // Default state — list shows the per-row preview chevron, no canvas.
    await expect(
      page.getByRole("button", { name: /toggle 3d preview for cube\.stl/i }),
    ).toBeVisible();
    await expect(page.locator("canvas")).toHaveCount(0);
    await expect(page).toHaveScreenshot("viewer3d-mobile.png", {
      maxDiffPixelRatio: 0.01,
    });
  });
});
