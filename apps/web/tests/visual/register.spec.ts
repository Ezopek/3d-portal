import type { Page, Route } from "@playwright/test";

import { expect, test } from "./_test";
import { waitForReady } from "./helpers";

const VALID_TOKEN = "test-token-43-chars-AAAAAAAAAAAAAAAAAAAA";

async function stubRegister(page: Page, status: number, detail: string) {
  await page.route("**/api/auth/register", (route: Route) =>
    route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify({ detail }),
    }),
  );
}

async function fillAndSubmit(page: Page) {
  await page.getByLabel(/email|e-mail/i).fill("newbie@example.com");
  await page.getByLabel(/password|hasło/i).fill("correct horse battery staple");
  // Submit button shares its label with the H1 ("Utwórz konto") under pl-PL.
  // Match the button explicitly so we don't accidentally click the theme
  // toggle or language switcher in the banner.
  await page.getByRole("button", { name: /utwórz konto|create account/i }).click();
}

test("renders register form with token in URL", async ({ page }) => {
  await page.goto(`/register?token=${VALID_TOKEN}`);
  await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
  await waitForReady(page);
  await expect(page.getByLabel(/email|e-mail/i)).toBeVisible();
  await expect(page.getByLabel(/password|hasło/i)).toBeVisible();
  await expect(page).toHaveScreenshot("register-form-with-token.png", {
    fullPage: true,
  });
});

test("renders missing-token error state", async ({ page }) => {
  await page.goto("/register");
  await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
  await waitForReady(page);
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByLabel(/email|e-mail/i)).toHaveCount(0);
  await expect(page).toHaveScreenshot("register-missing-token.png", {
    fullPage: true,
  });
});

test("renders token_invalid error state", async ({ page }) => {
  await stubRegister(page, 404, "token_invalid");
  await page.goto(`/register?token=${VALID_TOKEN}`);
  await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
  await waitForReady(page);
  await fillAndSubmit(page);
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByLabel(/email|e-mail/i)).toHaveCount(0);
  await expect(page).toHaveScreenshot("register-token-invalid.png", {
    fullPage: true,
  });
});

test("renders token_consumed error state", async ({ page }) => {
  await stubRegister(page, 410, "token_consumed");
  await page.goto(`/register?token=${VALID_TOKEN}`);
  await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
  await waitForReady(page);
  await fillAndSubmit(page);
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByLabel(/email|e-mail/i)).toHaveCount(0);
  await expect(page).toHaveScreenshot("register-token-consumed.png", {
    fullPage: true,
  });
});

test("renders weak_password inline error", async ({ page }) => {
  await stubRegister(page, 422, "password must be at least 12 characters");
  await page.goto(`/register?token=${VALID_TOKEN}`);
  await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
  await waitForReady(page);
  await fillAndSubmit(page);
  await expect(
    page.getByText("password must be at least 12 characters"),
  ).toBeVisible();
  // Form still visible
  await expect(page.getByLabel(/email|e-mail/i)).toBeVisible();
  await expect(page).toHaveScreenshot("register-weak-password.png", {
    fullPage: true,
  });
});

test("renders email_taken inline error", async ({ page }) => {
  await stubRegister(page, 409, "email_taken");
  await page.goto(`/register?token=${VALID_TOKEN}`);
  await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
  await waitForReady(page);
  await fillAndSubmit(page);
  await expect(page.getByRole("alert")).toBeVisible();
  // Form still visible
  await expect(page.getByLabel(/email|e-mail/i)).toBeVisible();
  await expect(page).toHaveScreenshot("register-email-taken.png", {
    fullPage: true,
  });
});
