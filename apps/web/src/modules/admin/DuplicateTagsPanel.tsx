import { useTranslation } from "react-i18next";

import type { TagReadWithCount } from "@/lib/api-types";
import { Badge } from "@/ui/badge";
import { Button } from "@/ui/button";

// Story 46.3 — presentational "possible duplicates" panel. Purely a renderer
// over already-computed clusters (see duplicateTags.ts); it owns no mutation
// and no dialog state — the parent (TagGroupsPage) supplies `onMergeCluster`.
// Token-only warning styling (`--color-warning` family), matching the existing
// warning-banner precedent in ProfileLibraryPage.tsx.
export interface DuplicateTagsPanelProps {
  clusters: TagReadWithCount[][];
  localize: (nameEn: string, namePl: string | null) => string;
  onMergeCluster: (tagIds: string[]) => void;
}

export function DuplicateTagsPanel({ clusters, localize, onMergeCluster }: DuplicateTagsPanelProps) {
  const { t } = useTranslation();

  // Absent entirely (not an empty shell) when no clusters are detected.
  if (clusters.length === 0) return null;

  return (
    <section
      className="flex flex-col gap-2 rounded-md border border-warning/40 bg-warning/10 p-3"
      data-testid="duplicate-tags-panel"
    >
      <h2 className="text-sm font-semibold text-foreground">
        {t("modules.admin.tagGroups.duplicates.title")}
      </h2>
      <ul className="flex flex-col gap-2">
        {clusters.map((cluster) => {
          const tagIds = cluster.map((tag) => tag.id);
          const label = cluster.map((tag) => localize(tag.name_en, tag.name_pl)).join(" · ");
          return (
            <li
              key={tagIds.join(",")}
              className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-warning/40 bg-card px-3 py-2"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm text-card-foreground">{label}</span>
                <Badge variant="outline" className="border-warning/40 bg-warning/10 text-warning">
                  {t("modules.admin.tagGroups.duplicates.count_badge", { count: cluster.length })}
                </Badge>
              </div>
              <Button variant="outline" size="sm" onClick={() => onMergeCluster(tagIds)}>
                {t("modules.admin.tagGroups.duplicates.merge_action")}
              </Button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
