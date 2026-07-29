import { Link } from "@tanstack/react-router";
import { TriangleAlert } from "lucide-react";
import { useTranslation } from "react-i18next";

import type {
  BrowseCategoryAdminRead,
  OverCategorizedResponse,
  TagGroupsResponse,
} from "@/lib/api-types";
import { Button } from "@/ui/button";

import {
  computeCurationChecks,
  type CurationCheckGroup,
  type CurationFinding,
} from "./curationChecks";

// Story 52.3 — the curation-QA panel on /admin/categories. Six advisory checks,
// each a row with a warning marker, the finding, the affected entity and a link
// to the fix.
//
// It is advisory in the strongest sense: it holds NO mutation hook and issues no
// write. Every action is a navigation, an in-page anchor, or the opening of a
// shipped 52.2 dialog. It deliberately does NOT copy DuplicateTagsPanel's
// `onMergeCluster` — and, unlike that panel, it does not `return null` when it
// has nothing to say: this surface owes an explicit "Nothing needs attention."
//
// Warning is the only colour permitted here. `destructive` means "this write
// failed / this will delete data", and every finding on this surface is
// advisory by FR26-ADMIN-2.

/** The slice of a TanStack query this panel actually consumes. */
export interface CurationSource<T> {
  data: T | undefined;
  isError: boolean;
  isFetching: boolean;
  refetch: () => void;
}

export interface CurationQaPanelProps {
  categories: CurationSource<BrowseCategoryAdminRead[]>;
  /** The ALREADY-MOUNTED `uncategorized` models query — never a second instance. */
  uncategorized: CurationSource<{ total: number }>;
  tagGroups: CurationSource<TagGroupsResponse>;
  overCategorized: CurationSource<OverCategorizedResponse>;
  localize: (nameEn: string, namePl: string | null) => string;
  /** Opens the shipped 52.2 replace-set editor. The panel performs no write itself. */
  onEditModelCategories: (modelId: string, modelName: string) => void;
}

const ACTION_CLASS =
  "inline-flex min-h-7 shrink-0 items-center rounded-md border border-warning/40 px-2.5 text-xs font-medium text-foreground transition-colors hover:bg-warning/20 focus-visible:ring-3 focus-visible:ring-ring/50";

export function CurationQaPanel({
  categories,
  uncategorized,
  tagGroups,
  overCategorized,
  localize,
  onEditModelCategories,
}: CurationQaPanelProps) {
  const { t } = useTranslation();

  const sources = [categories, uncategorized, tagGroups, overCategorized];
  // D-6, carrying forward the 52.2 review defects R-3/R-4. UNRESOLVED means a
  // source has neither data nor an error yet — the panel must not render a count
  // and must never fabricate the green empty state over a pending read.
  const unresolved = sources.some((s) => s.data === undefined && !s.isError);
  // A source that errored WITH cached data does not land here: the computation
  // below reads `.data` regardless of `isError`, so the panel keeps rendering
  // still-valid rows instead of blanking (the shipped stale-while-error posture).
  const failedSources = sources.filter((s) => s.data === undefined && s.isError);

  const { groups, totalFindings } = computeCurationChecks({
    categories: categories.data,
    tagGroups: tagGroups.data,
    overCategorized: overCategorized.data,
    uncategorizedTotal: uncategorized.data?.total,
  });

  function renderAction(finding: CurationFinding) {
    switch (finding.kind) {
      case "empty_category":
      case "tiny_category": {
        const name = localize(finding.category.name_en, finding.category.name_pl);
        const key = finding.kind === "empty_category" ? "empty_category" : "tiny_category";
        return (
          <a
            href={`#browse-category-${finding.category.slug}`}
            className={ACTION_CLASS}
            aria-label={t(`modules.admin.categories.qa.${key}.action_label`, { name })}
          >
            {t(`modules.admin.categories.qa.${key}.action`)}
          </a>
        );
      }
      case "label_collision": {
        const category = localize(finding.category.name_en, finding.category.name_pl);
        const tag = localize(finding.tag.name_en, finding.tag.name_pl);
        return (
          <Link
            to="/admin/tag-groups"
            className={ACTION_CLASS}
            aria-label={t("modules.admin.categories.qa.label_collision.action_label", {
              category,
              tag,
            })}
          >
            {t("modules.admin.categories.qa.label_collision.action")}
          </Link>
        );
      }
      case "over_categorized": {
        const name = localize(finding.model.name_en, finding.model.name_pl);
        return (
          <Button
            variant="outline"
            size="sm"
            className="shrink-0 border-warning/40 text-xs"
            // The editor needs the full category list to render its checkboxes,
            // mirroring the shipped queue row's own guard.
            disabled={categories.data === undefined}
            aria-label={t("modules.admin.categories.qa.over_categorized.action_label", { name })}
            onClick={() => onEditModelCategories(finding.model.model_id, name)}
          >
            {t("modules.admin.categories.qa.over_categorized.action")}
          </Button>
        );
      }
      case "uncategorized_models":
        return (
          <a
            href="#curation-queue"
            className={ACTION_CLASS}
            aria-label={t("modules.admin.categories.qa.uncategorized_models.action_label")}
          >
            {t("modules.admin.categories.qa.uncategorized_models.action")}
          </a>
        );
      case "ungrouped_tags":
        return (
          <Link
            to="/admin/tag-groups"
            className={ACTION_CLASS}
            aria-label={t("modules.admin.categories.qa.ungrouped_tags.action_label")}
          >
            {t("modules.admin.categories.qa.ungrouped_tags.action")}
          </Link>
        );
    }
  }

  function findingText(finding: CurationFinding): string {
    switch (finding.kind) {
      case "empty_category":
        return t("modules.admin.categories.qa.empty_category.finding", {
          name: localize(finding.category.name_en, finding.category.name_pl),
        });
      case "tiny_category":
        return t("modules.admin.categories.qa.tiny_category.finding", {
          name: localize(finding.category.name_en, finding.category.name_pl),
          count: finding.category.model_count,
        });
      case "label_collision": {
        const category = localize(finding.category.name_en, finding.category.name_pl);
        const tag = localize(finding.tag.name_en, finding.tag.name_pl);
        // A GROUPLESS tag renders with no group suffix — never a placeholder,
        // the same rule the suggestion pill already follows.
        if (finding.group === null) {
          return t("modules.admin.categories.qa.label_collision.finding_groupless", {
            category,
            tag,
          });
        }
        return t("modules.admin.categories.qa.label_collision.finding", {
          category,
          tag,
          group: localize(finding.group.name_en, finding.group.name_pl),
        });
      }
      case "over_categorized":
        return t("modules.admin.categories.qa.over_categorized.finding", {
          name: localize(finding.model.name_en, finding.model.name_pl),
          count: finding.model.category_count,
        });
      case "uncategorized_models":
        return t("modules.admin.categories.qa.uncategorized_models.finding", {
          count: finding.count,
        });
      case "ungrouped_tags":
        return t("modules.admin.categories.qa.ungrouped_tags.finding", { count: finding.count });
    }
  }

  function renderGroup(group: CurationCheckGroup) {
    const remaining = group.total - group.rows.length;
    return (
      <li key={group.kind}>
        <ul className="flex flex-col gap-2">
          {group.rows.map((finding) => (
            <li
              key={finding.id}
              className="flex flex-wrap items-start justify-between gap-2 rounded-md border border-warning/40 bg-card px-3 py-2"
              data-testid={`curation-finding-${finding.id}`}
            >
              <div className="flex min-w-0 flex-1 items-start gap-2">
                <TriangleAlert className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden />
                <div className="min-w-0">
                  <p className="text-sm text-card-foreground">{findingText(finding)}</p>
                  <p className="text-xs text-muted-foreground">
                    {t(`modules.admin.categories.qa.${finding.kind}.sub`)}
                  </p>
                </div>
              </div>
              {renderAction(finding)}
            </li>
          ))}
          {remaining > 0 ? (
            // Non-interactive and not a focus stop: the cap must never read as
            // "these are all of them", but it is not itself an affordance.
            <li
              className="px-3 text-xs text-muted-foreground"
              data-testid={`curation-overflow-${group.kind}`}
            >
              {t("modules.admin.categories.qa.overflow", { count: remaining })}
            </li>
          ) : null}
        </ul>
      </li>
    );
  }

  return (
    <section
      className="flex flex-col gap-2 rounded-md border border-warning/40 bg-warning/10 p-3"
      aria-labelledby="curation-qa-heading"
      data-testid="curation-qa-panel"
    >
      <h2 id="curation-qa-heading" className="text-sm font-semibold text-foreground">
        {/* The count is asserted ONLY when all four sources actually answered.
            "Curation QA (0)" printed beside "some checks could not run" would
            be the fabricated-green claim D-6 exists to prevent — the total is
            genuinely unknown while a source is missing. */}
        {unresolved || failedSources.length > 0
          ? t("modules.admin.categories.qa.title_pending")
          : t("modules.admin.categories.qa.title", { count: totalFindings })}
      </h2>
      <p className="text-xs text-muted-foreground">
        {t("modules.admin.categories.qa.description")}
      </p>

      {unresolved ? (
        <div className="flex flex-col gap-2" aria-hidden="true" data-testid="curation-qa-skeleton">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-12 animate-pulse rounded-md bg-muted" />
          ))}
        </div>
      ) : (
        <>
          {groups.length > 0 ? (
            <ul className="flex flex-col gap-2">{groups.map(renderGroup)}</ul>
          ) : null}

          {failedSources.length > 0 ? (
            // Never the green empty state in this branch: some checks provably
            // could not run, so silence would be a claim the panel cannot make.
            <div
              className="flex flex-wrap items-center gap-2"
              data-testid="curation-qa-partial"
            >
              <p className="text-sm text-foreground">
                {t("modules.admin.categories.qa.partial")}
              </p>
              <Button
                variant="outline"
                size="sm"
                className="border-warning/40"
                disabled={failedSources.some((s) => s.isFetching)}
                onClick={() => failedSources.forEach((s) => s.refetch())}
              >
                {t("common.retry")}
              </Button>
            </div>
          ) : groups.length === 0 ? (
            // Only reachable when all four sources resolved successfully with
            // zero findings. Not an error, not a celebration.
            <p className="text-sm text-muted-foreground" data-testid="curation-qa-empty">
              {t("modules.admin.categories.qa.empty")}
            </p>
          ) : null}
        </>
      )}
    </section>
  );
}
