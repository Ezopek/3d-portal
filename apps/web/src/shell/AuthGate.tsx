import { useLocation, useNavigate } from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "@/shell/AuthContext";

// Initiative 6 Story 11.3 — AuthGate is no longer the primary auth-gating
// primitive (AppShell.tsx hoisted the gate to shell level per Decision O).
// This component remains as a thin wrapper for any legacy callers that
// still import it; the implementation is kept aligned with shell-level
// semantics (uses `searchStr` not `search` per 64447ff P2 codex finding).
// Future cleanup may delete this file entirely once no callers remain
// (grep for `<AuthGate` to verify — Story 11.3 removes 4 known callers).
export function AuthGate({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const { pathname, searchStr } = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    if (!auth.isLoading && !auth.isAuthenticated) {
      // Initiative 6 Story 11.3 — `searchStr` is the pre-stringified search
      // portion with leading `?` (from TanStack ParsedLocation). The
      // pre-Init-6 implementation used `search` (the parsed object), which
      // template-literal-coerced to `"[object Object]"` and produced
      // `next=%5Bobject%20Object%5D` artifacts on /catalog redirects
      // (P2 from 64447ff codex review verbatim). Using `searchStr` produces
      // a faithful URL-encoded copy of the original location.
      const next = encodeURIComponent(pathname + (searchStr || ""));
      void navigate({ to: "/login", search: { next }, replace: true });
    }
  }, [auth.isLoading, auth.isAuthenticated, navigate, pathname, searchStr]);

  if (auth.isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="size-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!auth.isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
