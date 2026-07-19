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
  "crealitycloud",
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
const TAG_MATCHES = ["all", "any"] as const;
export type TagMatch = (typeof TAG_MATCHES)[number];

// Canonical 8-4-4-4-12 UUID, case-insensitive, version-agnostic. Deliberately a
// narrower subset of pydantic `uuid.UUID` (which also accepts hyphenless/braced/
// urn forms): validateSearch only ever DROPS an exotic form, never forwards a
// malformed one, so it cannot induce a backend 422 the wire type wouldn't.
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export interface CatalogSearch {
  category_id?: string;
  tag_ids?: string[];
  tag_match?: TagMatch;
  untagged?: boolean;
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
    let tagIdCandidates: string[] | null = null;
    if (Array.isArray(raw.tag_ids)) {
      tagIdCandidates = raw.tag_ids.filter((x): x is string => typeof x === "string");
    } else if (typeof raw.tag_ids === "string") {
      tagIdCandidates = [raw.tag_ids];
    }
    if (tagIdCandidates !== null) {
      const seen = new Set<string>();
      const normalized: string[] = [];
      for (const candidate of tagIdCandidates) {
        const trimmed = candidate.trim();
        if (trimmed.length === 0 || !UUID_RE.test(trimmed) || seen.has(trimmed)) continue;
        seen.add(trimmed);
        normalized.push(trimmed);
      }
      if (normalized.length > 0) out.tag_ids = normalized;
    }
    // `tag_match` (AND/OR) only changes results with ≥2 selected tags, so it is
    // only meaningful — and only surfaced by the FilterRibbon toggle — at that
    // threshold. Normalize it away below 2 tags so a hand-crafted URL cannot
    // strand an un-clearable `tag_match=any`, keeping this validator consistent
    // with `CatalogList.setFilters`, which gates the same write (E44.2 review).
    if (
      typeof raw.tag_match === "string" &&
      (TAG_MATCHES as readonly string[]).includes(raw.tag_match) &&
      raw.tag_match !== "all" &&
      (out.tag_ids?.length ?? 0) >= 2
    ) {
      out.tag_match = raw.tag_match as TagMatch;
    }
    if (raw.untagged === true || raw.untagged === "true") {
      out.untagged = true;
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
