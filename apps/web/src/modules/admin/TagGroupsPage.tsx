import { useTranslation } from "react-i18next";

import type { TagGroupRead, TagReadWithCount } from "@/lib/api-types";
import { useTagGroups } from "@/modules/catalog/hooks/useTagGroups";
import { Button } from "@/ui/button";

import { AdminTabs } from "./AdminTabs";

// TAG-GROUPS-1 (Story 46.1) — locale-aware group/tag naming follows the same
// `preferPl` fallback used by ModelHero (apps/web/src/modules/catalog/components/ModelHero.tsx:67-80):
// prefer name_pl only when the active locale is Polish AND name_pl is non-null/non-empty.
function useLocalizedName() {
  const { i18n } = useTranslation();
  const preferPl = i18n.language.startsWith("pl");
  return (nameEn: string, namePl: string | null): string =>
    preferPl && namePl !== null && namePl !== "" ? namePl : nameEn;
}

function TagRow({ tag }: { tag: TagReadWithCount }) {
  const { t } = useTranslation();
  const localize = useLocalizedName();
  return (
    <li className="flex items-center justify-between rounded-md border border-border bg-card px-3 py-2">
      <span className="text-sm text-card-foreground">{localize(tag.name_en, tag.name_pl)}</span>
      <span className="text-xs tabular-nums text-muted-foreground">
        {t("modules.admin.tagGroups.model_count", { count: tag.model_count })}
      </span>
    </li>
  );
}

function GroupSection({ group }: { group: TagGroupRead }) {
  const { t } = useTranslation();
  const localize = useLocalizedName();
  return (
    <section className="flex flex-col gap-2" data-testid={`tag-group-${group.slug}`}>
      <h2 className="text-sm font-semibold text-foreground">
        {localize(group.name_en, group.name_pl)}
      </h2>
      {group.tags.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("modules.admin.tagGroups.group_empty")}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {group.tags.map((tag) => (
            <TagRow key={tag.id} tag={tag} />
          ))}
        </ul>
      )}
    </section>
  );
}

function GrouplessSection({ tags }: { tags: TagReadWithCount[] }) {
  const { t } = useTranslation();
  // I/O Matrix "No groupless tags" row — omitted entirely, not rendered empty.
  if (tags.length === 0) return null;
  return (
    <section className="flex flex-col gap-2" data-testid="tag-group-ungrouped">
      <h2 className="text-sm font-semibold text-foreground">
        {t("modules.admin.tagGroups.ungrouped_title")}
      </h2>
      <ul className="flex flex-col gap-2">
        {tags.map((tag) => (
          <TagRow key={tag.id} tag={tag} />
        ))}
      </ul>
    </section>
  );
}

export function TagGroupsPage() {
  const { t } = useTranslation();
  const query = useTagGroups();

  return (
    <div className="flex flex-col gap-4 p-4">
      <AdminTabs activeTab="tag-groups" />

      <header className="flex flex-col gap-1">
        <h1 className="text-lg font-semibold text-foreground">
          {t("modules.admin.tagGroups.title")}
        </h1>
        <p className="text-xs text-muted-foreground">
          {t("modules.admin.tagGroups.description")}
        </p>
      </header>

      {query.data ? (
        // Prefer showing already-loaded data over a background-refetch error (mirrors
        // TanStack Query's stale-while-error convention): a transient refetch failure
        // must not hide previously-successful, still-valid tag groups.
        query.data.groups.length === 0 && query.data.groupless.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("modules.admin.tagGroups.empty")}</p>
        ) : (
          <>
            {query.data.groups.map((group) => (
              <GroupSection key={group.id} group={group} />
            ))}
            <GrouplessSection tags={query.data.groupless} />
          </>
        )
      ) : query.isError ? (
        // Fails-closed: never fabricate an empty/green state on a failed read (mirrors QueuesPage).
        <div className="flex flex-col items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-4">
          <p className="text-sm font-medium text-destructive">
            {t("modules.admin.tagGroups.error_title")}
          </p>
          <Button
            variant="outline"
            size="sm"
            disabled={query.isFetching}
            onClick={() => void query.refetch()}
          >
            {t("modules.admin.tagGroups.retry")}
          </Button>
        </div>
      ) : (
        <div className="flex flex-col gap-3" aria-hidden="true" data-testid="tag-groups-skeleton">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-md bg-muted" />
          ))}
        </div>
      )}
    </div>
  );
}
