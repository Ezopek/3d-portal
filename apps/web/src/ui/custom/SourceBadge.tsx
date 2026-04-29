import { Badge } from "@/ui/badge";

import type { Source } from "@/modules/catalog/types";

export function SourceBadge({ source }: { source: Source }) {
  if (source === "unknown") return null;
  return <Badge variant="secondary" className="text-xs">{source}</Badge>;
}
