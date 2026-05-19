import { createFileRoute } from "@tanstack/react-router";

import { Settings2faPage } from "@/modules/auth/Settings2faPage";
import { AuthGate } from "@/shell/AuthGate";

interface Settings2faSearch {
  next?: string;
}

export const Route = createFileRoute("/settings/2fa")({
  component: () => (
    <AuthGate>
      <Settings2faPage />
    </AuthGate>
  ),
  validateSearch: (raw: Record<string, unknown>): Settings2faSearch => {
    return typeof raw.next === "string" && raw.next.length > 0
      ? { next: raw.next }
      : {};
  },
});
