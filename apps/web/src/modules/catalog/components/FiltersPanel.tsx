import { SlidersHorizontal } from "lucide-react";
import { useSyncExternalStore } from "react";
import { useTranslation } from "react-i18next";

import type {
  ModelSource,
  ModelStatus,
  TagGroupRead,
  TagReadWithCount,
} from "@/lib/api-types";
import { cn } from "@/lib/utils";
import { FacetSidebar } from "@/modules/catalog/components/FacetSidebar";
import type { FilterRibbonState } from "@/modules/catalog/components/FilterRibbon";
import type { ModelListSort } from "@/modules/catalog/hooks/useModels";
import { Button } from "@/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/ui/select";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/ui/sheet";

const STATUS_VALUES: ModelStatus[] = ["not_printed", "printed", "in_progress", "broken"];
const SOURCE_VALUES: ModelSource[] = [
  "unknown",
  "printables",
  "thangs",
  "makerworld",
  "cults3d",
  "thingiverse",
  "crealitycloud",
  "own",
  "other",
];
const SORT_VALUES: ModelListSort[] = ["recent", "oldest", "name_asc", "name_desc", "status", "rating"];

const ANY_STATUS = "__any_status__";
const ANY_SOURCE = "__any_source__";

// Story 52.1 D-6 — the `lg` regime boundary EXPERIENCE.md:330 names: at `lg`+
// the Filters surface is a RIGHT panel, below it a BOTTOM sheet. 1024 is the
// Tailwind `lg` breakpoint the rest of this epic already keys on
// (`BrowseRail`'s `lg:flex`, `BrowseSheet`'s `lg:hidden`), so this constant
// points at the contract rather than copying a neighbouring file's number.
//
// Deliberately file-local (D-6 / §5): a shared `@/lib` hook is a wider blast
// radius than this story needs, and no second consumer exists.
const LG_MEDIA_QUERY = "(min-width: 1024px)";

function matchMediaAvailable(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function";
}

function subscribeToLgRegime(onStoreChange: () => void): () => void {
  if (!matchMediaAvailable()) return () => {};
  const mql = window.matchMedia(LG_MEDIA_QUERY);
  mql.addEventListener("change", onStoreChange);
  return () => mql.removeEventListener("change", onStoreChange);
}

// jsdom does not implement `matchMedia`, so the fallback must be a plain
// branch returning the compact regime — NOT an optional chain yielding
// `undefined`, which `useSyncExternalStore` would treat as a changing snapshot.
function readLgRegime(): boolean {
  if (!matchMediaAvailable()) return false;
  return window.matchMedia(LG_MEDIA_QUERY).matches;
}

function readLgRegimeOnServer(): boolean {
  return false;
}

function useIsDesktopRegime(): boolean {
  return useSyncExternalStore(subscribeToLgRegime, readLgRegime, readLgRegimeOnServer);
}

/**
 * Story 52.1 D-2 — the `(n)` contract, verbatim per EXPERIENCE.md:227:
 *
 *   n = tag_ids.length + untagged + status + source
 *
 * `sort` is an ordering, not a constraint. `tag_match` modifies an
 * already-counted set. `q` has its own visible surface. The browse category is
 * structurally unreachable from here (D-7) — this component receives no scope
 * prop at all, so the scope cannot be counted even by mistake.
 */
function activeFilterCount(state: FilterRibbonState, untaggedActive: boolean): number {
  return (
    state.tag_ids.length +
    (untaggedActive ? 1 : 0) +
    (state.status !== undefined ? 1 : 0) +
    (state.source !== undefined ? 1 : 0)
  );
}

interface Props {
  state: FilterRibbonState;
  onChange: (next: FilterRibbonState) => void;
  groups: TagGroupRead[];
  groupless: TagReadWithCount[];
  onToggleTag: (id: string) => void;
  untaggedActive: boolean;
  onToggleUntagged: () => void;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// Story 52.1 D-1 — the ONE canonical refinement surface. It replaces three
// shipped controls: the all-viewport "Tagi" facet sheet, the `md:hidden`
// "Filtry" select sheet and the desktop inline select row. One `Sheet` mount
// with a responsive `side` (D-6), never two breakpoint-gated mounts — that
// would duplicate the whole subtree (and its test ids) in the DOM.
//
// The panel takes `onChange` (the three Selects) and `onToggleTag` /
// `onToggleUntagged` (the facet list) as SEPARATE props and passes each
// straight through: merging them would move `tag_match` normalisation out of
// the route's `validateSearch` and into this component (D-11).
export function FiltersPanel({
  state,
  onChange,
  groups,
  groupless,
  onToggleTag,
  untaggedActive,
  onToggleUntagged,
  open,
  onOpenChange,
}: Props) {
  const { t } = useTranslation();
  const isDesktop = useIsDesktopRegime();
  const count = activeFilterCount(state, untaggedActive);
  // D-10 — the count belongs in the ACCESSIBLE NAME, not only in a visual
  // badge: a screen-reader user must hear "Filtry (3)", never a bare "Filtry".
  const triggerName =
    count > 0
      ? t("catalog.filters.openFiltersWithCount", { count })
      : t("catalog.filters.openFilters");

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetTrigger
        render={
          // Not breakpoint-gated (AC-1a): unlike Browse, whose desktop rail
          // already covers `lg`+, this is the only refinement control at every
          // viewport. `flex-1` below `lg` keeps the shipped full-bar geometry
          // the retired Tagi trigger held; at `lg`+ it shrinks to its label.
          <Button
            variant="outline"
            size="sm"
            className="flex-1 justify-start lg:w-auto lg:flex-none"
            aria-label={triggerName}
          >
            <SlidersHorizontal className="size-3.5" aria-hidden />
            <span className="ml-1.5">{t("catalog.filters.openFilters")}</span>
            {/* Omitted ENTIRELY at n === 0 (EXPERIENCE.md:204, DESIGN.md:279)
                — never a "0", never a hidden-but-present node. `aria-hidden`
                because `triggerName` already announces the count once. */}
            {count > 0 && (
              <span
                aria-hidden
                data-testid="filters-trigger-badge"
                className="ml-1 rounded-full bg-primary px-1.5 text-[10px] font-medium text-primary-foreground"
              >
                {count}
              </span>
            )}
          </Button>
        }
      />
      <SheetContent
        side={isDesktop ? "right" : "bottom"}
        // D-6 geometry: the shipped facet-sheet width vocabulary at `lg`+, the
        // shipped bottom-sheet vocabulary below it. No new size token.
        className={cn(
          "overflow-y-auto p-0",
          isDesktop ? "w-80 max-w-[85vw]" : "max-h-[80vh]",
        )}
      >
        <SheetHeader>
          <SheetTitle>{t("catalog.filters.title")}</SheetTitle>
        </SheetHeader>
        {/* EXPERIENCE.md:228 fixes this order: the facet surface first (group
            search → collapsible groups with per-tag counts → trailing
            `Bez tagów` row), THEN status, source, sort.

            `FacetSidebar` is RELOCATED, not rewritten (D-8): it already ships
            in-panel tag search, collapse persistence under
            `catalog:facet-collapse` and the groupless section. `untaggedCount`
            stays unpassed — no endpoint supplies it (D-9).

            No loading/skeleton/error branch here: `CatalogList` already guards
            on `tagGroups.data === undefined` before this ever mounts (D-1). */}
        <FacetSidebar
          groups={groups}
          groupless={groupless}
          selectedTagIds={state.tag_ids}
          onToggleTag={onToggleTag}
          untaggedActive={untaggedActive}
          onToggleUntagged={onToggleUntagged}
          mobile
        />
        <div className="grid gap-3 border-t border-border bg-card p-4">
          <FilterSelects state={state} onChange={onChange} />
        </div>
      </SheetContent>
    </Sheet>
  );
}

// Moved verbatim from `FilterRibbon.tsx` (D-1): same three Selects, same
// ANY_STATUS/ANY_SOURCE sentinels, same aria-labels, same SelectValue render
// props. A file move, not a rewrite. `fullWidth` is gone with the move — inside
// the panel every trigger is full width, which is what the shipped mobile
// Filters sheet already did.
function FilterSelects({
  state,
  onChange,
}: {
  state: FilterRibbonState;
  onChange: (next: FilterRibbonState) => void;
}) {
  const { t } = useTranslation();
  return (
    <>
      <Select
        value={state.status ?? ANY_STATUS}
        onValueChange={(v) =>
          onChange({ ...state, status: v === ANY_STATUS ? undefined : (v as ModelStatus) })
        }
      >
        <SelectTrigger className="w-full" aria-label={t("catalog.filters.status")}>
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
        <SelectTrigger className="w-full" aria-label={t("catalog.filters.source")}>
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
        <SelectTrigger className="w-full" aria-label={t("catalog.filters.sort")}>
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
