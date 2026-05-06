import { expect, test } from "@playwright/test";

import { stubSotList, stubViewerModelDetail } from "./api-stubs";
import { waitForReady } from "./helpers";

const MODEL_ID = "33333333-3333-3333-3333-333333333333";
const STL_ID = "44444444-4444-4444-4444-444444444444";

test.describe("viewer3d — inline placeholder", () => {
  test("offline render placeholder + Open 3D button before user clicks", async ({
    page,
  }) => {
    await stubSotList(page);
    await stubViewerModelDetail(page, {
      modelId: MODEL_ID,
      stlFileId: STL_ID,
      thumbnailFileId: "thumb-1",
    });
    await page.goto(`/catalog/${MODEL_ID}`);
    await waitForReady(page);
    await page.getByRole("tab", { name: /^files\b/i }).click();
    await expect(page.getByRole("button", { name: /open 3d|otwórz 3d/i })).toBeVisible();
    await expect(page).toHaveScreenshot("viewer3d-inline-placeholder.png", {
      maxDiffPixelRatio: 0.01,
      fullPage: false,
    });
  });
});
