import { expect, test } from "@playwright/test";

import { stubSotList } from "./api-stubs";
import { waitForReady } from "./helpers";

test.describe("catalog card carousel", () => {
  test("renders dot indicators on multi-image cards", async ({ page }) => {
    await stubSotList(page);
    await page.goto("/catalog");
    await waitForReady(page);
    const dots = page.getByTestId("card-carousel-dots");
    await expect(dots).toHaveCount(1);
    await expect(dots.locator("button")).toHaveCount(3);
  });

  test("clicking a dot does not navigate to the detail page", async ({ page }) => {
    await stubSotList(page);
    await page.goto("/catalog");
    await waitForReady(page);
    const dots = page.getByTestId("card-carousel-dots").locator("button");
    await dots.nth(1).click();
    await expect(page).toHaveURL(/\/catalog$/);
  });
});
