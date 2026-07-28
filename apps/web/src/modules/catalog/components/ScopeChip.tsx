import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import type { CatalogListSearch } from "@/routes/catalog/index";

interface Props {
  /** Resolved category label, or the raw slug when the slug is unknown (D-7). */
  label: string;
  /** True when q / tag_ids / untagged / status / source is active (D-6). */
  otherConstraintsActive: boolean;
  /** Current URL search layer, forwarded verbatim through the escape (AC-10). */
  search: CatalogListSearch;
}

// Geometry and tokens are verbatim from DESIGN.md:84-95, :244, :250, :256-258.
// `primary` @10% is the LOCATION role — the same treatment the active browse-rail
// row and the active module row carry, so "which category am I in" reads exactly
// like "which module am I in" (DESIGN.md:203). Never `accent`: that is the
// chosen-constraint vocabulary the tag chips own, and reusing it here would make
// a place look like a filter (DESIGN.md:204, :294).
//
// `rounded-md`, deliberately not `rounded-full` — the tag pill is `rounded-full`,
// so the shape contrast reinforces place-vs-constraint for free (DESIGN.md:258).
// Flat: separation comes from the inset ring, never from a shadow (DESIGN.md:250).
const CHIP =
  "flex min-h-6 w-full items-center justify-between gap-3 rounded-md bg-primary/10 px-3 py-1.5 text-sm text-foreground ring-1 ring-inset ring-primary";

// A text label, never a bare × (DESIGN.md:274, :296). `min-h-6 min-w-6` is the
// 24×24 CSS px floor WCAG 2.2 SC 2.5.8 asks for, and the underline is on both
// hover AND focus-visible so the affordance is never hover-only (SC 2.5.1).
const ACTION =
  "inline-flex min-h-6 min-w-6 shrink-0 items-center justify-center rounded-md px-1 text-sm font-medium text-primary underline-offset-2 hover:underline focus-visible:underline";

export function ScopeChip({ label, otherConstraintsActive, search }: Props) {
  const { t } = useTranslation();

  // ONE navigation with TWO labels, not two behaviours: the transition table
  // (EXPERIENCE.md:376) gives both rows the same effect — scope cleared,
  // everything else preserved, page reset. Only the promise made to the user
  // differs, and it has to be honest about what survives (D-6).
  const actionKey = otherConstraintsActive
    ? "catalog.browse.searchEntireCatalog"
    : "catalog.browse.clearCategory";

  return (
    <div className="px-3 pt-3">
      {/* `role="group"` + aria-label, deliberately NOT a live region: the result
          count is what announces, and it owns the single polite region in the
          results area (EXPERIENCE.md:314-316, D-11). */}
      <div
        role="group"
        aria-label={t("catalog.browse.activeScope", { name: label })}
        className={CHIP}
      >
        <span className="min-w-0 flex-1 truncate font-medium">{label}</span>
        {/* A scope change is a route change, so the escape is a real anchor:
            middle-click, copy-link-address and the browser's own hover URL come
            for free, and it PUSHES so Back returns to the category (D-5).
            Leaving the path IS the whole of the clearing — every other URL layer
            is forwarded verbatim (AC-10).

            An explicit search OBJECT, not an updater: an updater's `prev` is
            typed as the union across EVERY registered route, so spreading it
            would only typecheck by accident and would widen silently whenever
            an unrelated route changed — the same trap D-2 rejected
            `useSearch({strict:false})` for. `CatalogListSearch` is exact. */}
        <Link
          to="/catalog"
          search={{ ...search, page: undefined }}
          className={ACTION}
        >
          {t(actionKey)}
        </Link>
      </div>
    </div>
  );
}
