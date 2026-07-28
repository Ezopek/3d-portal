import { createFileRoute } from "@tanstack/react-router";

import { CatalogList } from "@/modules/catalog/routes/CatalogList";
import type { CatalogSearch } from "@/routes/catalog/index";
import { validateCatalogSearch } from "@/routes/catalog/index";

export const Route = createFileRoute("/categories/$slug")({
  component: CategoryBrowseRoute,
  // The browse scope lives in the PATH on this route and only there (D-1).
  // Re-use the shipped catalog validator verbatim (D-3), then drop `category`
  // so a hand-crafted `/categories/a?category=b` cannot express two scopes at
  // once — the impossible state is made unrepresentable rather than merely
  // unlikely (AC-2).
  validateSearch: (
    raw: Record<string, unknown>,
  ): Omit<CatalogSearch, "category"> => {
    const { category: scopeLivesInThePath, ...rest } = validateCatalogSearch(raw);
    void scopeLivesInThePath;
    return rest;
  },
});

function CategoryBrowseRoute() {
  const { slug } = Route.useParams();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  return (
    <CatalogList
      scopeSlug={slug}
      search={search}
      onSearchChange={(updater) =>
        void navigate({ search: updater, replace: true })
      }
    />
  );
}
