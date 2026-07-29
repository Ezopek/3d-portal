import { expect, test } from "./_test";

import { stubSotDetail } from "./api-stubs";
import { waitForReady } from "./helpers";
import type { Page, Route } from "@playwright/test";

// Story 51.4 — model-detail category display (FR26-CAT-2, FR26-BROWSE-2).
// The harness forces pl-PL, so every text matcher below is Polish or
// locale-independent. `stubSotDetail` now emits a two-category default whose
// second entry carries `name_pl: null`, so the pl run exercises BOTH the
// name_pl path and the name_en fallback in one render.
const MODEL_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";

const CATEGORIES_LABEL = "Kategorie";
const NO_CATEGORIES_ADVISORY = "Bez kategorii — do uzupełnienia";

async function gotoDetail(
  page: Page,
  options: { categories?: [] } = {},
) {
  await stubSotDetail(page, options);
  await page.goto(`/catalog/${MODEL_ID}`);
  await waitForReady(page);
}

async function asMember(page: Page) {
  // The shared `_test.ts` fixture defaults `/api/auth/me` to admin; Playwright
  // matches handlers in reverse registration order, so this override wins.
  await page.route("**/api/auth/me", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "22222222-2222-2222-2222-222222222222",
        email: "member@localhost.localdomain",
        display_name: "Member",
        role: "member",
      }),
    }),
  );
}

test("model-detail categories match baseline for an admin viewer", async ({ page }) => {
  await gotoDetail(page);

  await expect(page.getByText(CATEGORIES_LABEL, { exact: true })).toBeVisible();
  const entries = page.getByTestId("model-category-link");
  await expect(entries).toHaveCount(2);
  await expect(entries.first()).toBeVisible();
  await expect(entries.last()).toBeVisible();
  // Wire order preserved, pl label first, en fallback second (D-8, D-9).
  await expect(entries.first()).toHaveText("Przechowywanie i organizacja");
  await expect(entries.last()).toHaveText("Holders & mounts");
  await expect(entries.first()).toHaveAttribute(
    "href",
    "/categories/storage-organization",
  );
  // An admin gets no extra affordance while the model HAS categories.
  await expect(page.getByText(NO_CATEGORIES_ADVISORY)).toHaveCount(0);

  await expect(page).toHaveScreenshot("catalog-detail-categories-admin.png", {
    fullPage: true,
  });
});

test("model-detail categories match baseline for a member viewer", async ({ page }) => {
  await asMember(page);
  await gotoDetail(page);

  await expect(page.getByText(CATEGORIES_LABEL, { exact: true })).toBeVisible();
  const entries = page.getByTestId("model-category-link");
  await expect(entries).toHaveCount(2);
  await expect(entries.first()).toBeVisible();
  await expect(entries.last()).toBeVisible();

  await expect(page).toHaveScreenshot("catalog-detail-categories-member.png", {
    fullPage: true,
  });
});

// FR26-CAT-2's "zero categories is valid" verifiable, admin half: exactly one
// muted advisory line, static text — never a link to the assignment surface,
// which does not exist until Story 52.2 (D-5, V-8). The member half renders
// nothing at all and is covered by the unit suite (AC-8), where "no heading,
// no dash, no placeholder" is assertable and a screenshot of an absence is not.
test("model-detail zero-category advisory matches baseline for an admin viewer", async ({
  page,
}) => {
  await gotoDetail(page, { categories: [] });

  const advisory = page.getByText(NO_CATEGORIES_ADVISORY, { exact: true });
  await expect(advisory).toBeVisible();
  await expect(page.getByTestId("model-category-link")).toHaveCount(0);
  await expect(page.getByText(CATEGORIES_LABEL, { exact: true })).toHaveCount(0);
  // Story 52.2 (AC-20) discharges 51.4's recorded §9 handoff. 51.4 shipped this
  // as static text ON PURPOSE, because `/admin/categories` did not exist yet and
  // a link to a 404 would have been worse than an honest advisory. That surface
  // now exists, so this becomes the "link to assign" the UX contract always
  // specified. The assertion is TIGHTENED, not relaxed: the advisory is now
  // pinned to a link with an exact href, and it is still never a button.
  await expect(
    page.getByRole("link", { name: NO_CATEGORIES_ADVISORY }),
  ).toHaveAttribute("href", "/admin/categories");
  await expect(page.getByTestId("model-categories-curation-link")).toBeVisible();
  await expect(
    page.getByRole("button", { name: NO_CATEGORIES_ADVISORY }),
  ).toHaveCount(0);

  await expect(page).toHaveScreenshot(
    "catalog-detail-categories-empty-admin.png",
    { fullPage: true },
  );
});
