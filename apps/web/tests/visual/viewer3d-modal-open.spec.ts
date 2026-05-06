import { expect, test } from "@playwright/test";

import { stubSotList, stubViewerModelDetail, stubViewerStl } from "./api-stubs";
import { waitForReady } from "./helpers";

const MODEL_ID = "33333333-3333-3333-3333-333333333333";
const STL_ID = "44444444-4444-4444-4444-444444444444";

test.describe("viewer3d — modal open selector", () => {
  test("file selector dropdown shows the search field and one cube row", async ({
    page,
  }) => {
    await stubSotList(page);
    await stubViewerModelDetail(page, {
      modelId: MODEL_ID,
      stlFileId: STL_ID,
      thumbnailFileId: null,
    });
    await stubViewerStl(page, MODEL_ID, STL_ID);
    await page.goto(`/catalog/${MODEL_ID}`);
    await waitForReady(page);
    await page.getByRole("tab", { name: /^files\b/i }).click();
    await page.locator("canvas").first().waitFor({ state: "visible" });
    await page.getByRole("button", { name: /expand|powiększ/i }).click();
    await page.getByRole("dialog").waitFor({ state: "visible" });
    // The selector trigger inside the dialog has aria-label "Plik: cube.stl"
    // (or "File: cube.stl" for en-US). Click it to open the dropdown.
    await page
      .getByRole("dialog")
      .getByRole("button", { name: /^(plik|file):\s*cube\.stl$/i })
      .click();
    await expect(page.getByPlaceholder(/filtruj|filter/i)).toBeVisible();
    await page.waitForTimeout(300);
    await expect(page).toHaveScreenshot("viewer3d-modal-open.png", {
      maxDiffPixelRatio: 0.05,
    });
  });
});
