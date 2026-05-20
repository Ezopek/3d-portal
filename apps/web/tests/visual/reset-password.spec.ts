import type { Page, Route } from "@playwright/test";

import { expect, test } from "./_test";
import { waitForReady } from "./helpers";

const VALID_TOKEN = "test-token-43-chars-AAAAAAAAAAAAAAAAAAAA";

async function stubResetPassword(page: Page, status: number, detail: string) {
  await page.route("**/api/auth/password-reset", (route: Route) =>
    route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify({ detail }),
    }),
  );
}

async function fillAndSubmit(page: Page) {
  await page.getByLabel(/password|hasło/i).fill("correct horse battery staple");
  // Submit button shares its label with the H1 ("Ustaw nowe hasło"). Match
  // the button explicitly to disambiguate from the heading.
  await page
    .getByRole("button", { name: /ustaw nowe hasło|set a new password/i })
    .click();
}

test("renders reset-password form with token in URL", async ({ page }) => {
  await page.goto(`/reset-password?token=${VALID_TOKEN}`);
  await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
  await waitForReady(page);
  await expect(page.getByLabel(/password|hasło/i)).toBeVisible();
  await expect(page).toHaveScreenshot("reset-password-form-with-token.png", {
    fullPage: true,
  });
});

test("renders reset-password token_invalid error state", async ({ page }) => {
  await stubResetPassword(page, 404, "token_invalid");
  await page.goto(`/reset-password?token=${VALID_TOKEN}`);
  await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
  await waitForReady(page);
  await fillAndSubmit(page);
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByLabel(/password|hasło/i)).toHaveCount(0);
  await expect(page).toHaveScreenshot("reset-password-token-invalid.png", {
    fullPage: true,
  });
});

test("renders reset-password weak-password inline error", async ({ page }) => {
  await stubResetPassword(page, 422, "password must be at least 12 characters");
  await page.goto(`/reset-password?token=${VALID_TOKEN}`);
  await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
  await waitForReady(page);
  await fillAndSubmit(page);
  await expect(
    page.getByText("password must be at least 12 characters"),
  ).toBeVisible();
  // Form still visible
  await expect(page.getByLabel(/password|hasło/i)).toBeVisible();
  await expect(page).toHaveScreenshot("reset-password-weak-password.png", {
    fullPage: true,
  });
});
