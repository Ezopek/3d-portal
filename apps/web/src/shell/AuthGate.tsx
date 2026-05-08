import { useLocation, useNavigate } from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "@/shell/AuthContext";

export function AuthGate({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const { pathname, search } = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    if (!auth.isLoading && !auth.isAuthenticated) {
      const next = encodeURIComponent(pathname + (search ? `?${search}` : ""));
      void navigate({ to: "/login", search: { next }, replace: true });
    }
  }, [auth.isLoading, auth.isAuthenticated, navigate, pathname, search]);

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
