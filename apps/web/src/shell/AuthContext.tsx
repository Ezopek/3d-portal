import { useQuery } from "@tanstack/react-query";
import { createContext, useContext, useMemo, type ReactNode } from "react";

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

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthState {
  return useContext(AuthCtx);
}
