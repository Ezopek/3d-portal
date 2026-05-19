import { expect, test } from "./_test";

import { waitForReady } from "./helpers";
import type { Page, Route } from "@playwright/test";

const FIXED_GENERATED_AT = "2026-05-19T12:00:00Z";
const FIXED_BATCH_ID = "11111111-1111-4111-8111-111111111111";
const DETERMINISTIC_QR_SVG =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="180" height="180">' +
  '<rect width="100" height="100" fill="hsl(0 0% 100%)"/>' +
  '<rect x="10" y="10" width="80" height="80" fill="hsl(0 0% 0%)"/>' +
  '<rect x="22" y="22" width="56" height="56" fill="hsl(0 0% 100%)"/>' +
  '<rect x="34" y="34" width="32" height="32" fill="hsl(0 0% 0%)"/>' +
  "</svg>";

const DETERMINISTIC_CODES = [
  "00000001",
  "00000002",
  "00000003",
  "00000004",
  "00000005",
  "00000006",
  "00000007",
  "00000008",
];

async function stubAuthMe(page: Page) {
  await page.route("**/api/auth/me", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "u1",
        email: "test@example.com",
        display_name: "Test User",
        role: "member",
      }),
    }),
  );
}

async function stubStatus(
  page: Page,
  body: {
    enabled: boolean;
    batch_id?: string | null;
    generated_at?: string | null;
    codes_remaining?: number | null;
  },
) {
  await page.route("**/api/auth/2fa/status", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        enabled: body.enabled,
        batch_id: body.batch_id ?? null,
        generated_at: body.generated_at ?? null,
        codes_remaining: body.codes_remaining ?? null,
      }),
    }),
  );
}

async function stubEnroll(page: Page) {
  await page.route("**/api/auth/2fa/enroll", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        qr_svg: DETERMINISTIC_QR_SVG,
        manual_secret: "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP",
        enrollment_token: "deterministic-token-for-visual-tests",
      }),
    }),
  );
}

async function stubConfirm(page: Page) {
  await page.route("**/api/auth/2fa/enroll/confirm", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        recovery_codes: DETERMINISTIC_CODES,
        batch_id: FIXED_BATCH_ID,
        generated_at: FIXED_GENERATED_AT,
      }),
    }),
  );
}

test("2fa-status-disabled matches baseline", async ({ page }) => {
  await stubAuthMe(page);
  await stubStatus(page, { enabled: false });
  await page.goto("/settings/2fa");
  await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
  await waitForReady(page);
  await expect(page).toHaveScreenshot("2fa-status-disabled.png", {
    fullPage: true,
  });
});

test("2fa-enroll-qr matches baseline", async ({ page }) => {
  await stubAuthMe(page);
  await stubStatus(page, { enabled: false });
  await stubEnroll(page);
  await page.goto("/settings/2fa");
  await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
  await page.getByRole("button", { name: /Włącz uwierzytelnianie|Enable two-factor/ }).click();
  await page.getByTestId("totp-qr").waitFor({ state: "visible" });
  await waitForReady(page);
  await expect(page).toHaveScreenshot("2fa-enroll-qr.png", {
    fullPage: true,
  });
});

test("2fa-show-codes matches baseline", async ({ page }) => {
  await stubAuthMe(page);
  await stubStatus(page, { enabled: false });
  await stubEnroll(page);
  await stubConfirm(page);
  await page.goto("/settings/2fa");
  await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
  await page.getByRole("button", { name: /Włącz uwierzytelnianie|Enable two-factor/ }).click();
  await page.getByTestId("totp-qr").waitFor({ state: "visible" });
  // Fill in a 6-digit code; stub returns success regardless.
  const codeInput = page.locator('input[inputmode="numeric"]');
  await codeInput.fill("123456");
  await page.getByRole("button").filter({ hasText: /Zweryfikuj|Verify/ }).click();
  await page.getByTestId("totp-recovery-codes").waitFor({ state: "visible" });
  await waitForReady(page);
  await expect(page).toHaveScreenshot("2fa-show-codes.png", {
    fullPage: true,
  });
});

test("2fa-status-enabled matches baseline", async ({ page }) => {
  await stubAuthMe(page);
  await stubStatus(page, {
    enabled: true,
    batch_id: FIXED_BATCH_ID,
    generated_at: FIXED_GENERATED_AT,
    codes_remaining: 8,
  });
  await page.goto("/settings/2fa");
  await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
  await waitForReady(page);
  await expect(page).toHaveScreenshot("2fa-status-enabled.png", {
    fullPage: true,
  });
});
