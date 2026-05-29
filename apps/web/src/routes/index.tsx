import { createFileRoute } from "@tanstack/react-router";

import { LandingPage } from "@/modules/landing/LandingPage";

// Story 31.4 (Init 19) — graduates the redirect-to-/catalog stub into a real
// landing surface now that two modules ship real implementations (catalog +
// spools). Hosts the LowStockCard for the FR19-LOWSTOCK-1 demoable signal.
export const Route = createFileRoute("/")({
  component: LandingPage,
});
