import { useNavigate, useSearch } from "@tanstack/react-router";
import { useEffect, useMemo, useRef } from "react";
import { useTranslation } from "react-i18next";

import { applySearch } from "@/lib/search";
import { CategorySidebar } from "@/modules/catalog/components/CategorySidebar";
import { useModels } from "@/modules/catalog/hooks/useModels";
import type { ModelListItem } from "@/modules/catalog/types";
import type { CatalogSearch } from "@/routes/catalog/index";
import { EmptyState } from "@/ui/custom/EmptyState";
import { FilterBar, type FilterState, type SortKey } from "@/ui/custom/FilterBar";
import { ModelCard } from "@/ui/custom/ModelCard";
import { Input } from "@/ui/input";

const STORAGE_KEY = "catalog:last-filters";

export function CatalogList() {
  const { t } = useTranslation();
  const search = useSearch({ from: "/catalog/" });
  const navigate = useNavigate({ from: "/catalog/" });
  const { data, isLoading, isError } = useModels();

  const { category: searchCategory, status: searchStatus, sort: searchSort, q: searchQ } = search;

  // Hydrate from sessionStorage exactly once on mount, only if the URL has no
  // filters (e.g. arriving via the sidebar "Catalog" link). After that the URL
  // is the source of truth — clearing a filter must NOT trigger re-hydration.
  const hydratedRef = useRef(false);
  useEffect(() => {
    if (hydratedRef.current) return;
    hydratedRef.current = true;
    const isEmpty =
      searchCategory === undefined &&
      searchStatus === undefined &&
      searchSort === undefined &&
      searchQ === undefined;
    if (!isEmpty) return;
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw === null) return;
    try {
      const stored = JSON.parse(raw) as CatalogSearch;
      const hasAny =
        stored.category !== undefined ||
        stored.status !== undefined ||
        stored.sort !== undefined ||
        stored.q !== undefined;
      if (hasAny) void navigate({ search: stored, replace: true });
    } catch {
      sessionStorage.removeItem(STORAGE_KEY);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Persist current filters to sessionStorage on every change (including the
  // empty state, so an intentional clear doesn't get re-hydrated next visit).
  useEffect(() => {
    const isEmpty =
      searchCategory === undefined &&
      searchStatus === undefined &&
      searchSort === undefined &&
      searchQ === undefined;
    if (isEmpty) {
      sessionStorage.removeItem(STORAGE_KEY);
      return;
    }
    const snapshot: CatalogSearch = {
      category: searchCategory,
      status: searchStatus,
      sort: searchSort,
      q: searchQ,
    };
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
  }, [searchCategory, searchStatus, searchSort, searchQ]);

  const filterState: FilterState = {
    category: search.category ?? null,
    status: search.status ?? null,
    sort: search.sort ?? "recent",
  };
  const query = search.q ?? "";

  const setFilterState = (next: FilterState) => {
    void navigate({
      search: (prev: CatalogSearch): CatalogSearch => ({
        ...prev,
        category: next.category ?? undefined,
        status: next.status ?? undefined,
        sort: next.sort === "recent" ? undefined : next.sort,
      }),
      replace: true,
    });
  };

  const setQuery = (q: string) => {
    void navigate({
      search: (prev: CatalogSearch): CatalogSearch => ({
        ...prev,
        q: q === "" ? undefined : q,
      }),
      replace: true,
    });
  };

  const visible = useMemo(() => {
    if (data === undefined) return [];
    let items: ModelListItem[] = [...data.models];
    if (filterState.category !== null) items = items.filter((m) => m.category === filterState.category);
    if (filterState.status !== null) items = items.filter((m) => m.status === filterState.status);
    items = applySearch(items, query);
    items = sortModels(items, filterState.sort);
    return items;
  }, [data, filterState.category, filterState.status, filterState.sort, query]);

  if (isLoading) return <div className="p-4 text-sm text-muted-foreground">…</div>;
  if (isError || data === undefined) {
    return <div className="p-4 text-sm text-destructive">{t("errors.network")}</div>;
  }

  return (
    <div className="flex">
      <CategorySidebar models={data.models} state={filterState} onChange={setFilterState} />
      <div className="min-w-0 flex-1">
        <div className="hidden border-b border-border bg-background/95 p-3 lg:block">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("common.search")}
          />
        </div>
        <FilterBar state={filterState} onChange={setFilterState} />
        {visible.length === 0 ? (
          <EmptyState messageKey="catalog.empty" />
        ) : (
          <div className="grid grid-cols-2 gap-3 p-3 md:grid-cols-3 lg:grid-cols-4">
            {visible.map((m) => <ModelCard key={m.id} model={m} />)}
          </div>
        )}
      </div>
    </div>
  );
}

function sortModels(items: ModelListItem[], sort: SortKey): ModelListItem[] {
  const copy = [...items];
  switch (sort) {
    case "recent":
      return copy.sort((a, b) => b.date_added.localeCompare(a.date_added));
    case "oldest":
      return copy.sort((a, b) => a.date_added.localeCompare(b.date_added));
    case "name_asc":
      return copy.sort((a, b) => a.name_en.localeCompare(b.name_en));
    case "name_desc":
      return copy.sort((a, b) => b.name_en.localeCompare(a.name_en));
    case "status":
      return copy.sort((a, b) => a.status.localeCompare(b.status));
  }
}
