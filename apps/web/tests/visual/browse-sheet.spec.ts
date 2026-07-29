import { expect, test } from "./_test";
import { stubSotList } from "./api-stubs";
import { waitForReady } from "./helpers";

// Story 51.3 — the mobile Browse sheet. It renders only below `lg`
// (`lg:hidden` on the trigger, inside `BrowseSheet`), mirroring
// `browse-rail.spec.ts`'s desktop-only skip in the opposite direction. The
// harness forces pl-PL, so every expectation below is the Polish browse
// vocabulary ("Przeglądaj", "Przeglądaj kategorie", "Cały katalog") already
// ratified for the desktop rail (EXPERIENCE.md:202) and reused verbatim here.
function skipOnDesktop(testInfo: { project: { name: string } }) {
  test.skip(
    !testInfo.project.name.startsWith("mobile-"),
    "BrowseSheet's trigger is lg:hidden; the desktop surface is BrowseRail (Story 51.1).",
  );
}

const TRIGGER = { name: "Przeglądaj" };
const DIALOG = { name: "Przeglądaj kategorie" };

test.describe("BrowseSheet — mobile Browse surface", () => {
  test("closed: the Browse trigger is visible, distinct from the Filtry trigger", async ({
    page,
  }, testInfo) => {
    skipOnDesktop(testInfo);
    await stubSotList(page);
    await page.goto("/catalog");
    await waitForReady(page);

    const trigger = page.getByRole("button", TRIGGER);
    await expect(trigger).toBeVisible();
    // Story 52.1 — the "Tagi" trigger is gone; the toolbar now carries exactly
    // one refinement trigger beside Browse (AC-1).
    await expect(page.getByRole("button", { name: "Tagi", exact: true })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Filtry", exact: true })).toBeVisible();
    await expect(page.getByRole("dialog", DIALOG)).not.toBeVisible();

    await expect(page).toHaveScreenshot("browse-sheet-closed.png", { fullPage: true });
  });

  test("open/default: All catalog current, categories with counts, same vocabulary as the rail", async ({
    page,
  }, testInfo) => {
    skipOnDesktop(testInfo);
    await stubSotList(page);
    await page.goto("/catalog");
    await waitForReady(page);

    await page.getByRole("button", TRIGGER).click();

    const dialog = page.getByRole("dialog", DIALOG);
    await expect(dialog).toBeVisible();
    const allCatalog = dialog.getByRole("link", { name: "Cały katalog" });
    await expect(allCatalog).toBeVisible();
    await expect(allCatalog).toHaveAttribute("aria-current", "page");
    await expect(dialog.getByRole("link", { name: /Organizery, 12 modeli/ })).toBeVisible();
    await expect(
      dialog.getByRole("link", { name: /Uchwyty i mocowania, 7 modeli/ }),
    ).toBeVisible();

    await expect(page).toHaveScreenshot("browse-sheet-open-default.png", { fullPage: true });
  });

  test("open/active-category: the scoped row carries the same active treatment as the rail", async ({
    page,
  }, testInfo) => {
    skipOnDesktop(testInfo);
    await stubSotList(page);
    await page.goto("/categories/uchwyty");
    await waitForReady(page);

    await page.getByRole("button", TRIGGER).click();

    const dialog = page.getByRole("dialog", DIALOG);
    const active = dialog.getByRole("link", { name: /Uchwyty i mocowania, 7 modeli/ });
    await expect(active).toBeVisible();
    await expect(active).toHaveAttribute("aria-current", "page");
    await expect(dialog.getByRole("link", { name: "Cały katalog" })).not.toHaveAttribute(
      "aria-current",
      "page",
    );

    await expect(page).toHaveScreenshot("browse-sheet-open-active-category.png", {
      fullPage: true,
    });
  });
});
