import { test as base } from "@playwright/test";

// Default API stubs shared by every visual test.
//
// Without these the unstubbed `/api/*` calls go through the Vite dev-server
// proxy to localhost:8000 (which is not running during a `npm run test:visual`
// session). The proxy hangs for ~2 minutes per request before giving up,
// which blocks Playwright's networkidle wait and trips a 30 s test timeout.
//
//   - `/api/auth/me` → 401 (anonymous). Spec files that need an admin
//     re-register this route later; Playwright matches handlers in reverse
//     registration order so the per-test stub wins.
//   - `/api/**` catch-all → 404. Tests that need real-looking data register
//     more specific routes (e.g. `**/api/categories`) which win the same way.
//     This stops every "I forgot to stub /api/activity-log" from blocking
//     networkidle for 2 minutes.
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
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "not_authenticated" }),
      }),
    );
    await use(page);
  },
});
/* eslint-enable react-hooks/rules-of-hooks */

export { expect } from "@playwright/test";
