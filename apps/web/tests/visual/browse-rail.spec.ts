import { expect, test } from "./_test";
import { stubSotList } from "./api-stubs";
import { waitForReady } from "./helpers";

// Story 51.1 — desktop browse navigation. The harness forces pl-PL, so every
// expectation below is against the Polish rail vocabulary ("Cały katalog",
// "Przeglądaj kategorie") ratified in EXPERIENCE.md:202.
//
// Per the Epic 45/46 TEST-AUTHORING action items, each test asserts the
// concrete rendered state with toBeVisible() *immediately before*
// toHaveScreenshot, so a silently-degraded render fails the assertion rather
// than only producing a pixel diff.

// The rail carries `hidden ... lg:flex` — real desktop-only chrome. The mobile
// Browse surface is Story 51.3 and does not exist yet, so below `lg` there is
// deliberately nothing to capture. Same pattern as facet-filtering.spec.ts.
function skipOnMobile(testInfo: { project: { name: string } }) {
  test.skip(
    testInfo.project.name.startsWith("mobile-"),
    "BrowseRail renders desktop-only (hidden lg:flex); the mobile Browse surface is Story 51.3.",
  );
}

const RAIL = { name: "Przeglądaj kategorie" };

test.describe("BrowseRail — desktop browse navigation", () => {
  test("default state: All catalog current, categories with counts", async ({ page }, testInfo) => {
    skipOnMobile(testInfo);
    await stubSotList(page);
    await page.goto("/catalog");
    await waitForReady(page);

    const rail = page.getByRole("navigation", RAIL);
    await expect(rail).toBeVisible();

    const allCatalog = rail.getByRole("link", { name: "Cały katalog" });
    await expect(allCatalog).toBeVisible();
    await expect(allCatalog).toHaveAttribute("aria-current", "page");
    await expect(rail.getByRole("link", { name: /Organizery, 12 modeli/ })).toBeVisible();
    await expect(rail.getByRole("link", { name: /Uchwyty i mocowania, 7 modeli/ })).toBeVisible();

    await expect(page).toHaveScreenshot("browse-rail-default.png", { fullPage: true });
  });

  test("active state: the scoped category row carries the location treatment", async ({
    page,
  }, testInfo) => {
    skipOnMobile(testInfo);
    await stubSotList(page);
    await page.goto("/categories/uchwyty");
    await waitForReady(page);

    const rail = page.getByRole("navigation", RAIL);
    const active = rail.getByRole("link", { name: /Uchwyty i mocowania, 7 modeli/ });
    await expect(active).toBeVisible();
    await expect(active).toHaveAttribute("aria-current", "page");
    await expect(rail.getByRole("link", { name: "Cały katalog" })).not.toHaveAttribute(
      "aria-current",
      "page",
    );

    await expect(page).toHaveScreenshot("browse-rail-active.png", { fullPage: true });
  });

  test("empty category: dimmed label, still focusable and navigable", async ({
    page,
  }, testInfo) => {
    skipOnMobile(testInfo);
    await stubSotList(page);
    await page.goto("/catalog");
    await waitForReady(page);

    const rail = page.getByRole("navigation", RAIL);
    const empty = rail.getByRole("link", { name: /Dekoracje i wystrój, 0 modeli/ });
    await expect(empty).toBeVisible();
    await expect(empty).toBeEnabled();
    // Focusable: keyboard users must still be able to reach an empty category.
    await empty.focus();
    await expect(empty).toBeFocused();

    await expect(page).toHaveScreenshot("browse-rail-empty-category-focused.png", {
      fullPage: true,
    });
  });

  test("cold load: skeleton rows, and the grid is NOT blanked", async ({ page }, testInfo) => {
    skipOnMobile(testInfo);
    // `never` leaves /api/categories hanging, so the rail stays pending.
    await stubSotList(page, { categories: "never" });
    await page.goto("/catalog");

    // `waitForReady`'s networkidle would never settle with a hanging request,
    // so wait on the concrete state and disable animations by hand instead.
    const rail = page.getByRole("navigation", RAIL);
    await expect(rail.getByRole("link", { name: "Cały katalog" })).toBeVisible();
    await expect(page.getByTestId("browse-rail-skeleton").first()).toBeVisible();
    // The catalogue itself must be fully painted while the rail is still pending.
    await expect(page.getByRole("link", { name: /Dragon|Smok/ }).first()).toBeVisible();
    await page.addStyleTag({
      content:
        "*, *::before, *::after { animation-duration: 0s !important; transition-duration: 0s !important; }",
    });

    await expect(page).toHaveScreenshot("browse-rail-cold-load.png", { fullPage: true });
  });

  test("error: degrades to All catalog + inline retry, grid stays usable", async ({
    page,
  }, testInfo) => {
    skipOnMobile(testInfo);
    await stubSotList(page, { categories: "error" });
    await page.goto("/catalog");
    await waitForReady(page);

    const rail = page.getByRole("navigation", RAIL);
    await expect(rail.getByRole("link", { name: "Cały katalog" })).toBeVisible();
    await expect(rail.getByRole("button", { name: "Spróbuj ponownie" })).toBeVisible();
    // The navigation aid failed; the catalogue did not.
    await expect(page.getByRole("link", { name: /Dragon|Smok/ }).first()).toBeVisible();

    await expect(page).toHaveScreenshot("browse-rail-error.png", { fullPage: true });
  });
});

// The facet surface is relocated, not removed (FR26-BROWSE-1 verifiable (b)):
// one interaction from the toolbar reaches the shipped grouped-tag surface on
// EVERY viewport, so this test is deliberately not desktop-gated.
test("grouped facets stay one interaction away on every viewport", async ({ page }) => {
  await stubSotList(page);
  await page.goto("/catalog");
  await waitForReady(page);

  // Story 52.1 — the one interaction is now the consolidated "Filtry" trigger;
  // the "Tagi" trigger it replaced is deleted. The guarantee is unchanged: the
  // shipped grouped-tag surface is one click from the toolbar on every viewport.
  await page.getByRole("button", { name: "Filtry", exact: true }).click();

  const untagged = page.getByRole("checkbox", { name: "Modele bez tagów" });
  await expect(untagged).toBeVisible();
  await expect(page.getByRole("button", { name: /Motyw/ })).toBeVisible();

  await expect(page).toHaveScreenshot("browse-rail-relocated-facets-open.png", { fullPage: true });
});
