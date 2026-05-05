import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";
import { Badge } from "@/ui/badge";

import type { ModelStatus } from "@/lib/api-types";

const STYLES: Record<ModelStatus, string> = {
  printed: "border-success/40 bg-success/10 text-success",
  in_progress: "border-warning/40 bg-warning/10 text-warning",
  broken: "border-destructive/40 bg-destructive/10 text-destructive",
  not_printed: "border-border bg-muted text-muted-foreground",
};

export function StatusBadge({ status }: { status: ModelStatus }) {
  const { t } = useTranslation();
  return (
    <Badge variant="outline" className={cn("text-xs", STYLES[status])}>
      {t(`catalog.status.${status}`, { defaultValue: status })}
    </Badge>
  );
}
