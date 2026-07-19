import { useNavigate, useSearch } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { AddModelButton } from "@/modules/admin/AddModelButton";
import { FacetSidebar } from "@/modules/catalog/components/FacetSidebar";
import { FilterRibbon, type FilterRibbonState } from "@/modules/catalog/components/FilterRibbon";
import { useModels } from "@/modules/catalog/hooks/useModels";
import { useTagGroups } from "@/modules/catalog/hooks/useTagGroups";
import { useTags } from "@/modules/catalog/hooks/useTags";
import type { CatalogSearch } from "@/routes/catalog/index";
import { Button } from "@/ui/button";
import { EmptyState } from "@/ui/custom/EmptyState";
import { LoadingState } from "@/ui/custom/LoadingState";
import { ModelCard } from "@/ui/custom/ModelCard";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/ui/sheet";

const PAGE_SIZE = 48;

export function CatalogList() {
  const { t } = useTranslation();
  const search = useSearch({ from: "/catalog/" });
  const navigate = useNavigate({ from: "/catalog/" });
  const [mobileTagsOpen, setMobileTagsOpen] = useState(false);

  const tagGroups = useTagGroups();
  const tags = useTags();
  const tagsData = tags.data;
  const tagsById = useMemo(() => {
    const m = new Map<string, NonNullable<typeof tagsData>[number]>();
    for (const tag of tagsData ?? []) m.set(tag.id, tag);
    return m;
  }, [tagsData]);

  const models = useModels({
    tag_ids: search.tag_ids,
    tag_match: search.tag_match,
    untagged: search.untagged,
    status: search.status,
    source: search.source,
    q: search.q,
    sort: search.sort,
    page: search.page,
  });

  const filterState: FilterRibbonState = {
    q: search.q ?? "",
    tag_ids: search.tag_ids ?? [],
    tag_match: search.tag_match ?? "all",
    status: search.status,
    source: search.source,
    sort: search.sort ?? "recent",
  };

  function setFilters(next: FilterRibbonState) {
    void navigate({
      search: (prev: CatalogSearch): CatalogSearch => ({
        ...prev,
        q: next.q.length > 0 ? next.q : undefined,
        tag_ids: next.tag_ids.length > 0 ? next.tag_ids : undefined,
        // Only persist a non-default tag_match while ≥2 tags are selected. AND
        // vs OR is meaningless with <2 tags, and the toggle that sets it hides
        // below that threshold — writing it anyway would strand an "any" the
        // user can no longer see or clear (review 2026-07-20).
        tag_match:
          next.tag_ids.length >= 2 && next.tag_match && next.tag_match !== "all"
            ? next.tag_match
            : undefined,
        status: next.status,
        source: next.source,
        sort: next.sort === "recent" ? undefined : next.sort,
        page: undefined, // reset to page 1 on any filter change
      }),
      replace: true,
    });
  }

  function toggleTag(id: string) {
    void navigate({
      search: (prev: CatalogSearch): CatalogSearch => {
        const current = prev.tag_ids ?? [];
        const next = current.includes(id)
          ? current.filter((tid) => tid !== id)
          : [...current, id];
        return {
          ...prev,
          // Let validateSearch normalize a now-stranded tag_match (a non-default
          // value only survives with ≥2 tags — E44.2 enforcement layer).
          tag_ids: next.length > 0 ? next : undefined,
          page: undefined,
        };
      },
      replace: true,
    });
  }

  function toggleUntagged() {
    void navigate({
      search: (prev: CatalogSearch): CatalogSearch => ({
        ...prev,
        untagged: prev.untagged ? undefined : true,
        page: undefined,
      }),
      replace: true,
    });
  }

  function setPage(page: number) {
    void navigate({
      search: (prev: CatalogSearch): CatalogSearch => ({
        ...prev,
        page: page === 1 ? undefined : page,
      }),
      replace: true,
    });
  }

  // Guard on data presence rather than `isLoading`: on the very first render
  // TanStack Query has not yet mounted the queries, so `isLoading` is still
  // false. Without this, FacetSidebar paints with empty group data before
  // `tagGroups.data` resolves. `tags` is guarded alongside the browse-surface
  // deps because it feeds the FilterRibbon chip-label map (`tagsById`): on a
  // tags failure the selected-tag chips would otherwise fall back to truncated
  // UUIDs, so its error/retry/loading is folded in here too.
  if (tagGroups.isError || models.isError || tags.isError) {
    return (
      <EmptyState
        messageKey="errors.network"
        tone="error"
        action={{
          labelKey: "common.retry",
          onClick: () => {
            void tagGroups.refetch();
            void models.refetch();
            void tags.refetch();
          },
        }}
      />
    );
  }
  if (
    tagGroups.data === undefined ||
    models.data === undefined ||
    tags.data === undefined
  ) {
    return <LoadingState variant="skeleton-grid" cols={5} rows={3} />;
  }

  const items = models.data?.items ?? [];
  const total = models.data?.total ?? 0;
  const offset = models.data?.offset ?? 0;
  const limit = models.data?.limit ?? PAGE_SIZE;
  const page = Math.floor(offset / limit) + 1;
  const lastPage = Math.max(1, Math.ceil(total / limit));

  const filtersActive =
    (search.tag_ids?.length ?? 0) > 0 ||
    search.status !== undefined ||
    search.source !== undefined ||
    (search.q?.length ?? 0) > 0 ||
    search.untagged === true;

  // AND intersection that yields nothing is recoverable by switching to OR:
  // ≥2 tags selected with an effective AND (tag_match unset or "all") and the
  // whole filtered set (not just this page) is empty (HANDOFF mockup 08D). Key
  // on `total === 0`, not `items.length === 0`, so a stale `?page=2` overshoot
  // that still has matches on page 1 falls through to the Clear-filters branch
  // instead of falsely offering "Switch to OR" (review 2026-07-20).
  const andTooNarrow =
    total === 0 &&
    (search.tag_ids?.length ?? 0) >= 2 &&
    (search.tag_match ?? "all") === "all";

  return (
    <div className="flex">
      <FacetSidebar
        groups={tagGroups.data.groups}
        groupless={tagGroups.data.groupless}
        selectedTagIds={search.tag_ids ?? []}
        onToggleTag={toggleTag}
        untaggedActive={search.untagged ?? false}
        onToggleUntagged={toggleUntagged}
      />
      <div className="min-w-0 flex-1">
        <div className="border-b border-border bg-background/95 px-3 pt-3 lg:hidden">
          <Sheet open={mobileTagsOpen} onOpenChange={setMobileTagsOpen}>
            <SheetTrigger
              render={
                <Button variant="outline" size="sm" className="w-full justify-start">
                  {t("catalog.filters.openTags")}
                </Button>
              }
            />
            <SheetContent side="left" className="w-80 max-w-[85vw] overflow-y-auto p-0">
              <SheetHeader>
                <SheetTitle>{t("catalog.filters.openTags")}</SheetTitle>
              </SheetHeader>
              <FacetSidebar
                groups={tagGroups.data.groups}
                groupless={tagGroups.data.groupless}
                selectedTagIds={search.tag_ids ?? []}
                onToggleTag={toggleTag}
                untaggedActive={search.untagged ?? false}
                onToggleUntagged={toggleUntagged}
                mobile
              />
            </SheetContent>
          </Sheet>
        </div>
        {/* Initiative 13 Story 20.2 — admin-only "Add Model" CTA in the
            catalog toolbar. Operator-aligned 2026-05-23: top-right placement
            next to filter controls. AddModelButton role-gates on isAdmin
            (non-admin users see nothing in this slot).
            Story 28.1 (Init 17 / TB-048): outer flex uses `items-center`
            so the AddModelButton's vertical center aligns with the
            FilterRibbon's (FilterRibbon is internally a single-row
            `items-center` flex of search input + facet dropdowns).
            The previous `items-start` + magic `pt-1` on the button
            wrapper produced a small mis-baseline that operator's
            hands-on (`tmp/add_model_misalligned.png`) flagged. The
            `pt-1` hack is now removed since `items-center` does the
            alignment canonically. */}
        <div className="flex items-center justify-between gap-3 px-3 pt-3">
          <div className="min-w-0 flex-1">
            <FilterRibbon state={filterState} tagsById={tagsById} onChange={setFilters} />
          </div>
          <div className="shrink-0">
            <AddModelButton />
          </div>
        </div>
        {items.length === 0 ? (
          andTooNarrow ? (
            <EmptyState
              messageKey="catalog.empty"
              action={{
                labelKey: "catalog.actions.switch_to_or",
                onClick: () => {
                  void navigate({
                    search: (prev: CatalogSearch): CatalogSearch => ({
                      ...prev,
                      tag_match: "any",
                      page: undefined,
                    }),
                    replace: true,
                  });
                },
              }}
              secondaryAction={{
                labelKey: "catalog.actions.clear_filters",
                onClick: () => {
                  void navigate({ search: {}, replace: true });
                },
              }}
            />
          ) : (
            <EmptyState
              messageKey="catalog.empty"
              action={
                filtersActive
                  ? {
                      labelKey: "catalog.actions.clear_filters",
                      onClick: () => {
                        void navigate({ search: {}, replace: true });
                      },
                    }
                  : undefined
              }
            />
          )
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 p-3 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
              {items.map((m) => (
                <ModelCard key={m.id} model={m} />
              ))}
            </div>
            <div className="flex items-center justify-center gap-2 p-4 text-sm">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                {t("common.prev")}
              </Button>
              <span className="text-muted-foreground">
                {page} / {lastPage} · {total} {t("catalog.totalSuffix")}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= lastPage}
                onClick={() => setPage(page + 1)}
              >
                {t("common.next")}
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
