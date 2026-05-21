import { useLocation, useNavigate } from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "./AuthContext";
import { ModuleRail } from "./ModuleRail";
import { TopBar } from "./TopBar";

// Initiative 6 Story 11.3 Decision O — explicit public-path allowlist for
// anonymous-allowed routes. Mirrors backend `_PUBLIC_ROUTES` posture (FR6-AUTH-2):
// every protected route requires authentication, EXCEPT the surfaces in this
// allowlist + the dynamic `/share/<token>` family handled separately below.
// Adding to this list requires a Sprint Change Proposal (FR6-AUTH-2 procedural
// gate — same property as the backend allowlist).
const _PUBLIC_PATHS = new Set<string>([
  "/login",
  "/register",
  "/reset-password",
]);

export function AppShell({ children }: { children: ReactNode }) {
  const { pathname, searchStr } = useLocation();
  const auth = useAuth();
  const navigate = useNavigate();

  // 1. Share path bypass (anonymous-allowed dynamic family, preserved from
  //    Init 0; never renders shell chrome). Token paths under /share/<token>
  //    are not enumerable in the static allowlist; the prefix match is the
  //    canonical predicate.
  const isSharePath = pathname.startsWith("/share/");

  // 2. Public path bypass — explicit allowlist for login / register /
  //    reset-password and their nested children (if any). Use startsWith
  //    so deep paths like /reset-password/confirm continue to bypass.
  const isPublicPath =
    _PUBLIC_PATHS.has(pathname) ||
    Array.from(_PUBLIC_PATHS).some((p) => pathname === p || pathname.startsWith(`${p}/`));

  // 3. Anonymous redirect to login — must fire as an effect because TanStack
  //    Router rejects synchronous router.navigate() calls during render.
  //    The redirect carries the original (pathname + searchStr) as
  //    URL-encoded `next` param so post-login lands the user where they
  //    intended (closes 64447ff P2 codex finding: `searchStr` is the
  //    pre-stringified search portion with leading `?`, NOT the parsed
  //    `search` object which would coerce to `[object Object]`).
  useEffect(() => {
    if (auth.isLoading) return;
    if (isSharePath || isPublicPath) return;
    if (!auth.isAuthenticated) {
      // Codex P2 (2026-05-21) — pass raw `pathname + searchStr` to navigate.
      // TanStack Router encodes search values via URLSearchParams; manually
      // calling encodeURIComponent here would double-encode (the resulting URL
      // becomes `/login?next=%252Fcatalog%253Fcategory_id%253Dxyz` instead of
      // `/login?next=%2Fcatalog%3Fcategory_id%3Dxyz`).
      const next = pathname + (searchStr || "");
      void navigate({ to: "/login", search: { next }, replace: true });
    }
  }, [auth.isLoading, auth.isAuthenticated, isSharePath, isPublicPath, navigate, pathname, searchStr]);

  // Share path: render bare children (no shell chrome).
  if (isSharePath) {
    return <>{children}</>;
  }

  // Public path: render bare children (login screen IS the shell for
  // anonymous users on these routes — no ModuleRail, no TopBar).
  if (isPublicPath) {
    return <>{children}</>;
  }

  // Auth loading state — minimal viewport-centered spinner without any
  // shell chrome (avoids the "module rail flash" race that would expose
  // protected surface for ~50ms during auth resolution).
  if (auth.isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="size-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  // Unauthenticated on a protected path — render nothing while the effect
  // above issues the navigate redirect. Returning `null` for one render
  // tick is intentional and indistinguishable to the user from the
  // navigate transition (browser shows the login route on the next tick).
  if (!auth.isAuthenticated) {
    return null;
  }

  // Authenticated — full shell with ModuleRail + TopBar.
  return (
    <div className="flex min-h-screen">
      <ModuleRail />
      <div className="flex min-h-screen min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="flex-1 pb-16 lg:pb-0">{children}</main>
      </div>
    </div>
  );
}
