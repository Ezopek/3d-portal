import { createFileRoute } from "@tanstack/react-router";

import { CatalogDetail } from "@/modules/catalog/routes/CatalogDetail";
import { AuthGate } from "@/shell/AuthGate";

// Post-Init-5 cutover: catalog detail requires member-or-admin auth.
export const Route = createFileRoute("/catalog/$id")({
  component: () => (
    <AuthGate>
      <CatalogDetail />
    </AuthGate>
  ),
});
