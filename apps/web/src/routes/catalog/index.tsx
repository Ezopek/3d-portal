import { createFileRoute } from "@tanstack/react-router";

import { CatalogList } from "@/modules/catalog/routes/CatalogList";
import type { ModelListSort } from "@/modules/catalog/hooks/useModels";
import type { ModelSource, ModelStatus } from "@/lib/api-types";

const STATUSES: readonly ModelStatus[] = ["not_printed", "printed", "in_progress", "broken"];
const SOURCES: readonly ModelSource[] = [
  "unknown",
  "printables",
  "thangs",
  "makerworld",
  "cults3d",
  "thingiverse",
  "own",
  "other",
];
const SORTS: readonly ModelListSort[] = [
  "recent",
  "oldest",
  "name_asc",
  "name_desc",
  "status",
  "rating",
];

export interface CatalogSearch {
  category_id?: string;
  tag_ids?: string[];
  status?: ModelStatus;
  source?: ModelSource;
  sort?: ModelListSort;
  q?: string;
  page?: number;
}

export const Route = createFileRoute("/catalog/")({
  component: CatalogList,
  validateSearch: (raw: Record<string, unknown>): CatalogSearch => {
    const out: CatalogSearch = {};
    if (typeof raw.category_id === "string" && raw.category_id.length > 0) {
      out.category_id = raw.category_id;
    }
    if (Array.isArray(raw.tag_ids)) {
      const arr = raw.tag_ids.filter((x): x is string => typeof x === "string");
      if (arr.length > 0) out.tag_ids = arr;
    } else if (typeof raw.tag_ids === "string" && raw.tag_ids.length > 0) {
      out.tag_ids = [raw.tag_ids];
    }
    if (typeof raw.status === "string" && (STATUSES as readonly string[]).includes(raw.status)) {
      out.status = raw.status as ModelStatus;
    }
    if (typeof raw.source === "string" && (SOURCES as readonly string[]).includes(raw.source)) {
      out.source = raw.source as ModelSource;
    }
    if (typeof raw.sort === "string" && (SORTS as readonly string[]).includes(raw.sort)) {
      out.sort = raw.sort as ModelListSort;
    }
    if (typeof raw.q === "string" && raw.q.length > 0) {
      out.q = raw.q;
    }
    if (typeof raw.page === "number" && raw.page > 0) {
      out.page = Math.floor(raw.page);
    } else if (typeof raw.page === "string" && raw.page.length > 0) {
      const parsed = Number(raw.page);
      if (!Number.isNaN(parsed) && parsed > 0) out.page = Math.floor(parsed);
    }
    return out;
  },
});
