import { createFileRoute } from "@tanstack/react-router";

import { ComingSoonStub } from "@/ui/custom/ComingSoonStub";

export const Route = createFileRoute("/queue/")({
  component: () => <ComingSoonStub moduleKey="queue" />,
});
