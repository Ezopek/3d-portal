import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { ModelListResponse, ModelSource, ModelStatus } from "@/lib/api-types";

export type ModelListSort = "recent" | "oldest" | "name_asc" | "name_desc" | "status" | "rating";

export interface ModelsFilters {
  category_id?: string;
  /**
   * Multiple category ids (e.g. a parent and all its descendants). Sent as
   * repeated `?category_ids=` query params. When both `category_id` and
   * `category_ids` are provided, `category_ids` wins.
   */
  category_ids?: string[];
  tag_ids?: string[];
  status?: ModelStatus;
  source?: ModelSource;
  q?: string;
  sort?: ModelListSort;
  page?: number; // 1-indexed
}

const PAGE_SIZE = 48;

export function useModels(filters: ModelsFilters) {
  const params = buildParams(filters);
  const path = `/models?${params.toString()}`;
  return useQuery<ModelListResponse>({
    queryKey: ["sot", "models", filters],
    queryFn: () => api<ModelListResponse>(path),
    staleTime: 30 * 1000,
    // Hold onto the previous result while a new filter set is loading so
    // CatalogList does not unmount its search input on every keystroke
    // (the early-return loading branch renders only when `data` is
    // undefined). Without this, typing into the search box loses focus
    // after each character.
    placeholderData: keepPreviousData,
  });
}

function buildParams(f: ModelsFilters): URLSearchParams {
  const p = new URLSearchParams();
  if (f.category_ids !== undefined && f.category_ids.length > 0) {
    for (const cid of f.category_ids) p.append("category_ids", cid);
  } else if (f.category_id !== undefined) {
    p.append("category_ids", f.category_id);
  }
  if (f.tag_ids !== undefined) {
    for (const tid of f.tag_ids) p.append("tag_ids", tid);
  }
  if (f.status !== undefined) p.set("status", f.status);
  if (f.source !== undefined) p.set("source", f.source);
  if (f.q !== undefined && f.q.length > 0) p.set("q", f.q);
  p.set("sort", f.sort ?? "recent");
  const page = f.page ?? 1;
  const offset = (page - 1) * PAGE_SIZE;
  p.set("offset", String(offset));
  p.set("limit", String(PAGE_SIZE));
  return p;
}

export const PAGE_SIZE_EXPORT = PAGE_SIZE;
