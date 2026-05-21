import { createFileRoute } from "@tanstack/react-router";

import { Settings2faPage } from "@/modules/auth/Settings2faPage";

interface Settings2faSearch {
  next?: string;
}

export const Route = createFileRoute("/settings/2fa")({
  // Initiative 6 Story 11.3 — shell-level AuthGate (AppShell.tsx Decision O)
  // handles the anonymous redirect; per-route wrapper removed.
  component: Settings2faPage,
  validateSearch: (raw: Record<string, unknown>): Settings2faSearch => {
    return typeof raw.next === "string" && raw.next.length > 0
      ? { next: raw.next }
      : {};
  },
});
