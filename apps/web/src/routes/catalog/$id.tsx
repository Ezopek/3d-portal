import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/catalog/$id")({
  component: () => <div className="p-4">Catalog detail (Phase 8)</div>,
});
