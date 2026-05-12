import { expect, test } from "@playwright/test";

import { waitForReady } from "./helpers";
import type { Page, Route } from "@playwright/test";

async function stubSessionsPage(page: Page) {
  // Stub /api/auth/me so AuthGate considers the user authenticated
  await page.route("**/api/auth/me", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "u1",
        email: "test@example.com",
        display_name: "Test User",
        role: "admin",
      }),
    }),
  );

  // Stub /api/auth/sessions with deterministic data
  await page.route("**/api/auth/sessions", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            family_id: "f-1",
            last_used_at: "2026-05-07T10:00:00Z",
            family_issued_at: "2026-05-01T10:00:00Z",
            ip: "1.2.3.4",
            user_agent: "Chrome 130 / macOS",
            is_current: true,
          },
          {
            family_id: "f-2",
            last_used_at: "2026-05-06T08:00:00Z",
            family_issued_at: "2026-05-02T08:00:00Z",
            ip: "5.6.7.8",
            user_agent: "Firefox 132 / Windows",
            is_current: false,
          },
        ],
      }),
    }),
  );
}

test.describe("/settings/sessions desktop", () => {
  test("desktop layout matches baseline", async ({ page }) => {
    await stubSessionsPage(page);
    await page.goto("/settings/sessions");
    // Role-only heading match; sessions.tsx renders a single <h1>, so this is
    // locale-agnostic (works under playwright.config.ts locale="pl-PL").
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);
    await expect(page).toHaveScreenshot("sessions-desktop.png", {
      fullPage: true,
    });
  });
});

test.describe("/settings/sessions mobile", () => {
  test.use({ viewport: { width: 375, height: 800 } });
  test("mobile layout matches baseline", async ({ page }) => {
    await stubSessionsPage(page);
    await page.goto("/settings/sessions");
    // Role-only heading match; sessions.tsx renders a single <h1>, so this is
    // locale-agnostic (works under playwright.config.ts locale="pl-PL").
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);
    await expect(page).toHaveScreenshot("sessions-mobile.png", {
      fullPage: true,
    });
  });
});
