import { StatusBadge } from "portal-web";

export function AllStatuses() {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <StatusBadge status="printed" />
      <StatusBadge status="in_progress" />
      <StatusBadge status="broken" />
      <StatusBadge status="not_printed" />
    </div>
  );
}
