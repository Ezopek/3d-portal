import { expect, test } from "@playwright/test";

import { stubSotList, stubViewerModelDetail, stubViewerStl } from "./api-stubs";
import { waitForReady } from "./helpers";

const MODEL_ID = "33333333-3333-3333-3333-333333333333";
const STL_ID = "44444444-4444-4444-4444-444444444444";

test.describe("viewer3d — point-to-point measurement", () => {
  test("two clicks on the cube produce a labelled measurement", async ({ page }) => {
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

    // Enable measure mode (Ruler icon — tooltip text is "Pomiar (punkt do
    // punktu)" / "Measure (point-to-point)"). Verify aria-pressed flipped
    // to confirm the click actually wired through.
    const ruler = page
      .getByRole("dialog")
      .getByRole("button", { name: /pomiar|measure/i });
    await ruler.click();
    await expect(ruler).toHaveAttribute("aria-pressed", "true");
    await page.waitForTimeout(300);

    // Click on the canvas via Locator.click(position) — Playwright issues a
    // proper pointer-down/move/up sequence at the given offset relative to
    // the canvas, which is what R3F's raycaster listens for.
    const canvas = page.locator("[role=dialog] canvas").first();
    const box = await canvas.boundingBox();
    if (box === null) throw new Error("canvas not laid out");
    await canvas.click({
      position: { x: Math.round(box.width * 0.45), y: Math.round(box.height * 0.5) },
    });
    await page.waitForTimeout(250);
    await canvas.click({
      position: { x: Math.round(box.width * 0.55), y: Math.round(box.height * 0.5) },
    });
    await page.waitForTimeout(500);

    // Functional assertion: the off-canvas summary should now show one
    // measurement formatted as `#1 — X.X mm`. This is the part we trust to
    // be stable; the WebGL canvas pixels are not.
    await expect(
      page.locator("[role=dialog]").getByText(/#1\s*[—-]\s*\d+\.\d\s*mm/i),
    ).toBeVisible();

    await expect(page).toHaveScreenshot("viewer3d-measure-pp.png", {
      maxDiffPixelRatio: 0.08,
    });
  });
});
