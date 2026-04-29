import type { ReactNode } from "react";

import { readToken } from "@/lib/auth";

export function AuthGate({ children, fallback = null }: { children: ReactNode; fallback?: ReactNode }) {
  const token = readToken();
  if (token === null) return <>{fallback}</>;
  return <>{children}</>;
}
