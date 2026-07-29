import type { Page } from "@playwright/test";

import { expect, test } from "./_test";
import { waitForReady } from "./helpers";

// Story 52.2 — the admin browse-category screen (/admin/categories).
//
// Every state is driven by MOCKED reads so the four projects
// (desktop-light/dark, mobile-light/dark) are pixel-stable. No payload carries a
// rendered timestamp except the deliberately-frozen audit row used by the
// replace-set editor, so screenshots are deterministic.
//
// Per the Epic 45 retro action ("every UI story that adds a rendered state owes a
// pre-screenshot toBeVisible() assertion for that specific state"), each test
// asserts the concrete rendered content immediately before toHaveScreenshot — so a
// silently-degraded render fails the assertion loudly rather than rubber-stamping
// a pixel diff. The visual harness forces pl-PL (playwright.config.ts), so text
// matchers below are Polish; structure matchers use locale-independent testids.
//
// NOTE (loading state): the skeleton (`data-testid="categories-skeleton"`) is
// transient and aria-hidden; capturing it deterministically requires holding the
// read open, which also stalls the harness's networkidle wait. Consistent with
// admin-tag-groups / admin-queues / admin-users, it is NOT baselined; populated,
// empty and error are the load-bearing states.

// The eight starter categories from `app/core/db/seed.py`, rendered 1:1 in the
// ratified mockup (`mockups/key-admin-curation.html` frame 1) — including the
// zero-model "Części zamienne" row and the criterion line each one carries.
const CATEGORIES = [
  {
    id: "c1",
    slug: "storage-organization",
    name_en: "Storage & organization",
    name_pl: "Przechowywanie i organizacja",
    description_en: null,
    description_pl: null,
    position: 0,
    parent_id: null,
    model_count: 34,
    inclusion_criterion:
      "Model służy przede wszystkim do przechowywania, sortowania lub porządkowania innych przedmiotów.",
  },
  {
    id: "c2",
    slug: "home-decor",
    name_en: "Home decor",
    name_pl: "Dekoracje i wystrój",
    description_en: null,
    description_pl: null,
    position: 1,
    parent_id: null,
    model_count: 21,
    inclusion_criterion:
      "Model wybiera się głównie ze względu na wygląd w przestrzeni mieszkalnej, a nie pełnioną funkcję.",
  },
  {
    id: "c3",
    slug: "holders-mounts",
    name_en: "Holders & mounts",
    name_pl: "Uchwyty i mocowania",
    description_en: null,
    description_pl: null,
    position: 2,
    parent_id: null,
    model_count: 18,
    inclusion_criterion:
      "Model istnieje po to, by trzymać jeden konkretny przedmiot w ustalonej pozycji lub przymocować coś do powierzchni.",
  },
  {
    id: "c4",
    slug: "electronics-cables",
    name_en: "Electronics & cables",
    name_pl: "Elektronika i kable",
    description_en: null,
    description_pl: null,
    position: 3,
    parent_id: null,
    model_count: 11,
    inclusion_criterion: "Model mieści, prowadzi, chroni lub mocuje elektronikę, okablowanie albo złącza.",
  },
  {
    id: "c5",
    slug: "replacement-parts",
    name_en: "Replacement parts",
    name_pl: "Części zamienne",
    description_en: null,
    description_pl: null,
    position: 4,
    parent_id: null,
    model_count: 0,
    // Deliberately null: a category with no criterion must render NOTHING on
    // that line — no placeholder, no dash.
    inclusion_criterion: null,
  },
];

const QUEUE = {
  items: [
    { id: "m1", slug: "spiral-vase", name_en: "Spiral vase", name_pl: "Wazon spiralny" },
    { id: "m2", slug: "cable-clip", name_en: "Cable clip", name_pl: "Klips do kabli" },
  ],
  total: 2,
  offset: 0,
  limit: 48,
};

const MODEL_DETAIL = {
  id: "m1",
  slug: "spiral-vase",
  name_en: "Spiral vase",
  name_pl: "Wazon spiralny",
  tags: [],
  // FOUR categories, so the editor opens straight into the advisory state that
  // FR26-CAT-3 makes load-bearing: a warning, with the save control still live.
  categories: [
    { id: "c1", slug: "storage-organization", name_en: "Storage & organization", name_pl: "Przechowywanie i organizacja", position: 0, parent_id: null },
    { id: "c2", slug: "home-decor", name_en: "Home decor", name_pl: "Dekoracje i wystrój", position: 1, parent_id: null },
    { id: "c3", slug: "holders-mounts", name_en: "Holders & mounts", name_pl: "Uchwyty i mocowania", position: 2, parent_id: null },
    { id: "c4", slug: "electronics-cables", name_en: "Electronics & cables", name_pl: "Elektronika i kable", position: 3, parent_id: null },
  ],
};

// A frozen category-replace audit row, so the "last audited writer" note renders
// a constant string. `actor_user_id` matches the harness's default admin, which
// is what makes the "you" branch deterministic.
const AUDIT = {
  items: [
    {
      id: "a1",
      actor_user_id: "11111111-1111-1111-1111-111111111111",
      action: "model.update",
      entity_type: "model",
      entity_id: "m1",
      before_json: { category_ids: ["c1"] },
      after_json: { category_ids: ["c1", "c2", "c3", "c4"] },
      at: "2026-07-29T21:04:00",
    },
  ],
};

async function stubAdminCategories(
  page: Page,
  opts: {
    categories?: unknown;
    queue?: unknown;
    error?: boolean;
    /** Status for DELETE, so the 409 conflict state can be baselined. */
    deleteStatus?: number;
    deleteDetail?: string;
  } = {},
) {
  await page.route("**/api/admin/categories**", (route) => {
    if (route.request().method() === "DELETE") {
      return route.fulfill({
        status: opts.deleteStatus ?? 204,
        contentType: "application/json",
        body: JSON.stringify({ detail: opts.deleteDetail ?? "" }),
      });
    }
    if (opts.error) {
      return route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "boom" }),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(opts.categories ?? CATEGORIES),
    });
  });
  await page.route("**/api/admin/audit-log**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(AUDIT),
    }),
  );
  // Single handler for both /api/models and /api/models/<id> — the visual config
  // folds overlapping model routes into one handler so registration order cannot
  // silently shadow the detail read.
  await page.route("**/api/models**", (route) => {
    const url = route.request().url();
    const isDetail = /\/api\/models\/[^/?]+/.test(url);
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(isDetail ? MODEL_DETAIL : (opts.queue ?? QUEUE)),
    });
  });
}

async function gotoPopulated(page: Page) {
  await stubAdminCategories(page);
  await page.goto("/admin/categories");
  await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
  await waitForReady(page);
}

test.describe("/admin/categories baselines", () => {
  test("populated — rows in order with position, slug, criterion, count, and the curation queue", async ({
    page,
  }) => {
    await gotoPopulated(page);

    await expect(page.getByTestId("browse-category-storage-organization")).toBeVisible();
    await expect(page.getByTestId("browse-category-replacement-parts")).toBeVisible();
    // The criterion renders IN THE LIST — the admission test must be comparable
    // across two rows without opening a dialog.
    await expect(
      page.getByText(
        "Model mieści, prowadzi, chroni lub mocuje elektronikę, okablowanie albo złącza.",
      ),
    ).toBeVisible();
    await expect(page.getByText("0 modeli", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Nowa kategoria" })).toBeVisible();
    // The curation queue: a valid state, presented as work, not as a defect.
    await expect(page.getByTestId("curation-queue")).toBeVisible();
    await expect(page.getByTestId("curation-model-spiral-vase")).toBeVisible();
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("admin-categories-populated.png", { fullPage: true });
  });

  test("empty — no categories and an empty curation queue", async ({ page }) => {
    await stubAdminCategories(page, {
      categories: [],
      queue: { items: [], total: 0, offset: 0, limit: 48 },
    });
    await page.goto("/admin/categories");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);

    await expect(page.getByText("Brak kategorii przeglądania.")).toBeVisible();
    // Not an error, not a celebration.
    await expect(page.getByText("Nic nie wymaga uwagi.")).toBeVisible();
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("admin-categories-empty.png", { fullPage: true });
  });

  test("error — fails-closed error banner + retry", async ({ page }) => {
    await stubAdminCategories(page, { error: true });
    await page.goto("/admin/categories");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);

    await expect(page.getByText("Nie udało się wczytać kategorii przeglądania")).toBeVisible();
    await expect(page.getByRole("button", { name: "Spróbuj ponownie" })).toBeVisible();
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("admin-categories-error.png", { fullPage: true });
  });
});

test.describe("/admin/categories dialogs", () => {
  test("replace-set editor — advisory over three, save still enabled, last writer named", async ({
    page,
  }) => {
    await gotoPopulated(page);
    const assign = page.getByTestId("curation-model-spiral-vase").getByRole("button");
    // The curation queue is the LAST section on the page, so on Pixel 5 it lands
    // flush against the bottom viewport edge and Playwright's stability check
    // flaps while it re-scrolls. Scrolling to the document end first settles the
    // row well inside the viewport. Deliberately NOT `click({ force: true })` —
    // that would skip the actionability checks and could mask a real overlap.
    // Plain pointer click. This only became reliable on the mobile projects once
    // `AdminTabs` stopped overflowing the document: while the tab row forced
    // mobile Chrome to expand the LAYOUT viewport (measured 675x1249) away from
    // the visual one (393x727), Playwright's pointer coordinates landed on a
    // category row instead of this button. Deliberately NOT `force: true` — the
    // actionability check is what caught that divergence in the first place.
    await assign.scrollIntoViewIfNeeded();
    await assign.click();

    await expect(page.getByRole("heading", { name: "Kategorie modelu" })).toBeVisible();
    // The three load-bearing honesty properties of this surface, asserted before
    // the pixels: the advisory is visible, the save control is STILL enabled
    // (FR26-CAT-3 is a warning, never a block), and it reads "Zastąp kategorie"
    // rather than "Zapisz zmiany" — the verb states what the API does.
    await expect(page.getByTestId("category-advisory")).toBeVisible();
    await expect(page.getByText("Ostatnia zmiana: Ty, 2026-07-29 21:04")).toBeVisible();
    const save = page.getByRole("button", { name: "Zastąp kategorie" });
    await expect(save).toBeVisible();
    await expect(save).toBeEnabled();
    // Reaching the queue button required scrolling, and this is a `fullPage`
    // capture, so the BACKGROUND page would otherwise be photographed at a
    // scroll offset that varies run to run (~4k pixels of churn on mobile).
    // The dialog is fixed-position, so resetting the underlying scroll makes the
    // shot deterministic without changing what is under test.
    await page.evaluate(() => window.scrollTo(0, 0));
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("admin-categories-replace-set-editor.png", {
      fullPage: true,
    });
  });

  test("delete — 409 in-use names the count and offers the explicit detach", async ({ page }) => {
    await stubAdminCategories(page, { deleteStatus: 409, deleteDetail: "category_in_use" });
    await page.goto("/admin/categories");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);

    await page.getByRole("button", { name: "Akcje dla kategorii Przechowywanie i organizacja" }).click();
    await page.getByRole("menuitem", { name: "Usuń" }).click();
    await page.getByRole("button", { name: "Usuń", exact: true }).click();

    await expect(page.getByText("Nie można usunąć — przypisane są 34 modele")).toBeVisible();
    // Never a silent cascade: the detach is a second, explicit decision.
    await expect(page.getByRole("button", { name: "Odepnij i usuń" })).toBeVisible();
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("admin-categories-delete-conflict.png", {
      fullPage: true,
    });
  });

  test("create dialog — slug, both names, and the inclusion criterion", async ({ page }) => {
    await gotoPopulated(page);
    await page.getByRole("button", { name: "Nowa kategoria" }).click();

    await expect(page.getByRole("heading", { name: "Nowa kategoria" })).toBeVisible();
    await expect(page.getByRole("textbox", { name: "Identyfikator" })).toBeVisible();
    await expect(page.getByRole("textbox", { name: "Kryterium przynależności" })).toBeVisible();
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("admin-categories-dialog-create.png", { fullPage: true });
  });
});
