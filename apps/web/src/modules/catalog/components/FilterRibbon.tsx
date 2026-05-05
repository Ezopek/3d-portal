import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { ModelSource, ModelStatus, TagRead } from "@/lib/api-types";
import { useTags } from "@/modules/catalog/hooks/useTags";
import type { ModelListSort } from "@/modules/catalog/hooks/useModels";
import { Button } from "@/ui/button";
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

export function FilterRibbon({ state, tagsById, onChange }: Props) {
  const { t } = useTranslation();
  const [tagPickerOpen, setTagPickerOpen] = useState(false);
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
                aria-label={`remove tag ${label}`}
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
        />
      )}
      <Select
        value={state.status ?? ANY_STATUS}
        onValueChange={(v) =>
          onChange({ ...state, status: v === ANY_STATUS ? undefined : (v as ModelStatus) })
        }
      >
        <SelectTrigger className="w-36" aria-label={t("catalog.filters.status")}>
          <SelectValue />
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
        <SelectTrigger className="w-36" aria-label={t("catalog.filters.source")}>
          <SelectValue />
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
        <SelectTrigger className="w-36" aria-label={t("catalog.filters.sort")}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {SORT_VALUES.map((s) => (
            <SelectItem key={s} value={s}>
              {t(`catalog.sort.${s}`, { defaultValue: s })}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function TagPicker({ selected, onAdd }: { selected: string[]; onAdd: (id: string) => void }) {
  const [q, setQ] = useState("");
  const tagsQuery = useTags(q);
  const items = (tagsQuery.data ?? []).filter((t) => !selected.includes(t.id));
  return (
    <div className="absolute z-50 mt-1 w-64 rounded border border-border bg-card p-2 shadow">
      <Input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search tag…"
        className="mb-2 text-xs"
      />
      <div className="max-h-48 space-y-1 overflow-y-auto">
        {items.length === 0 && (
          <p className="text-xs text-muted-foreground">No matches</p>
        )}
        {items.map((tag) => (
          <button
            key={tag.id}
            type="button"
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
