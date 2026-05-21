import { expect, test } from "./_test";

import { waitForReady } from "./helpers";
import type { Page, Route } from "@playwright/test";

async function stubHubPage(page: Page) {
  // Stub /api/auth/me so AuthGate considers the user authenticated and the
  // hub landing renders the three cards (the hub itself makes no other API
  // calls — Story 12.4 is a pure-navigation landing).
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

test.describe("/settings hub", () => {
  test("hub layout matches baseline across all viewports", async ({ page }) => {
    await stubHubPage(page);
    await page.goto("/settings");
    // Role-only heading match; index.tsx renders a single <h1>, so this is
    // locale-agnostic (works under playwright.config.ts locale="pl-PL").
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);
    await expect(page).toHaveScreenshot("settings-hub.png", {
      fullPage: true,
    });
  });
});
