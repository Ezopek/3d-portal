import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { applySearch } from "@/lib/search";
import { CategorySidebar } from "@/modules/catalog/components/CategorySidebar";
import { useModels } from "@/modules/catalog/hooks/useModels";
import type { ModelListItem } from "@/modules/catalog/types";
import { EmptyState } from "@/ui/custom/EmptyState";
import { FilterBar, type FilterState, type SortKey } from "@/ui/custom/FilterBar";
import { ModelCard } from "@/ui/custom/ModelCard";
import { Input } from "@/ui/input";

export function CatalogList() {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useModels();
  const [state, setState] = useState<FilterState>({ category: null, status: null, sort: "recent" });
  const [query, setQuery] = useState("");

  const visible = useMemo(() => {
    if (data === undefined) return [];
    let items: ModelListItem[] = [...data.models];
    if (state.category !== null) items = items.filter((m) => m.category === state.category);
    if (state.status !== null) items = items.filter((m) => m.status === state.status);
    items = applySearch(items, query);
    items = sortModels(items, state.sort);
    return items;
  }, [data, state, query]);

  if (isLoading) return <div className="p-4 text-sm text-muted-foreground">…</div>;
  if (isError || data === undefined) {
    return <div className="p-4 text-sm text-destructive">{t("errors.network")}</div>;
  }

  return (
    <div className="flex">
      <CategorySidebar models={data.models} state={state} onChange={setState} />
      <div className="flex-1">
        <div className="hidden border-b border-border bg-background/95 p-3 lg:block">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("common.search")}
          />
        </div>
        <FilterBar state={state} onChange={setState} />
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
