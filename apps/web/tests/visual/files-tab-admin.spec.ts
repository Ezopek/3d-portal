import { expect, test } from "@playwright/test";

import { stubCatalogMultiStl } from "./api-stubs";
import { loginAsAdmin, waitForReady } from "./helpers";

// Admin FileList checkboxes are desktop-only in practice but visible on mobile
// in this test because there is no sticky-header conflict with the files tab.
test.describe("Model files tab — admin", () => {
  test("default state shows auto badge on first STL", async ({ page }) => {
    await loginAsAdmin(page);
    await stubCatalogMultiStl(page);
    await page.goto("/catalog/001");
    await waitForReady(page);

    // Click the "Model files" tab (pl: "Pliki modelu").
    await page.getByRole("tab", { name: /pliki modelu/i }).click();
    await waitForReady(page);

    // The first STL (alphabetically) gets the "auto" badge when no paths are saved.
    await expect(page.getByText("auto")).toBeVisible();

    // Apply button is present but disabled (no pending changes).
    const applyBtn = page.getByRole("button", { name: /zapisz i przerenderuj/i });
    await expect(applyBtn).toBeVisible();
    await expect(applyBtn).toBeDisabled();

    await expect(page).toHaveScreenshot("files-tab-admin-default.png", {
      fullPage: true,
    });
  });

  test("pending state after toggling two checkboxes enables Apply", async ({ page }) => {
    await loginAsAdmin(page);
    await stubCatalogMultiStl(page);

    // Stub the PUT so the mutation can succeed without a real backend.
    await page.route("**/api/admin/models/001/render-selection", async (route) => {
      if (route.request().method() === "PUT") {
        await route.fulfill({ status: 204, body: "" });
      } else {
        await route.fallback();
      }
    });

    await page.goto("/catalog/001");
    await waitForReady(page);

    await page.getByRole("tab", { name: /pliki modelu/i }).click();
    await waitForReady(page);

    // Check both STL checkboxes.
    const checkboxes = page.getByRole("checkbox");
    await checkboxes.nth(0).check();
    await checkboxes.nth(1).check();

    // Apply button must now be enabled.
    const applyBtn = page.getByRole("button", { name: /zapisz i przerenderuj/i });
    await expect(applyBtn).toBeEnabled();

    await expect(page).toHaveScreenshot("files-tab-admin-pending.png", {
      fullPage: true,
    });
  });
});
