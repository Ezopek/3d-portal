import * as Sentry from "@sentry/react";
import { useQuery } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useMemo, type ReactNode } from "react";

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

export function AuthProvider({ children }: { children: ReactNode }) {
  const meQuery = useQuery<MeResponse>({
    queryKey: ["auth", "me"],
    queryFn: () => api<MeResponse>("/auth/me"),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const value = useMemo<AuthState>(() => {
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
  }, [meQuery.isPending, meQuery.isError, meQuery.data]);

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
