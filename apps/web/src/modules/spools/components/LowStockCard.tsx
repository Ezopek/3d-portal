import { PackageOpen } from "lucide-react";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { useSpoolsSummary } from "@/modules/spools/hooks/useSpoolsSummary";
import {
  formatTimeOfDay,
  formatWeight,
  minutesSince,
} from "@/modules/spools/lib/format";
import {
  LOW_STOCK_LIST_CAP,
  type LowStockRow,
  selectLowStockRows,
} from "@/modules/spools/components/LowStockCard.lib";
import { Card, CardContent, CardHeader, CardTitle } from "@/ui/card";
import { EmptyState } from "@/ui/custom/EmptyState";

function LastUpdated({ iso }: { iso: string }) {
  const { t } = useTranslation();
  const time = formatTimeOfDay(iso);
  const minutes = minutesSince(iso);
  const text =
    minutes < 1
      ? t("modules.spools.index.last_updated", { time })
      : t("modules.spools.index.last_updated_with_ago", { time, ago: minutes });
  return <p className="text-xs text-muted-foreground">{text}</p>;
}

export function LowStockCard() {
  const { t } = useTranslation();
  const query = useSpoolsSummary();
  const rows = useMemo(() => {
    if (query.data === undefined) return [];
    return selectLowStockRows(query.data.spools, query.data.filaments);
  }, [query.data]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("modules.spools.lowstock.title")}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {query.isLoading ? (
          <p className="text-sm text-muted-foreground">
            {t("modules.spools.lowstock.loading")}
          </p>
        ) : query.isError ? (
          <EmptyState
            messageKey="modules.spools.lowstock.error"
            tone="error"
            icon={<PackageOpen className="size-8" />}
            action={{ labelKey: "common.retry", onClick: () => void query.refetch() }}
          />
        ) : query.data === undefined ? null : (
          <LowStockBody
            data={query.data}
            rows={rows}
            t={t}
          />
        )}
      </CardContent>
    </Card>
  );
}

interface BodyProps {
  data: NonNullable<ReturnType<typeof useSpoolsSummary>["data"]>;
  rows: LowStockRow[];
  t: (key: string, opts?: Record<string, unknown>) => string;
}

function LowStockBody({ data, rows, t }: BodyProps) {
  const visible = rows.slice(0, LOW_STOCK_LIST_CAP);
  const overflow = rows.length - visible.length;
  const hasEverSucceeded = data.last_success_ts !== null;

  if (rows.length === 0 && !hasEverSucceeded) {
    return (
      <EmptyState
        messageKey="modules.spools.lowstock.unavailable"
        tone="error"
        icon={<PackageOpen className="size-8" />}
      />
    );
  }

  if (rows.length === 0) {
    return (
      <>
        <EmptyState
          messageKey="modules.spools.lowstock.all_ok"
          tone="muted"
          icon={<PackageOpen className="size-8" />}
        />
        {data.last_success_ts !== null && <LastUpdated iso={data.last_success_ts} />}
      </>
    );
  }

  return (
    <>
      <ul className="flex flex-col gap-2">
        {visible.map(({ spool, filament }) => {
          const swatch = filament?.color_hex
            ? `#${filament.color_hex.replace(/^#/, "")}`
            : undefined;
          return (
            <li
              key={spool.id}
              className="flex items-center gap-3 rounded-md border bg-background/40 p-2"
            >
              <span
                aria-hidden
                className="size-3 shrink-0 rounded-sm border border-border"
                style={swatch !== undefined ? { backgroundColor: swatch } : undefined}
              />
              <p className="min-w-0 flex-1 truncate text-sm">
                {filament?.name ?? `#${spool.filament_id}`}
              </p>
              <p className="shrink-0 text-sm font-medium tabular-nums">
                {formatWeight(spool.remaining_weight)}
              </p>
            </li>
          );
        })}
      </ul>
      {overflow > 0 && (
        <p className="text-xs text-muted-foreground">
          {t("modules.spools.lowstock.more_count", { n: overflow })}
        </p>
      )}
      {data.last_success_ts !== null && <LastUpdated iso={data.last_success_ts} />}
    </>
  );
}
