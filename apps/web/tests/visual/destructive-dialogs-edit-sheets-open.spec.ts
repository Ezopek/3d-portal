import { expect, test } from "./_test";

import { stubSotDetail } from "./api-stubs";
import { loginAsAdmin, waitForReady } from "./helpers";
import type { Page, Route } from "@playwright/test";

// 5.12b covers four destructive / edit surfaces on /catalog/:id (admin):
//   - ConfirmDialog (PrintsTab "delete print" → primitive baseline; ConfirmDialog
//     has 4 callsites but covering one variant validates the Dialog open state)
//   - DeleteModelDialog
//   - EditTagsSheet
//   - EditDescriptionSheet
// All four require admin auth — loginAsAdmin seeds a JWT with role=admin so
// useAuth().isAdmin returns true and ModelHero renders the kebab + popover
// chips. The admin /api/auth/me stub keeps AuthGate happy.

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

async function setup(page: Page) {
  await loginAsAdmin(page);
  await stubAdminAuth(page);
  await stubSotDetail(page);
  await page.goto(`/catalog/${MODEL_ID}`);
  await waitForReady(page);
}

// Story 45.3 visual-coverage repair — EditTagsSheet mounts unconditionally
// whenever isAdmin (ModelHero.tsx), so useTags() fires on page load, not on
// sheet-open click. stubSotDetail's own /api/tag-groups fixture already
// defines two known groups (tg-theme "Motyw", tg-material "Materiał"); this
// test-local override for /api/tags returns 3 unselected candidates spanning
// both groups plus one groupless orphan, so the grouped picker actually
// renders section headers + candidate rows in the baseline instead of an
// empty list. Kept local to this test (not folded into shared stubSotDetail)
// so the other three specs in this file, which never open EditTagsSheet,
// keep their existing baselines untouched.
async function stubTagCandidates(page: Page) {
  await page.route("**/api/tags*", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "t1",
          slug: "dragon",
          name_en: "Dragon",
          name_pl: "Smok",
          group_id: "tg-theme",
          group_position: 0,
        },
        {
          id: "t2",
          slug: "articulated",
          name_en: "Articulated",
          name_pl: null,
          group_id: null,
          group_position: 0,
        },
        {
          id: "t3",
          slug: "fire",
          name_en: "Fire",
          name_pl: "Ogień",
          group_id: "tg-theme",
          group_position: 1,
        },
        {
          id: "t4",
          slug: "resin",
          name_en: "Resin",
          name_pl: "Żywica",
          group_id: "tg-material",
          group_position: 0,
        },
        {
          id: "t5",
          slug: "orphan-decor",
          name_en: "Orphan Decor",
          name_pl: "Sierota",
          group_id: null,
          group_position: 0,
        },
      ]),
    }),
  );
}

async function openAdminKebab(page: Page) {
  // Polish aria-label from catalog.actions.modelActions = "Akcje modelu".
  const kebab = page.getByRole("button", { name: /^Akcje modelu$/i });
  await kebab.waitFor({ state: "visible" });
  await kebab.click();
  const menu = page.locator("[data-slot='dropdown-menu-content']");
  await menu.waitFor({ state: "visible" });
}

test.describe("Destructive dialogs + EditSheets — open-state baselines (E5.12b)", () => {
  test("DeleteModelDialog open", async ({ page }) => {
    await setup(page);
    await openAdminKebab(page);
    // catalog.actions.delete = "Usuń"; matched within the dropdown menu item.
    await page.getByRole("menuitem", { name: /^Usuń$/i }).click();
    const dialog = page.locator("[data-slot='dialog-content']");
    await dialog.waitFor({ state: "visible" });
    await page.waitForTimeout(50);
    await expect(dialog).toHaveScreenshot("delete-model-dialog-open.png");
  });

  test("EditDescriptionSheet open", async ({ page }) => {
    await setup(page);
    await openAdminKebab(page);
    // catalog.actions.editDescription = "Edytuj opis".
    await page.getByRole("menuitem", { name: /^Edytuj opis$/i }).click();
    const sheet = page.locator("[data-slot='sheet-content']");
    await sheet.waitFor({ state: "visible" });
    await page.waitForTimeout(50);
    await expect(sheet).toHaveScreenshot("edit-description-sheet-open.png");
  });

  test("EditTagsSheet open", async ({ page }) => {
    await stubTagCandidates(page);
    await setup(page);
    // EditTagsSheet is reached via the small Pencil button beside tag chips,
    // not the kebab. catalog.actions.editTags = "Edytuj tagi".
    await page.getByRole("button", { name: /^Edytuj tagi$/i }).click();
    const sheet = page.locator("[data-slot='sheet-content']");
    await sheet.waitFor({ state: "visible" });
    // Story 45.3 visual proof: assert the grouped candidate picker actually
    // rendered — two known-group headers (pl-PL labels from stubSotDetail's
    // /api/tag-groups fixture) plus the trailing "Ungrouped" section, each
    // with its representative candidate row, before capturing the baseline.
    await expect(sheet.getByText("Motyw", { exact: true })).toBeVisible();
    await expect(sheet.getByText("Materiał", { exact: true })).toBeVisible();
    await expect(sheet.getByText("Bez grupy", { exact: true })).toBeVisible();
    await expect(sheet.getByRole("button", { name: "+ fire" })).toBeVisible();
    await expect(sheet.getByRole("button", { name: "+ resin" })).toBeVisible();
    await expect(
      sheet.getByRole("button", { name: "+ orphan-decor" }),
    ).toBeVisible();
    await page.waitForTimeout(50);
    await expect(sheet).toHaveScreenshot("edit-tags-sheet-open.png");
  });

  test("ConfirmDialog (delete print) open", async ({ page }) => {
    await setup(page);
    // Navigate to the Prints tab; tab label uses catalog.tabs.prints = "Moje wydruki"
    // followed by a count suffix " (1)".
    await page.getByRole("tab", { name: /^Moje wydruki/i }).click();
    // The PrintsTab in the stubbed detail has exactly 1 print → 1 delete button.
    // catalog.actions.deletePrint = "Usuń wydruk".
    await page.getByRole("button", { name: /^Usuń wydruk$/i }).click();
    const dialog = page.locator("[data-slot='dialog-content']");
    await dialog.waitFor({ state: "visible" });
    await page.waitForTimeout(50);
    await expect(dialog).toHaveScreenshot("confirm-dialog-delete-print-open.png");
  });
});
