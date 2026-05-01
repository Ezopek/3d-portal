import { expect, test } from "@playwright/test";

import { stubCatalog } from "./api-stubs";
import { waitForReady } from "./helpers";

test.describe("catalog card carousel", () => {
  test("dots are visible for cards with >= 2 images", async ({ page }) => {
    await stubCatalog(page);
    await page.goto("/catalog");
    await waitForReady(page);

    // Model 001 has image_count=3 in the stub.
    const dragonCard = page.locator("a", { hasText: "Smok" }).first();
    const dots = dragonCard.locator('button[aria-label^="go to image"]');
    await expect(dots).toHaveCount(3);
  });

  test("clicking a dot does not navigate to detail view", async ({ page }) => {
    await stubCatalog(page);
    await page.goto("/catalog");
    await waitForReady(page);

    const dragonCard = page.locator("a", { hasText: "Smok" }).first();
    const secondDot = dragonCard.locator('button[aria-label="go to image 2"]');

    await expect(page).toHaveURL(/\/catalog$/);
    // Dots are always visible (no hover-gating, no pointer-coarse:hidden), so
    // they're the deterministic surface to assert click stopPropagation.
    // Force-click avoids flakes from sticky header / neighbouring card overlap
    // on the mobile (Pixel 5) viewport.
    await secondDot.click({ force: true });
    await expect(page).toHaveURL(/\/catalog$/);
  });

  test("renders no carousel UI when image_count < 2", async ({ page }) => {
    await stubCatalog(page);
    await page.goto("/catalog");
    await waitForReady(page);

    // Model 002 (Vase) has image_count=1 in the stub.
    const vaseCard = page.locator("a", { hasText: "Wazon" }).first();
    const dots = vaseCard.locator('button[aria-label^="go to image"]');
    await expect(dots).toHaveCount(0);
  });
});
