import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
} from "@tanstack/react-router";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import type {
  BrowseCategoryRead,
  ModelSummary,
  TagGroupsResponse,
} from "@/lib/api-types";
import i18n from "@/locales/i18n";
import { Route as CategoryRoute } from "@/routes/categories/$slug";
import { Route as CatalogRoute } from "@/routes/catalog/index";

// Two well-formed UUIDs so `validateSearch` keeps both `tag_ids` (its UUID_RE
// gate) and the `>=2` `tag_match` threshold is reachable.
const TAG_A = "11111111-1111-1111-1111-111111111111";
const TAG_B = "22222222-2222-2222-2222-222222222222";
const GROUP_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

beforeAll(async () => {
  await i18n.changeLanguage("en");
  // jsdom has no scroll implementation; TanStack Router's scroll restoration
  // calls window.scrollTo on every navigation. Stub it so the transitions under
  // test don't spam "Not implemented: window.scrollTo".
  vi.stubGlobal("scrollTo", () => {});
});

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function tagGroups(): TagGroupsResponse {
  return {
    groups: [
      {
        id: GROUP_ID,
        slug: "material",
        name_en: "Material",
        name_pl: null,
        position: 0,
        tags: [
          {
            id: TAG_A,
            slug: "pla",
            name_en: "PLA",
            name_pl: null,
            group_id: GROUP_ID,
            group_position: 0,
            model_count: 3,
          },
        ],
      },
    ],
    groupless: [],
  };
}

function oneModel(): ModelSummary {
  return {
    id: "33333333-3333-3333-3333-333333333333",
    slug: "dragon",
    name_en: "Dragon",
    name_pl: null,
    source: "printables",
    status: "printed",
    rating: null,
    thumbnail_file_id: null,
    date_added: "2026-04-12",
    deleted_at: null,
    created_at: "2026-04-12T00:00:00Z",
    updated_at: "2026-04-12T00:00:00Z",
    tags: [],
    gallery_file_ids: [],
    image_count: 0,
  };
}

function browseCategories(): BrowseCategoryRead[] {
  return [
    {
      id: "44444444-4444-4444-4444-444444444444",
      slug: "organizery",
      name_en: "Organisers",
      name_pl: "Organizery",
      position: 0,
      parent_id: null,
      description_en: null,
      description_pl: null,
      model_count: 12,
    },
    {
      id: "55555555-5555-5555-5555-555555555555",
      slug: "uchwyty",
      name_en: "Mounts",
      name_pl: "Uchwyty i mocowania",
      position: 1,
      parent_id: null,
      description_en: null,
      description_pl: null,
      model_count: 7,
    },
  ];
}

// Stub the CatalogList data endpoints. Models come back EMPTY unless the
// request carries `tag_match=any` (the OR broadening), so a ≥2-tag AND lands on
// the AND-too-narrow empty state and "Switch to OR" visibly recovers.
function installFetch(
  opts: {
    categories?: "ok" | "error" | "pending";
    models?: "empty" | "one";
  } = {},
) {
  const calls: string[] = [];
  const categoriesMode = opts.categories ?? "ok";
  const modelsMode = opts.models ?? "empty";
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    calls.push(url);
    if (url.includes("/api/tag-groups")) return json(tagGroups());
    // Story 51.1 — the browse rail's source. `pending` never settles, which is
    // exactly how the "rail still loading" case is proven not to blank the grid.
    if (url.includes("/api/categories")) {
      if (categoriesMode === "error")
        return new Response("boom", { status: 500 });
      if (categoriesMode === "pending") return new Promise<Response>(() => {});
      return json(browseCategories());
    }
    if (url.includes("/api/tags")) return json([]);
    if (url.includes("/api/models")) {
      // Opt-in painted grid: the scope-navigation and focus cases need a
      // rendered results region, which the default all-empty stub cannot give.
      if (modelsMode === "one" && !url.includes("offset=48")) {
        return json({ items: [oneModel()], total: 1, offset: 0, limit: 48 });
      }
      if (url.includes("tag_match=any")) {
        return json({ items: [oneModel()], total: 1, offset: 0, limit: 48 });
      }
      // Page overshoot: results exist (total>0) but this page is past the end,
      // so the current page returns no items with a non-zero offset. `useModels`
      // serializes page 2 as `offset=48` (PAGE_SIZE 48).
      if (url.includes("offset=48")) {
        return json({ items: [], total: 3, offset: 48, limit: 48 });
      }
      return json({ items: [], total: 0, offset: 0, limit: 48 });
    }
    return json({});
  });
  vi.stubGlobal("fetch", fetchMock);
  return { calls };
}

// Story 51.2 D-2 — `CatalogList` no longer binds itself to one route id, so the
// harness mounts BOTH surfaces that share it: `/catalog/` (unscoped) and
// `/categories/$slug` (scoped). Each registers the REAL route's `component`,
// `validateSearch` and `beforeLoad`, so URL normalization, the legacy
// `?category=` canonicalisation and the cross-route transitions all behave
// exactly as in production. Route ids are mirrored verbatim, which is what lets
// each route component's own `Route.use*` hooks resolve their match.
async function mountAt(url: string) {
  const root = createRootRoute({ component: () => <Outlet /> });
  const catalog = createRoute({
    getParentRoute: () => root,
    path: "/catalog/",
    component: CatalogRoute.options.component,
    validateSearch: CatalogRoute.options.validateSearch,
    beforeLoad: CatalogRoute.options.beforeLoad,
  });
  const categories = createRoute({
    getParentRoute: () => root,
    path: "/categories/$slug",
    component: CategoryRoute.options.component,
    validateSearch: CategoryRoute.options.validateSearch,
  });
  const router = createRouter({
    routeTree: root.addChildren([catalog, categories]),
    history: createMemoryHistory({ initialEntries: [url] }),
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  await router.load();
  render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { router };
}

const switchToOr = { name: /Switch to OR|Przełącz na dowolne/ };
const clearFilters = { name: /Clear filters|Wyczyść filtry/ };
const backToPage1 = { name: /Back to first page|Wróć na pierwszą stronę/ };
const searchEntireCatalog = {
  name: /Search entire catalog|Szukaj w całym katalogu/,
};
const clearCategory = { name: /Clear category|Wyczyść kategorię/ };

describe("CatalogList facet empty states (E44.3)", () => {
  it("offers Switch to OR + Clear filters when a ≥2-tag AND is empty, and Switch to OR refetches with tag_match=any", async () => {
    const { calls } = installFetch();
    await mountAt(`/catalog/?tag_ids=${TAG_A}&tag_ids=${TAG_B}`);

    const switchBtn = await screen.findByRole("button", switchToOr);
    expect(screen.getByRole("button", clearFilters)).toBeTruthy();

    fireEvent.click(switchBtn);

    await waitFor(() => {
      expect(
        calls.some(
          (u) => u.includes("/api/models") && u.includes("tag_match=any"),
        ),
      ).toBe(true);
    });
  });

  it("offers only Clear filters (no Switch to OR) when a single-tag filter is empty", async () => {
    installFetch();
    await mountAt(`/catalog/?tag_ids=${TAG_A}`);

    expect(await screen.findByRole("button", clearFilters)).toBeTruthy();
    expect(screen.queryByRole("button", switchToOr)).toBeNull();
  });

  it("offers no recovery action when there are no active filters and no results", async () => {
    installFetch();
    await mountAt("/catalog/");

    // The empty message renders, but neither recovery button is offered.
    await screen.findByText(
      /No models match the filter\.|Brak modeli pasujących do filtra\./,
    );
    expect(screen.queryByRole("button", switchToOr)).toBeNull();
    expect(screen.queryByRole("button", clearFilters)).toBeNull();
  });

  it("offers a Back-to-first-page recovery (not Clear filters) on a page overshoot where results still exist", async () => {
    await mountAt("/catalog/?page=2");

    // total>0 but this page is empty → recoverable overshoot, not a dead end.
    expect(await screen.findByRole("button", backToPage1)).toBeTruthy();
    // Must NOT offer Clear filters here (there are no filters to clear, and it
    // would be the wrong affordance).
    expect(screen.queryByRole("button", clearFilters)).toBeNull();
  });

  it("sends untagged=true to the models query when the URL carries untagged", async () => {
    const { calls } = installFetch();
    await mountAt("/catalog/?untagged=true");

    await waitFor(() => {
      expect(
        calls.some(
          (u) => u.includes("/api/models") && u.includes("untagged=true"),
        ),
      ).toBe(true);
    });
  });
});

// Story 50.2 (Initiative 26) — `category` is a browse SCOPE, not another filter:
// it reaches the models query, it does not move the Filters (n) badge, and it
// survives both a filter/search change and "Clear filters".
describe("CatalogList browse-category scope (Story 50.2)", () => {
  it("sends category=<slug> to the models query when the URL carries a category", async () => {
    const { calls } = installFetch();
    await mountAt("/catalog/?category=home-decor");

    await waitFor(() => {
      expect(
        calls.some(
          (u) => u.includes("/api/models") && u.includes("category=home-decor"),
        ),
      ).toBe(true);
    });
  });

  it("sends no category key at all when the URL carries none", async () => {
    const { calls } = installFetch();
    await mountAt("/catalog/?status=printed");

    await waitFor(() => {
      expect(calls.some((u) => u.includes("/api/models"))).toBe(true);
    });
    // Regression lock: adding the filter key must be byte-identical on the wire
    // for every user who has no category (the query-key hash is unchanged too —
    // TanStack's hashKey drops undefined-valued properties).
    for (const url of calls.filter((u) => u.includes("/api/models"))) {
      expect(url.includes("category=")).toBe(false);
    }
  });

  it("leaves the Filters (n) badge identical whether or not a category is active", async () => {
    // FR26-BROWSE-2's verifiable, satisfied by adding NOTHING to
    // FilterRibbonState / activeFilterCount (which count only status, source and
    // a non-default sort). Asserted through the real component so the fence
    // cannot be vacuous.
    installFetch();
    await mountAt("/catalog/?status=printed");
    const withoutCategory = (
      await screen.findByRole("button", { name: "Filters" })
    ).textContent;
    // Pin the count so the comparison below cannot pass on two empty strings.
    expect(withoutCategory).toContain("1");
    cleanup();

    installFetch();
    await mountAt("/catalog/?status=printed&category=home-decor");
    const withCategory = (
      await screen.findByRole("button", { name: "Filters" })
    ).textContent;
    expect(withCategory).toBe(withoutCategory);
  });

  it("keeps the scope through a search change made in the real UI", async () => {
    // No bespoke preservation code: every navigation helper spreads `...prev`,
    // so a present category survives a filter/search change for free.
    const { calls } = installFetch();
    await mountAt("/catalog/?category=home-decor");

    fireEvent.change(await screen.findByPlaceholderText("Search"), {
      target: { value: "vase" },
    });

    await waitFor(() => {
      expect(
        calls.some(
          (u) =>
            u.includes("/api/models") &&
            u.includes("q=vase") &&
            u.includes("category=home-decor"),
        ),
      ).toBe(true);
    });
  });

  it("preserves the scope when Clear filters clears the filters", async () => {
    const { calls } = installFetch();
    await mountAt("/catalog/?category=home-decor&status=printed");

    fireEvent.click(await screen.findByRole("button", clearFilters));

    await waitFor(() => {
      expect(
        calls.some(
          (u) =>
            u.includes("/api/models") &&
            u.includes("category=home-decor") &&
            !u.includes("status="),
        ),
      ).toBe(true);
    });
  });

  it("offers the scope escape — not Clear filters — for a category-only empty result", async () => {
    // Story 51.2 AC-23 closes the gap 51.1 deliberately left open here. The
    // escape is still NOT "Clear filters": `filtersActive` remains un-extended
    // with `category` (D-6/D-13), so the only recovery offered is the one that
    // actually widens the place.
    installFetch();
    await mountAt("/categories/home-decor");

    await screen.findByText(
      /Nothing in this category yet\.|W tej kategorii nie ma jeszcze nic\./,
    );
    expect(await screen.findByRole("button", searchEntireCatalog)).toBeTruthy();
    expect(screen.queryByRole("button", switchToOr)).toBeNull();
    expect(screen.queryByRole("button", clearFilters)).toBeNull();
  });
});

// Story 51.1 (Initiative 26) — the desktop left column is browse navigation.
// The facet surface is relocated behind the shipped Tags sheet, and the rail's
// own loading/error states must never blank the grid.
describe("CatalogList desktop browse navigation (Story 51.1)", () => {
  const allCatalog = { name: /All catalog|Cały katalog/ };

  it("mounts the browse rail and no longer renders a standalone facet sidebar", async () => {
    installFetch();
    await mountAt("/catalog/");

    const rail = await screen.findByRole("navigation", {
      name: /Browse categories|Przeglądaj/,
    });
    expect(rail).toBeTruthy();
    // Story 51.2 D-4 — rows are anchors now, so the role is `link`.
    expect(
      await screen.findByRole("link", { name: /Organisers, 12 models/ }),
    ).toBeTruthy();

    // The relocated FacetSidebar lives behind the Sheet trigger now, so no tag
    // checkbox and no "Untagged models" row is present at rest.
    expect(
      screen.queryByRole("checkbox", {
        name: /Untagged models|Modele bez tagów/,
      }),
    ).toBeNull();
    expect(screen.queryByRole("checkbox", { name: /PLA/ })).toBeNull();
  });

  it("keeps the grouped facet surface one interaction away behind the Tags trigger", async () => {
    installFetch();
    await mountAt("/catalog/");

    fireEvent.click(
      await screen.findByRole("button", { name: /^(Tags|Tagi)$/ }),
    );

    // One click reveals the shipped FacetSidebar verbatim: its group tree, its
    // per-tag checkbox and the pinned Untagged row.
    expect(
      await screen.findByRole("checkbox", {
        name: /Untagged models|Modele bez tagów/,
      }),
    ).toBeTruthy();
    expect(screen.getByRole("checkbox", { name: /PLA/ })).toBeTruthy();
  });

  // Story 51.2 AC-14 — the rail navigates by PATH now. The assertion moves from
  // "a `?category=` param was written" to "the route changed and every other URL
  // layer survived", which is the same guarantee stated against the canonical URL.
  it("navigates to /categories/<slug> and preserves q and tag_ids when a rail row is activated", async () => {
    const { calls } = installFetch();
    const { router } = await mountAt(`/catalog/?q=vase&tag_ids=${TAG_A}`);

    fireEvent.click(
      await screen.findByRole("link", { name: /Mounts, 7 models/ }),
    );

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/categories/uchwyty");
    });
    await waitFor(() => {
      expect(
        calls.some(
          (u) =>
            u.includes("/api/models") &&
            u.includes("category=uchwyty") &&
            u.includes("q=vase") &&
            u.includes(TAG_A),
        ),
      ).toBe(true);
    });
    // AC-18 — nothing in the app writes `?category=` any more.
    expect(router.state.location.searchStr).not.toContain("category=");
  });

  it("replaces rather than accumulates the scope when a second category is picked", async () => {
    const { calls } = installFetch();
    const { router } = await mountAt("/categories/organizery");

    fireEvent.click(
      await screen.findByRole("link", { name: /Mounts, 7 models/ }),
    );

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/categories/uchwyty");
    });
    await waitFor(() => {
      expect(
        calls.some(
          (u) => u.includes("/api/models") && u.includes("category=uchwyty"),
        ),
      ).toBe(true);
    });
    for (const url of calls.filter((u) => u.includes("category=uchwyty"))) {
      expect(url.includes("category=organizery")).toBe(false);
    }
  });

  it("clears only the scope when All catalog is activated, keeping every other layer", async () => {
    const { calls } = installFetch();
    const { router } = await mountAt(
      "/categories/organizery?status=printed&q=vase",
    );

    fireEvent.click(await screen.findByRole("link", allCatalog));

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/catalog");
    });
    await waitFor(() => {
      expect(
        calls.some(
          (u) =>
            u.includes("/api/models") &&
            !u.includes("category=") &&
            u.includes("status=printed") &&
            u.includes("q=vase"),
        ),
      ).toBe(true);
    });
  });

  it("marks the active category row aria-current from the URL scope", async () => {
    installFetch();
    await mountAt("/categories/uchwyty");

    const active = await screen.findByRole("link", {
      name: /Mounts, 7 models/,
    });
    expect(active.getAttribute("aria-current")).toBe("page");
    expect(
      screen.getByRole("link", allCatalog).getAttribute("aria-current"),
    ).toBeNull();
    // AC-15 — exactly one row is current.
    expect(
      screen
        .getAllByRole("link")
        .filter((l) => l.getAttribute("aria-current") === "page"),
    ).toHaveLength(1);
  });

  it("keeps the grid rendered when the category read FAILS (rail degrades, catalog does not)", async () => {
    installFetch({ categories: "error" });
    await mountAt("/catalog/?page=2");

    // The grid's own recovery affordance still renders — proof the failed
    // navigation aid did not take the catalog down with it.
    expect(await screen.findByRole("button", backToPage1)).toBeTruthy();
    expect(screen.getByRole("link", allCatalog)).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /Retry|Spróbuj ponownie/ }),
    ).toBeTruthy();
  });

  it("keeps the grid rendered while the category read is still PENDING", async () => {
    installFetch({ categories: "pending" });
    await mountAt("/catalog/?page=2");

    expect(await screen.findByRole("button", backToPage1)).toBeTruthy();
    expect(screen.getByRole("link", allCatalog)).toBeTruthy();
    expect(
      screen.getAllByTestId("browse-rail-skeleton").length,
    ).toBeGreaterThan(0);
  });
});

// Story 51.2 (Initiative 26) — the category becomes a real place: its own URL,
// a scope chip above the results, and a one-click escape that widens the place
// without throwing away the query and filters already chosen.
describe("CatalogList category route + scope chip (Story 51.2)", () => {
  const scopeRow = { name: /Active category|Aktywna kategoria/ };

  // ---- route ----------------------------------------------------------

  it("canonicalises a legacy /catalog?category=<slug> to /categories/<slug>, preserving every other layer", async () => {
    // AC-4. Story 51.1 shipped the writer for this URL form and the 51.1 deploy
    // smoke used one, so these links exist in the wild.
    const { router } = await mountAt(
      `/catalog/?category=uchwyty&q=vase&tag_ids=${TAG_A}`,
    );
    installFetch();

    expect(router.state.location.pathname).toBe("/categories/uchwyty");
    expect(router.state.location.searchStr).toContain("q=vase");
    expect(router.state.location.searchStr).toContain(TAG_A);
    expect(router.state.location.searchStr).not.toContain("category=");
  });

  it("does NOT redirect /catalog when it carries no category", async () => {
    installFetch();
    const { router } = await mountAt("/catalog/?status=printed");

    expect(router.state.location.pathname).toBe("/catalog");
  });

  it("drops a hand-crafted ?category= on the scoped route so two scopes are unrepresentable", async () => {
    // AC-2 — `/categories/a?category=b` renders scope `a` and carries no
    // `category` param at all.
    const { calls } = installFetch();
    const { router } = await mountAt("/categories/uchwyty?category=organizery");

    expect(router.state.location.pathname).toBe("/categories/uchwyty");
    expect(router.state.matches.at(-1)?.routeId).toBe("/categories/$slug");
    // The scope the surface actually uses is the PATH param, and the stray
    // token must not survive forward into any onward navigation either.
    const rail = await screen.findByRole("navigation", {
      name: /Browse categories|Przeglądaj/,
    });
    for (const link of within(rail).getAllByRole("link")) {
      expect(link.getAttribute("href")).not.toContain("category=");
    }
    expect(
      screen
        .getByRole("link", { name: /Clear category|Wyczyść kategorię/ })
        .getAttribute("href"),
    ).not.toContain("category=");
    await waitFor(() => {
      expect(
        calls.some(
          (u) => u.includes("/api/models") && u.includes("category=uchwyty"),
        ),
      ).toBe(true);
    });
    for (const url of calls.filter((u) => u.includes("/api/models"))) {
      expect(url.includes("category=organizery")).toBe(false);
    }
  });

  it("renders an unknown slug as an empty page with a working escape — never an error surface", async () => {
    // AC-5 / AC-11 / D-7. The backend returns 200 + total 0 for an unknown slug,
    // and `useCategoryBySlug` (which WOULD 404) is deliberately not mounted.
    installFetch();
    await mountAt("/categories/nie-ma-takiej");

    const row = await screen.findByRole("group", scopeRow);
    // The label degrades to the raw slug — a rendered value, not an error.
    expect(row.textContent).toContain("nie-ma-takiej");
    // No other constraint is active, so the escape carries the "Clear category"
    // label — but it is present and it works, which is what AC-5 requires.
    expect(screen.getByRole("link", clearCategory)).toBeTruthy();
    expect(screen.queryByText(/Network error|Błąd sieci/)).toBeNull();
  });

  // ---- chip -----------------------------------------------------------

  it("renders no chip row at all on the unscoped catalogue", async () => {
    // AC-7 — absent from the DOM, not merely hidden.
    installFetch();
    await mountAt("/catalog/");

    await screen.findByRole("navigation", {
      name: /Browse categories|Przeglądaj/,
    });
    expect(screen.queryByRole("group", scopeRow)).toBeNull();
    expect(screen.queryByRole("link", searchEntireCatalog)).toBeNull();
    expect(screen.queryByRole("link", clearCategory)).toBeNull();
  });

  it("renders the chip with the resolved category label when a scope is active", async () => {
    // AC-6 / AC-11 — the label comes from the ALREADY-loaded category list
    // (`name_en` in the en locale), never from a second request.
    installFetch();
    await mountAt("/categories/uchwyty");

    const row = await screen.findByRole("group", scopeRow);
    expect(row.textContent).toContain("Mounts");
  });

  it("labels the chip action 'Clear category' when the scope is the only constraint", async () => {
    installFetch(); // AC-9, filtersActive === false
    await mountAt("/categories/uchwyty");

    expect(await screen.findByRole("link", clearCategory)).toBeTruthy();
    expect(screen.queryByRole("link", searchEntireCatalog)).toBeNull();
  });

  it("labels the chip action 'Search entire catalog' once any other constraint is active", async () => {
    installFetch(); // AC-9, filtersActive === true
    await mountAt("/categories/uchwyty?status=printed");

    expect(await screen.findByRole("link", searchEntireCatalog)).toBeTruthy();
    expect(screen.queryByRole("link", clearCategory)).toBeNull();
  });

  it("clears ONLY the scope when the chip escape is activated", async () => {
    // AC-10 / FR26-BROWSE-2 verifiable (b) — q, tag_ids, tag_match, untagged,
    // status, source and sort all survive; only the place changes.
    const { calls } = installFetch();
    const { router } = await mountAt(
      `/categories/uchwyty?q=vase&status=printed&source=own&sort=rating&untagged=true&tag_ids=${TAG_A}&tag_ids=${TAG_B}&tag_match=any`,
    );

    fireEvent.click(await screen.findByRole("link", searchEntireCatalog));

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/catalog");
    });
    const s = router.state.location.searchStr;
    expect(s).toContain("q=vase");
    expect(s).toContain("status=printed");
    expect(s).toContain("source=own");
    expect(s).toContain("sort=rating");
    expect(s).toContain("untagged=true");
    expect(s).toContain(TAG_A);
    expect(s).toContain(TAG_B);
    expect(s).toContain("tag_match=any");
    expect(s).not.toContain("category=");
    await waitFor(() => {
      expect(
        calls.some(
          (u) =>
            u.includes("/api/models") &&
            !u.includes("category=") &&
            u.includes("q=vase"),
        ),
      ).toBe(true);
    });
  });

  it("exposes the chip as a group, never as a checkbox or a toggle", async () => {
    // AC-8 — a scope is a place, not another facet.
    installFetch();
    await mountAt("/categories/uchwyty");

    const row = await screen.findByRole("group", scopeRow);
    expect(row.querySelectorAll("input")).toHaveLength(0);
    expect(row.querySelectorAll("button")).toHaveLength(0);
  });

  // ---- scoped search --------------------------------------------------

  it("keeps a search committed inside a category INSIDE that category", async () => {
    // AC-13 — the path does not move; only search params do.
    const { calls } = installFetch();
    const { router } = await mountAt("/categories/uchwyty");

    fireEvent.change(await screen.findByPlaceholderText("Search"), {
      target: { value: "vase" },
    });

    await waitFor(() => {
      expect(
        calls.some(
          (u) =>
            u.includes("/api/models") &&
            u.includes("q=vase") &&
            u.includes("category=uchwyty"),
        ),
      ).toBe(true);
    });
    expect(router.state.location.pathname).toBe("/categories/uchwyty");
  });

  // ---- empty-state branch order ---------------------------------------

  it("keeps the shipped andTooNarrow branch winning while scoped, and the scope survives both actions", async () => {
    // AC-22 — the scoped branches slot AFTER this one, so it must still win.
    const { router } = await mountAt(
      `/categories/uchwyty?tag_ids=${TAG_A}&tag_ids=${TAG_B}`,
    );
    installFetch();

    expect(await screen.findByRole("button", switchToOr)).toBeTruthy();
    expect(screen.getByRole("button", clearFilters)).toBeTruthy();
    // Not the scoped-empty copy.
    expect(
      screen.queryByText(/No matches in|Brak wyników w kategorii/),
    ).toBeNull();

    fireEvent.click(screen.getByRole("button", clearFilters));
    await waitFor(() => {
      // AC-26 — "Clear filters" preserves the scope, now structurally.
      expect(router.state.location.pathname).toBe("/categories/uchwyty");
    });
  });

  it("keeps the shipped page-overshoot branch ahead of the scoped-empty branches", async () => {
    // AC-25 — total>0 with an out-of-range page is still a recoverable overshoot.
    installFetch();
    await mountAt("/categories/uchwyty?page=2");

    expect(await screen.findByRole("button", backToPage1)).toBeTruthy();
    expect(
      screen.queryByText(/Nothing in this category yet|W tej kategorii/),
    ).toBeNull();
    expect(
      screen.queryByText(/No matches in|Brak wyników w kategorii/),
    ).toBeNull();
  });

  it("offers both the escape and Clear filters when a scoped, filtered search is empty", async () => {
    // AC-24 — `catalog.emptyInCategory` interpolated with the category label.
    const { router } = await mountAt("/categories/uchwyty?status=printed");
    installFetch();

    expect(await screen.findByText(/No matches in Mounts\./)).toBeTruthy();
    const escape = screen.getByRole("button", searchEntireCatalog);
    expect(screen.getByRole("button", clearFilters)).toBeTruthy();

    fireEvent.click(escape);
    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/catalog");
    });
    // Keeps the filter it promised to keep.
    expect(router.state.location.searchStr).toContain("status=printed");
  });

  it("drops the filters but keeps the scope when Clear filters runs on a scoped empty state", async () => {
    // AC-26, the mirror image of the case above.
    const { router } = await mountAt("/categories/uchwyty?status=printed");
    installFetch();

    fireEvent.click(await screen.findByRole("button", clearFilters));

    await waitFor(() => {
      expect(router.state.location.searchStr).not.toContain("status=printed");
    });
    expect(router.state.location.pathname).toBe("/categories/uchwyty");
  });

  // ---- a11y -----------------------------------------------------------

  it("exposes exactly ONE polite live region, carrying the result count", async () => {
    // AC-32 / D-11 — one region for the surface, and the chip is not it.
    installFetch({ models: "one" });
    await mountAt("/categories/uchwyty");

    // Wait for the results region itself: the LOADING branch also renders a
    // role="status" node, so asserting the count before the grid paints would
    // measure the skeleton, not the live region.
    await screen.findByRole("group", scopeRow);
    expect(screen.getAllByRole("status")).toHaveLength(1);
    const live = screen.getByRole("status");
    expect(live.getAttribute("aria-live")).toBe("polite");
    expect(live.textContent).toContain("1");
    expect(
      screen.getByRole("group", scopeRow).getAttribute("aria-live"),
    ).toBeNull();
  });

  it("moves focus to the results heading on a scope change, and NOT on a filter change", async () => {
    // AC-31 / D-10 — EXPERIENCE.md:324.
    installFetch({ models: "one" });
    await mountAt("/catalog/");

    // A filter change does not relocate the user, so focus must stay put.
    const input = await screen.findByPlaceholderText("Search");
    input.focus();
    fireEvent.change(input, { target: { value: "vase" } });
    await waitFor(() => {
      expect(document.activeElement).toBe(input);
    });

    // A scope change does relocate the user.
    fireEvent.click(
      await screen.findByRole("link", { name: /Mounts, 7 models/ }),
    );
    await waitFor(() => {
      const heading = screen.getByRole("heading", { level: 2, hidden: true });
      expect(document.activeElement).toBe(heading);
      expect(heading.textContent).toBe("Mounts");
    });
  });
});
