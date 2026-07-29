import { useTranslation } from "react-i18next";

import type { BrowseCategoryRead } from "@/lib/api-types";
import { BrowseCategoryList } from "@/modules/catalog/components/BrowseCategoryList";
import type { CatalogListSearch } from "@/routes/catalog/index";

interface Props {
  categories: BrowseCategoryRead[];
  /** `undefined` => no browse scope is active, so "All catalog" is current. */
  activeSlug: string | undefined;
  /** Current URL search layer, carried across every row's navigation (AC-14). */
  search: CatalogListSearch;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}

export function BrowseRail({
  categories,
  activeSlug,
  search,
  isLoading,
  isError,
  onRetry,
}: Props) {
  const { t } = useTranslation();

  return (
    <nav
      aria-label={t("catalog.browse.railLabel")}
      className="hidden w-60 shrink-0 flex-col border-r border-border bg-card lg:flex"
    >
      {/* Story 51.3 D-2 — row markup, skeleton and error footer are shared
          verbatim with `BrowseSheet` via `BrowseCategoryList`; this component
          now only owns the desktop-only `<nav>` chrome. */}
      <BrowseCategoryList
        categories={categories}
        activeSlug={activeSlug}
        search={search}
        isLoading={isLoading}
        isError={isError}
        onRetry={onRetry}
      />
    </nav>
  );
}
