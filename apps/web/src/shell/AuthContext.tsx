import { useQuery } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useMemo, type ReactNode } from "react";

import { ApiError, api } from "@/lib/api";
import type { MeResponse, Role } from "@/lib/api-types";
import { clearToken, readToken } from "@/lib/auth";
import { decodeJwtRole } from "@/lib/jwt";

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

export function AuthProvider({ children }: { children: ReactNode }) {
  const stored = readToken();
  const role = stored === null ? null : decodeJwtRole(stored.token);
  const isAuthenticated = stored !== null && role !== null;

  const meQuery = useQuery<MeResponse, ApiError>({
    queryKey: ["auth", "me", stored?.token ?? null],
    queryFn: () => api<MeResponse>("/auth/me"),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });

  // If /me responds 401, the token is no good — clear it. Reload so the
  // synchronous reads pick up the cleared state. (No router dep here.)
  useEffect(() => {
    if (meQuery.isError && meQuery.error instanceof ApiError && meQuery.error.status === 401) {
      clearToken();
      window.location.reload();
    }
  }, [meQuery.isError, meQuery.error]);

  const value = useMemo<AuthState>(() => {
    if (!isAuthenticated) return ANONYMOUS;
    return {
      user: meQuery.data ?? null,
      role,
      isAdmin: role === "admin",
      isMember: role === "member",
      isAdminOrAgent: role === "admin" || role === "agent",
      isAuthenticated: true,
      isLoading: meQuery.isLoading,
    };
  }, [isAuthenticated, role, meQuery.data, meQuery.isLoading]);

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthState {
  return useContext(AuthCtx);
}
