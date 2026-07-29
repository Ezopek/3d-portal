import { Link } from "@tanstack/react-router";
import type { MouseEvent } from "react";
import { useTranslation } from "react-i18next";

import type { BrowseCategoryRead } from "@/lib/api-types";
import { cn } from "@/lib/utils";
import type { CatalogListSearch } from "@/routes/catalog/index";

// Number of placeholder rows painted while the category read is pending. Sized
// to the ratified starter taxonomy (eight governed categories, G26-CAT-SET) so
// the skeleton occupies roughly the height the resolved list will occupy and
// the column does not visibly jump. Module-local and unexported so the file's
// only export stays the component — otherwise
// `react-refresh/only-export-components` would warn, and lint runs with
// `--max-warnings=0` (mirrors the same guard in `FacetSidebar.tsx`).
const SKELETON_ROW_COUNT = 6;

interface Props {
  categories: BrowseCategoryRead[];
  /** `undefined` => no browse scope is active, so "All catalog" is current. */
  activeSlug: string | undefined;
  /** Current URL search layer, carried across every row's navigation (AC-14). */
  search: CatalogListSearch;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  /** Fired from a row's `Link onClick`, in addition to its own navigation —
   * used by `BrowseSheet` to close itself on selection (Story 51.3 D-2).
   * `BrowseRail` passes nothing, so its own behavior is byte-unchanged. */
  onNavigate?: () => void;
}

// The active treatment is copied verbatim from the shipped `ModuleRail`
// (`shell/ModuleRail.tsx:34`) rather than re-derived: the UX spine requires the
// active browse row and the active module row to be visually identical, so
// "which category am I in" reads as location exactly like "which module am I
// in" (DESIGN.md:269, :194). Primary — never accent — because accent is the
// selected-tag vocabulary and would collide with the tag chips (DESIGN.md:204).
const ROW_BASE =
  "flex min-h-9 w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm";
const ROW_ACTIVE =
  "bg-primary/10 text-foreground font-medium ring-1 ring-inset ring-primary";
const ROW_IDLE = "text-muted-foreground hover:text-foreground hover:bg-accent";

// A modified click (middle-click, Cmd/Ctrl/Shift/Alt-click) opens the target
// in a new tab/window instead of navigating the current one — `Link` itself
// skips its own SPA navigation for these (matching browser-default
// behavior), so `onNavigate` must skip closing the sheet for the same
// clicks, or a background-tab open would still collapse the open sheet.
const isPlainLeftClick = (event: MouseEvent) =>
  event.button === 0 &&
  !event.metaKey &&
  !event.altKey &&
  !event.ctrlKey &&
  !event.shiftKey;

export function BrowseCategoryList({
  categories,
  activeSlug,
  search,
  isLoading,
  isError,
  onRetry,
  onNavigate,
}: Props) {
  const { t, i18n } = useTranslation();
  const preferPl = i18n.language.startsWith("pl");
  // Empty string is a valid `name_pl` per the API type; treat it like null and
  // fall back to `name_en` so a pl-locale row never renders a blank label
  // (same guard as `FacetSidebar` and `ModelHero`).
  const labelOf = (item: { name_en: string; name_pl: string | null }) =>
    preferPl && item.name_pl ? item.name_pl : item.name_en;

  const allActive = activeSlug === undefined;

  return (
    <>
      <ul className="flex flex-col gap-1 p-2">
        {/* Story 51.2 D-4 — rows are `Link`s, discharging the divergence 51.1
            recorded (EXPERIENCE.md:219 says each row IS a Link; 51.1 deferred it
            only because the target route did not exist yet). An anchor gives
            middle-click, copy-link-address and the browser's own hover URL for
            free, which is exactly what a NAVIGATION surface owes. A scope change
            is a real navigation, so these PUSH (no `replace`) and Back returns
            to the previous category (D-5). `page` resets because the result set
            changes; every other URL layer is forwarded verbatim.

            An explicit search OBJECT rather than an updater: an updater's `prev`
            is typed as the union across every registered route, which is the
            same silent-widening trap D-2 rejected `useSearch({strict:false})`
            for. `CatalogListSearch` is exact at both link targets. */}
        <li>
          <Link
            to="/catalog"
            aria-current={allActive ? "page" : undefined}
            search={{ ...search, page: undefined }}
            className={cn(ROW_BASE, allActive ? ROW_ACTIVE : ROW_IDLE)}
            onClick={(event) => {
              if (isPlainLeftClick(event)) onNavigate?.();
            }}
          >
            <span className="flex-1 truncate">
              {t("catalog.browse.allCatalog")}
            </span>
          </Link>
        </li>
        {/* Rendered in API order — the backend sorts by `(position, slug)` and
            owns that contract (architecture.md Decision AY); re-sorting here
            would silently fork it. `parent_id` is deliberately ignored: MVP
            browse is flat (FR26-CAT-4), so no row nests inside another. */}
        {categories.map((c) => {
          const active = c.slug === activeSlug;
          const label = labelOf(c);
          return (
            <li key={c.id}>
              <Link
                to="/categories/$slug"
                params={{ slug: c.slug }}
                aria-current={active ? "page" : undefined}
                // Label and count are folded into ONE accessible name so a
                // screen reader announces the row as a single item rather than
                // a label followed by a stray number (EXPERIENCE.md:220).
                aria-label={t("catalog.browse.categoryWithCount", {
                  name: label,
                  count: c.model_count,
                })}
                search={{ ...search, page: undefined }}
                className={cn(ROW_BASE, active ? ROW_ACTIVE : ROW_IDLE)}
                onClick={(event) => {
                  if (isPlainLeftClick(event)) onNavigate?.();
                }}
              >
                <span
                  className={cn(
                    "flex-1 truncate",
                    // An empty category is dimmed but stays focusable and
                    // navigable — never hidden (DESIGN.md:271).
                    c.model_count === 0 &&
                      !active &&
                      "text-muted-foreground/60",
                  )}
                >
                  {label}
                </span>
                <span className="text-xs tabular-nums text-muted-foreground">
                  {c.model_count}
                </span>
              </Link>
            </li>
          );
        })}
        {isLoading &&
          Array.from({ length: SKELETON_ROW_COUNT }, (_, i) => (
            <li key={`skeleton-${i}`} aria-hidden>
              <div
                data-testid="browse-rail-skeleton"
                className="min-h-9 animate-pulse rounded-md bg-muted"
              />
            </li>
          ))}
      </ul>
      {/* A failed navigation aid must never make the catalogue unreachable, so
          the list degrades to "All catalog" plus an inline retry while the grid
          stays fully usable (EXPERIENCE.md:253). Reuses the shipped
          `errors.network` / `common.retry` copy. */}
      {isError && (
        <div className="mt-1 flex flex-col items-start gap-1 px-3 pb-2">
          <p className="text-xs text-muted-foreground">{t("errors.network")}</p>
          <button
            type="button"
            onClick={onRetry}
            className="min-h-9 rounded-md text-xs font-medium text-primary underline-offset-2 hover:underline"
          >
            {t("common.retry")}
          </button>
        </div>
      )}
    </>
  );
}
