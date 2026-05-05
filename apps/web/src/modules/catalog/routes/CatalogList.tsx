import { useNavigate, useSearch } from "@tanstack/react-router";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { CategoryTreeSidebar } from "@/modules/catalog/components/CategoryTreeSidebar";
import { FilterRibbon, type FilterRibbonState } from "@/modules/catalog/components/FilterRibbon";
import { useCategoriesTree } from "@/modules/catalog/hooks/useCategoriesTree";
import { useModels } from "@/modules/catalog/hooks/useModels";
import { useTags } from "@/modules/catalog/hooks/useTags";
import type { CatalogSearch } from "@/routes/catalog/index";
import { Button } from "@/ui/button";
import { EmptyState } from "@/ui/custom/EmptyState";
import { ModelCard } from "@/ui/custom/ModelCard";

const PAGE_SIZE = 48;

export function CatalogList() {
  const { t } = useTranslation();
  const search = useSearch({ from: "/catalog/" });
  const navigate = useNavigate({ from: "/catalog/" });

  const tree = useCategoriesTree();
  const tags = useTags();
  const tagsData = tags.data;
  const tagsById = useMemo(() => {
    const m = new Map<string, NonNullable<typeof tagsData>[number]>();
    for (const tag of tagsData ?? []) m.set(tag.id, tag);
    return m;
  }, [tagsData]);

  const models = useModels({
    category_id: search.category_id,
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

  // Counts map: cheap derivation from current `models.data`. Best-effort.
  // For accurate per-category counts the backend would need to ship them
  // alongside the tree; deferred until a later slice.
  const counts = useMemo(() => {
    const m = new Map<string | null, number>();
    m.set(null, models.data?.total ?? 0);
    return m;
  }, [models.data?.total]);

  if (tree.isLoading || models.isLoading) {
    return <div className="p-4 text-sm text-muted-foreground">…</div>;
  }
  if (tree.isError || models.isError) {
    return <div className="p-4 text-sm text-destructive">{t("errors.network")}</div>;
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
          counts={counts}
          selectedId={search.category_id ?? null}
          onSelect={setCategoryId}
        />
      )}
      <div className="min-w-0 flex-1">
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
