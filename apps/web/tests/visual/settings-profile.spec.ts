import { expect, test } from "./_test";

import { waitForReady } from "./helpers";
import type { Page, Route } from "@playwright/test";

async function stubProfilePage(page: Page) {
  // Stub /api/auth/me so AuthGate considers the user authenticated and the
  // page can seed the display_name input from the cached MeResponse.
  // ⚠️ Story 54.2 AC-8 — KEPT, LOAD-BEARING. This is a `role: "member"`
  // override of `_test.ts`'s admin default, and the payload PAINTS: the
  // `display_name` seeds the profile input and the header `UserMenu` label.
  // Deleting it would silently repaint every baseline in this file as an admin
  // named "Admin". Do not consolidate.
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

test.describe("/settings/profile desktop", () => {
  test("desktop layout matches baseline", async ({ page }) => {
    await stubProfilePage(page);
    await page.goto("/settings/profile");
    // Role-only heading match; profile.tsx renders a single <h1>, so this is
    // locale-agnostic (works under playwright.config.ts locale="pl-PL").
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);
    await expect(page).toHaveScreenshot("settings-profile-desktop.png", {
      fullPage: true,
    });
  });
});

test.describe("/settings/profile mobile", () => {
  test.use({ viewport: { width: 375, height: 800 } });
  test("mobile layout matches baseline", async ({ page }) => {
    await stubProfilePage(page);
    await page.goto("/settings/profile");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);
    await expect(page).toHaveScreenshot("settings-profile-mobile.png", {
      fullPage: true,
    });
  });
});
