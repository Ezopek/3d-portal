import { useTranslation } from "react-i18next";

import type { ModelSource, ModelStatus, TagRead } from "@/lib/api-types";
import { SearchSuggest } from "@/modules/catalog/components/SearchSuggest";
import type { ModelListSort } from "@/modules/catalog/hooks/useModels";
import type { TagMatch } from "@/routes/catalog/index";

export interface FilterRibbonState {
  q: string;
  tag_ids: string[];
  tag_match?: TagMatch;
  status: ModelStatus | undefined;
  source: ModelSource | undefined;
  sort: ModelListSort;
}

interface Props {
  state: FilterRibbonState;
  tagsById: Map<string, TagRead>;
  onChange: (next: FilterRibbonState) => void;
}

// Story 52.1 D-1 — after the Filters-panel consolidation this component holds
// exactly three things, all of them ACTIVE-CONSTRAINT DISPLAY, which
// EXPERIENCE.md:347 requires to stay visible OUTSIDE the panel: the search
// input, the selected-tag chips with their remove buttons, and the ≥2-tag
// match-mode toggle. The `+tag` picker, the status/source/sort Selects, the
// mobile Filters sheet and the `(n)` badge all moved to `FiltersPanel`.
export function FilterRibbon({ state, tagsById, onChange }: Props) {
  const { t } = useTranslation();
  const matchMode = state.tag_match ?? "all";
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-border bg-background/95 p-3">
      <SearchSuggest
        q={state.q}
        tagIds={state.tag_ids}
        onQueryChange={(q) => onChange({ ...state, q })}
        onSelectTag={(tagId) => onChange({ ...state, tag_ids: [...state.tag_ids, tagId], q: "" })}
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
        {state.tag_ids.length >= 2 && (
          <div
            role="group"
            aria-label={t("catalog.filters.matchMode")}
            className="flex items-center rounded-md border border-border"
          >
            {(["all", "any"] as const).map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={matchMode === value}
                onClick={() => onChange({ ...state, tag_match: value })}
                className={
                  matchMode === value
                    ? "rounded-md px-2 py-0.5 text-xs bg-primary text-primary-foreground"
                    : "rounded-md px-2 py-0.5 text-xs text-muted-foreground hover:bg-accent"
                }
              >
                {value === "all" ? t("catalog.filters.matchAll") : t("catalog.filters.matchAny")}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
