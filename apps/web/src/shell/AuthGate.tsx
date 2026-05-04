import type { ReactNode } from "react";

import { useAuth } from "@/shell/AuthContext";

export function AuthGate({ children, fallback = null }: { children: ReactNode; fallback?: ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <>{fallback}</>;
  return <>{children}</>;
}
