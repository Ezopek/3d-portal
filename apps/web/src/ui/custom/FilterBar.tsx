import { useTranslation } from "react-i18next";

import { SORT_OPTIONS, type SortKey } from "@/modules/catalog/sortOptions";
import { Button } from "@/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/ui/select";
import { cn } from "@/lib/utils";

import type { Category, Status } from "@/modules/catalog/types";

export type { SortKey };

const CATEGORIES: Category[] = [
  "decorations", "printer_3d", "gridfinity", "multiboard",
  "tools", "practical", "premium", "own_models", "other",
];

const STATUSES: Status[] = ["printed", "not_printed", "in_progress", "needs_revision"];

export interface FilterState {
  category: Category | null;
  status: Status | null;
  sort: SortKey;
}

interface Props {
  state: FilterState;
  onChange: (next: FilterState) => void;
}

export function FilterBar({ state, onChange }: Props) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-2 border-b border-border bg-background/95 p-3 lg:hidden">
      <div className="flex gap-1 overflow-x-auto [mask-image:linear-gradient(to_right,black_calc(100%-2rem),transparent)]">
        <Pill
          active={state.category === null}
          onClick={() => onChange({ ...state, category: null })}
          label={t("catalog.filters.category")}
        />
        {CATEGORIES.map((c) => (
          <Pill
            key={c}
            active={state.category === c}
            onClick={() => onChange({ ...state, category: c })}
            label={t(`catalog.category.${c}`, { defaultValue: c })}
          />
        ))}
      </div>
      <div className="flex gap-1 overflow-x-auto [mask-image:linear-gradient(to_right,black_calc(100%-2rem),transparent)]">
        <Pill
          active={state.status === null}
          onClick={() => onChange({ ...state, status: null })}
          label={t("catalog.filters.status")}
        />
        {STATUSES.map((s) => (
          <Pill
            key={s}
            active={state.status === s}
            onClick={() => onChange({ ...state, status: s })}
            label={t(`catalog.status.${s}`)}
          />
        ))}
      </div>
      <Select value={state.sort} onValueChange={(v) => onChange({ ...state, sort: v as SortKey })}>
        <SelectTrigger className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {SORT_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {t(opt.labelKey)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function Pill({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <Button
      variant={active ? "default" : "outline"}
      size="sm"
      className={cn("shrink-0 text-xs")}
      onClick={onClick}
    >
      {label}
    </Button>
  );
}
