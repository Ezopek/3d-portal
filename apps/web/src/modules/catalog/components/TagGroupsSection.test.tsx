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

import type { ModelDetail, TagGroupsResponse } from "@/lib/api-types";
import i18n from "@/locales/i18n";
import { Route as CatalogRoute } from "@/routes/catalog/index";

import { TagGroupsSection } from "./TagGroupsSection";

// GROUP_A carries one of this model's tags; GROUP_B never does (in the
// "mixed" fixture below) so it exercises the empty-group visibility rule.
const GROUP_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const GROUP_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";
const TAG_A = "11111111-1111-1111-1111-111111111111"; // in GROUP_A
const TAG_GROUPLESS = "22222222-2222-2222-2222-222222222222"; // group_id: null

const mockUseTagGroups = vi.fn();
vi.mock("@/modules/catalog/hooks/useTagGroups", () => ({
  useTagGroups: () => mockUseTagGroups(),
}));

beforeAll(async () => {
  await i18n.changeLanguage("en");
});

afterEach(() => {
  cleanup();
  mockUseTagGroups.mockReset();
});

function tagGroupsResponse(): TagGroupsResponse {
  return {
    groups: [
      // Deliberately out of position order — the component must sort.
      { id: GROUP_B, slug: "material", name_en: "Material", name_pl: "Materiał", position: 1, tags: [] },
      { id: GROUP_A, slug: "theme", name_en: "Theme", name_pl: "Motyw", position: 0, tags: [] },
    ],
    groupless: [],
  };
}

function makeDetail(over: Partial<ModelDetail> = {}): ModelDetail {
  return {
    id: "model-1",
    slug: "dragon",
    name_en: "Dragon",
    name_pl: "Smok",
    category_id: "cat-1",
    source: "printables",
    status: "printed",
    rating: null,
    thumbnail_file_id: null,
    date_added: "2026-04-12",
    deleted_at: null,
    created_at: "2026-04-12T00:00:00Z",
    updated_at: "2026-04-12T00:00:00Z",
    tags: [
      { id: TAG_A, slug: "dragon", name_en: "Dragon", name_pl: null, group_id: GROUP_A, group_position: 0 },
      {
        id: TAG_GROUPLESS,
        slug: "articulated",
        name_en: "Articulated",
        name_pl: null,
        group_id: null,
        group_position: 0,
      },
    ],
    category: {
      id: "cat-1",
      parent_id: null,
      slug: "decorations",
      name_en: "Decorations",
      name_pl: "Dekoracje",
    },
    files: [],
    prints: [],
    notes: [],
    external_links: [],
    gallery_file_ids: [],
    image_count: 0,
    ...over,
  };
}

// Mount TagGroupsSection at "/" under a router whose sibling "/catalog/"
// route reuses the real route's `validateSearch`, mirroring CatalogList.test.tsx's
// `mountAt` pattern — needed because tag chips are `<Link>`s that must resolve
// against real router context.
async function mountAt(props: {
  detail: ModelDetail;
  isAdmin: boolean;
  onAddTags?: () => void;
}) {
  const onAddTags = props.onAddTags ?? vi.fn();
  const root = createRootRoute({ component: () => <Outlet /> });
  const host = createRoute({
    getParentRoute: () => root,
    path: "/",
    component: () => (
      <TagGroupsSection detail={props.detail} isAdmin={props.isAdmin} onAddTags={onAddTags} />
    ),
  });
  const catalog = createRoute({
    getParentRoute: () => root,
    path: "/catalog/",
    component: () => <div data-testid="catalog-route" />,
    validateSearch: CatalogRoute.options.validateSearch,
  });
  const router = createRouter({
    routeTree: root.addChildren([host, catalog]),
    history: createMemoryHistory({ initialEntries: ["/"] }),
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  await router.load();
  render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { router, onAddTags };
}

describe("TagGroupsSection", () => {
  it("renders a group's label and chips when it has ≥1 of this model's tags", async () => {
    mockUseTagGroups.mockReturnValue({ data: tagGroupsResponse() });
    await mountAt({ detail: makeDetail(), isAdmin: false });

    expect(screen.getByText("Theme")).toBeTruthy();
    const chip = screen.getByText("dragon");
    expect(chip.getAttribute("data-testid")).toBe("tag-chip");
  });

  it("omits an empty group entirely (no heading, no dash) for a non-admin", async () => {
    mockUseTagGroups.mockReturnValue({ data: tagGroupsResponse() });
    await mountAt({ detail: makeDetail(), isAdmin: false });

    expect(screen.queryByText("Material")).toBeNull();
  });

  it("shows an empty group's label + dash + Add control for an admin", async () => {
    mockUseTagGroups.mockReturnValue({ data: tagGroupsResponse() });
    const { onAddTags } = await mountAt({ detail: makeDetail(), isAdmin: true });

    expect(screen.getByText("Material")).toBeTruthy();
    expect(screen.getByText("—")).toBeTruthy();
    // Accessible name is group-scoped ("Add tag to Material"), not the shared
    // visible "+ tag" text, so a screen-reader user can distinguish this
    // button from another empty group's Add control.
    const addButton = screen.getByRole("button", { name: "Add tag to Material" });
    fireEvent.click(addButton);
    expect(onAddTags).toHaveBeenCalledTimes(1);
  });

  it("renders a trailing Ungrouped section for tags with group_id: null", async () => {
    mockUseTagGroups.mockReturnValue({ data: tagGroupsResponse() });
    await mountAt({ detail: makeDetail(), isAdmin: false });

    expect(screen.getByText("Ungrouped")).toBeTruthy();
    const chips = screen.getAllByTestId("tag-chip");
    expect(chips.map((c) => c.textContent)).toContain("articulated");
  });

  it("renders nothing for a zero-tag model viewed by a non-admin", async () => {
    mockUseTagGroups.mockReturnValue({ data: tagGroupsResponse() });
    await mountAt({ detail: makeDetail({ tags: [] }), isAdmin: false });

    expect(screen.queryByTestId("tag-chip")).toBeNull();
    expect(screen.queryByText("Theme")).toBeNull();
    expect(screen.queryByText("Material")).toBeNull();
    expect(screen.queryByText("Ungrouped")).toBeNull();
  });

  it("renders every fetched group (+ groupless) as a dash + Add row for an admin on a zero-tag model", async () => {
    mockUseTagGroups.mockReturnValue({ data: tagGroupsResponse() });
    await mountAt({ detail: makeDetail({ tags: [] }), isAdmin: true });

    expect(screen.getByText("Theme")).toBeTruthy();
    expect(screen.getByText("Material")).toBeTruthy();
    expect(screen.getByText("Ungrouped")).toBeTruthy();
    expect(screen.getAllByText("—").length).toBe(3);
    // Each Add button's accessible name is scoped to its own group label, so
    // all three are independently findable/distinguishable.
    expect(screen.getByRole("button", { name: "Add tag to Theme" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Add tag to Material" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Add tag to Ungrouped" })).toBeTruthy();
    expect(screen.queryByTestId("tag-chip")).toBeNull();
  });

  it("renders nothing while useTagGroups() is pending", async () => {
    mockUseTagGroups.mockReturnValue({ data: undefined, isPending: true, isError: false });
    await mountAt({ detail: makeDetail(), isAdmin: true });

    expect(screen.queryByText("Theme")).toBeNull();
    expect(screen.queryByTestId("tag-chip")).toBeNull();
  });

  it("renders nothing when useTagGroups() errors", async () => {
    mockUseTagGroups.mockReturnValue({ data: undefined, isPending: false, isError: true });
    await mountAt({ detail: makeDetail(), isAdmin: true });

    expect(screen.queryByText("Theme")).toBeNull();
    expect(screen.queryByTestId("tag-chip")).toBeNull();
  });

  it("navigates to /catalog with tag_ids containing only the clicked tag's id", async () => {
    mockUseTagGroups.mockReturnValue({ data: tagGroupsResponse() });
    const { router } = await mountAt({ detail: makeDetail(), isAdmin: false });

    const chip = screen.getByText("dragon");
    expect(chip.getAttribute("data-testid")).toBe("tag-chip");
    expect(chip.getAttribute("href")).toContain("/catalog");
    fireEvent.click(chip);

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/catalog");
    });
    expect(router.state.location.search).toEqual({ tag_ids: [TAG_A] });
  });

  it("folds a tag whose group_id matches no fetched group into Ungrouped instead of dropping it", async () => {
    mockUseTagGroups.mockReturnValue({ data: tagGroupsResponse() });
    const ORPHAN_TAG = "33333333-3333-3333-3333-333333333333";
    const STALE_GROUP_ID = "99999999-9999-9999-9999-999999999999";
    await mountAt({
      detail: makeDetail({
        tags: [
          {
            id: ORPHAN_TAG,
            slug: "orphan",
            name_en: "Orphan",
            name_pl: null,
            group_id: STALE_GROUP_ID,
            group_position: 0,
          },
        ],
      }),
      isAdmin: false,
    });

    expect(screen.getByText("Ungrouped")).toBeTruthy();
    const chip = screen.getByText("orphan");
    expect(chip.getAttribute("data-testid")).toBe("tag-chip");
  });

  it("uses name_pl for a group label when the UI language is Polish and name_pl is non-empty", async () => {
    await i18n.changeLanguage("pl");
    mockUseTagGroups.mockReturnValue({ data: tagGroupsResponse() });
    await mountAt({ detail: makeDetail(), isAdmin: true });

    expect(screen.getByText("Materiał")).toBeTruthy();
    expect(screen.queryByText("Material")).toBeNull();
    await i18n.changeLanguage("en");
  });
});
