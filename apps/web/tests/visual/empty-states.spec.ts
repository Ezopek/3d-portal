import { expect, test } from "@playwright/test";

import { stubCatalog } from "./api-stubs";
import { waitForReady } from "./helpers";

test("catalog empty state offers a clear-filters action when filters active", async ({ page }) => {
  await stubCatalog(page);
  // The stub returns only `decorations` models; filtering by `premium` produces
  // an empty result, exercising the EmptyState's action branch.
  await page.goto("/catalog?category=premium");
  await waitForReady(page);
  await expect(page).toHaveScreenshot("catalog-empty-with-action.png", { fullPage: true });
});

test("catalog empty state hides clear-filters button without active filters", async ({ page }) => {
  // No stub — useModels returns isError, but we test the no-filter path.
  // Faster path: stub catalog as empty.
  await page.route("**/api/catalog/models", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ total: 0, models: [] }),
    }),
  );
  await page.goto("/catalog");
  await waitForReady(page);
  // The clear-filters button should NOT exist when no filter is active.
  await expect(page.getByRole("button", { name: /clear filters|wyczyść/i })).toHaveCount(0);
});

test("share view error renders destructive-toned EmptyState with icon", async ({ page }) => {
  await page.route("**/api/share/bad-token", (route) =>
    route.fulfill({ status: 404, contentType: "application/json", body: '{"detail":"not found"}' }),
  );
  await page.goto("/share/bad-token");
  await waitForReady(page);
  await expect(page).toHaveScreenshot("share-error.png", { fullPage: true });
});
