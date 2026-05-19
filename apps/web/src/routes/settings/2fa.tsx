import { createFileRoute } from "@tanstack/react-router";

import { Settings2faPage } from "@/modules/auth/Settings2faPage";
import { AuthGate } from "@/shell/AuthGate";

export const Route = createFileRoute("/settings/2fa")({
  component: () => (
    <AuthGate>
      <Settings2faPage />
    </AuthGate>
  ),
});
