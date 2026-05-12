import { expect, test } from "@playwright/test";

import { stubSotList, stubViewerModelDetail, stubViewerStl } from "./api-stubs";
import { waitForReady } from "./helpers";

const MODEL_ID = "33333333-3333-3333-3333-333333333333";
const STL_ID = "44444444-4444-4444-4444-444444444444";

test.describe("viewer3d — plane-aware measurement", () => {
  test.beforeEach(async ({ page }) => {
    await stubSotList(page);
    await stubViewerModelDetail(page, {
      modelId: MODEL_ID,
      stlFileId: STL_ID,
      thumbnailFileId: null,
    });
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
    await page.getByRole("button", { name: /expand|powiększ/i }).click();
    await page.getByRole("dialog").waitFor({ state: "visible" });
  });

  test("p2pl mode button highlights when active", async ({ page }) => {
    const btn = page
      .getByRole("dialog")
      .getByRole("button", { name: /punkt-do-płaszczyzny/i });
    await btn.click();
    await expect(btn).toHaveAttribute("aria-pressed", "true");
    await expect(page).toHaveScreenshot("viewer3d-mode-buttons-p2pl.png", {
      maxDiffPixelRatio: 0.05,
    });
  });

  test("clicking a cube face shows cluster overlay + step banner", async ({ page }) => {
    const btn = page
      .getByRole("dialog")
      .getByRole("button", { name: /punkt-do-płaszczyzny/i });
    await btn.click();
    const canvas = page.locator("[role=dialog] canvas").first();
    const box = await canvas.boundingBox();
    if (box === null) throw new Error("no canvas");
    await canvas.click({
      position: { x: Math.round(box.width / 2), y: Math.round(box.height / 2) },
    });
    await page.waitForTimeout(500);
    await expect(page).toHaveScreenshot("viewer3d-cluster-overlay.png", {
      maxDiffPixelRatio: 0.08,
    });
  });

  test("tolerance popover opens", async ({ page }) => {
    await page
      .getByRole("dialog")
      .getByRole("button", { name: /punkt-do-płaszczyzny/i })
      .click();
    const toleranceBtn = page
      .getByRole("dialog")
      .getByRole("button", { name: /tolerance|tolerancja/i });
    await toleranceBtn.click();
    await expect(page).toHaveScreenshot("viewer3d-tolerance-popover.png", {
      maxDiffPixelRatio: 0.05,
    });
  });
});
