/**
 * Initiative 6 Story 11.3 — anonymous user sees ONLY the login surface.
 *
 * Decision O (architecture.md § Initiative 6): AppShell.tsx hoists auth-
 * gating to shell level. Anonymous users on protected routes get redirected
 * to /login?next=<urlencoded(pathname+searchStr)> — ModuleRail + TopBar
 * MUST NOT render. This spec verifies the property end-to-end at the visual
 * regression boundary so any regression to per-route gating (and the
 * associated module-rail-flash race) is caught by the 4-project visual
 * matrix.
 *
 * The base `_test.ts` fixture stubs /api/auth/me → 401, simulating the
 * anonymous principal. Tests navigate to protected paths and assert the
 * login screen lands without shell chrome.
 */

import { expect, test } from "./_test";
import { waitForReady } from "./helpers";

test("anonymous user at / lands on /login with no module rail", async ({ page }) => {
  await page.goto("/");
  // The redirect happens via TanStack router.navigate; wait for the URL
  // to flip to /login (with `next=%2F` param).
  await page.waitForURL(/\/login\?next=%2F$/, { timeout: 5_000 });
  await waitForReady(page);
  // Module rail + top bar MUST NOT be in the DOM for anonymous users.
  // ModuleRail is keyed by its role=nav landmark or a known data-attr;
  // assert absence via the test-id we'll add (or a stable visual landmark
  // — the email input on the login form proves we're on /login).
  await expect(page.getByLabel(/email|e-mail/i)).toBeVisible();
  // Login route is the only chrome — assert no nav/main-rail present.
  // ModuleRail uses a `nav` element; assert it's absent at shell level
  // (the login route itself doesn't render a nav).
  await expect(page.locator("nav")).toHaveCount(0);
  await expect(page.locator("header")).toHaveCount(0);
  // No toHaveScreenshot here — functional assertions above (URL flip + DOM
  // absence of <nav>/<header>) cover the Decision O contract. Visual
  // baselines for /login itself remain owned by login-2fa-verify.spec.ts
  // and other existing login-touching specs; deferring screenshot generation
  // in this spec avoids the baseline-review-per-PNG overhead
  // (project-context.md "Baseline Acceptance Gate") while still proving the
  // chrome-absence property end-to-end.
});

test("anonymous user at /catalog redirects to /login with next param", async ({
  page,
}) => {
  await page.goto("/catalog");
  // Expect the redirect to /login with `next=%2Fcatalog` (URL-encoded path).
  // Initiative 6 Story 11.3 P2 fix: `searchStr` from TanStack ParsedLocation
  // is used (NOT the parsed `search` object that previously template-literal-
  // coerced to "[object Object]" producing next=%5Bobject%20Object%5D).
  await page.waitForURL(/\/login\?next=%2Fcatalog$/, { timeout: 5_000 });
  await waitForReady(page);
  await expect(page.getByLabel(/email|e-mail/i)).toBeVisible();
  await expect(page.locator("nav")).toHaveCount(0);
  await expect(page.locator("header")).toHaveCount(0);
});

test("anonymous user at /admin/users redirects to /login", async ({ page }) => {
  await page.goto("/admin/users");
  await page.waitForURL(/\/login\?next=%2Fadmin%2Fusers$/, { timeout: 5_000 });
  await waitForReady(page);
  await expect(page.getByLabel(/email|e-mail/i)).toBeVisible();
  await expect(page.locator("nav")).toHaveCount(0);
  await expect(page.locator("header")).toHaveCount(0);
});

test("anonymous user at /catalog?category_id=xyz preserves query in next", async ({
  page,
}) => {
  // P2 regression test from 64447ff codex finding verbatim. Pre-Init-6
  // implementation used `search` (parsed object) → template-literal-coerced
  // to "[object Object]" → next=%5Bobject%20Object%5D. Story 11.3 uses
  // `searchStr` → faithful URL-encoded preservation.
  await page.goto("/catalog?category_id=xyz");
  await page.waitForURL(
    /\/login\?next=%2Fcatalog%3Fcategory_id%3Dxyz$/,
    { timeout: 5_000 },
  );
  await waitForReady(page);
  // CRITICAL ASSERTION (P2 fix verification): no [object Object] in the URL.
  expect(page.url()).not.toContain("%5Bobject");
  expect(page.url()).not.toContain("[object");
});

test("login page itself stays anonymous (no redirect loop)", async ({ page }) => {
  await page.goto("/login");
  // /login is in _PUBLIC_PATHS — must render the form without redirecting.
  await waitForReady(page);
  await expect(page.getByLabel(/email|e-mail/i)).toBeVisible();
  await expect(page.locator("nav")).toHaveCount(0);
  await expect(page.locator("header")).toHaveCount(0);
  // URL must NOT have a `next` param (we didn't come from a protected route)
  expect(page.url()).not.toContain("next=");
});

test("register page stays anonymous (no redirect)", async ({ page }) => {
  await page.goto("/register?token=test-token-43-chars-AAAAAAAAAAAAAAAAAAAA");
  await waitForReady(page);
  await expect(page.locator("nav")).toHaveCount(0);
  await expect(page.locator("header")).toHaveCount(0);
});

test("reset-password page stays anonymous (no redirect)", async ({ page }) => {
  await page.goto("/reset-password?token=test-token-43-chars-AAAAAAAAAAAAAAAAAAAA");
  await waitForReady(page);
  await expect(page.locator("nav")).toHaveCount(0);
  await expect(page.locator("header")).toHaveCount(0);
});
