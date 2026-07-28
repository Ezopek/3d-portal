import "@/locales/i18n";

import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import type { ComponentProps } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import i18n from "@/locales/i18n";
import type { BrowseCategoryRead } from "@/lib/api-types";

import { BrowseRail } from "./BrowseRail";

function category(
  id: string,
  slug: string,
  name_en: string,
  name_pl: string | null,
  position: number,
  model_count: number,
  parent_id: string | null = null,
): BrowseCategoryRead {
  return {
    id,
    slug,
    name_en,
    name_pl,
    position,
    parent_id,
    description_en: null,
    description_pl: null,
    model_count,
  };
}

// The API orders by `(position, slug)`; the component must render this array
// verbatim. The `position` values below are deliberately NOT ascending in array
// order, so any client-side re-sort would visibly reorder the rows and fail.
const CATEGORIES: BrowseCategoryRead[] = [
  category("c1", "organizery", "Organisers", "Organizery", 5, 12),
  category("c2", "uchwyty", "Mounts", "Uchwyty i mocowania", 1, 7),
  category("c3", "dekoracje", "Decor", "Dekoracje i wystrój", 3, 0),
];

function renderRail(overrides: Partial<ComponentProps<typeof BrowseRail>> = {}) {
  const props = {
    categories: CATEGORIES,
    activeSlug: undefined as string | undefined,
    onSelect: vi.fn(),
    isLoading: false,
    isError: false,
    onRetry: vi.fn(),
    ...overrides,
  };
  render(<BrowseRail {...props} />);
  return props;
}

/** Row accessible names are composed label+count, so match on the label prefix. */
function row(name: RegExp | string) {
  return screen.getByRole("button", { name });
}

afterEach(() => {
  cleanup();
});

describe("BrowseRail", () => {
  it("renders a named nav whose first row is 'All catalog', then categories in API order", () => {
    renderRail();

    const nav = screen.getByRole("navigation", { name: /browse categories/i });
    expect(nav).toBeTruthy();

    const rows = screen.getAllByRole("button");
    // 1 "All catalog" + 3 categories, in the order the API returned them.
    expect(rows).toHaveLength(4);
    expect(rows[0]?.textContent).toContain("All catalog");
    expect(rows[1]?.textContent).toContain("Organisers");
    expect(rows[2]?.textContent).toContain("Mounts");
    expect(rows[3]?.textContent).toContain("Decor");
  });

  it("renders each category's model_count in a tabular-nums element", () => {
    renderRail();

    const count = screen.getByText("12");
    expect(count.className).toContain("tabular-nums");
    expect(count.className).toContain("text-xs");
    expect(screen.getByText("7")).toBeTruthy();
    expect(screen.getByText("0")).toBeTruthy();
  });

  it("folds the count into the row's accessible name so it reads as one item", () => {
    renderRail();
    expect(row(/Organisers, 12 models/)).toBeTruthy();
  });

  it("marks 'All catalog' aria-current when no scope is active, and nothing else", () => {
    renderRail({ activeSlug: undefined });

    expect(row(/All catalog/).getAttribute("aria-current")).toBe("page");
    expect(
      screen.getAllByRole("button").filter((b) => b.getAttribute("aria-current") === "page"),
    ).toHaveLength(1);
  });

  it("marks exactly the matching category aria-current when a scope is active", () => {
    renderRail({ activeSlug: "uchwyty" });

    expect(row(/Mounts/).getAttribute("aria-current")).toBe("page");
    expect(row(/All catalog/).getAttribute("aria-current")).toBeNull();
    expect(
      screen.getAllByRole("button").filter((b) => b.getAttribute("aria-current") === "page"),
    ).toHaveLength(1);
  });

  it("applies the shipped ModuleRail active treatment to the active row only", () => {
    renderRail({ activeSlug: "uchwyty" });

    const active = row(/Mounts/);
    expect(active.className).toContain("bg-primary/10");
    expect(active.className).toContain("ring-1");
    expect(active.className).toContain("ring-inset");
    expect(active.className).toContain("ring-primary");
    expect(active.className).toContain("font-medium");

    expect(row(/Organisers/).className).not.toContain("ring-primary");
  });

  it("fires onSelect with the slug when a category row is activated", () => {
    const { onSelect } = renderRail();

    fireEvent.click(row(/Organisers/));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith("organizery");
  });

  it("fires onSelect with undefined when 'All catalog' is activated", () => {
    const { onSelect } = renderRail({ activeSlug: "uchwyty" });

    fireEvent.click(row(/All catalog/));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(undefined);
  });

  it("dims a zero-count category label but keeps the row focusable and navigable", () => {
    const { onSelect } = renderRail();

    const empty = row(/Decor/);
    expect(empty.hasAttribute("disabled")).toBe(false);
    expect(empty.getAttribute("tabindex")).toBeNull();
    expect(screen.getByText("Decor").className).toContain("text-muted-foreground/60");

    fireEvent.click(empty);
    expect(onSelect).toHaveBeenCalledWith("dekoracje");
  });

  it("renders no checkbox anywhere — rows are navigation, not multi-select", () => {
    renderRail();
    expect(screen.queryAllByRole("checkbox")).toHaveLength(0);
  });

  it("renders skeleton rows while loading and keeps 'All catalog' reachable", () => {
    renderRail({ isLoading: true, categories: [] });

    expect(row(/All catalog/)).toBeTruthy();
    expect(screen.getAllByTestId("browse-rail-skeleton").length).toBeGreaterThan(0);
    expect(screen.queryByText(/no models match/i)).toBeNull();
  });

  it("renders 'All catalog' alone on an empty category list, with no error copy", () => {
    renderRail({ categories: [] });

    expect(screen.getAllByRole("button")).toHaveLength(1);
    expect(row(/All catalog/)).toBeTruthy();
    expect(screen.queryByTestId("browse-rail-skeleton")).toBeNull();
    expect(screen.queryByRole("button", { name: /retry/i })).toBeNull();
  });

  it("degrades to 'All catalog' plus an inline retry when the category read fails", () => {
    const { onRetry } = renderRail({ isError: true, categories: [] });

    expect(row(/All catalog/)).toBeTruthy();
    const retry = screen.getByRole("button", { name: /retry/i });
    fireEvent.click(retry);
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("ignores parent_id — MVP browse is flat, with no nesting", () => {
    renderRail({
      categories: [
        category("p", "parent", "Parent", null, 0, 4),
        category("k", "child", "Child", null, 1, 2, "p"),
      ],
    });

    // Both rows are siblings in one list; a child never nests inside a parent row.
    const parentRow = row(/Parent/);
    expect(parentRow.textContent).not.toContain("Child");
    expect(screen.getAllByRole("listitem")).toHaveLength(3); // All catalog + 2
  });

  it("falls back to name_en when name_pl is an empty string in the pl locale", async () => {
    await i18n.changeLanguage("pl");
    try {
      renderRail({ categories: [category("c", "widget", "Widget", "", 0, 3)] });
      expect(screen.getByText("Widget")).toBeTruthy();
    } finally {
      await i18n.changeLanguage("en");
    }
  });

  it("prefers name_pl in the pl locale when it is non-empty", async () => {
    await i18n.changeLanguage("pl");
    try {
      renderRail();
      expect(screen.getByText("Uchwyty i mocowania")).toBeTruthy();
      expect(screen.queryByText("Mounts")).toBeNull();
    } finally {
      await i18n.changeLanguage("en");
    }
  });
});
