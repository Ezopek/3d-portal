import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import type { ModelDetail, TagRead } from "@/lib/api-types";
import { useTagGroups } from "@/modules/catalog/hooks/useTagGroups";
import { Button } from "@/ui/button";

// Sentinel id for the trailing groupless section — same literal value as
// FacetSidebar's own (independently-defined, unexported) GROUPLESS_ID.
// Real group ids are backend-issued UUIDs, so this never collides.
const GROUPLESS_ID = "__groupless__";

interface Section {
  id: string;
  label: string;
  tags: TagRead[];
}

interface Props {
  detail: ModelDetail;
  isAdmin: boolean;
  onAddTags: () => void;
}

export function TagGroupsSection({ detail, isAdmin, onAddTags }: Props) {
  const { t, i18n } = useTranslation();
  const tagGroups = useTagGroups();

  // Guard on data presence rather than isPending/isError individually — in
  // both cases `data` stays undefined, so this single check fails closed
  // (renders nothing) for loading and error alike. The badge-row pencil
  // (admin-only) remains available as a fallback path to manage tags.
  if (tagGroups.data === undefined) return null;

  const preferPl = i18n.language.startsWith("pl");
  // Empty string is a valid `name_pl` per the API type; treat it like null so
  // a pl-locale group never renders a blank label (mirrors FacetSidebar's
  // `labelOf`).
  const labelOf = (item: { name_en: string; name_pl: string | null }) =>
    preferPl && item.name_pl ? item.name_pl : item.name_en;

  // `TagGroupRead.tags` is the group's catalog-wide roster, not this model's —
  // grouping keys off `detail.tags[].group_id`, not `group.tags`.
  const sortedGroups = [...tagGroups.data.groups].sort((a, b) => a.position - b.position);
  const knownGroupIds = new Set(sortedGroups.map((g) => g.id));
  const sections: Section[] = sortedGroups.map((g) => ({
    id: g.id,
    label: labelOf(g),
    tags: detail.tags.filter((tag) => tag.group_id === g.id),
  }));
  // A tag's group_id can reference a group that's been deleted/renamed since
  // this tag was assigned (or the 5-minute-cached tag-groups response predates
  // it) — fold those orphaned tags into "Ungrouped" instead of silently
  // dropping them from every section.
  sections.push({
    id: GROUPLESS_ID,
    label: t("catalog.filters.ungrouped"),
    tags: detail.tags.filter(
      (tag) => tag.group_id === null || !knownGroupIds.has(tag.group_id),
    ),
  });

  // A group is visible when it has ≥1 of this model's tags, or the viewer is
  // admin (who sees a dash + Add affordance for empty groups).
  const visible = sections.filter((s) => s.tags.length > 0 || isAdmin);
  if (visible.length === 0) return null;

  return (
    <div className="mt-2 space-y-1.5">
      {visible.map((section) => (
        <div key={section.id} className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {section.label}
          </span>
          {section.tags.length > 0 ? (
            section.tags.map((tag) => (
              <Link
                key={tag.id}
                to="/catalog"
                search={{ tag_ids: [tag.id] }}
                data-testid="tag-chip"
                className="rounded bg-muted px-1.5 py-0.5 text-xs text-chip-foreground hover:bg-accent"
              >
                {tag.slug}
              </Link>
            ))
          ) : (
            <>
              <span className="text-xs text-muted-foreground">—</span>
              <Button
                variant="outline"
                size="xs"
                onClick={onAddTags}
                aria-label={t("a11y.addTagToGroup", { name: section.label })}
              >
                {t("catalog.actions.addTag")}
              </Button>
            </>
          )}
        </div>
      ))}
    </div>
  );
}
