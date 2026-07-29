import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import type { ModelDetail } from "@/lib/api-types";

// The LOCATION vocabulary, copied verbatim from the two shipped surfaces that
// already own it (`ScopeChip.tsx:26`, `BrowseCategoryList.tsx:41`) rather than
// re-derived — a category answers "where does this model live", exactly like
// the active browse-rail row and the active scope chip (DESIGN.md:140-144,
// :203). Never `bg-muted`/`accent`: that is the tag-chip vocabulary sitting
// directly below this row, and reusing it would make a place look like a
// filter (DESIGN.md:204, :294).
//
// `rounded-md`, deliberately not `rounded-full` — shape AND colour both
// separate a category from a tag chip (DESIGN.md:258). `min-h-6` is the 24×24
// CSS px floor WCAG 2.2 SC 2.5.8 asks for, while `px-2 py-0.5 text-xs` keeps
// the entry visually lighter than the full-width `ScopeChip`.
//
// Module-local and unexported so the file's only export stays the component —
// otherwise `react-refresh/only-export-components` would warn, and lint runs
// with `--max-warnings=0` (same guard as `BrowseCategoryList.tsx:9-16`).
const ENTRY =
  "inline-flex min-h-6 items-center rounded-md bg-primary/10 px-2 py-0.5 text-xs text-foreground ring-1 ring-inset ring-primary";

interface Props {
  detail: ModelDetail;
  isAdmin: boolean;
}

export function ModelCategoriesSection({ detail, isAdmin }: Props) {
  const { t, i18n } = useTranslation();
  // Read straight off the embedded summary — no hook, no fetch. The detail
  // contract deliberately carries no `model_count` (architecture.md Decision
  // AY), so enriching it via `useCategories()` would cost a request per detail
  // view for a number this surface never shows, and would make a LOCATION
  // label look like the rail's SIZE readout (D-10).
  const categories = detail.categories;

  // A zero-category model is normal, not broken: a member sees nothing at all
  // — no heading, no dash, no placeholder (FR26-CAT-2, EXPERIENCE.md:230,
  // :251). Only an admin, who can act on it, gets the advisory below.
  if (categories.length === 0 && !isAdmin) return null;

  const preferPl = i18n.language.startsWith("pl");
  // Empty string is a valid `name_pl` per the API type; treat it like null so
  // a pl-locale entry never renders a blank label (same guard as
  // `TagGroupsSection` and `BrowseCategoryList` — intentionally duplicated
  // module-locals, not a shared util).
  const labelOf = (item: { name_en: string; name_pl: string | null }) =>
    preferPl && item.name_pl ? item.name_pl : item.name_en;

  // Story 52.2 discharges 51.4's recorded handoff: `/admin/categories` now
  // exists, so the advisory becomes the "link to assign" EXPERIENCE.md:251
  // always specified. 51.4 shipped this as static text on purpose (D-5, V-8) —
  // the destination was backlog and a link to a 404 would have been worse than
  // an honest advisory. Member behaviour is unchanged: the early return above
  // still renders NOTHING for a non-admin, because a zero-category model is a
  // normal state, not a defect (FR26-CAT-2).
  if (categories.length === 0) {
    return (
      <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1">
        <Link
          to="/admin/categories"
          data-testid="model-categories-curation-link"
          className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
        >
          {t("catalog.browse.noCategoriesAdmin")}
        </Link>
      </div>
    );
  }

  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1">
      <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {t("catalog.browse.modelCategoriesLabel")}
      </span>
      {/* Rendered in API order — the backend already sorts by (position, slug)
          and owns that contract (service.py:527-534); re-sorting here would
          silently fork it. `parent_id` is deliberately ignored: MVP browse is
          flat (FR26-CAT-4), so no entry nests inside another (D-9).

          No `search` prop: the detail page owns no catalog search state to
          preserve, so this is a fresh, path-scoped navigation exactly as the
          tag chips next door are (D-4). The visible label IS the accessible
          name — no `aria-label` may shadow it (WCAG 2.2 SC 2.5.3). */}
      {categories.map((category) => (
        <Link
          key={category.id}
          to="/categories/$slug"
          params={{ slug: category.slug }}
          data-testid="model-category-link"
          className={ENTRY}
        >
          {labelOf(category)}
        </Link>
      ))}
    </div>
  );
}
