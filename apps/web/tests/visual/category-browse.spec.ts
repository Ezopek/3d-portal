import { expect, test } from "./_test";
import { stubSotList } from "./api-stubs";
import { waitForReady } from "./helpers";

// Story 51.2 — canonical `/categories/$slug` browse route + scope chip.
// The harness forces pl-PL, so chip/action copy below uses the ratified Polish
// UX vocabulary from the Initiative 26 design spine.
//
// Per the Epic 45/46 TEST-AUTHORING action items, each screenshot has a concrete
// `toBeVisible()` assertion immediately before capture, so a blank or redirected
// page cannot silently create a misleading baseline.

async function stubEmptyScopedModels(page: Parameters<typeof stubSotList>[0]) {
  await page.route("**/api/models*", (route) => {
    const url = new URL(route.request().url());
    if (url.searchParams.get("category") !== null) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ total: 0, offset: 0, limit: 48, items: [] }),
      });
    }
    return route.fallback();
  });
}

test.describe("Category browse route — scope chip", () => {
  test("scoped populated category shows the active chip and active rail link", async ({
    page,
  }, testInfo) => {
    await stubSotList(page);
    await page.goto("/categories/uchwyty?q=dragon");
    await waitForReady(page);

    const chip = page.getByRole("group", { name: "Aktywna kategoria: Uchwyty i mocowania" });
    await expect(chip).toBeVisible();
    await expect(chip.getByRole("link", { name: "Szukaj w całym katalogu" })).toBeVisible();

    if (!testInfo.project.name.startsWith("mobile-")) {
      const rail = page.getByRole("navigation", { name: "Przeglądaj kategorie" });
      await expect(rail.getByRole("link", { name: /Uchwyty i mocowania, 7 modeli/ })).toHaveAttribute(
        "aria-current",
        "page",
      );
    }

    await expect(page).toHaveScreenshot("category-browse-scoped-populated.png", { fullPage: true });
  });

  test("unknown/empty category keeps the raw slug escape visible", async ({ page }) => {
    await stubSotList(page);
    await stubEmptyScopedModels(page);
    await page.goto("/categories/nieznana-kategoria");
    await waitForReady(page);

    const chip = page.getByRole("group", { name: "Aktywna kategoria: nieznana-kategoria" });
    await expect(chip).toBeVisible();
    await expect(chip.getByRole("link", { name: "Wyczyść kategorię" })).toBeVisible();
    await expect(page.getByText("W tej kategorii nie ma jeszcze nic.")).toBeVisible();

    await expect(page).toHaveScreenshot("category-browse-empty-unknown.png", { fullPage: true });
  });
});
