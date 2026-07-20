import { expect, test } from "./_test";

import { stubSotList } from "./api-stubs";
import { waitForReady } from "./helpers";

test("catalog empty state offers a clear-filters action when filters active", async ({ page }) => {
  await stubSotList(page);
  // Override /api/models to return an empty list for a no-match search,
  // exercising the EmptyState action branch through an E44-supported filter.
  await page.route(
    "**/api/models?**q=no-match**",
    (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ total: 0, offset: 0, limit: 48, items: [] }),
      }),
  );
  await page.goto("/catalog?q=no-match");
  await waitForReady(page);
  await expect(page).toHaveScreenshot("catalog-empty-with-action.png", { fullPage: true });
});

test("catalog empty state hides clear-filters button without active filters", async ({ page }) => {
  await stubSotList(page);
  // Override only the model list so all E44 catalog dependencies still load
  // and the no-filter branch renders a genuine empty catalog state.
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
