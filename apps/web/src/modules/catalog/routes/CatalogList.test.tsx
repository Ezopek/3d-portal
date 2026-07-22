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
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import type { ModelSummary, TagGroupsResponse } from "@/lib/api-types";
import { CatalogList } from "@/modules/catalog/routes/CatalogList";
import i18n from "@/locales/i18n";
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

// Stub the three CatalogList data endpoints. Models come back EMPTY unless the
// request carries `tag_match=any` (the OR broadening), so a ≥2-tag AND lands on
// the AND-too-narrow empty state and "Switch to OR" visibly recovers.
function installFetch() {
  const calls: string[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    calls.push(url);
    if (url.includes("/api/tag-groups")) return json(tagGroups());
    if (url.includes("/api/tags")) return json([]);
    if (url.includes("/api/models")) {
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

// Mount CatalogList under a route whose id matches its hard-coded
// `useSearch/useNavigate({ from: "/catalog/" })`, reusing the real route's
// `validateSearch` so URL state normalizes exactly as in production.
async function mountAt(url: string) {
  const root = createRootRoute({ component: () => <Outlet /> });
  const catalog = createRoute({
    getParentRoute: () => root,
    path: "/catalog/",
    component: CatalogList,
    validateSearch: CatalogRoute.options.validateSearch,
  });
  const router = createRouter({
    routeTree: root.addChildren([catalog]),
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

describe("CatalogList facet empty states (E44.3)", () => {
  it("offers Switch to OR + Clear filters when a ≥2-tag AND is empty, and Switch to OR refetches with tag_match=any", async () => {
    const { calls } = installFetch();
    await mountAt(`/catalog/?tag_ids=${TAG_A}&tag_ids=${TAG_B}`);

    const switchBtn = await screen.findByRole("button", switchToOr);
    expect(screen.getByRole("button", clearFilters)).toBeTruthy();

    fireEvent.click(switchBtn);

    await waitFor(() => {
      expect(calls.some((u) => u.includes("/api/models") && u.includes("tag_match=any"))).toBe(true);
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
    await screen.findByText(/No models match the filter\.|Brak modeli pasujących do filtra\./);
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
      expect(calls.some((u) => u.includes("/api/models") && u.includes("untagged=true"))).toBe(true);
    });
  });
});
