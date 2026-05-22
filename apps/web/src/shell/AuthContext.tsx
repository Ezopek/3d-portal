import * as Sentry from "@sentry/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api } from "@/lib/api";
import type { MeResponse, Role } from "@/lib/api-types";

interface AuthState {
  user: MeResponse | null;
  role: Role | null;
  isAdmin: boolean;
  isMember: boolean;
  isAdminOrAgent: boolean;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const ANONYMOUS: AuthState = {
  user: null,
  role: null,
  isAdmin: false,
  isMember: false,
  isAdminOrAgent: false,
  isAuthenticated: false,
  isLoading: false,
};

const AuthCtx = createContext<AuthState>(ANONYMOUS);

// Module-scoped mirror of the auth state for non-React callers (e.g. the
// router.subscribe('onLoad', ...) listener in instrument-router.ts, which
// fires outside the render tree and cannot use useAuth()). Updated by the
// AuthProvider effect below; defaults to ANONYMOUS until the provider mounts.
let authSnapshot: { isAuthenticated: boolean } = { isAuthenticated: false };

// Initiative 10 Story 16.3 (NFR10-SHARE-SECURITY-1) — track pathname
// reactively so that client-side SPA navigation (history.pushState) from
// authenticated routes onto /share/<token> disables the /auth/me query.
// `window.location` is not React-reactive; popstate covers back/forward;
// history.pushState is monkey-patched once at module load to fire a
// synthetic event the listener picks up.
function _emitLocationChange(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event("portal:locationchange"));
}

if (typeof window !== "undefined" && !("_portalPathnameHooked" in window)) {
  const origPushState = window.history.pushState.bind(window.history);
  const origReplaceState = window.history.replaceState.bind(window.history);
  window.history.pushState = (...args) => {
    origPushState(...args);
    _emitLocationChange();
  };
  window.history.replaceState = (...args) => {
    origReplaceState(...args);
    _emitLocationChange();
  };
  window.addEventListener("popstate", _emitLocationChange);
  (window as unknown as { _portalPathnameHooked: true })._portalPathnameHooked = true;
}

function useReactivePathname(): string {
  const [pathname, setPathname] = useState<string>(() =>
    typeof window === "undefined" ? "/" : window.location.pathname,
  );
  useEffect(() => {
    const onChange = () => setPathname(window.location.pathname);
    window.addEventListener("portal:locationchange", onChange);
    return () => window.removeEventListener("portal:locationchange", onChange);
  }, []);
  return pathname;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const pathname = useReactivePathname();
  const isAnonymousShareRoute = pathname.startsWith("/share/");
  const qc = useQueryClient();

  // When the route flips onto /share/*, invalidate any cached auth state so
  // a subsequent re-enable (user navigates back to a protected route) does
  // not return a stale logged-in snapshot. This is defense-in-depth — the
  // `enabled` flag already prevents new fetches, but a memoized cache hit
  // could leak.
  useEffect(() => {
    if (isAnonymousShareRoute) {
      qc.removeQueries({ queryKey: ["auth", "me"] });
    }
  }, [isAnonymousShareRoute, qc]);

  const meQuery = useQuery<MeResponse>({
    queryKey: ["auth", "me"],
    queryFn: () => api<MeResponse>("/auth/me"),
    retry: false,
    staleTime: 5 * 60 * 1000,
    enabled: !isAnonymousShareRoute,
  });

  const value = useMemo<AuthState>(() => {
    // Share routes: query is disabled, isPending stays true forever. Short-
    // circuit to ANONYMOUS so child components see a stable not-loading
    // anonymous state instead of an infinite spinner.
    if (isAnonymousShareRoute) return ANONYMOUS;
    if (meQuery.isPending) return { ...ANONYMOUS, isLoading: true };
    if (meQuery.isError) return ANONYMOUS;
    const u = meQuery.data!;
    return {
      user: u,
      role: u.role,
      isAdmin: u.role === "admin",
      isMember: u.role === "member",
      isAdminOrAgent: u.role === "admin" || u.role === "agent",
      isAuthenticated: true,
      isLoading: false,
    };
  }, [isAnonymousShareRoute, meQuery.isPending, meQuery.isError, meQuery.data]);

  useEffect(() => {
    authSnapshot = { isAuthenticated: value.isAuthenticated };
    // Re-emit to Sentry's active scope eagerly — the router-onLoad listener
    // (instrument-router.ts) only fires on navigation, so login/logout that
    // resolves between routes (or the common initial-page-load case where
    // /auth/me resolves AFTER the first onLoad) would leave a stale
    // `auth.is_authenticated` tag attached to subsequent captures until the
    // user navigated again. Mirror to scope here so every auth-state flip
    // is reflected immediately, regardless of routing activity.
    Sentry.setTag("auth.is_authenticated", String(value.isAuthenticated));
  }, [value.isAuthenticated]);

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function getAuthSnapshot(): { isAuthenticated: boolean } {
  return authSnapshot;
}

export function useAuth(): AuthState {
  return useContext(AuthCtx);
}
