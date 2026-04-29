import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";
import type { Category, ModelListItem, Status } from "@/modules/catalog/types";

import type { FilterState } from "@/ui/custom/FilterBar";

interface Props {
  models: readonly ModelListItem[];
  state: FilterState;
  onChange: (next: FilterState) => void;
}

export function CategorySidebar({ models, state, onChange }: Props) {
  const { t } = useTranslation();
  const counts = countBy(models, "category") as Record<Category, number>;
  const statusCounts = countBy(models, "status") as Record<Status, number>;
  const topTags = topN(models.flatMap((m) => m.tags), 12);

  return (
    <aside className="hidden w-60 shrink-0 border-r border-border bg-card p-4 lg:block">
      <Group label={t("catalog.filters.category")}>
        <Row
          label="All"
          count={models.length}
          active={state.category === null}
          onClick={() => onChange({ ...state, category: null })}
        />
        {(Object.keys(counts) as Category[]).map((c) => (
          <Row
            key={c}
            label={t(`catalog.category.${c}`, { defaultValue: c })}
            count={counts[c]}
            active={state.category === c}
            onClick={() => onChange({ ...state, category: c })}
          />
        ))}
      </Group>
      <Group label={t("catalog.filters.status")}>
        {(Object.keys(statusCounts) as Status[]).map((s) => (
          <Row
            key={s}
            label={t(`catalog.status.${s}`)}
            count={statusCounts[s]}
            active={state.status === s}
            onClick={() => onChange({ ...state, status: state.status === s ? null : s })}
          />
        ))}
      </Group>
      <Group label={t("catalog.filters.tags")}>
        <div className="flex flex-wrap gap-1">
          {topTags.map(([tag, count]) => (
            <span key={tag} className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
              {tag} · {count}
            </span>
          ))}
        </div>
      </Group>
    </aside>
  );
}

function Group({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-6">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</h3>
      <ul className="space-y-1">{children}</ul>
    </div>
  );
}

function Row({ label, count, active, onClick }: { label: string; count: number; active: boolean; onClick: () => void }) {
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        className={cn(
          "flex w-full items-center justify-between rounded px-2 py-1 text-left text-sm",
          active ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground",
        )}
      >
        <span>{label}</span>
        <span className="text-xs">{count}</span>
      </button>
    </li>
  );
}

function countBy<T, K extends keyof T>(items: readonly T[], key: K): Record<string, number> {
  const out: Record<string, number> = {};
  for (const item of items) {
    const k = String(item[key]);
    out[k] = (out[k] ?? 0) + 1;
  }
  return out;
}

function topN(values: string[], n: number): [string, number][] {
  const counts = new Map<string, number>();
  for (const v of values) counts.set(v, (counts.get(v) ?? 0) + 1);
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, n);
}
