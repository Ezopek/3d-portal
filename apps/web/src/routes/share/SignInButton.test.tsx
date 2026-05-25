// Initiative 18 Story 30.3 — SignInButton unit tests.
//
// CHROME-1 verifies the button is rendered with the share.view.signin_aria
// label (matches PL OR EN — jsdom's navigator.language defaults to en-US
// in CI, so the LanguageDetector resolves to English; production resolves
// to Polish for Polish browsers per i18n.ts detection order). Matching
// both locales keeps the assertion meaningful regardless of test-env
// locale resolution.
// CHROME-2 verifies that clicking the button navigates to
// /login?next=/share/<token>; this is the FR18-RETURN-URL-1 happy path
// that pairs with Story 30.1's hardened _isSafeReturnPath (which already
// accepts /share/<token> via vitest RU-1).
//
// CHROME-3 (ThemeToggle + LangToggle presence in the share-view header)
// is covered by the Playwright visual baseline at
// tests/visual/share-anonymous-with-signin.spec.ts — exercising the full
// header at the integration level captures the toggles by construction.
//
// Per [[feedback_vitest_manual_cleanup]] the global vitest.setup.ts
// auto-registers afterEach(cleanup); no per-file boilerplate needed.

import {
  Outlet,
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import "@/locales/i18n";

import { SignInButton } from "./SignInButton";

async function renderSignInButton(token: string) {
  const root = createRootRoute({ component: () => <Outlet /> });
  const sharePath = createRoute({
    getParentRoute: () => root,
    path: "/share/$token",
    component: () => <SignInButton token={token} />,
  });
  const loginPath = createRoute({
    getParentRoute: () => root,
    path: "/login",
    component: () => <div>login-page</div>,
    validateSearch: (raw: Record<string, unknown>): { next?: string } => {
      // Mirror the Story 30.1-hardened validator semantics for the test
      // router so search.next propagates exactly as production would.
      if (typeof raw.next === "string" && raw.next.startsWith("/") && !raw.next.startsWith("//")) {
        return { next: raw.next };
      }
      return {};
    },
  });
  const router = createRouter({
    routeTree: root.addChildren([sharePath, loginPath]),
    history: createMemoryHistory({ initialEntries: [`/share/${token}`] }),
  });
  render(<RouterProvider router={router} />);
  return router;
}

describe("Story 30.3 — SignInButton chrome additions", () => {
  it("CHROME-1: renders Sign in button with share.view.signin_aria label", async () => {
    await renderSignInButton("abc123");
    // getByRole throws if absent — implicit assertion of presence.
    await waitFor(() => {
      const btn = screen.getByRole("button", {
        name: /Zaloguj się, aby zobaczyć więcej opcji|Sign in to access more options/i,
      });
      expect(btn.tagName).toBe("BUTTON");
    });
  });

  it("CHROME-2: navigates to /login?next=/share/<token> on click", async () => {
    const router = await renderSignInButton("xyz789");
    const btn = await waitFor(() =>
      screen.getByRole("button", {
        name: /Zaloguj się, aby zobaczyć więcej opcji|Sign in to access more options/i,
      }),
    );
    fireEvent.click(btn);
    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/login");
      expect(router.state.location.search).toEqual({ next: "/share/xyz789" });
    });
  });
});
