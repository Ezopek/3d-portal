import { useNavigate, useSearch } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import type { CategoryNode, CategoryTree } from "@/lib/api-types";
import { CategoryTreeSidebar } from "@/modules/catalog/components/CategoryTreeSidebar";
import { FilterRibbon, type FilterRibbonState } from "@/modules/catalog/components/FilterRibbon";
import { useCategoriesTree } from "@/modules/catalog/hooks/useCategoriesTree";
import { useModels } from "@/modules/catalog/hooks/useModels";
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
  const [mobileCategoriesOpen, setMobileCategoriesOpen] = useState(false);

  const tree = useCategoriesTree();
  const tags = useTags();
  const tagsData = tags.data;
  const tagsById = useMemo(() => {
    const m = new Map<string, NonNullable<typeof tagsData>[number]>();
    for (const tag of tagsData ?? []) m.set(tag.id, tag);
    return m;
  }, [tagsData]);

  const categoryIds = useMemo(
    () => expandCategoryIds(tree.data, search.category_id),
    [tree.data, search.category_id],
  );

  const models = useModels({
    category_ids: categoryIds,
    tag_ids: search.tag_ids,
    status: search.status,
    source: search.source,
    q: search.q,
    sort: search.sort,
    page: search.page,
  });

  const filterState: FilterRibbonState = {
    q: search.q ?? "",
    tag_ids: search.tag_ids ?? [],
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
        status: next.status,
        source: next.source,
        sort: next.sort === "recent" ? undefined : next.sort,
        page: undefined, // reset to page 1 on any filter change
      }),
      replace: true,
    });
  }

  function setCategoryId(id: string | null) {
    void navigate({
      search: (prev: CatalogSearch): CatalogSearch => ({
        ...prev,
        category_id: id === null ? undefined : id,
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
  // false. Without this, CategoryTreeSidebar paints with empty subtree counts
  // before `tree.data` resolves (QA round 2 issue 3).
  if (tree.isError || models.isError) {
    return (
      <EmptyState
        messageKey="errors.network"
        tone="error"
        action={{
          labelKey: "common.retry",
          onClick: () => {
            void tree.refetch();
            void models.refetch();
          },
        }}
      />
    );
  }
  if (tree.data === undefined || models.data === undefined) {
    return <LoadingState variant="skeleton-grid" cols={5} rows={3} />;
  }

  const items = models.data?.items ?? [];
  const total = models.data?.total ?? 0;
  const offset = models.data?.offset ?? 0;
  const limit = models.data?.limit ?? PAGE_SIZE;
  const page = Math.floor(offset / limit) + 1;
  const lastPage = Math.max(1, Math.ceil(total / limit));

  const filtersActive =
    search.category_id !== undefined ||
    (search.tag_ids?.length ?? 0) > 0 ||
    search.status !== undefined ||
    search.source !== undefined ||
    (search.q?.length ?? 0) > 0;

  return (
    <div className="flex">
      {tree.data !== undefined && (
        <CategoryTreeSidebar
          tree={tree.data}
          selectedId={search.category_id ?? null}
          onSelect={setCategoryId}
        />
      )}
      <div className="min-w-0 flex-1">
        {tree.data !== undefined && (
          <div className="border-b border-border bg-background/95 px-3 pt-3 lg:hidden">
            <Sheet open={mobileCategoriesOpen} onOpenChange={setMobileCategoriesOpen}>
              <SheetTrigger
                render={
                  <Button variant="outline" size="sm" className="w-full justify-start">
                    {t("catalog.filters.openCategories")}
                  </Button>
                }
              />
              <SheetContent side="left" className="w-80 max-w-[85vw] overflow-y-auto p-0">
                <SheetHeader>
                  <SheetTitle>{t("catalog.filters.openCategories")}</SheetTitle>
                </SheetHeader>
                <CategoryTreeSidebar
                  tree={tree.data}
                  selectedId={search.category_id ?? null}
                  onSelect={(id) => {
                    setCategoryId(id);
                    setMobileCategoriesOpen(false);
                  }}
                  mobile
                />
              </SheetContent>
            </Sheet>
          </div>
        )}
        <FilterRibbon state={filterState} tagsById={tagsById} onChange={setFilters} />
        {items.length === 0 ? (
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
                {page} / {lastPage} · {total} {t("catalog.totalSuffix", { defaultValue: "total" })}
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

/**
 * Expand a selected category id to the list of ids the API should match.
 *
 * Backend `/api/models?category_ids=...` filters by exact match, so picking a
 * parent like "Practical" without expansion returns 0 models even when its
 * children (e.g. "Practical → Cables") have plenty. This walks the loaded
 * tree and returns the selected id plus all descendant ids.
 *
 * Returns `undefined` (no filter) when the user has not selected a category.
 * Returns `[selectedId]` as a degenerate fallback when the tree is not yet
 * loaded or the id is not found — that matches pre-fix behavior so we never
 * silently widen the result set.
 */
function expandCategoryIds(
  tree: CategoryTree | undefined,
  selectedId: string | undefined,
): string[] | undefined {
  if (selectedId === undefined) return undefined;
  if (tree === undefined) return [selectedId];
  const root = findNode(tree.roots, selectedId);
  if (root === null) return [selectedId];
  const ids: string[] = [];
  const stack: CategoryNode[] = [root];
  while (stack.length > 0) {
    const node = stack.pop() as CategoryNode;
    ids.push(node.id);
    for (const child of node.children) stack.push(child);
  }
  return ids;
}

function findNode(roots: CategoryNode[], id: string): CategoryNode | null {
  for (const node of roots) {
    if (node.id === id) return node;
    const found = findNode(node.children, id);
    if (found !== null) return found;
  }
  return null;
}
