import { test as base } from "@playwright/test";

// Default API stubs shared by every visual test.
//
// Without these the unstubbed `/api/*` calls go through the Vite dev-server
// proxy to localhost:8000 (which is not running during a `npm run test:visual`
// session). The proxy hangs for ~2 minutes per request before giving up,
// which blocks Playwright's networkidle wait and trips a 30 s test timeout.
//
//   - `/api/auth/me` → 200 ADMIN by default (Initiative 6 Story 11.3 + Codex
//     P1 review 2026-05-21). With shell-level AuthGate (AppShell.tsx
//     Decision O), an anonymous /api/auth/me response now redirects every
//     protected-route visit to /login. To keep every existing protected-
//     route visual spec (catalog-list, catalog-detail, v2-placeholders,
//     dev, admin-users, admin-invites, settings/*, etc.) exercising its
//     intended page, the default fixture authenticates as admin. Specs
//     that need anonymous behavior (anon-login-only.spec.ts) explicitly
//     re-register /api/auth/me → 401 — Playwright matches handlers in
//     reverse registration order so the per-test override wins.
//   - `/api/**` catch-all → 404. Tests that need real-looking data register
//     more specific routes (e.g. `**/api/tag-groups`) which win the same way.
//     This stops every "I forgot to stub /api/activity-log" from blocking
//     networkidle for 2 minutes.
const DEFAULT_ADMIN_ME = {
  id: "11111111-1111-1111-1111-111111111111",
  email: "admin@localhost.localdomain",
  display_name: "Admin",
  role: "admin" as const,
};
/* eslint-disable react-hooks/rules-of-hooks -- `use` here is the Playwright fixture callback, not React's `use` hook. */
export const test = base.extend({
  page: async ({ page }, use) => {
    await page.route("**/api/**", (route) =>
      route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ detail: "stub_not_configured" }),
      }),
    );
    await page.route("**/api/auth/me", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(DEFAULT_ADMIN_ME),
      }),
    );
    await page.route("**/api/profiles/offers/published**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ offers: [] }),
      }),
    );
    await use(page);
  },
});
/* eslint-enable react-hooks/rules-of-hooks */

export { expect } from "@playwright/test";
