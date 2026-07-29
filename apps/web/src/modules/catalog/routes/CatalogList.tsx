import { useNavigate, useRouterState } from "@tanstack/react-router";
import { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { AddModelButton } from "@/modules/admin/AddModelButton";
import { BrowseRail } from "@/modules/catalog/components/BrowseRail";
import { BrowseSheet } from "@/modules/catalog/components/BrowseSheet";
import {
  FilterRibbon,
  type FilterRibbonState,
} from "@/modules/catalog/components/FilterRibbon";
import { FiltersPanel } from "@/modules/catalog/components/FiltersPanel";
import { ScopeChip } from "@/modules/catalog/components/ScopeChip";
import { useCategories } from "@/modules/catalog/hooks/useCategories";
import { useModels } from "@/modules/catalog/hooks/useModels";
import { useTagGroups } from "@/modules/catalog/hooks/useTagGroups";
import { useTags } from "@/modules/catalog/hooks/useTags";
import type { CatalogSearch } from "@/routes/catalog/index";
import { Button } from "@/ui/button";
import { EmptyState } from "@/ui/custom/EmptyState";
import { LoadingState } from "@/ui/custom/LoadingState";
import { ModelCard } from "@/ui/custom/ModelCard";

const PAGE_SIZE = 48;

interface Props {
  /** Path-borne browse scope. `undefined` on /catalog — the unscoped catalogue. */
  scopeSlug: string | undefined;
  search: CatalogSearch;
  /** Route-bound search updater. Always replace:true — the shipped behaviour. */
  onSearchChange: (updater: (prev: CatalogSearch) => CatalogSearch) => void;
}

// Story 51.2 D-2 — this component is shared verbatim by `/catalog` and
// `/categories/$slug`, so it no longer binds itself to one route id. Each route
// file resolves `search` / `params` / `navigate` through its own strictly-typed
// `Route.use*` hooks and passes the three props above. `useSearch({strict:false})`
// was rejected: its result is the union across every registered route, so
// `search.q` would only typecheck by accident and would widen silently whenever
// an unrelated route changed.
export function CatalogList({ scopeSlug, search, onSearchChange }: Props) {
  const { t, i18n } = useTranslation();
  // Unbound on purpose: the ONLY navigation this component owns that leaves the
  // current route is the scope escape, and it targets one literal path with an
  // explicit (not updater-derived) search object — so it stays exactly typed
  // without reintroducing the route-tree coupling D-2 removed.
  const navigate = useNavigate();
  // Story 52.1 D-5 — 51.3's three-boolean invariant collapses to two. There is
  // exactly ONE filter surface now, so the Browse sheet and the Filters sheet
  // are siblings: opening one closes the other (EXPERIENCE.md:62, :333). The
  // second boolean is `filtersOpen`, NOT `mobileFiltersOpen` — after D-6 the
  // panel exists on desktop too, so a `mobile` prefix would be a lie.
  //
  // Per EXPERIENCE.md:367 neither open state is written to the URL or
  // persisted; the panel is deliberately not a linkable surface.
  const [mobileBrowseOpen, setMobileBrowseOpenState] = useState(false);
  const [filtersOpen, setFiltersOpenState] = useState(false);

  function setMobileBrowseOpen(open: boolean) {
    setMobileBrowseOpenState(open);
    if (open) setFiltersOpenState(false);
  }
  function setFiltersOpen(open: boolean) {
    setFiltersOpenState(open);
    if (open) setMobileBrowseOpenState(false);
  }

  const tagGroups = useTagGroups();
  const tags = useTags();
  // Initiative 26 (Story 51.1) — the browse rail's data source. Deliberately
  // NOT part of either fatal guard below: a pending or failed navigation aid
  // must never blank an already-painted grid (EXPERIENCE.md:242, :253). The
  // rail owns its own loading/error/retry surface.
  const categories = useCategories();
  const tagsData = tags.data;
  const tagsById = useMemo(() => {
    const m = new Map<string, NonNullable<typeof tagsData>[number]>();
    for (const tag of tagsData ?? []) m.set(tag.id, tag);
    return m;
  }, [tagsData]);

  const models = useModels({
    tag_ids: search.tag_ids,
    tag_match: search.tag_match,
    untagged: search.untagged,
    status: search.status,
    source: search.source,
    // Story 51.2 D-1 — the scope comes from the PATH now, never from a search
    // param. One source of truth for the chip, the rail's active row and this
    // query, so they cannot disagree.
    category: scopeSlug,
    q: search.q,
    sort: search.sort,
    page: search.page,
  });

  // Story 51.2 D-7 — the chip's label reads the ALREADY-loaded category list
  // (mounted unconditionally above), so a scope change costs zero extra
  // requests. `useCategoryBySlug` is deliberately NOT mounted here: it 404s on
  // an unknown slug, and the UX contract requires an unknown slug to render an
  // empty page with a working escape, never an error surface
  // (EXPERIENCE.md:258). Falling back to the raw slug covers all three
  // non-resolving states — unknown slug, pending list, failed list — in one path.
  const preferPl = i18n.language.startsWith("pl");
  const categoriesData = categories.data;
  const scopeLabel = useMemo(() => {
    if (scopeSlug === undefined) return undefined;
    const hit = categoriesData?.find((c) => c.slug === scopeSlug);
    if (hit === undefined) return scopeSlug;
    return preferPl && hit.name_pl ? hit.name_pl : hit.name_en;
  }, [categoriesData, scopeSlug, preferPl]);

  // Story 51.2 D-10 — EXPERIENCE.md:324 puts focus on the results heading after
  // a scope change, not at the top of the document.
  //
  // Two things make this trickier than a `useEffect` on `scopeSlug`. First,
  // `/catalog` and `/categories/$slug` are different routes, so a scope change
  // REMOUNTS this component — a "previous scope" ref cannot survive it to tell a
  // navigation apart from a cold load. The history index can: it is 0 for the
  // entry the session started on and increments on every push, and it lives in
  // the router, not in React. Second, a remount lands on the loading branch
  // below (a fresh query key has no data yet), so the heading does not exist
  // when a mount effect would run — hence a ref CALLBACK, which fires when the
  // node actually attaches.
  //
  // Net effect: focus moves when the user navigates to a scope, and does NOT
  // move on a cold load (which would strand Tab past the browse rail) or on a
  // filter / sort / page change (all `replace`, so the index does not move and
  // the callback identity is stable, so it is never re-invoked).
  const arrivedByNavigation = useRouterState({
    select: (s) => s.location.state.__TSR_index > 0,
  });
  const headingRef = useCallback(
    (node: HTMLHeadingElement | null) => {
      if (node !== null && arrivedByNavigation) node.focus();
    },
    [arrivedByNavigation],
  );

  // Story 51.2 D-1 — the search layer this component hands onward (rail hrefs,
  // the chip escape) must never carry `category`. The scoped route's
  // `validateSearch` already strips it, but TanStack merges the ROOT match's
  // RAW parsed search into every child match, so a hand-crafted
  // `/categories/uchwyty?category=organizery` puts the stray token back and it
  // would ride forward into every onward URL — resurrecting the second scope
  // source D-1 exists to abolish. Dropped once, here, at the single seam.
  const { category: scopeLivesInThePath, ...forwardSearch } = search;
  void scopeLivesInThePath;

  const filterState: FilterRibbonState = {
    q: search.q ?? "",
    tag_ids: search.tag_ids ?? [],
    tag_match: search.tag_match ?? "all",
    status: search.status,
    source: search.source,
    sort: search.sort ?? "recent",
  };

  function setFilters(next: FilterRibbonState) {
    onSearchChange(
      (prev: CatalogSearch): CatalogSearch => ({
        ...prev,
        q: next.q.length > 0 ? next.q : undefined,
        tag_ids: next.tag_ids.length > 0 ? next.tag_ids : undefined,
        // Only persist a non-default tag_match while ≥2 tags are selected. AND
        // vs OR is meaningless with <2 tags, and the toggle that sets it hides
        // below that threshold — writing it anyway would strand an "any" the
        // user can no longer see or clear (review 2026-07-20).
        tag_match:
          next.tag_ids.length >= 2 && next.tag_match && next.tag_match !== "all"
            ? next.tag_match
            : undefined,
        status: next.status,
        source: next.source,
        sort: next.sort === "recent" ? undefined : next.sort,
        page: undefined, // reset to page 1 on any filter change
      }),
    );
  }

  function toggleTag(id: string) {
    onSearchChange((prev: CatalogSearch): CatalogSearch => {
      const current = prev.tag_ids ?? [];
      const next = current.includes(id)
        ? current.filter((tid) => tid !== id)
        : [...current, id];
      return {
        ...prev,
        // Let validateSearch normalize a now-stranded tag_match (a non-default
        // value only survives with ≥2 tags — E44.2 enforcement layer).
        tag_ids: next.length > 0 ? next : undefined,
        page: undefined,
      };
    });
  }

  function toggleUntagged() {
    onSearchChange(
      (prev: CatalogSearch): CatalogSearch => ({
        ...prev,
        untagged: prev.untagged ? undefined : true,
        page: undefined,
      }),
    );
  }

  function setPage(page: number) {
    onSearchChange(
      (prev: CatalogSearch): CatalogSearch => ({
        ...prev,
        page: page === 1 ? undefined : page,
      }),
    );
  }

  // Story 51.2 D-5 / AC-10 — the ONE navigation the scope escape performs, from
  // both the chip and the scoped empty states. It leaves the route, and leaving
  // the route IS the whole of the clearing: `q`, `tag_ids`, `tag_match`,
  // `untagged`, `status`, `source` and `sort` all ride along untouched, and only
  // `page` resets because the result set changes. Deliberately NOT
  // `replace: true` — a scope change is a genuine navigation, so Back returns
  // to the category you escaped (EXPERIENCE.md:387, D-5).
  function escapeScope() {
    void navigate({
      to: "/catalog",
      search: { ...forwardSearch, page: undefined },
    });
  }

  // Guard on data presence rather than `isLoading`: on the very first render
  // TanStack Query has not yet mounted the queries, so `isLoading` is still
  // false. Without this, FacetSidebar paints with empty group data before
  // `tagGroups.data` resolves.
  //
  // `tags` is deliberately NOT part of the fatal guard: it only feeds the
  // FilterRibbon chip-label map (`tagsById`), so a tags-only failure degrades
  // gracefully (chips fall back to a truncated id) while the grid, sidebar, and
  // pagination stay fully usable — blanking the whole catalog for a cosmetic
  // label gap would be a worse outcome. The retry below still refetches `tags`
  // so a shared-backend blip recovers everything in one click.
  if (tagGroups.isError || models.isError) {
    return (
      <EmptyState
        messageKey="errors.network"
        tone="error"
        action={{
          labelKey: "common.retry",
          onClick: () => {
            void tagGroups.refetch();
            void models.refetch();
            void tags.refetch();
          },
        }}
      />
    );
  }
  if (tagGroups.data === undefined || models.data === undefined) {
    return <LoadingState variant="skeleton-grid" cols={5} rows={3} />;
  }

  const items = models.data?.items ?? [];
  const total = models.data?.total ?? 0;
  const offset = models.data?.offset ?? 0;
  const limit = models.data?.limit ?? PAGE_SIZE;
  const page = Math.floor(offset / limit) + 1;
  const lastPage = Math.max(1, Math.ceil(total / limit));

  const filtersActive =
    (search.tag_ids?.length ?? 0) > 0 ||
    search.status !== undefined ||
    search.source !== undefined ||
    (search.q?.length ?? 0) > 0 ||
    search.untagged === true;

  // AND intersection that yields nothing is recoverable by switching to OR:
  // ≥2 tags selected with an effective AND (tag_match unset or "all") and the
  // whole filtered set (not just this page) is empty (HANDOFF mockup 08D). Key
  // on `total === 0`, not `items.length === 0`, so a stale `?page=2` overshoot
  // that still has matches on page 1 falls through to the Clear-filters branch
  // instead of falsely offering "Switch to OR" (review 2026-07-20).
  const andTooNarrow =
    total === 0 &&
    (search.tag_ids?.length ?? 0) >= 2 &&
    (search.tag_match ?? "all") === "all";

  return (
    <div className="flex">
      {/* Initiative 26 (Story 51.1) — the desktop left column is browse
          navigation now: broad categories only, never tag groups or tags
          (FR26-BROWSE-1). It occupies the exact `w-60 border-r` geometry the
          FacetSidebar <aside> held, so the cutover is a swap in one column
          rather than a grid reflow (DESIGN.md:242). The mobile Browse surface
          is Story 51.3. Since Story 51.2 the rows are `Link`s to
          /categories/$slug, so the rail owns no navigation callback. */}
      <BrowseRail
        categories={categories.data ?? []}
        activeSlug={scopeSlug}
        search={forwardSearch}
        isLoading={categories.data === undefined && !categories.isError}
        isError={categories.isError}
        onRetry={() => void categories.refetch()}
      />
      <div className="min-w-0 flex-1">
        {/* Story 51.2 D-10 — the results heading 51.1 deferred here because no
            heading existed. `sr-only` + `tabIndex={-1}`: it is the focus target
            for a scope change, never a tab stop, and it adds no pixels, so it
            cannot move a visual baseline. */}
        <h2 ref={headingRef} tabIndex={-1} className="sr-only">
          {scopeLabel ?? t("catalog.browse.allCatalog")}
        </h2>
        {/* Story 51.2 D-11 — ONE polite live region for the whole surface, not
            one per control (EXPERIENCE.md:314-316). Keying it on the result
            count satisfies all three required triggers at once — scope change,
            filter change and query commit each change `total`. The scope chip
            is deliberately NOT a live region; the count is. */}
        <p role="status" aria-live="polite" className="sr-only">
          {total} {t("catalog.totalSuffix")}
        </p>
        {/* Story 52.1 D-12 / AC-18 — the search row now comes FIRST, so the
            toolbar's reading AND tab order is search → Browse → Filters,
            matching EXPERIENCE.md:278. Before this story the two triggers sat
            above the search input, which put them ahead of it in both orders.
            No positive `tabIndex` is involved: DOM order does the whole job.

            Initiative 13 Story 20.2 — admin-only "Add Model" CTA in the
            catalog toolbar. Operator-aligned 2026-05-23: top-right placement
            next to filter controls. AddModelButton role-gates on isAdmin
            (non-admin users see nothing in this slot).
            Story 28.1 (Init 17 / TB-048): outer flex uses `items-center`
            so the AddModelButton's vertical center aligns with the
            FilterRibbon's (FilterRibbon is internally a single-row
            `items-center` flex of search input + active-constraint chips).
            The previous `items-start` + magic `pt-1` on the button
            wrapper produced a small mis-baseline that operator's
            hands-on (`tmp/add_model_misalligned.png`) flagged. The
            `pt-1` hack is now removed since `items-center` does the
            alignment canonically. */}
        <div className="flex items-center justify-between gap-3 px-3 pt-3">
          <div className="min-w-0 flex-1">
            <FilterRibbon
              state={filterState}
              tagsById={tagsById}
              onChange={setFilters}
            />
          </div>
          <div className="shrink-0">
            <AddModelButton />
          </div>
        </div>
        <div className="flex items-center gap-2 border-b border-border bg-background/95 px-3 pt-3">
          {/* Story 51.3 D-3 — the Browse trigger sits before the refinement
              trigger in the same toolbar row, distinct in both icon and label
              (EXPERIENCE.md:333). `lg:hidden` lives on the trigger itself
              (inside `BrowseSheet`) since the desktop rail already covers
              `lg`+. */}
          <BrowseSheet
            categories={categories.data ?? []}
            activeSlug={scopeSlug}
            search={forwardSearch}
            isLoading={categories.data === undefined && !categories.isError}
            isError={categories.isError}
            onRetry={() => void categories.refetch()}
            open={mobileBrowseOpen}
            onOpenChange={setMobileBrowseOpen}
          />
          {/* Story 52.1 D-1 — the ONE refinement control, replacing the "Tagi"
              facet sheet, the `md:hidden` "Filtry" sheet and the desktop
              inline select row. It receives no category/scope prop, which is
              why the browse scope cannot reach its `(n)` badge even by mistake
              (D-7). The three write paths stay separate (D-11): `setFilters`
              for the Selects, `toggleTag` / `toggleUntagged` for the facets. */}
          <FiltersPanel
            state={filterState}
            onChange={setFilters}
            groups={tagGroups.data.groups}
            groupless={tagGroups.data.groupless}
            onToggleTag={toggleTag}
            untaggedActive={search.untagged ?? false}
            onToggleUntagged={toggleUntagged}
            open={filtersOpen}
            onOpenChange={setFiltersOpen}
          />
        </div>
        {/* Story 51.2 AC-6/AC-7 — one full-width row between the toolbar and the
            grid, present on every viewport and absent from the DOM (not merely
            hidden) when nothing is scoped. `scopeLabel` is defined exactly when
            `scopeSlug` is, so this is the same condition stated once. */}
        {scopeLabel !== undefined && (
          <ScopeChip
            label={scopeLabel}
            otherConstraintsActive={filtersActive}
            search={forwardSearch}
          />
        )}
        {items.length === 0 ? (
          andTooNarrow ? (
            <EmptyState
              messageKey="catalog.empty"
              action={{
                labelKey: "catalog.actions.switch_to_or",
                onClick: () => {
                  onSearchChange(
                    (prev: CatalogSearch): CatalogSearch => ({
                      ...prev,
                      tag_match: "any",
                      page: undefined,
                    }),
                  );
                },
              }}
              secondaryAction={{
                labelKey: "catalog.actions.clear_filters",
                onClick: () => {
                  // Category is a SCOPE, not a filter (FR26-BROWSE-2), so
                  // "Clear filters" must not silently drop it. Since Story 51.2
                  // the scope lives in the PATH, so it now survives STRUCTURALLY
                  // — this handler cannot drop it even by mistake (AC-26).
                  onSearchChange(() => ({}));
                },
              }}
            />
          ) : total > 0 ? (
            // Page overshoot: the filtered set is non-empty but this page is
            // past its end (a stale/hand-crafted `?page=N`). Offer a "back to
            // first page" recovery rather than a dead end — and never
            // "Clear filters" here, which would needlessly wipe the user's
            // still-matching filters (review 2026-07-20).
            <EmptyState
              messageKey="catalog.emptyPage"
              action={{
                labelKey: "catalog.actions.back_to_page_1",
                onClick: () => setPage(1),
              }}
            />
          ) : scopeLabel !== undefined ? (
            // Story 51.2 AC-23/AC-24 — the scoped empty states, slotted AFTER
            // the shipped `andTooNarrow` and page-overshoot branches so neither
            // is shadowed (EXPERIENCE.md:247, AC-22/AC-25). Both offer the
            // scope escape as the primary recovery, because widening the place
            // is the only move that can turn an empty scoped page into results.
            filtersActive ? (
              <EmptyState
                messageKey="catalog.emptyInCategory"
                messageParams={{ name: scopeLabel }}
                action={{
                  // Keeps `q` and the tags, drops only the scope.
                  labelKey: "catalog.browse.searchEntireCatalog",
                  onClick: escapeScope,
                }}
                secondaryAction={{
                  // The mirror image: keeps the scope (structurally — it is in
                  // the path), drops everything else (EXPERIENCE.md:385).
                  labelKey: "catalog.actions.clear_filters",
                  onClick: () => onSearchChange(() => ({})),
                }}
              />
            ) : (
              <EmptyState
                messageKey="catalog.emptyCategory"
                action={{
                  labelKey: "catalog.browse.searchEntireCatalog",
                  onClick: escapeScope,
                }}
              />
            )
          ) : (
            <EmptyState
              messageKey="catalog.empty"
              action={
                filtersActive
                  ? {
                      labelKey: "catalog.actions.clear_filters",
                      onClick: () => onSearchChange(() => ({})),
                    }
                  : undefined
              }
            />
          )
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
                {page} / {lastPage} · {total} {t("catalog.totalSuffix")}
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
