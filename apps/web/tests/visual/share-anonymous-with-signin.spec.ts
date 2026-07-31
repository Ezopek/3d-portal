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
    // ⚠️ Story 54.2 AC-8 — KEPT, LOAD-BEARING. Without the 401 this spec
    // renders the member chrome, not the anonymous chrome it baselines.
    // Do not consolidate.
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

// Story 54.2 / AC-1 + T13 (V-8) — the `/share` half of the duplicate
// accessible name. `routes/share/$token.tsx:308` (full-frame trigger) and
// `:321` (corner icon) both rendered `catalog.image_viewer.trigger_label`, and
// the corner one is hidden with `sm:opacity-0` — opacity, not `display` or
// `aria-hidden` — so both stayed in the accessibility tree permanently and a
// screen-reader user heard one name twice for one function. The `/catalog` half
// is pinned in `src/modules/catalog/components/ModelGallery.test.tsx`; this is
// the anonymous twin, which no vitest suite mounts.
//
// Deliberately assertion-only: NO `toHaveScreenshot`, so it adds zero baselines.
test("share carousel exposes the fullscreen trigger label exactly once (V-8)", async ({
  page,
}) => {
  const IMAGE_URL = `/api/share/${TOKEN}/files/img-1/content`;
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
      body: JSON.stringify({ ...SHARE_VIEW_FIXTURE, images: [IMAGE_URL] }),
    }),
  );
  await page.route(`**/api/share/${TOKEN}/files`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 50 }),
    }),
  );
  // A 1x1 transparent GIF is enough: the assertion is about the accessible
  // name of the two buttons, which render whether or not the blob decodes.
  await page.route(`**${IMAGE_URL}**`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "image/gif",
      body: Buffer.from("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7", "base64"),
    }),
  );

  await page.goto(`/share/${TOKEN}`);
  await expect(page.getByTestId("share-fullscreen-trigger")).toBeVisible();

  // Polish is the harness locale; `catalog.image_viewer.trigger_label`.
  await expect(
    page.getByRole("button", { name: "Otwórz na pełnym ekranie" }),
  ).toHaveCount(1);

  const icon = page.getByTestId("share-fullscreen-icon");
  await expect(icon).toHaveAttribute("aria-hidden", "true");
  await expect(icon).toHaveAttribute("tabindex", "-1");
});
