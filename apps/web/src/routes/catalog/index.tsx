import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/catalog/")({
  component: () => <div className="p-4">Catalog list (Phase 8)</div>,
});
