import { ChevronDown, ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import type { TagGroupRead, TagReadWithCount } from "@/lib/api-types";
import { cn } from "@/lib/utils";
import { Input } from "@/ui/input";

const STORAGE_KEY = "catalog:facet-collapse";
// Number of leading groups (by `position`) expanded on first render when there
// is no persisted collapse state. Tunable without touching the default-rule
// logic. Kept module-local (unexported) so the file's only export is the
// component — otherwise `react-refresh/only-export-components` would warn.
const DEFAULT_EXPANDED_GROUP_COUNT = 2;
// Sentinel id for the trailing groupless section in the expanded-id set. Real
// group ids are UUID strings, so this never collides.
const GROUPLESS_ID = "__groupless__";

interface Props {
  groups: TagGroupRead[];
  groupless: TagReadWithCount[];
  selectedTagIds: string[];
  onToggleTag: (id: string) => void;
  untaggedActive: boolean;
  onToggleUntagged: () => void;
  untaggedCount?: number;
  /**
   * When true, the sidebar omits its desktop-only `hidden lg:block` wrapper and
   * adapts layout for being slotted inside a Sheet/drawer on mobile.
   */
  mobile?: boolean;
}

interface Section {
  id: string;
  label: string;
  tags: TagReadWithCount[];
}

export function FacetSidebar({
  groups,
  groupless,
  selectedTagIds,
  onToggleTag,
  untaggedActive,
  onToggleUntagged,
  untaggedCount,
  mobile = false,
}: Props) {
  const { t, i18n } = useTranslation();
  const [query, setQuery] = useState("");
  const [expandedGroupIds, setExpandedGroupIds] = useState<Set<string>>(() => {
    const persisted = loadPersisted();
    return persisted ?? computeDefaultExpanded(groups, groupless, selectedTagIds);
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...expandedGroupIds]));
    } catch {
      // Persisting collapse state is best-effort; never surface a storage error.
    }
  }, [expandedGroupIds]);

  function toggleGroup(id: string) {
    setExpandedGroupIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const preferPl = i18n.language.startsWith("pl");
  const q = query.trim().toLowerCase();
  const searching = q.length > 0;
  // Empty string is a valid `name_pl` per the API type; treat it like null and
  // fall back to `name_en` so a pl-locale row never renders a blank label
  // (matches the guard in the sibling `ModelHero`).
  const labelOf = (item: { name_en: string; name_pl: string | null }) =>
    preferPl && item.name_pl ? item.name_pl : item.name_en;

  const sortedGroups = [...groups].sort((a, b) => a.position - b.position);
  const sections: Section[] = sortedGroups.map((g) => ({
    id: g.id,
    label: labelOf(g),
    tags: g.tags,
  }));
  if (groupless.length > 0) {
    sections.push({ id: GROUPLESS_ID, label: t("catalog.filters.ungrouped"), tags: groupless });
  }

  const visibleSections = searching
    ? sections
        .map((s) => ({ ...s, tags: s.tags.filter((tag) => matchesQuery(tag, q)) }))
        .filter((s) => s.tags.length > 0)
    : sections;

  const showNoMatches = searching && visibleSections.length === 0;

  const asideClassName = mobile
    ? "flex w-full flex-col bg-card p-4"
    : "hidden w-60 shrink-0 flex-col border-r border-border bg-card p-4 lg:flex";

  return (
    <aside className={asideClassName}>
      <Input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={t("catalog.tags.searchPlaceholder")}
        aria-label={t("catalog.tags.searchPlaceholder")}
        className="mb-3 text-sm"
      />
      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
        {showNoMatches && (
          <p className="px-2 py-4 text-sm text-muted-foreground">{t("catalog.tags.noMatches")}</p>
        )}
        {visibleSections.map((section) => {
          const isExpanded = searching || expandedGroupIds.has(section.id);
          return (
            <div key={section.id}>
              <button
                type="button"
                aria-expanded={isExpanded}
                aria-label={
                  isExpanded
                    ? t("a11y.collapse", { name: section.label })
                    : t("a11y.expand", { name: section.label })
                }
                onClick={() => {
                  // During an active search every section is force-expanded, so a
                  // toggle has no visible effect; guard it to avoid silently
                  // mutating (and persisting) collapse state the user can't see.
                  if (!searching) toggleGroup(section.id);
                }}
                className="flex min-h-9 w-full items-center gap-1 rounded px-2 py-1 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground hover:bg-accent hover:text-foreground"
              >
                {isExpanded ? (
                  <ChevronDown className="size-3.5" aria-hidden />
                ) : (
                  <ChevronRight className="size-3.5" aria-hidden />
                )}
                <span className="flex-1">{section.label}</span>
              </button>
              {isExpanded && (
                <ul className="mt-0.5 space-y-0.5">
                  {section.tags.map((tag) => {
                    const checked = selectedTagIds.includes(tag.id);
                    return (
                      <li key={tag.id}>
                        <label
                          className={cn(
                            "flex min-h-9 cursor-pointer items-center gap-2 rounded px-2 py-1 text-sm hover:bg-accent",
                            checked ? "text-foreground" : "text-muted-foreground",
                          )}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => onToggleTag(tag.id)}
                            className="size-4 shrink-0 rounded border-input accent-primary"
                          />
                          <span className="flex-1">{labelOf(tag)}</span>
                          <span className="text-xs">{tag.model_count}</span>
                        </label>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          );
        })}
      </div>
      <div className="mt-2 border-t border-border pt-2">
        <label
          className={cn(
            "flex min-h-9 cursor-pointer items-center gap-2 rounded px-2 py-1 text-sm hover:bg-accent",
            untaggedActive ? "text-foreground" : "text-muted-foreground",
          )}
        >
          <input
            type="checkbox"
            checked={untaggedActive}
            onChange={() => onToggleUntagged()}
            className="size-4 shrink-0 rounded border-input accent-primary"
          />
          <span className="flex-1">{t("catalog.filters.untagged")}</span>
          {untaggedCount !== undefined && <span className="text-xs">{untaggedCount}</span>}
        </label>
      </div>
    </aside>
  );
}

function matchesQuery(tag: TagReadWithCount, q: string): boolean {
  const haystack = `${tag.name_en} ${tag.name_pl ?? ""}`.toLowerCase();
  return haystack.includes(q);
}

function computeDefaultExpanded(
  groups: TagGroupRead[],
  groupless: TagReadWithCount[],
  selectedTagIds: string[],
): Set<string> {
  const selected = new Set(selectedTagIds);
  const sorted = [...groups].sort((a, b) => a.position - b.position);
  const ids = new Set<string>();
  sorted.slice(0, DEFAULT_EXPANDED_GROUP_COUNT).forEach((g) => ids.add(g.id));
  sorted.forEach((g) => {
    if (g.tags.some((tag) => selected.has(tag.id))) ids.add(g.id);
  });
  if (groupless.some((tag) => selected.has(tag.id))) ids.add(GROUPLESS_ID);
  return ids;
}

function loadPersisted(): Set<string> | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === null) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return null;
    return new Set(parsed.filter((s): s is string => typeof s === "string"));
  } catch {
    return null;
  }
}
