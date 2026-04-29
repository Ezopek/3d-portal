import { createFileRoute } from "@tanstack/react-router";

import { ComingSoonStub } from "@/ui/custom/ComingSoonStub";

export const Route = createFileRoute("/printer/")({
  component: () => <ComingSoonStub moduleKey="printer" />,
});
