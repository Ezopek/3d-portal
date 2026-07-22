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
 * The base `_test.ts` fixture stubs /api/auth/me → 200 ADMIN by default
 * (Codex P1 review 2026-05-21 — keeps every other protected-route visual
 * spec exercising its intended page). This spec OPTS IN to anonymous
 * behavior via a beforeEach override that re-registers /api/auth/me → 401.
 * Playwright matches handlers in reverse registration order so the per-spec
 * override wins.
 */

import { expect, test } from "./_test";
import { waitForReady } from "./helpers";

test.beforeEach(async ({ page }) => {
  // Override the default-fixture admin stub to anonymous (401) for this spec.
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ detail: "not_authenticated" }),
    }),
  );
});

test("anonymous user at / lands on /login with no module rail", async ({ page }) => {
  await page.goto("/");
  // Story 31.4 (Init 19): `/` graduated from a redirect-to-/catalog stub
  // to a real LandingPage component. AuthGate now captures the literal `/`
  // as the post-redirect next param (was `%2Fcatalog` pre-31.4 because of
  // the route-level redirect firing first). The Decision O contract is
  // unchanged — anonymous user lands on /login carrying pathname-as-next;
  // only the captured pathname shifts because the redirect deferral ended.
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
  // Decision O contract — anonymous deep link to a protected admin route
  // surfaces /login?next=%2Fadmin%2Fusers (pathname preserved). The admin
  // route components defer to AppShell.AuthGate via the
  // `!isAuthenticated → return null` guard so the role-tier `<Navigate to="/">`
  // doesn't race ahead of the shell-level auth gate for anonymous users.
  await page.waitForURL(/\/login\?next=%2Fadmin%2Fusers$/, { timeout: 5_000 });
  await waitForReady(page);
  await expect(page.getByLabel(/email|e-mail/i)).toBeVisible();
  await expect(page.locator("nav")).toHaveCount(0);
  await expect(page.locator("header")).toHaveCount(0);
});

test("anonymous user at /catalog?q=xyz preserves query in next", async ({
  page,
}) => {
  // P2 regression test from 64447ff codex finding verbatim. Pre-Init-6
  // implementation used `search` (parsed object) → template-literal-coerced
  // to "[object Object]" → next=%5Bobject%20Object%5D. Story 11.3 uses
  // `searchStr` → faithful URL-encoded preservation.
  await page.goto("/catalog?q=xyz");
  await page.waitForURL(
    /\/login\?next=%2Fcatalog%3Fq%3Dxyz$/,
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
