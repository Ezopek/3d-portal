import { expect, test } from "./_test";

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

  // Stub /api/auth/sessions with deterministic data. Story 12.5 — both UAs
  // carry the `Mozilla/` prefix so they're treated as browser sessions
  // (the page hides non-browser UAs by default; using `Mozilla/`-prefixed
  // strings keeps the baseline focused on the canonical happy path).
  await page.route("**/api/auth/sessions**", (route: Route) =>
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
            user_agent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130",
            is_current: true,
          },
          {
            family_id: "f-2",
            last_used_at: "2026-05-06T08:00:00Z",
            family_issued_at: "2026-05-02T08:00:00Z",
            ip: "5.6.7.8",
            user_agent: "Mozilla/5.0 (Windows NT 10.0) Gecko/20100101 Firefox/132",
            is_current: false,
          },
        ],
        total: 2,
        page: 1,
        page_size: 20,
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
