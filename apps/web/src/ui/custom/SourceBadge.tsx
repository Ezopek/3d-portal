import { Badge } from "@/ui/badge";

import type { Source } from "@/modules/catalog/types";

const LABEL: Record<Source, string> = {
  printables: "Printables",
  thangs: "Thangs",
  thingiverse: "Thingi",
  makerworld: "MakerW",
  creality_cloud: "Creality",
  own: "Own",
  premium: "Premium",
  unknown: "",
};

export function SourceBadge({ source }: { source: Source }) {
  if (source === "unknown") return null;
  return (
    <Badge
      variant="secondary"
      className="text-xs whitespace-nowrap max-w-[7ch] truncate"
    >
      {LABEL[source]}
    </Badge>
  );
}
