import { createFileRoute } from "@tanstack/react-router";

import { SpoolsIndexPage } from "@/modules/spools/components/SpoolsIndexPage";

export const Route = createFileRoute("/spools/")({
  component: SpoolsIndexPage,
});
