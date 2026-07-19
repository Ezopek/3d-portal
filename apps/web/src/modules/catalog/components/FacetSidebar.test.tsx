import "@/locales/i18n";

import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import type { ComponentProps } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "@/locales/i18n";
import type { TagGroupRead, TagReadWithCount } from "@/lib/api-types";

import { FacetSidebar } from "./FacetSidebar";

const STORAGE_KEY = "catalog:facet-collapse";

function tag(
  id: string,
  name_en: string,
  name_pl: string | null,
  model_count: number,
): TagReadWithCount {
  return { id, slug: id, name_en, name_pl, group_id: null, group_position: 0, model_count };
}

function group(
  id: string,
  position: number,
  name_en: string,
  tags: TagReadWithCount[],
): TagGroupRead {
  return { id, slug: id, name_en, name_pl: null, position, tags };
}

const T_DRAGON = tag("t_dragon", "Dragon", "Smok", 5);
const T_VASE = tag("t_vase", "Vase", "Wazon", 3);
const T_KITCHEN = tag("t_kitchen", "Kitchen", "Kuchnia", 2);
const T_GRIDFINITY = tag("t_gridfinity", "Gridfinity", null, 7);
const T_PLA = tag("t_pla", "PLA", null, 1);
const T_MISC = tag("t_misc", "Misc", "Rozne", 4);

// Deliberately out of `position` order to exercise the sort.
const GROUPS: TagGroupRead[] = [
  group("g_system", 2, "System", [T_GRIDFINITY]),
  group("g_type", 0, "Type", [T_DRAGON, T_VASE]),
  group("g_material", 3, "Material", [T_PLA]),
  group("g_room", 1, "Room", [T_KITCHEN]),
];
const GROUPLESS: TagReadWithCount[] = [T_MISC];

function renderSidebar(overrides: Partial<ComponentProps<typeof FacetSidebar>> = {}) {
  const props = {
    groups: GROUPS,
    groupless: GROUPLESS,
    selectedTagIds: [] as string[],
    onToggleTag: vi.fn(),
    untaggedActive: false,
    onToggleUntagged: vi.fn(),
    ...overrides,
  };
  render(<FacetSidebar {...props} />);
  return props;
}

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  cleanup();
  localStorage.clear();
});

describe("FacetSidebar", () => {
  it("renders search input; expands the first 2 groups by position; shows checkbox, name, and count", () => {
    renderSidebar();

    expect(screen.getByPlaceholderText(/search tag/i)).toBeTruthy();

    // Groups by position: Type(0), Room(1) expanded -> their tags visible.
    expect(screen.getByText("Dragon")).toBeTruthy();
    expect(screen.getByText("Vase")).toBeTruthy();
    expect(screen.getByText("Kitchen")).toBeTruthy();
    // System(2), Material(3) collapsed -> their tags hidden.
    expect(screen.queryByText("Gridfinity")).toBeNull();
    expect(screen.queryByText("PLA")).toBeNull();

    // A visible tag row exposes checkbox + count.
    expect(screen.getByRole("checkbox", { name: /Dragon/i })).toBeTruthy();
    expect(screen.getByText("5")).toBeTruthy();

    // Untagged pinned footer row.
    expect(screen.getByRole("checkbox", { name: /untagged/i })).toBeTruthy();
  });

  it("expands a group beyond the first 2 when it contains a selected tag (no persisted state)", () => {
    renderSidebar({ selectedTagIds: ["t_gridfinity"] });

    // System is position 2 (beyond first 2) but holds a selected tag.
    const cb = screen.getByRole("checkbox", { name: /Gridfinity/i }) as HTMLInputElement;
    expect(cb).toBeTruthy();
    expect(cb.checked).toBe(true);
  });

  it("fires onToggleTag once with the tag id and reflects controlled checked state", () => {
    const { onToggleTag } = renderSidebar({ selectedTagIds: ["t_dragon"] });

    const dragon = screen.getByRole("checkbox", { name: /Dragon/i }) as HTMLInputElement;
    expect(dragon.checked).toBe(true);
    const vase = screen.getByRole("checkbox", { name: /Vase/i }) as HTMLInputElement;
    expect(vase.checked).toBe(false);

    fireEvent.click(vase);
    expect(onToggleTag).toHaveBeenCalledTimes(1);
    expect(onToggleTag).toHaveBeenCalledWith("t_vase");
  });

  it("fires onToggleUntagged once and reflects untaggedActive", () => {
    const { onToggleUntagged } = renderSidebar({ untaggedActive: true });

    const untagged = screen.getByRole("checkbox", { name: /untagged/i }) as HTMLInputElement;
    expect(untagged.checked).toBe(true);

    fireEvent.click(untagged);
    expect(onToggleUntagged).toHaveBeenCalledTimes(1);
  });

  it("renders untaggedCount when provided", () => {
    renderSidebar({ untaggedCount: 42 });
    expect(screen.getByText("42")).toBeTruthy();
  });

  it("filters tags by case-insensitive substring, expands matching groups, hides non-matching, keeps untagged pinned", () => {
    renderSidebar();

    fireEvent.change(screen.getByPlaceholderText(/search tag/i), { target: { value: "GRID" } });

    // Gridfinity is in a group collapsed-by-default, but a search match forces expansion.
    expect(screen.getByText("Gridfinity")).toBeTruthy();
    // Non-matching tags hidden.
    expect(screen.queryByText("Dragon")).toBeNull();
    expect(screen.queryByText("Kitchen")).toBeNull();
    // Untagged row still pinned.
    expect(screen.getByRole("checkbox", { name: /untagged/i })).toBeTruthy();
  });

  it("matches on name_pl as well as name_en", () => {
    renderSidebar();
    fireEvent.change(screen.getByPlaceholderText(/search tag/i), { target: { value: "kuchnia" } });
    expect(screen.getByText("Kitchen")).toBeTruthy();
    expect(screen.queryByText("Dragon")).toBeNull();
  });

  it("shows the no-matches message and still pins the untagged row when nothing matches", () => {
    renderSidebar();
    fireEvent.change(screen.getByPlaceholderText(/search tag/i), { target: { value: "zzzzz" } });
    expect(screen.getByText(/no matches/i)).toBeTruthy();
    expect(screen.getByRole("checkbox", { name: /untagged/i })).toBeTruthy();
  });

  it("persists collapse state across remounts", () => {
    renderSidebar();
    // Type is expanded by default -> its header is a "Collapse" control.
    fireEvent.click(screen.getByRole("button", { name: /collapse Type/i }));
    expect(screen.queryByText("Dragon")).toBeNull();

    cleanup();
    renderSidebar();

    // Type stays collapsed after remount; Room (also default-expanded) stays open.
    expect(screen.queryByText("Dragon")).toBeNull();
    expect(screen.getByText("Kitchen")).toBeTruthy();
  });

  it("renders the groupless section header when groupless is non-empty and omits it when empty", () => {
    renderSidebar();
    expect(screen.getByText("Ungrouped")).toBeTruthy();
    // Groupless is collapsed by default; expand it to reveal its tag.
    fireEvent.click(screen.getByRole("button", { name: /expand Ungrouped/i }));
    expect(screen.getByText("Misc")).toBeTruthy();

    cleanup();
    localStorage.clear();
    renderSidebar({ groupless: [] });
    expect(screen.queryByText("Ungrouped")).toBeNull();
  });

  it("falls back to default expansion without throwing on malformed localStorage", () => {
    localStorage.setItem(STORAGE_KEY, "{ this is not json");
    expect(() => renderSidebar()).not.toThrow();
    // Default rule still applies: first 2 groups by position expanded, rest collapsed.
    expect(screen.getByText("Dragon")).toBeTruthy();
    expect(screen.queryByText("Gridfinity")).toBeNull();
  });

  it("falls back to name_en when name_pl is an empty string in the pl locale", async () => {
    await i18n.changeLanguage("pl");
    try {
      const emptyPl = tag("t_empty", "Widget", "", 9);
      renderSidebar({ groups: [group("g_only", 0, "OnlyGroup", [emptyPl])], groupless: [] });
      // Empty-string name_pl must not render a blank label.
      expect(screen.getByText("Widget")).toBeTruthy();
      expect(screen.getByRole("checkbox", { name: /Widget/i })).toBeTruthy();
    } finally {
      await i18n.changeLanguage("en");
    }
  });

  it("does not mutate persisted collapse state when a header is clicked during search", () => {
    renderSidebar();
    // Type is expanded by default. Start a search that forces all sections open.
    fireEvent.change(screen.getByPlaceholderText(/search tag/i), { target: { value: "a" } });
    // Clicking the (force-expanded) Type header must be a no-op on collapse state.
    fireEvent.click(screen.getByRole("button", { name: /collapse Type/i }));
    // Clear the search: Type must still be expanded (its default), proving the
    // in-search click did not silently collapse-and-persist it.
    fireEvent.change(screen.getByPlaceholderText(/search tag/i), { target: { value: "" } });
    expect(screen.getByText("Dragon")).toBeTruthy();
  });
});
