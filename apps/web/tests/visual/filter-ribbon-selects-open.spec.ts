import { expect, test } from "./_test";

import { stubSotList } from "./api-stubs";
import { waitForReady } from "./helpers";
import type { Page, Route } from "@playwright/test";

// The three refinement Selects (status / source / sort) used to render inline
// in `FilterRibbon` on desktop and inside a `md:hidden` sheet on mobile. Story
// 52.1 consolidated both into the single `FiltersPanel` surface, so they are
// now reached the same way on EVERY viewport: open "Filtry", then open the
// Select. These tests therefore run on all four projects without a skip.
//
// Each SelectTrigger still carries its locale-bound aria-label
// (t("catalog.filters.<key>")), so under playwright.config.ts locale="pl-PL"
// the resolved strings remain "Status", "Źródło", "Sortowanie".

async function stubAuth(page: Page) {
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

async function setup(page: Page) {
  await stubAuth(page);
  await stubSotList(page);
  await page.goto("/catalog");
  await waitForReady(page);
}

async function openPanel(page: Page) {
  // catalog.filters.openFilters = "Filtry" — at n === 0 that is the whole
  // accessible name of the one refinement trigger.
  await page.getByRole("button", { name: "Filtry", exact: true }).click();
  const sheet = page.locator("[data-slot='sheet-content']");
  await expect(sheet).toBeVisible();
  return sheet;
}

async function openSelectAndSnapshot(
  page: Page,
  ariaLabelPattern: RegExp,
  snapshotName: string,
) {
  const sheet = await openPanel(page);
  const trigger = sheet.getByRole("combobox", { name: ariaLabelPattern });
  await expect(trigger).toBeVisible();
  await trigger.click();
  const content = page.locator("[data-slot='select-content']");
  await expect(content).toBeVisible();
  // The global helper disables animations; one frame keeps the popper
  // transform/position settled across browsers.
  await page.waitForTimeout(50);
  await expect(page.locator("body")).toHaveScreenshot(snapshotName);
}

test.describe("FiltersPanel Selects — open-state baselines (Story 52.1)", () => {
  test("status Select open", async ({ page }) => {
    await setup(page);
    // Polish aria-label from catalog.filters.status = "Status".
    await openSelectAndSnapshot(page, /^Status$/i, "filters-panel-status-open.png");
  });

  test("source Select open", async ({ page }) => {
    await setup(page);
    // Polish aria-label from catalog.filters.source = "Źródło".
    await openSelectAndSnapshot(page, /^Źródło$/i, "filters-panel-source-open.png");
  });

  test("sort Select open", async ({ page }) => {
    await setup(page);
    // Polish aria-label from catalog.filters.sort = "Sortowanie".
    await openSelectAndSnapshot(page, /^Sortowanie$/i, "filters-panel-sort-open.png");
  });
});
