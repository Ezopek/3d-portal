import { expect, test } from "@playwright/test";

import { stubSotList } from "./api-stubs";
import { waitForReady } from "./helpers";
import type { Page, Route } from "@playwright/test";

// FilterRibbon renders three desktop-inline Selects (status / source / sort)
// at /catalog. Each SelectTrigger carries a locale-bound aria-label
// (t("catalog.filters.<key>")), so under playwright.config.ts locale="pl-PL"
// the resolved strings are "Status", "Źródło", "Sortowanie". Mobile viewports
// hide these triggers (md:hidden inverted) — there the trio lives inside the
// mobile-filters Sheet covered by 5.12d.

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

async function openSelectAndSnapshot(
  page: Page,
  ariaLabelPattern: RegExp,
  snapshotName: string,
) {
  const trigger = page.getByRole("combobox", { name: ariaLabelPattern });
  await trigger.waitFor({ state: "visible" });
  await trigger.click();
  const content = page.locator("[data-slot='select-content']");
  await content.waitFor({ state: "visible" });
  // The global helper disables animations; one frame keeps the popper
  // transform/position settled across browsers.
  await page.waitForTimeout(50);
  await expect(page.locator("body")).toHaveScreenshot(snapshotName);
}

// The desktop-inline Selects are hidden on mobile viewports (the inline
// container uses md:hidden inversion). Skip the mobile-* projects per test.
function skipOnMobile(testInfo: { project: { name: string } }) {
  test.skip(
    testInfo.project.name.startsWith("mobile-"),
    "FilterRibbon Selects render inline on desktop only; mobile uses the Filters Sheet (covered by 5.12d).",
  );
}

test.describe("FilterRibbon Selects — open-state baselines (E5.12a)", () => {
  test("status Select open", async ({ page }, testInfo) => {
    skipOnMobile(testInfo);
    await setup(page);
    // Polish aria-label from catalog.filters.status = "Status".
    await openSelectAndSnapshot(page, /^Status$/i, "filter-ribbon-status-open.png");
  });

  test("source Select open", async ({ page }, testInfo) => {
    skipOnMobile(testInfo);
    await setup(page);
    // Polish aria-label from catalog.filters.source = "Źródło".
    await openSelectAndSnapshot(page, /^Źródło$/i, "filter-ribbon-source-open.png");
  });

  test("sort Select open", async ({ page }, testInfo) => {
    skipOnMobile(testInfo);
    await setup(page);
    // Polish aria-label from catalog.filters.sort = "Sortowanie".
    await openSelectAndSnapshot(page, /^Sortowanie$/i, "filter-ribbon-sort-open.png");
  });
});
