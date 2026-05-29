import { Boxes, RefreshCw } from "lucide-react";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { useSpoolsSummary } from "@/modules/spools/hooks/useSpoolsSummary";
import { formatTimeOfDay, formatWeight, minutesSince } from "@/modules/spools/lib/format";
import type { FilamentView, SpoolView, VendorView } from "@/lib/api-types";
import { cn } from "@/lib/utils";
import { Badge } from "@/ui/badge";
import { Button } from "@/ui/button";
import { EmptyState } from "@/ui/custom/EmptyState";

interface SortedRow {
  spool: SpoolView;
  filament: FilamentView | undefined;
  vendor: VendorView | undefined;
}

function buildRows(
  spools: SpoolView[],
  filaments: FilamentView[],
  vendors: VendorView[],
): SortedRow[] {
  const filamentById = new Map(filaments.map((f) => [f.id, f]));
  const vendorById = new Map(vendors.map((v) => [v.id, v]));
  const rows: SortedRow[] = spools.map((spool) => {
    const filament = filamentById.get(spool.filament_id);
    const vendor =
      filament?.vendor_id != null ? vendorById.get(filament.vendor_id) : undefined;
    return { spool, filament, vendor };
  });
  rows.sort((a, b) => {
    if (a.spool.archived !== b.spool.archived) {
      return a.spool.archived ? 1 : -1;
    }
    const aw = a.spool.remaining_weight ?? -1;
    const bw = b.spool.remaining_weight ?? -1;
    return bw - aw;
  });
  return rows;
}

function PercentRemaining(spool: SpoolView): number | null {
  if (spool.remaining_weight === null || spool.initial_weight === null) return null;
  if (spool.initial_weight <= 0) return null;
  const pct = (spool.remaining_weight / spool.initial_weight) * 100;
  return Math.max(0, Math.min(100, pct));
}

function SpoolRow({ row }: { row: SortedRow }) {
  const { t } = useTranslation();
  const { spool, filament, vendor } = row;
  const pct = PercentRemaining(spool);
  const swatch = filament?.color_hex
    ? `#${filament.color_hex.replace(/^#/, "")}`
    : undefined;
  const secondary = [vendor?.name, filament?.material].filter(Boolean).join(" · ");
  return (
    <li
      className={cn(
        "flex items-center gap-4 rounded-md border bg-card p-3",
        spool.archived && "opacity-50",
      )}
    >
      <span
        aria-hidden
        className="size-4 shrink-0 rounded-sm border border-border"
        style={swatch !== undefined ? { backgroundColor: swatch } : undefined}
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="truncate text-sm font-medium">
            {filament?.name ?? `#${spool.filament_id}`}
          </p>
          {spool.archived && (
            <Badge variant="outline" className="text-[10px] uppercase">
              {t("modules.spools.index.archived_badge")}
            </Badge>
          )}
        </div>
        {secondary !== "" && (
          <p className="truncate text-xs text-muted-foreground">{secondary}</p>
        )}
        {pct !== null && (
          <div
            className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(pct)}
          >
            <div className="h-full bg-primary" style={{ width: `${pct}%` }} />
          </div>
        )}
      </div>
      <div className="shrink-0 text-right text-xs tabular-nums text-muted-foreground">
        {formatWeight(spool.remaining_weight)}
        <span className="mx-1">/</span>
        {formatWeight(spool.initial_weight)}
      </div>
    </li>
  );
}

export function SpoolsIndexPage() {
  const { t } = useTranslation();
  const query = useSpoolsSummary();
  const rows = useMemo(() => {
    if (query.data === undefined) return [];
    return buildRows(query.data.spools, query.data.filaments, query.data.vendors);
  }, [query.data]);

  if (query.isLoading) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-4 px-6 py-10">
        <h1 className="text-2xl font-semibold">{t("modules.spools.index.title")}</h1>
        <p className="text-sm text-muted-foreground">
          {t("modules.spools.index.loading")}
        </p>
      </div>
    );
  }

  if (query.isError) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-4 px-6 py-10">
        <h1 className="text-2xl font-semibold">{t("modules.spools.index.title")}</h1>
        <EmptyState
          messageKey="modules.spools.states.error"
          tone="error"
          icon={<Boxes className="size-10" />}
          action={{ labelKey: "common.retry", onClick: () => void query.refetch() }}
        />
      </div>
    );
  }

  const data = query.data!;
  const hasSpools = data.spools.length > 0;
  const hasEverSucceeded = data.last_success_ts !== null;

  if (!hasSpools && !hasEverSucceeded) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-4 px-6 py-10">
        <h1 className="text-2xl font-semibold">{t("modules.spools.index.title")}</h1>
        <EmptyState
          messageKey="modules.spools.states.unavailable"
          tone="error"
          icon={<RefreshCw className="size-10" />}
        />
      </div>
    );
  }

  if (!hasSpools) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-4 px-6 py-10">
        <h1 className="text-2xl font-semibold">{t("modules.spools.index.title")}</h1>
        {data.last_success_ts !== null && (
          <p className="text-xs text-muted-foreground">
            {(() => {
              const time = formatTimeOfDay(data.last_success_ts);
              const minutes = minutesSince(data.last_success_ts);
              if (minutes < 1) {
                return t("modules.spools.index.last_updated", { time });
              }
              return t("modules.spools.index.last_updated_with_ago", {
                time,
                count: minutes,
              });
            })()}
          </p>
        )}
        <EmptyState
          messageKey="modules.spools.states.empty"
          tone="muted"
          icon={<Boxes className="size-10" />}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4 px-6 py-10">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="text-2xl font-semibold">{t("modules.spools.index.title")}</h1>
        {data.last_success_ts !== null && (
          <p className="text-xs text-muted-foreground">
            {(() => {
              const time = formatTimeOfDay(data.last_success_ts);
              const minutes = minutesSince(data.last_success_ts);
              if (minutes < 1) {
                return t("modules.spools.index.last_updated", { time });
              }
              return t("modules.spools.index.last_updated_with_ago", {
                time,
                count: minutes,
              });
            })()}
          </p>
        )}
      </div>
      <ul className="flex flex-col gap-2">
        {rows.map((row) => (
          <SpoolRow key={row.spool.id} row={row} />
        ))}
      </ul>
      <div className="flex justify-end">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => void query.refetch()}
          aria-label={t("common.retry")}
        >
          <RefreshCw className="mr-1 size-3" />
          {t("common.retry")}
        </Button>
      </div>
    </div>
  );
}
