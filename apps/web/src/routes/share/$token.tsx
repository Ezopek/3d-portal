import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/share/$token")({
  component: () => <div className="p-4">Share view (Phase 9)</div>,
});
