import { expect, test } from "@playwright/test";

import { stubSotDetail, stubSotList, stubViewerModelDetail, stubViewerStl } from "./api-stubs";
import { loginAsAdmin, waitForReady } from "./helpers";
import type { Page, Route } from "@playwright/test";

// 5.12c covers four DropdownMenu / Tooltip open-state surfaces:
//   - ViewToolbar Tooltip (hover state inside Viewer3DModal)
//   - ModelHero admin kebab DropdownMenu
//   - StatusPopover (named *Popover but uses DropdownMenu primitive)
//   - RatingPopover (same naming surprise)
// All four require admin auth. The popovers/* directory name is misleading
// — both Status/Rating components instantiate DropdownMenu, not Popover.

const DETAIL_MODEL_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const VIEWER_MODEL_ID = "33333333-3333-3333-3333-333333333333";
const VIEWER_STL_ID = "44444444-4444-4444-4444-444444444444";

async function stubAdminAuth(page: Page) {
  await page.route("**/api/auth/me", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "u-admin",
        email: "ezop@example.com",
        display_name: "Ezop",
        role: "admin",
      }),
    }),
  );
}

async function setupDetail(page: Page) {
  await loginAsAdmin(page);
  await stubAdminAuth(page);
  await stubSotDetail(page);
  await page.goto(`/catalog/${DETAIL_MODEL_ID}`);
  await waitForReady(page);
}

test.describe("Admin DropdownMenus + Tooltip — open-state baselines (E5.12c)", () => {
  test("ModelHero admin kebab DropdownMenu open", async ({ page }) => {
    await setupDetail(page);
    // catalog.actions.modelActions = "Akcje modelu".
    await page.getByRole("button", { name: /^Akcje modelu$/i }).click();
    const menu = page.locator("[data-slot='dropdown-menu-content']");
    await menu.waitFor({ state: "visible" });
    await page.waitForTimeout(50);
    await expect(menu).toHaveScreenshot("model-hero-admin-menu-open.png");
  });

  test("StatusPopover (DropdownMenu) open", async ({ page }) => {
    await setupDetail(page);
    // The status chip is a <span> wrapped by DropdownMenuTrigger nativeButton=false.
    // It is the StatusBadge — labelled by its current status text. The stubbed
    // detail has status="printed" → PL = "Wydrukowane". Click on the span via
    // the StatusBadge text content; scope to the hero region first to avoid
    // hitting the filter ribbon Select.
    await page.getByText(/^Wydrukowane$/i).first().click();
    const menu = page.locator("[data-slot='dropdown-menu-content']");
    await menu.waitFor({ state: "visible" });
    await page.waitForTimeout(50);
    await expect(menu).toHaveScreenshot("status-popover-open.png");
  });

  test("RatingPopover (DropdownMenu) open", async ({ page }) => {
    await setupDetail(page);
    // The rating chip is a <span> showing "★ 4.5" (rating from stubSotDetail).
    // Click that span — the closest selectable rendered text is the star+value.
    await page.getByText(/^★\s*4\.5$/).first().click();
    const menu = page.locator("[data-slot='dropdown-menu-content']");
    await menu.waitFor({ state: "visible" });
    await page.waitForTimeout(50);
    await expect(menu).toHaveScreenshot("rating-popover-open.png");
  });

  test("ViewToolbar Tooltip hover", async ({ page }) => {
    // Different fixture — Viewer3DModal requires the viewer stub with cube STL.
    await loginAsAdmin(page);
    await stubAdminAuth(page);
    await stubSotList(page);
    await stubViewerModelDetail(page, {
      modelId: VIEWER_MODEL_ID,
      stlFileId: VIEWER_STL_ID,
      thumbnailFileId: null,
    });
    await stubViewerStl(page, VIEWER_MODEL_ID, VIEWER_STL_ID);
    await page.goto(`/catalog/${VIEWER_MODEL_ID}`);
    await waitForReady(page);
    // Open the Files tab → inline 3D preview → expand to modal (PL labels).
    await page.getByRole("tab", { name: /^pliki\b/i }).click();
    await page.getByRole("button", { name: /toggle 3d preview for cube\.stl/i }).click();
    await page.locator("canvas").first().waitFor({ state: "visible" });
    await page.getByRole("button", { name: /expand|powiększ/i }).click();
    await page.getByRole("dialog").waitFor({ state: "visible" });
    // Hover the "Reset view" toolbar button. viewer3d.tooltip.reset = "Resetuj widok".
    const dialog = page.getByRole("dialog");
    const resetBtn = dialog.getByRole("button", { name: /^Resetuj widok$/i });
    await resetBtn.hover();
    const tooltip = page.locator("[data-slot='tooltip-content']");
    await tooltip.waitFor({ state: "visible" });
    await page.waitForTimeout(100);
    await expect(page).toHaveScreenshot("view-toolbar-tooltip-open.png", {
      maxDiffPixelRatio: 0.05,
    });
  });
});
