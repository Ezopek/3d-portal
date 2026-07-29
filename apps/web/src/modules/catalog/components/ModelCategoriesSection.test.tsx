import "@/locales/i18n";

import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
} from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it } from "vitest";

import type { BrowseCategorySummary, ModelDetail } from "@/lib/api-types";
import i18n from "@/locales/i18n";
import { Route as CategoryRoute } from "@/routes/categories/$slug";

import { ModelCategoriesSection } from "./ModelCategoriesSection";

const CAT_STORAGE: BrowseCategorySummary = {
  id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
  slug: "storage-organization",
  name_en: "Storage & organization",
  name_pl: "Przechowywanie i organizacja",
  position: 0,
  parent_id: null,
};
// `name_pl: null` exercises the labelOf fallback under the pl locale.
const CAT_HOLDERS: BrowseCategorySummary = {
  id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
  slug: "holders-mounts",
  name_en: "Holders & mounts",
  name_pl: null,
  position: 2,
  parent_id: null,
};

beforeAll(async () => {
  await i18n.changeLanguage("en");
});

afterEach(cleanup);

function makeDetail(categories: BrowseCategorySummary[]): ModelDetail {
  return {
    id: "model-1",
    slug: "dragon",
    name_en: "Dragon",
    name_pl: "Smok",
    source: "printables",
    status: "printed",
    rating: null,
    thumbnail_file_id: null,
    date_added: "2026-04-12",
    deleted_at: null,
    created_at: "2026-04-12T00:00:00Z",
    updated_at: "2026-04-12T00:00:00Z",
    tags: [],
    files: [],
    prints: [],
    notes: [],
    categories,
    external_links: [],
    gallery_file_ids: [],
    image_count: 0,
  };
}

// Mount at "/" under a router whose sibling "/categories/$slug" route reuses
// the real route's `validateSearch` — the entries are `<Link>`s and must
// resolve against real router context (mirrors TagGroupsSection.test.tsx).
async function mountAt(props: { detail: ModelDetail; isAdmin: boolean }) {
  const root = createRootRoute({ component: () => <Outlet /> });
  const host = createRoute({
    getParentRoute: () => root,
    path: "/",
    component: () => (
      <ModelCategoriesSection detail={props.detail} isAdmin={props.isAdmin} />
    ),
  });
  const category = createRoute({
    getParentRoute: () => root,
    path: "/categories/$slug",
    component: () => <div data-testid="category-route" />,
    validateSearch: CategoryRoute.options.validateSearch,
  });
  const router = createRouter({
    routeTree: root.addChildren([host, category]),
    history: createMemoryHistory({ initialEntries: ["/"] }),
  });
  await router.load();
  render(<RouterProvider router={router} />);
  return { router };
}

describe("ModelCategoriesSection", () => {
  it("renders the heading and one link per category for a member", async () => {
    await mountAt({ detail: makeDetail([CAT_STORAGE, CAT_HOLDERS]), isAdmin: false });

    expect(screen.getByText("Categories")).toBeTruthy();
    const links = screen.getAllByTestId("model-category-link");
    expect(links).toHaveLength(2);
    expect(links.map((l) => l.textContent)).toEqual([
      "Storage & organization",
      "Holders & mounts",
    ]);
  });

  it("renders identically for an admin when the model has categories (no extra affordance)", async () => {
    await mountAt({ detail: makeDetail([CAT_STORAGE, CAT_HOLDERS]), isAdmin: true });

    expect(screen.getAllByTestId("model-category-link")).toHaveLength(2);
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.queryByText(/needs curation/i)).toBeNull();
  });

  it("preserves wire order rather than re-sorting by position (D-9)", async () => {
    // Deliberately reversed relative to `position`: the backend owns the sort
    // (position, slug) and the component must not fork that contract.
    await mountAt({ detail: makeDetail([CAT_HOLDERS, CAT_STORAGE]), isAdmin: false });

    expect(
      screen.getAllByTestId("model-category-link").map((l) => l.textContent),
    ).toEqual(["Holders & mounts", "Storage & organization"]);
  });

  it("renders nothing at all for a zero-category model viewed by a member", async () => {
    const { router } = await mountAt({ detail: makeDetail([]), isAdmin: false });

    expect(screen.queryByText("Categories")).toBeNull();
    expect(screen.queryByTestId("model-category-link")).toBeNull();
    expect(screen.queryByText("—")).toBeNull();
    expect(screen.queryByText(/needs curation/i)).toBeNull();
    expect(router.state.location.pathname).toBe("/");
  });

  it("renders exactly one static advisory line for a zero-category model viewed by an admin", async () => {
    await mountAt({ detail: makeDetail([]), isAdmin: true });

    const advisory = screen.getByText("No categories — needs curation");
    expect(advisory).toBeTruthy();
    // Static text: not a control, not a link, and it opens nothing (D-5, V-8 —
    // /admin/categories is Story 52.2 and does not exist yet).
    expect(advisory.tagName).toBe("SPAN");
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.queryByTestId("model-category-link")).toBeNull();
  });

  it("resolves each entry to /categories/{slug} with no catalog search params", async () => {
    await mountAt({ detail: makeDetail([CAT_STORAGE, CAT_HOLDERS]), isAdmin: false });

    const [storage, holders] = screen.getAllByTestId("model-category-link");
    expect(storage?.getAttribute("href")).toBe("/categories/storage-organization");
    expect(holders?.getAttribute("href")).toBe("/categories/holders-mounts");
  });

  it("navigates to the category route on activation", async () => {
    const { router } = await mountAt({
      detail: makeDetail([CAT_STORAGE]),
      isAdmin: false,
    });

    fireEvent.click(screen.getByTestId("model-category-link"));

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/categories/storage-organization");
    });
    expect(router.state.location.search).toEqual({});
  });

  it("gives each entry an accessible name equal to its visible label (WCAG 2.2 SC 2.5.3)", async () => {
    await mountAt({ detail: makeDetail([CAT_STORAGE, CAT_HOLDERS]), isAdmin: false });

    for (const label of ["Storage & organization", "Holders & mounts"]) {
      const link = screen.getByRole("link", { name: label });
      expect(link.textContent).toBe(label);
      // No aria-label may shadow the visible text.
      expect(link.getAttribute("aria-label")).toBeNull();
    }
  });

  it("keeps every entry keyboard-focusable and in reading order", async () => {
    await mountAt({ detail: makeDetail([CAT_STORAGE, CAT_HOLDERS]), isAdmin: false });

    const links = screen.getAllByTestId("model-category-link");
    for (const link of links) {
      // An anchor with an href is focusable by default; a negative tabIndex
      // would silently remove it from the tab order.
      expect(link.getAttribute("href")).toBeTruthy();
      expect(link.getAttribute("tabindex")).toBeNull();
      link.focus();
      expect(document.activeElement).toBe(link);
    }
  });

  it("carries the ≥24×24 CSS px target-size floor and the location vocabulary", async () => {
    await mountAt({ detail: makeDetail([CAT_STORAGE]), isAdmin: false });

    // jsdom has no layout engine, so the floor is asserted on the class that
    // sets it (`min-h-6` = 24px) rather than a measured box.
    const cls = screen.getByTestId("model-category-link").className;
    expect(cls).toContain("min-h-6");
    expect(cls).toContain("bg-primary/10");
    expect(cls).toContain("ring-primary");
    expect(cls).toContain("rounded-md");
    // The tag-chip vocabulary must never leak onto a category (DESIGN.md:294).
    expect(cls).not.toContain("bg-muted");
    expect(cls).not.toContain("rounded-full");
  });

  it("renders no model_count and does not nest or indent by parent_id", async () => {
    const child: BrowseCategorySummary = {
      ...CAT_HOLDERS,
      parent_id: CAT_STORAGE.id,
    };
    await mountAt({ detail: makeDetail([CAT_STORAGE, child]), isAdmin: false });

    const links = screen.getAllByTestId("model-category-link");
    expect(links).toHaveLength(2);
    // Flat MVP browse (FR26-CAT-4): the child is a sibling in the DOM, not a
    // descendant of the parent's entry.
    const [parent, nested] = links;
    if (parent === undefined || nested === undefined) throw new Error("missing entries");
    expect(parent.contains(nested)).toBe(false);
    expect(parent.className).toBe(nested.className);
    expect(document.body.textContent).not.toMatch(/\d/);
  });

  it("uses name_pl under the pl locale when it is a non-empty string", async () => {
    await i18n.changeLanguage("pl");
    try {
      await mountAt({ detail: makeDetail([CAT_STORAGE]), isAdmin: false });
      expect(screen.getByText("Przechowywanie i organizacja")).toBeTruthy();
      expect(screen.queryByText("Storage & organization")).toBeNull();
      expect(screen.getByText("Kategorie")).toBeTruthy();
    } finally {
      await i18n.changeLanguage("en");
    }
  });

  it("falls back to name_en under the pl locale when name_pl is null", async () => {
    await i18n.changeLanguage("pl");
    try {
      await mountAt({ detail: makeDetail([CAT_HOLDERS]), isAdmin: false });
      expect(screen.getByText("Holders & mounts")).toBeTruthy();
    } finally {
      await i18n.changeLanguage("en");
    }
  });

  it("falls back to name_en under the pl locale when name_pl is an empty string", async () => {
    await i18n.changeLanguage("pl");
    try {
      await mountAt({
        detail: makeDetail([{ ...CAT_STORAGE, name_pl: "" }]),
        isAdmin: false,
      });
      expect(screen.getByText("Storage & organization")).toBeTruthy();
    } finally {
      await i18n.changeLanguage("en");
    }
  });

  it("uses the pl advisory copy fixed by EXPERIENCE.md for a zero-category admin view", async () => {
    await i18n.changeLanguage("pl");
    try {
      await mountAt({ detail: makeDetail([]), isAdmin: true });
      expect(screen.getByText("Bez kategorii — do uzupełnienia")).toBeTruthy();
    } finally {
      await i18n.changeLanguage("en");
    }
  });
});
