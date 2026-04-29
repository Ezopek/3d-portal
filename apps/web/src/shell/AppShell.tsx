import { useLocation } from "@tanstack/react-router";
import type { ReactNode } from "react";

import { ModuleRail } from "./ModuleRail";
import { TopBar } from "./TopBar";

export function AppShell({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  // Share view bypasses the shell entirely.
  if (pathname.startsWith("/share/")) {
    return <>{children}</>;
  }
  return (
    <div className="flex min-h-screen">
      <ModuleRail />
      <div className="flex min-h-screen flex-1 flex-col">
        <TopBar />
        <main className="flex-1 pb-16 lg:pb-0">{children}</main>
      </div>
    </div>
  );
}
