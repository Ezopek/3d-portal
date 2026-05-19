import type { Page, Route } from "@playwright/test";

import { expect, test } from "./_test";
import { waitForReady } from "./helpers";

const PARTIAL_TOKEN = "deterministic-partial-token-for-visual-tests";

async function stubLoginPartialAuth(page: Page) {
  await page.route("**/api/auth/login", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        partial_auth: true,
        totp_required: true,
        partial_token: PARTIAL_TOKEN,
      }),
    }),
  );
}

async function stubVerify(page: Page, status: number, detail: string) {
  await page.route("**/api/auth/2fa/verify", (route: Route) =>
    route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify({ detail }),
    }),
  );
}

async function submitEmailPassword(page: Page) {
  await page.getByLabel(/email|e-mail/i).fill("anna@example.com");
  await page.getByLabel(/password|hasło/i).fill("correct horse battery staple");
  await page.getByRole("button", { name: /sign in|zaloguj/i }).click();
}

test("login-second-factor-prompt matches baseline", async ({ page }) => {
  await stubLoginPartialAuth(page);
  await page.goto("/login");
  await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
  await submitEmailPassword(page);
  // Wait for the transition to the second-factor sub-state.
  await page.getByLabel(/^code$|^kod$/i).waitFor({ state: "visible" });
  await waitForReady(page);
  await expect(page).toHaveScreenshot("login-second-factor-prompt.png", {
    fullPage: true,
  });
});

test("login-second-factor-invalid-code matches baseline", async ({ page }) => {
  await stubLoginPartialAuth(page);
  await stubVerify(page, 401, "invalid_code");
  await page.goto("/login");
  await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
  await submitEmailPassword(page);
  await page.getByLabel(/^code$|^kod$/i).waitFor({ state: "visible" });
  await page.getByLabel(/^code$|^kod$/i).fill("000000");
  await page.getByRole("button", { name: /verify|zweryfikuj/i }).click();
  await page.getByRole("alert").waitFor({ state: "visible" });
  await waitForReady(page);
  await expect(page).toHaveScreenshot("login-second-factor-invalid-code.png", {
    fullPage: true,
  });
});

test("login-second-factor-session-expired matches baseline", async ({ page }) => {
  await stubLoginPartialAuth(page);
  await stubVerify(page, 401, "partial_token_invalid");
  await page.goto("/login");
  await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
  await submitEmailPassword(page);
  await page.getByLabel(/^code$|^kod$/i).waitFor({ state: "visible" });
  await page.getByLabel(/^code$|^kod$/i).fill("123456");
  await page.getByRole("button", { name: /verify|zweryfikuj/i }).click();
  await page.getByRole("alert").waitFor({ state: "visible" });
  await waitForReady(page);
  await expect(page).toHaveScreenshot("login-second-factor-session-expired.png", {
    fullPage: true,
  });
});
