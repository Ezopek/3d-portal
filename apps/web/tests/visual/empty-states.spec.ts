import { expect, test } from "@playwright/test";

import { stubSotList } from "./api-stubs";
import { waitForReady } from "./helpers";

test("catalog empty state offers a clear-filters action when filters active", async ({ page }) => {
  await stubSotList(page);
  // Override /api/models to return an empty list when filtering by a
  // non-existent category UUID, exercising the EmptyState's action branch.
  await page.route(
    "**/api/models?**category_ids=00000000-0000-0000-0000-000000000000**",
    (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ total: 0, offset: 0, limit: 48, items: [] }),
      }),
  );
  await page.goto("/catalog?category_id=00000000-0000-0000-0000-000000000000");
  await waitForReady(page);
  await expect(page).toHaveScreenshot("catalog-empty-with-action.png", { fullPage: true });
});

test("catalog empty state hides clear-filters button without active filters", async ({ page }) => {
  // Stub the SoT endpoints with empty results so the no-filter branch renders
  // an EmptyState without a clear-filters action.
  await page.route("**/api/categories", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ roots: [] }),
    }),
  );
  await page.route("**/api/tags*", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    }),
  );
  await page.route("**/api/models*", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ total: 0, offset: 0, limit: 48, items: [] }),
    }),
  );
  await page.goto("/catalog");
  await waitForReady(page);
  // The clear-filters button should NOT exist when no filter is active.
  await expect(page.getByRole("button", { name: /clear filters|wyczyść/i })).toHaveCount(0);
});
