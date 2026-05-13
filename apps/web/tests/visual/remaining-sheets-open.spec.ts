import { expect, test } from "@playwright/test";

import { stubSotDetail, stubSotList } from "./api-stubs";
import { loginAsAdmin, waitForReady } from "./helpers";
import type { Page, Route } from "@playwright/test";

// 5.12d covers the remaining Sheet open-state surfaces:
//   - RenderSheet (form branch, from ModelHero admin kebab "Re-render")
//   - AddPrintSheet (from PrintsTab "+ Dodaj wydruk")
//   - AddNoteSheet (from OperationalNotesTab "+ Dodaj notatkę")
//   - FilterRibbon mobile-filters Sheet (mobile projects only — md:hidden)
//   - CatalogList mobile-categories Sheet (mobile projects only — lg:hidden)
// RenderSheet "success" branch is post-submit confirmation and would require
// faking a mutation response; deferred to operator (see commit-msg footer).

const MODEL_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";

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
  await page.goto(`/catalog/${MODEL_ID}`);
  await waitForReady(page);
}

async function setupCatalog(page: Page) {
  await stubAdminAuth(page);
  await stubSotList(page);
  await page.goto("/catalog");
  await waitForReady(page);
}

function skipOnDesktop(testInfo: { project: { name: string } }) {
  test.skip(
    testInfo.project.name.startsWith("desktop-"),
    "Mobile-only surface — desktop viewports render an inline sidebar/inline selects, no Sheet trigger.",
  );
}

test.describe("Remaining sheets — open-state baselines (E5.12d)", () => {
  test("RenderSheet (form) open", async ({ page }) => {
    await setupDetail(page);
    // Open ModelHero kebab → "Wygeneruj ponownie" (catalog.actions.rerender).
    await page.getByRole("button", { name: /^Akcje modelu$/i }).click();
    await page.getByRole("menuitem", { name: /^Wygeneruj ponownie$/i }).click();
    const sheet = page.locator("[data-slot='sheet-content']");
    await sheet.waitFor({ state: "visible" });
    await page.waitForTimeout(50);
    await expect(sheet).toHaveScreenshot("render-sheet-form-open.png");
  });

  test("AddPrintSheet open", async ({ page }) => {
    await setupDetail(page);
    // Navigate to Prints tab. catalog.tabs.prints = "Moje wydruki".
    await page.getByRole("tab", { name: /^Moje wydruki/i }).click();
    // catalog.actions.addPrint = "+ Dodaj wydruk".
    await page.getByRole("button", { name: /^\+\s*Dodaj wydruk$/i }).click();
    const sheet = page.locator("[data-slot='sheet-content']");
    await sheet.waitFor({ state: "visible" });
    await page.waitForTimeout(50);
    await expect(sheet).toHaveScreenshot("add-print-sheet-open.png");
  });

  test("AddNoteSheet open", async ({ page }) => {
    await setupDetail(page);
    // catalog.tabs.opsNotes = "Notatki techniczne".
    await page.getByRole("tab", { name: /^Notatki techniczne/i }).click();
    // catalog.actions.addNote = "+ Dodaj notatkę".
    await page.getByRole("button", { name: /^\+\s*Dodaj notatkę$/i }).click();
    const sheet = page.locator("[data-slot='sheet-content']");
    await sheet.waitFor({ state: "visible" });
    await page.waitForTimeout(50);
    await expect(sheet).toHaveScreenshot("add-note-sheet-open.png");
  });

  test("FilterRibbon mobile-filters Sheet open", async ({ page }, testInfo) => {
    skipOnDesktop(testInfo);
    await setupCatalog(page);
    // catalog.filters.openFilters = "Filtry" — the SheetTrigger button label.
    // Visible only when md:hidden does NOT hide it (i.e. viewport <768px).
    await page.getByRole("button", { name: /^Filtry$/i }).click();
    const sheet = page.locator("[data-slot='sheet-content']");
    await sheet.waitFor({ state: "visible" });
    await page.waitForTimeout(50);
    await expect(sheet).toHaveScreenshot("filter-ribbon-mobile-filters-sheet-open.png");
  });

  test("CatalogList mobile-categories Sheet open", async ({ page }, testInfo) => {
    skipOnDesktop(testInfo);
    await setupCatalog(page);
    // catalog.filters.openCategories = "Kategorie" — the SheetTrigger button.
    // Visible only when lg:hidden does NOT hide it (viewport <1024px).
    await page.getByRole("button", { name: /^Kategorie$/i }).click();
    const sheet = page.locator("[data-slot='sheet-content']");
    await sheet.waitFor({ state: "visible" });
    await page.waitForTimeout(50);
    await expect(sheet).toHaveScreenshot("catalog-list-mobile-categories-sheet-open.png");
  });
});
