import { createFileRoute, redirect } from "@tanstack/react-router";

import { CatalogList } from "@/modules/catalog/routes/CatalogList";
import type { ModelListSort } from "@/modules/catalog/hooks/useModels";
import type { ModelSource, ModelStatus } from "@/lib/api-types";

const STATUSES: readonly ModelStatus[] = [
  "not_printed",
  "printed",
  "in_progress",
  "broken",
];
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
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export interface CatalogSearch {
  tag_ids?: string[];
  tag_match?: TagMatch;
  untagged?: boolean;
  status?: ModelStatus;
  source?: ModelSource;
  // Initiative 26 (Story 50.2) — ONE browse-category slug. An INDEPENDENT
  // visible URL layer: never folded into tag_match, never counted in the
  // FilterRibbon's Filters (n) badge. The scope chip and the
  // "Search entire catalog" escape are Story 51.2.
  category?: string;
  sort?: ModelListSort;
  q?: string;
  page?: number;
}

// Exported so `/categories/$slug` can RE-USE it rather than re-author it
// (Story 51.2 D-3). Definition site and every rule below are unchanged: the
// 43.3 canonical-UUID `tag_ids` hardening, the E44.2 `tag_match` >=2-tag
// normalisation and the 50.2 `category` trim/drop all keep their exact shape,
// which is what makes `routes/catalog/index.test.ts` pass unmodified (AC-3).
// eslint-disable-next-line react-refresh/only-export-components -- Story 51.2 shares the exact search validator with /categories/$slug to avoid split URL semantics.
export function validateCatalogSearch(
  raw: Record<string, unknown>,
): CatalogSearch {
  const out: CatalogSearch = {};
  let tagIdCandidates: string[] | null = null;
  if (Array.isArray(raw.tag_ids)) {
    tagIdCandidates = raw.tag_ids.filter(
      (x): x is string => typeof x === "string",
    );
  } else if (typeof raw.tag_ids === "string") {
    tagIdCandidates = [raw.tag_ids];
  }
  if (tagIdCandidates !== null) {
    const seen = new Set<string>();
    const normalized: string[] = [];
    for (const candidate of tagIdCandidates) {
      const trimmed = candidate.trim();
      if (trimmed.length === 0 || !UUID_RE.test(trimmed) || seen.has(trimmed))
        continue;
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
  if (
    typeof raw.status === "string" &&
    (STATUSES as readonly string[]).includes(raw.status)
  ) {
    out.status = raw.status as ModelStatus;
  }
  if (
    typeof raw.source === "string" &&
    (SOURCES as readonly string[]).includes(raw.source)
  ) {
    out.source = raw.source as ModelSource;
  }
  // Initiative 26 (Story 50.2). A SINGLE slug — an array (`?category=a&category=b`)
  // is dropped wholesale rather than silently reduced to one element, because
  // FR26-BROWSE-2 allows exactly one active scope and a silent pick would make
  // the URL lie about which one. No format check: the wire type is a bare
  // `str | None` (`sot/router.py:196`) and an unknown slug returns 200 + an
  // empty page (`service.py:357-375`), so there is no 422 to protect against —
  // unlike `tag_ids`, whose wire type IS `uuid.UUID`. Trim + drop-if-empty is
  // required, not cosmetic: the backend treats `category=""` as a real,
  // unsatisfiable filter (`if category is not None`), which would blank the
  // catalog with no visible cause.
  if (typeof raw.category === "string") {
    const trimmed = raw.category.trim();
    if (trimmed.length > 0) out.category = trimmed;
  }
  if (
    typeof raw.sort === "string" &&
    (SORTS as readonly string[]).includes(raw.sort)
  ) {
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
}

// The search layer BOTH catalog surfaces share. `category` is absent by
// construction: since Story 51.2 the browse scope lives in the path and only
// there (D-1), so anything that forwards search across the two routes is typed
// exactly and cannot smuggle a second scope source back in.
export type CatalogListSearch = Omit<CatalogSearch, "category">;

export const Route = createFileRoute("/catalog/")({
  component: CatalogListRoute,
  validateSearch: validateCatalogSearch,
  // Story 51.2 D-12 — `/catalog?category=<slug>` is CANONICALISED, not
  // tolerated. Story 51.1 shipped the writer for that URL form (and the 51.1
  // deploy smoke itself used one), so those links exist in the wild; leaving
  // them working-but-non-canonical would mean `CatalogList` reads its scope
  // from two places forever. `replace: true` keeps the legacy URL out of
  // history. This cannot loop: the destination's schema has no `category`, so
  // the condition is false the moment we land (AC-4).
  beforeLoad: ({ search }) => {
    const { category, ...rest } = search;
    if (category !== undefined) {
      throw redirect({
        to: "/categories/$slug",
        params: { slug: category },
        search: rest,
        replace: true,
      });
    }
  },
});

// Story 51.2 D-2 — each route owns its own router binding and hands
// `CatalogList` three plain props, so the shared component is route-agnostic.
// `scopeSlug` is `undefined` here by construction: this is the unscoped
// catalogue, and the `beforeLoad` above guarantees no `?category=` survives.
function CatalogListRoute() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  return (
    <CatalogList
      scopeSlug={undefined}
      search={search}
      onSearchChange={(updater) =>
        void navigate({ search: updater, replace: true })
      }
    />
  );
}
