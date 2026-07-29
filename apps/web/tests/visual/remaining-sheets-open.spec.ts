import { expect, test } from "./_test";

import { stubSotDetail } from "./api-stubs";
import { loginAsAdmin, waitForReady } from "./helpers";
import type { Page, Route } from "@playwright/test";

// 5.12d covers the remaining Sheet open-state surfaces:
//   - RenderSheet (form branch, from ModelHero admin kebab "Re-render")
//   - AddPrintSheet (from PrintsTab "+ Dodaj wydruk")
//   - AddNoteSheet (from OperationalNotesTab "+ Dodaj notatkę")
// RenderSheet "success" branch is post-submit confirmation and would require
// faking a mutation response; deferred to operator (see commit-msg footer).
//
// Story 52.1 retired the two catalog-toolbar entries this file used to carry
// (the `md:hidden` "Filtry" select sheet and the all-viewport "Tagi" facet
// sheet). Both controls are gone from the DOM; their single consolidated
// successor has its own dedicated spec, `filters-panel.spec.ts`, which covers
// the right-panel AND bottom-sheet presentations. Nothing here clicks a
// deleted control.

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

});
