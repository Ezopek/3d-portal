import { Badge } from "@/ui/badge";

import type { ModelSource } from "@/lib/api-types";

const LABEL: Record<ModelSource, string> = {
  printables: "Printables",
  thangs: "Thangs",
  thingiverse: "Thingi",
  makerworld: "MakerW",
  cults3d: "Cults3D",
  own: "Own",
  other: "Other",
  unknown: "",
};

export function SourceBadge({ source }: { source: ModelSource }) {
  if (source === "unknown") return null;
  return (
    <Badge
      variant="secondary"
      className="text-xs whitespace-nowrap"
    >
      {LABEL[source]}
    </Badge>
  );
}
