import { createFileRoute } from "@tanstack/react-router";

import { CatalogList } from "@/modules/catalog/routes/CatalogList";
import { SORT_KEYS, type SortKey } from "@/modules/catalog/sortOptions";
import type { Category, Status } from "@/modules/catalog/types";

const CATEGORIES: readonly Category[] = [
  "decorations",
  "printer_3d",
  "gridfinity",
  "multiboard",
  "tools",
  "practical",
  "premium",
  "own_models",
  "other",
];

const STATUSES: readonly Status[] = ["printed", "not_printed", "in_progress", "needs_revision"];

export interface CatalogSearch {
  category?: Category;
  status?: Status;
  sort?: SortKey;
  q?: string;
}

export const Route = createFileRoute("/catalog/")({
  component: CatalogList,
  validateSearch: (raw: Record<string, unknown>): CatalogSearch => {
    const out: CatalogSearch = {};
    if (typeof raw.category === "string" && (CATEGORIES as readonly string[]).includes(raw.category)) {
      out.category = raw.category as Category;
    }
    if (typeof raw.status === "string" && (STATUSES as readonly string[]).includes(raw.status)) {
      out.status = raw.status as Status;
    }
    if (typeof raw.sort === "string" && (SORT_KEYS as readonly string[]).includes(raw.sort)) {
      out.sort = raw.sort as SortKey;
    }
    if (typeof raw.q === "string" && raw.q.length > 0) {
      out.q = raw.q;
    }
    return out;
  },
});
