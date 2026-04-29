import Fuse from "fuse.js";

import type { ModelListItem } from "@/modules/catalog/types";

export function buildIndex(models: readonly ModelListItem[]): Fuse<ModelListItem> {
  return new Fuse(models as ModelListItem[], {
    keys: ["name_en", "name_pl", "tags"],
    threshold: 0.32,
    ignoreLocation: true,
  });
}

export function applySearch(
  models: readonly ModelListItem[],
  query: string,
): ModelListItem[] {
  if (query.trim() === "") return [...models];
  return buildIndex(models).search(query).map((r) => r.item);
}
