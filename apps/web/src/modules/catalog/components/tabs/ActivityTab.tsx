import { useTranslation } from "react-i18next";

import { useAuditLog } from "@/modules/catalog/hooks/useAuditLog";
import { EmptyState } from "@/ui/custom/EmptyState";
import { LoadingState } from "@/ui/custom/LoadingState";

interface Props {
  modelId: string;
}

export function ActivityTab({ modelId }: Props) {
  const { t } = useTranslation();
  const q = useAuditLog({ entity_type: "model", entity_id: modelId, limit: 50 });
  if (q.isLoading) return <LoadingState variant="spinner" />;
  if (q.isError) {
    return (
      <EmptyState
        messageKey="errors.audit_log"
        tone="error"
        action={{ labelKey: "common.retry", onClick: () => void q.refetch() }}
      />
    );
  }
  const items = q.data?.items ?? [];
  if (items.length === 0) {
    return <p className="p-4 text-sm text-muted-foreground">{t("catalog.empty.activity")}</p>;
  }
  return (
    <ul className="space-y-2 p-3">
      {items.map((entry) => (
        <li
          key={entry.id}
          className="flex items-start gap-3 rounded border border-border bg-card p-3 text-xs"
        >
          <span
            className={`rounded px-1.5 py-0.5 font-mono ${
              entry.action.endsWith(".create")
                ? "bg-success/20 text-success"
                : entry.action.endsWith(".delete")
                  ? "bg-destructive/20 text-destructive"
                  : "bg-primary/20 text-primary"
            }`}
          >
            {entry.action}
          </span>
          <span className="flex-1 truncate text-muted-foreground">{entry.entity_type}</span>
          <span className="text-muted-foreground">
            {entry.at.slice(0, 16).replace("T", " ")}
          </span>
        </li>
      ))}
    </ul>
  );
}
