// Initiative 18 Story 30.3 / FR18-CHROME-ADDITIONS-1 — visual baseline for
// the anonymous share-view header after Story 30.3 added ThemeToggle +
// LangToggle + SignInButton (Sally Deliverable 1 right-aligned combined-
// with-banner layout).
//
// Per [[feedback_share_view_scope_boundary]] amended carve-out 2026-05-25,
// CHROME affordances on /share/* ARE subject to visual baseline regen
// (membership-path completion is not the deferred CONTENT-parity Phase B
// — it's the scope this baseline is for). 4 baselines × 4 projects
// (desktop-light / desktop-dark / mobile-light / mobile-dark).
//
// Anonymous render is enforced by overriding /api/auth/me → 401; the
// default api-stubs.ts fixture authenticates as admin, so we re-register
// the unauthenticated stub here (Playwright matches handlers in reverse
// registration order — per-test wins).

import { expect, test } from "./_test";

const TOKEN = "test-token-30-3";

const SHARE_VIEW_FIXTURE = {
  id: "00000000-0000-0000-0000-000000000030",
  name_en: "Test Share Model",
  name_pl: "Testowy model udostępniony",
  tags: ["sample"],
  thumbnail_url: null,
  has_3d: false,
  images: [],
  notes_en: "Sample share-view content for visual baseline.",
  notes_pl: "Przykładowa zawartość udostępniona dla baseline wizualnego.",
  stl_url: null,
  stl_size_bytes: null,
};

test.describe("Story 30.3 — share-view chrome additions", () => {
  test("anonymous share view with new chrome (Sign in + Theme + Lang)", async ({ page }) => {
    // Anonymous override — default fixture returns ADMIN; reverse-order
    // registration ensures this per-test stub wins for the anonymous case.
    await page.route("**/api/auth/me", (route) =>
      route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "missing_access" }),
      }),
    );
    await page.route(`**/api/share/${TOKEN}`, (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(SHARE_VIEW_FIXTURE),
      }),
    );
    await page.route(`**/api/share/${TOKEN}/files`, (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 50 }),
      }),
    );

    await page.goto(`/share/${TOKEN}`);
    // Wait for SignInButton to render (matches both PL and EN aria-label).
    await page
      .getByRole("button", { name: /Zaloguj się|Sign in/i })
      .first()
      .waitFor();

    await expect(page).toHaveScreenshot("share-anonymous-with-signin.png", {
      fullPage: false,
      animations: "disabled",
    });
  });
});
