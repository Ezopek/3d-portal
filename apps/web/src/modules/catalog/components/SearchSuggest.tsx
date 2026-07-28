import { Plus, Search } from "lucide-react";
import { useId, useMemo, useState } from "react";
import type { ChangeEvent, KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

import type { TagGroupRead, TagListItem } from "@/lib/api-types";
import { useTagGroups } from "@/modules/catalog/hooks/useTagGroups";
import { useTags } from "@/modules/catalog/hooks/useTags";
import { Input } from "@/ui/input";

// D-3 — combined list (plain-query row + tag rows) capped at 8; tag rows
// sliced to 7 so row 1 (always the plain-query row) fits under the cap.
const MAX_TAG_ROWS = 7;

interface SearchSuggestProps {
  q: string;
  tagIds: string[];
  onQueryChange: (q: string) => void;
  onSelectTag: (tagId: string) => void;
  className?: string;
}

type SuggestionRow = { kind: "query" } | { kind: "tag"; tag: TagListItem };

function labelOf(item: { name_en: string; name_pl: string | null }, preferPl: boolean): string {
  return preferPl && item.name_pl ? item.name_pl : item.name_en;
}

// D-4 — a matched-alias renders only when the typed query is a substring of
// the *other*-locale name and NOT a substring of the active-locale label.
function matchedAlias(tag: TagListItem, preferPl: boolean, query: string): string | undefined {
  const activeLabel = labelOf(tag, preferPl);
  const otherLabel = preferPl ? tag.name_en : tag.name_pl;
  const needle = query.trim().toLowerCase();
  if (!otherLabel || needle.length === 0) return undefined;
  const activeLower = activeLabel.toLowerCase();
  const otherLower = otherLabel.toLowerCase();
  if (otherLower.includes(needle) && !activeLower.includes(needle)) return otherLabel;
  return undefined;
}

export function SearchSuggest({
  q,
  tagIds,
  onQueryChange,
  onSelectTag,
  className,
}: SearchSuggestProps) {
  const { t, i18n } = useTranslation();
  const listboxId = useId();
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  // D-2/D-7 — closing (Enter/Escape/blur) must not reopen the panel merely
  // because `q` is still non-empty; typing again (handleChange) re-arms it.
  const [dismissed, setDismissed] = useState(false);

  const preferPl = i18n.language.startsWith("pl");
  const trimmed = q.trim();
  const isOpen = trimmed.length > 0 && !dismissed;

  // Query on the trimmed value: the backend LIKE-matches on the raw string
  // with no server-side trim, so a stray leading/trailing space (paste,
  // autocorrect, IME) would otherwise silently fail to match tags that the
  // trimmed text clearly matches, even though the panel is open.
  const tagsQuery = useTags(trimmed);
  const tagGroupsQuery = useTagGroups();

  const groupsById = useMemo(() => {
    const m = new Map<string, TagGroupRead>();
    for (const g of tagGroupsQuery.data?.groups ?? []) m.set(g.id, g);
    return m;
  }, [tagGroupsQuery.data]);

  const matchingTags = (tagsQuery.data ?? []).filter((tag) => !tagIds.includes(tag.id));
  const cappedTags = matchingTags.slice(0, MAX_TAG_ROWS);
  const hasOverflow = matchingTags.length > MAX_TAG_ROWS;

  const rows: SuggestionRow[] = isOpen
    ? [{ kind: "query" }, ...cappedTags.map((tag): SuggestionRow => ({ kind: "tag", tag }))]
    : [];

  const optionId = (index: number) => `${listboxId}-option-${index}`;
  const activeId =
    activeIndex !== null && rows[activeIndex] ? optionId(activeIndex) : undefined;

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    setDismissed(false);
    setActiveIndex(null);
    onQueryChange(e.target.value);
  }

  function selectQueryRow() {
    setDismissed(true);
    setActiveIndex(null);
  }

  function selectTagRow(tag: TagListItem) {
    // `onSelectTag` owns clearing `q` too (mirrors the existing `+tag`
    // TagPicker's onAdd semantics, D-1): it's one atomic FilterRibbonState
    // update, not two independent onChange dispatches racing on stale state.
    onSelectTag(tag.id);
    setDismissed(true);
    setActiveIndex(null);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (!isOpen) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((prev) => (prev === null ? 0 : Math.min(prev + 1, rows.length - 1)));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((prev) => (prev === null || prev === 0 ? null : prev - 1));
    } else if (e.key === "Enter") {
      const row = activeIndex !== null ? rows[activeIndex] : undefined;
      if (row?.kind === "tag") {
        e.preventDefault();
        selectTagRow(row.tag);
      } else {
        // D-2 — Enter with no explicit arrow-selection onto a +tag row is a
        // no-op beyond closing the panel; `q` is already committed via
        // onChange on every keystroke.
        setDismissed(true);
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      setDismissed(true);
      setActiveIndex(null);
    }
  }

  function handleBlur() {
    setDismissed(true);
  }

  return (
    <div className={`relative ${className ?? ""}`}>
      <Input
        role="combobox"
        aria-expanded={isOpen}
        aria-controls={listboxId}
        aria-activedescendant={activeId}
        aria-autocomplete="list"
        value={q}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        placeholder={t("common.search")}
        className="w-full"
      />
      {isOpen && (
        // D-8 — overflow: visible, no max-h/overflow-y-auto: the panel's
        // height is content-driven, bounded structurally by the 8-row cap.
        <div
          id={listboxId}
          role="listbox"
          className="absolute z-50 mt-1 w-full rounded border border-border bg-popover p-1 shadow-lg"
        >
          <div
            id={optionId(0)}
            role="option"
            aria-selected={activeIndex === 0}
            aria-label={t("catalog.suggestions.queryOption", { query: q })}
            tabIndex={-1}
            onMouseDown={(e) => e.preventDefault()}
            onClick={selectQueryRow}
            className="flex min-h-9 cursor-pointer items-center gap-2 rounded px-2 py-1 text-sm hover:bg-accent"
          >
            <Search className="size-3.5 shrink-0" aria-hidden />
            <span className="truncate">{q}</span>
          </div>
          {cappedTags.map((tag, i) => {
            const rowIndex = i + 1;
            const activeLabel = labelOf(tag, preferPl);
            const alias = matchedAlias(tag, preferPl, q);
            const group =
              tag.group_id !== null && tagGroupsQuery.data !== undefined
                ? groupsById.get(tag.group_id)
                : undefined;
            const groupLabel = group ? labelOf(group, preferPl) : undefined;
            const accessibleName = groupLabel
              ? t("catalog.suggestions.tagOption", { name: activeLabel, group: groupLabel })
              : t("catalog.suggestions.tagOptionNoGroup", { name: activeLabel });
            // The alias hint is sighted-only if left out of the accessible
            // name/description entirely (an explicit aria-label excludes all
            // descendant text from the accname computation). Expose it via
            // aria-describedby instead of folding it into aria-label, so the
            // tagOption/tagOptionNoGroup strings stay byte-identical to the
            // EXPERIENCE.md:207 contract asserted by suggestions-i18n.test.ts.
            const aliasId = alias ? `${optionId(rowIndex)}-alias` : undefined;
            return (
              <div
                key={tag.id}
                id={optionId(rowIndex)}
                role="option"
                aria-selected={activeIndex === rowIndex}
                aria-label={accessibleName}
                aria-describedby={aliasId}
                tabIndex={-1}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => selectTagRow(tag)}
                className="flex min-h-9 cursor-pointer items-center gap-2 rounded px-2 py-1 text-sm hover:bg-accent"
              >
                <Plus className="size-3.5 shrink-0" aria-hidden />
                <span className="flex items-center gap-1 rounded-full bg-accent px-2 py-0.5 text-xs text-accent-foreground">
                  {activeLabel}
                  {groupLabel && <span className="text-muted-foreground"> · {groupLabel}</span>}
                </span>
                {alias && (
                  <span id={aliasId} className="text-xs text-muted-foreground">
                    {alias}
                  </span>
                )}
              </div>
            );
          })}
          {hasOverflow && (
            <p aria-hidden className="px-2 py-1 text-xs text-muted-foreground">
              {t("catalog.suggestions.overflowNote")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
