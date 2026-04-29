import { createFileRoute } from "@tanstack/react-router";

function DevComponents() {
  return (
    <div className="p-4">
      <h1 className="text-xl font-semibold">Component playground</h1>
      <p className="text-sm text-muted-foreground">
        Phase 7 stub. Phase 10 fills with full primitive grid.
      </p>
    </div>
  );
}

export const Route = createFileRoute("/dev/components")({ component: DevComponents });
