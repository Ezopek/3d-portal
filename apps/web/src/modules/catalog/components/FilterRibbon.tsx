import { SlidersHorizontal } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import type { ModelSource, ModelStatus, TagRead } from "@/lib/api-types";
import { useTags } from "@/modules/catalog/hooks/useTags";
import type { ModelListSort } from "@/modules/catalog/hooks/useModels";
import { Button } from "@/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/ui/sheet";
import { Input } from "@/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/ui/select";

const STATUS_VALUES: ModelStatus[] = ["not_printed", "printed", "in_progress", "broken"];
const SOURCE_VALUES: ModelSource[] = [
  "unknown",
  "printables",
  "thangs",
  "makerworld",
  "cults3d",
  "thingiverse",
  "own",
  "other",
];
const SORT_VALUES: ModelListSort[] = ["recent", "oldest", "name_asc", "name_desc", "status", "rating"];

const ANY_STATUS = "__any_status__";
const ANY_SOURCE = "__any_source__";

export interface FilterRibbonState {
  q: string;
  tag_ids: string[];
  status: ModelStatus | undefined;
  source: ModelSource | undefined;
  sort: ModelListSort;
}

interface Props {
  state: FilterRibbonState;
  tagsById: Map<string, TagRead>;
  onChange: (next: FilterRibbonState) => void;
}

function activeFilterCount(state: FilterRibbonState): number {
  let n = 0;
  if (state.status !== undefined) n += 1;
  if (state.source !== undefined) n += 1;
  if (state.sort !== "recent") n += 1;
  return n;
}

export function FilterRibbon({ state, tagsById, onChange }: Props) {
  const { t } = useTranslation();
  const [tagPickerOpen, setTagPickerOpen] = useState(false);
  const [filtersSheetOpen, setFiltersSheetOpen] = useState(false);
  const activeCount = activeFilterCount(state);
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-border bg-background/95 p-3">
      <Input
        value={state.q}
        onChange={(e) => onChange({ ...state, q: e.target.value })}
        placeholder={t("common.search")}
        className="min-w-[160px] flex-1"
      />
      <div className="flex flex-wrap items-center gap-1">
        {state.tag_ids.map((tid) => {
          const tag = tagsById.get(tid);
          const label = tag?.slug ?? tid.slice(0, 6);
          return (
            <span
              key={tid}
              data-testid="tag-chip"
              className="flex items-center gap-1 rounded bg-accent px-2 py-0.5 text-xs text-accent-foreground"
            >
              {label}
              <button
                type="button"
                aria-label={t("catalog.tags.removeTag", { name: label })}
                onClick={() =>
                  onChange({ ...state, tag_ids: state.tag_ids.filter((x) => x !== tid) })
                }
              >
                ×
              </button>
            </span>
          );
        })}
        <Button
          variant="outline"
          size="sm"
          className="h-6 text-xs"
          onClick={() => setTagPickerOpen((v) => !v)}
        >
          {tagPickerOpen ? t("common.cancel") : t("catalog.actions.addTag")}
        </Button>
      </div>
      {tagPickerOpen && (
        <TagPicker
          selected={state.tag_ids}
          onAdd={(tid) => {
            onChange({ ...state, tag_ids: [...state.tag_ids, tid] });
            setTagPickerOpen(false);
          }}
          onClose={() => setTagPickerOpen(false)}
        />
      )}

      {/* Mobile: collapse status/source/sort into a Filters sheet */}
      <Sheet open={filtersSheetOpen} onOpenChange={setFiltersSheetOpen}>
        <SheetTrigger
          render={
            <Button
              variant="outline"
              size="sm"
              className="md:hidden"
              aria-label={t("catalog.filters.openFilters")}
            >
              <SlidersHorizontal className="size-3.5" aria-hidden />
              <span className="ml-1.5">{t("catalog.filters.openFilters")}</span>
              {activeCount > 0 && (
                <span className="ml-1 rounded-full bg-primary px-1.5 text-[10px] font-medium text-primary-foreground">
                  {activeCount}
                </span>
              )}
            </Button>
          }
        />
        <SheetContent side="bottom" className="max-h-[80vh] overflow-y-auto">
          <SheetHeader>
            <SheetTitle>{t("catalog.filters.title")}</SheetTitle>
          </SheetHeader>
          <div className="grid gap-3 p-4">
            <FilterSelects state={state} onChange={onChange} fullWidth />
          </div>
        </SheetContent>
      </Sheet>

      {/* Desktop: inline selects */}
      <div className="hidden flex-wrap items-center gap-2 md:flex">
        <FilterSelects state={state} onChange={onChange} />
      </div>
    </div>
  );
}

function FilterSelects({
  state,
  onChange,
  fullWidth = false,
}: {
  state: FilterRibbonState;
  onChange: (next: FilterRibbonState) => void;
  fullWidth?: boolean;
}) {
  const { t } = useTranslation();
  const triggerWidth = fullWidth ? "w-full" : "w-36";
  return (
    <>
      <Select
        value={state.status ?? ANY_STATUS}
        onValueChange={(v) =>
          onChange({ ...state, status: v === ANY_STATUS ? undefined : (v as ModelStatus) })
        }
      >
        <SelectTrigger className={triggerWidth} aria-label={t("catalog.filters.status")}>
          <SelectValue>
            {(value) =>
              value === ANY_STATUS || value === null || value === undefined
                ? t("catalog.filters.anyStatus")
                : t(`catalog.status.${value as ModelStatus}`, { defaultValue: value as string })
            }
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ANY_STATUS}>{t("catalog.filters.anyStatus")}</SelectItem>
          {STATUS_VALUES.map((s) => (
            <SelectItem key={s} value={s}>
              {t(`catalog.status.${s}`, { defaultValue: s })}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select
        value={state.source ?? ANY_SOURCE}
        onValueChange={(v) =>
          onChange({ ...state, source: v === ANY_SOURCE ? undefined : (v as ModelSource) })
        }
      >
        <SelectTrigger className={triggerWidth} aria-label={t("catalog.filters.source")}>
          <SelectValue>
            {(value) =>
              value === ANY_SOURCE || value === null || value === undefined
                ? t("catalog.filters.anySource")
                : (value as string)
            }
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ANY_SOURCE}>{t("catalog.filters.anySource")}</SelectItem>
          {SOURCE_VALUES.map((s) => (
            <SelectItem key={s} value={s}>
              {s}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select
        value={state.sort}
        onValueChange={(v) => onChange({ ...state, sort: v as ModelListSort })}
      >
        <SelectTrigger className={triggerWidth} aria-label={t("catalog.filters.sort")}>
          <SelectValue>
            {(value) =>
              value === null || value === undefined
                ? t("catalog.sort.recent")
                : t(`catalog.sort.${value as ModelListSort}`, { defaultValue: value as string })
            }
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {SORT_VALUES.map((s) => (
            <SelectItem key={s} value={s}>
              {t(`catalog.sort.${s}`, { defaultValue: s })}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </>
  );
}

function TagPicker({
  selected,
  onAdd,
  onClose,
}: {
  selected: string[];
  onAdd: (id: string) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [q, setQ] = useState("");
  const tagsQuery = useTags(q);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const items = (tagsQuery.data ?? []).filter((tag) => !selected.includes(tag.id));

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    }
    function onClick(e: MouseEvent) {
      if (
        containerRef.current &&
        e.target instanceof Node &&
        !containerRef.current.contains(e.target)
      ) {
        onClose();
      }
    }
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [onClose]);

  return (
    <div
      ref={containerRef}
      role="dialog"
      aria-label={t("catalog.tags.pickerTitle")}
      className="absolute z-50 mt-1 w-64 rounded border border-border bg-card p-2 shadow-lg"
    >
      <Input
        ref={inputRef}
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder={t("catalog.tags.searchPlaceholder")}
        className="mb-2 text-xs"
      />
      <div className="max-h-48 space-y-1 overflow-y-auto" role="listbox">
        {items.length === 0 && (
          <p className="text-xs text-muted-foreground">{t("catalog.tags.noMatches")}</p>
        )}
        {items.map((tag) => (
          <button
            key={tag.id}
            type="button"
            role="option"
            aria-selected={false}
            onClick={() => onAdd(tag.id)}
            className="block w-full rounded px-2 py-1 text-left text-xs hover:bg-accent"
          >
            {tag.slug}
          </button>
        ))}
      </div>
    </div>
  );
}
