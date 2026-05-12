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
    // Locale-dependent: SecondaryTabs renders 3-5 sibling tabs, so role-only
    // is ambiguous; match the PL render under playwright.config.ts locale="pl-PL".
    await page.getByRole("tab", { name: /^pliki\b/i }).click();
    await page
      .getByRole("button", { name: /toggle 3d preview for cube\.stl/i })
      .click();
    await page.locator("canvas").first().waitFor({ state: "visible" });
    await page.getByRole("button", { name: /expand|powiększ/i }).click();
    await page.getByRole("dialog").waitFor({ state: "visible" });

    // Locale-dependent: post-refactor toolbar exposes 4 mode buttons (p2p,
    // p2pl, pl2pl, diameter — deprecated `viewer3d.tooltip.measure` removed).
    // p2p is the point-to-point mode; PL label "Pomiar punkt-do-punktu"
    // (`viewer3d.measure.mode.p2p`). Anchored regex disambiguates from the
    // 3 sibling modes that all begin with "Pomiar".
    const ruler = page
      .getByRole("dialog")
      .getByRole("button", { name: /^pomiar punkt-do-punktu$/i });
    await ruler.click();
    await expect(ruler).toHaveAttribute("aria-pressed", "true");
    await page.waitForTimeout(300);

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

    // Layout was refactored in 34125a4 (MeasureSummary swatches): the row
    // is now two adjacent spans `#1` and `5.2 mm` (no em-dash separator).
    // Assert via the in-canvas floating label which carries the full
    // composite text (e.g. "#1 4.8 mm" or "#1 4.8 mm (przybliżone)") —
    // unique enough to disambiguate from the summary's bare "#1" span.
    await expect(
      page.locator("[role=dialog]").getByText(/^#1\s+\d+\.\d\s*mm/i),
    ).toBeVisible();

    await expect(page).toHaveScreenshot("viewer3d-measure-pp.png", {
      maxDiffPixelRatio: 0.08,
    });
  });
});
