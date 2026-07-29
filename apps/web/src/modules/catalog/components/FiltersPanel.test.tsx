import "@/locales/i18n";

import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { TagGroupRead, TagReadWithCount } from "@/lib/api-types";
import i18n from "@/locales/i18n";
import type { FilterRibbonState } from "@/modules/catalog/components/FilterRibbon";

import { FiltersPanel } from "./FiltersPanel";

const GROUP_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const TAG_A = "11111111-1111-1111-1111-111111111111";
const TAG_B = "22222222-2222-2222-2222-222222222222";
const TAG_C = "33333333-3333-3333-3333-333333333333";
const TAG_LOOSE = "44444444-4444-4444-4444-444444444444";

const GROUPS: TagGroupRead[] = [
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
      {
        id: TAG_B,
        slug: "petg",
        name_en: "PETG",
        name_pl: null,
        group_id: GROUP_ID,
        group_position: 1,
        model_count: 2,
      },
      {
        id: TAG_C,
        slug: "abs",
        name_en: "ABS",
        name_pl: null,
        group_id: GROUP_ID,
        group_position: 2,
        model_count: 1,
      },
    ],
  },
];

const GROUPLESS: TagReadWithCount[] = [
  {
    id: TAG_LOOSE,
    slug: "misc",
    name_en: "Miscellaneous",
    name_pl: null,
    group_id: null,
    group_position: 0,
    model_count: 4,
  },
];

function baseState(overrides: Partial<FilterRibbonState> = {}): FilterRibbonState {
  return {
    q: "",
    tag_ids: [],
    tag_match: "all",
    status: undefined,
    source: undefined,
    sort: "recent",
    ...overrides,
  };
}

// D-6's hook reads `window.matchMedia`, which jsdom does not implement. Every
// test that cares about the regime stubs it explicitly; the tests that do NOT
// stub it exercise the jsdom-safe fallback (compact / bottom sheet).
function stubMatchMedia(matches: boolean) {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  // `FacetSidebar` persists group-collapse state; a leaked set from one test
  // would silently change which tag rows the next one can see.
  localStorage.clear();
});

function renderPanel(
  overrides: Partial<Parameters<typeof FiltersPanel>[0]> = {},
) {
  const props = {
    state: baseState(),
    onChange: vi.fn(),
    groups: GROUPS,
    groupless: GROUPLESS,
    onToggleTag: vi.fn(),
    untaggedActive: false,
    onToggleUntagged: vi.fn(),
    open: false,
    onOpenChange: vi.fn(),
    ...overrides,
  };
  render(<FiltersPanel {...props} />);
  return props;
}

// `hidden: true` so the query still resolves while an open modal sheet marks
// the rest of the page `aria-hidden` — the same technique CatalogList's
// sheet-exclusivity block uses. The accessible name carries the count, so the
// caller states which one it expects.
function triggerButton(name = "Filters"): HTMLElement {
  return screen.getByRole("button", { name, hidden: true });
}

describe("FiltersPanel — the (n) badge contract (D-2)", () => {
  it("renders no badge at all at n === 0 — not a 0, not a hidden node", () => {
    renderPanel();

    expect(screen.queryByTestId("filters-trigger-badge")).toBeNull();
    expect(triggerButton().textContent ?? "").not.toMatch(/\d/);
  });

  it("counts each selected tag individually — three tags is exactly 3", () => {
    renderPanel({ state: baseState({ tag_ids: [TAG_A, TAG_B, TAG_C] }) });

    expect(screen.getByTestId("filters-trigger-badge").textContent).toBe("3");
  });

  it("counts untagged, status and source as one each", () => {
    renderPanel({
      state: baseState({ status: "printed", source: "printables" }),
      untaggedActive: true,
    });

    expect(screen.getByTestId("filters-trigger-badge").textContent).toBe("3");
  });

  it("adds every contributor together: 2 tags + untagged + status + source = 5", () => {
    renderPanel({
      state: baseState({
        tag_ids: [TAG_A, TAG_B],
        status: "broken",
        source: "own",
      }),
      untaggedActive: true,
    });

    expect(screen.getByTestId("filters-trigger-badge").textContent).toBe("5");
  });

  // AC-7 — the three negatives. `sort` is the behaviour change: the shipped
  // badge counted a non-default sort, EXPERIENCE.md:227 forbids it.
  it("does NOT count a non-default sort", () => {
    renderPanel({ state: baseState({ sort: "name_asc" }) });

    expect(screen.queryByTestId("filters-trigger-badge")).toBeNull();
  });

  it("does NOT count tag_match — flipping all/any leaves the count on the tags alone", () => {
    renderPanel({
      state: baseState({ tag_ids: [TAG_A, TAG_B], tag_match: "all" }),
    });
    expect(screen.getByTestId("filters-trigger-badge").textContent).toBe("2");
    cleanup();

    renderPanel({
      state: baseState({ tag_ids: [TAG_A, TAG_B], tag_match: "any" }),
    });
    expect(screen.getByTestId("filters-trigger-badge").textContent).toBe("2");
  });

  it("does NOT count a non-empty q", () => {
    renderPanel({ state: baseState({ q: "dragon" }) });

    expect(screen.queryByTestId("filters-trigger-badge")).toBeNull();
  });

  it("counts nothing at all when only sort, tag_match and q are set", () => {
    renderPanel({
      state: baseState({ q: "dragon", sort: "rating", tag_match: "any" }),
    });

    expect(screen.queryByTestId("filters-trigger-badge")).toBeNull();
    expect(triggerButton()).toBeTruthy();
  });
});

describe("FiltersPanel — trigger accessible name (D-10)", () => {
  it("is the plain Filters label at n === 0", () => {
    renderPanel();

    expect(triggerButton().getAttribute("aria-label")).toBe("Filters");
  });

  it("carries the number at n > 0, rendering the count into the name", () => {
    renderPanel({ state: baseState({ status: "printed" }) });

    expect(triggerButton("Filters (1)").getAttribute("aria-label")).toBe(
      "Filters (1)",
    );
  });

  it("renders a real Polish counted name, not the raw key", async () => {
    await i18n.changeLanguage("pl");
    renderPanel({ state: baseState({ tag_ids: [TAG_A, TAG_B, TAG_C] }) });

    expect(triggerButton("Filtry (3)").getAttribute("aria-label")).toBe(
      "Filtry (3)",
    );
  });

  it("hides the badge span from the accessibility tree so the count is announced once", () => {
    renderPanel({ state: baseState({ status: "printed", source: "own" }) });

    const badge = screen.getByTestId("filters-trigger-badge");
    expect(badge.getAttribute("aria-hidden")).toBe("true");
    expect(badge.className).toContain("bg-primary");
    expect(badge.className).toContain("rounded-full");
  });

  it("keeps the trigger target at least 24x24 CSS px", () => {
    renderPanel();

    // `size="sm"` resolves to `h-7` = 1.75rem = 28 px, above the 24 px floor
    // EXPERIENCE.md:302 / SC 2.5.8 sets. jsdom does no layout, so the class the
    // size variant emits is the assertable proxy for the box.
    expect(triggerButton().className).toMatch(/\bh-7\b/);
  });

  it("is not breakpoint-gated — it renders at every viewport (AC-1a)", () => {
    renderPanel();

    const cls = triggerButton().className;
    expect(cls).not.toMatch(/\b(lg|md|sm):hidden\b/);
    expect(cls).not.toMatch(/\bhidden\b/);
  });
});

describe("FiltersPanel — one Sheet, responsive side (D-6)", () => {
  it("renders on the right at lg and above", async () => {
    stubMatchMedia(true);
    renderPanel({ open: true });

    const dialog = await screen.findByRole("dialog", { name: "Filters" });
    expect(dialog.getAttribute("data-side")).toBe("right");
    expect(dialog.className).toContain("w-80");
    expect(dialog.className).toContain("max-w-[85vw]");
  });

  it("renders as a bottom sheet below lg", async () => {
    stubMatchMedia(false);
    renderPanel({ open: true });

    const dialog = await screen.findByRole("dialog", { name: "Filters" });
    expect(dialog.getAttribute("data-side")).toBe("bottom");
    expect(dialog.className).toContain("max-h-[80vh]");
  });

  it("falls back to the compact regime when matchMedia is unavailable (jsdom)", async () => {
    // Deliberately NOT stubbed: jsdom ships no `matchMedia`, so this is the
    // real fallback path, and it must yield a plain `false` rather than an
    // `undefined` snapshot that would make useSyncExternalStore loop.
    expect(typeof window.matchMedia).not.toBe("function");
    renderPanel({ open: true });

    const dialog = await screen.findByRole("dialog", { name: "Filters" });
    expect(dialog.getAttribute("data-side")).toBe("bottom");
  });

  it("mounts exactly ONE sheet content node, never a duplicated subtree", async () => {
    stubMatchMedia(true);
    renderPanel({ open: true });

    await screen.findByRole("dialog", { name: "Filters" });
    expect(document.querySelectorAll("[data-slot='sheet-content']")).toHaveLength(1);
    expect(screen.getAllByRole("dialog")).toHaveLength(1);
    // One facet surface, so exactly one tag-search input and one Untagged row.
    expect(
      screen.getAllByRole("checkbox", { name: "Untagged models" }),
    ).toHaveLength(1);
    expect(screen.getAllByRole("textbox", { name: "Search tag…" })).toHaveLength(1);
  });
});

describe("FiltersPanel — contents and their order (D-1, EXPERIENCE.md:228)", () => {
  it("reaches every tag group, the groupless section and Bez tagów in one interaction", async () => {
    renderPanel({ open: true });

    const dialog = await screen.findByRole("dialog", { name: "Filters" });
    // Group 1 is expanded by `FacetSidebar`'s shipped default rule.
    expect(
      within(dialog).getByRole("button", { name: "Collapse Material" }),
    ).toBeTruthy();
    expect(within(dialog).getByRole("checkbox", { name: /PLA/ })).toBeTruthy();
    expect(within(dialog).getByRole("checkbox", { name: /PETG/ })).toBeTruthy();
    expect(within(dialog).getByRole("checkbox", { name: /ABS/ })).toBeTruthy();
    // AC-14 — the groupless section starts collapsed (the shipped default),
    // and its tags are reachable by expanding it, inside the same panel.
    const groupless = within(dialog).getByRole("button", {
      name: "Expand Ungrouped",
    });
    expect(
      within(dialog).queryByRole("checkbox", { name: /Miscellaneous/ }),
    ).toBeNull();
    fireEvent.click(groupless);
    expect(
      within(dialog).getByRole("checkbox", { name: /Miscellaneous/ }),
    ).toBeTruthy();
    expect(
      within(dialog).getByRole("checkbox", { name: "Untagged models" }),
    ).toBeTruthy();
  });

  it("reaches a collapsed group's tags through the in-panel search too (AC-14)", async () => {
    renderPanel({ open: true });

    const dialog = await screen.findByRole("dialog", { name: "Filters" });
    fireEvent.change(
      within(dialog).getByRole("textbox", { name: "Search tag…" }),
      { target: { value: "misc" } },
    );

    // An active search force-expands every section, so a groupless tag is
    // reachable without touching the collapse state.
    expect(
      within(dialog).getByRole("checkbox", { name: /Miscellaneous/ }),
    ).toBeTruthy();
  });

  it("puts the facet surface before status, source and sort", async () => {
    renderPanel({ open: true });

    const dialog = await screen.findByRole("dialog", { name: "Filters" });
    const facetSearch = within(dialog).getByRole("textbox", {
      name: "Search tag…",
    });
    const untagged = within(dialog).getByRole("checkbox", {
      name: "Untagged models",
    });
    const status = within(dialog).getByRole("combobox", { name: "Status" });
    const source = within(dialog).getByRole("combobox", { name: "Source" });
    const sort = within(dialog).getByRole("combobox", { name: "Sort" });

    const order = [facetSearch, untagged, status, source, sort];
    for (let i = 0; i < order.length - 1; i += 1) {
      const relation = order[i]!.compareDocumentPosition(order[i + 1]!);
      expect(relation & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
  });

  it("keeps the in-panel tag search working, with the shipped no-match copy", async () => {
    renderPanel({ open: true });

    const dialog = await screen.findByRole("dialog", { name: "Filters" });
    const search = within(dialog).getByRole("textbox", { name: "Search tag…" });

    fireEvent.change(search, { target: { value: "pet" } });
    expect(within(dialog).getByRole("checkbox", { name: /PETG/ })).toBeTruthy();
    expect(within(dialog).queryByRole("checkbox", { name: /PLA/ })).toBeNull();

    fireEvent.change(search, { target: { value: "zzzz" } });
    expect(within(dialog).getByText("No matches")).toBeTruthy();
  });

  it("routes facet toggles and Select changes through SEPARATE handlers (D-11)", async () => {
    const props = renderPanel({ open: true });

    const dialog = await screen.findByRole("dialog", { name: "Filters" });
    fireEvent.click(within(dialog).getByRole("checkbox", { name: /PLA/ }));
    expect(props.onToggleTag).toHaveBeenCalledWith(TAG_A);
    expect(props.onChange).not.toHaveBeenCalled();

    fireEvent.click(
      within(dialog).getByRole("checkbox", { name: "Untagged models" }),
    );
    expect(props.onToggleUntagged).toHaveBeenCalled();
    expect(props.onChange).not.toHaveBeenCalled();
  });

  it("reflects the selected tags from state.tag_ids — one source, no parallel prop", async () => {
    renderPanel({ open: true, state: baseState({ tag_ids: [TAG_B] }) });

    const dialog = await screen.findByRole("dialog", { name: "Filters" });
    expect(
      (within(dialog).getByRole("checkbox", { name: /PETG/ }) as HTMLInputElement)
        .checked,
    ).toBe(true);
    expect(
      (within(dialog).getByRole("checkbox", { name: /PLA/ }) as HTMLInputElement)
        .checked,
    ).toBe(false);
  });

  it("renders no loading, skeleton or error branch of its own (AC-5b)", async () => {
    renderPanel({ open: true, groups: [], groupless: [] });

    const dialog = await screen.findByRole("dialog", { name: "Filters" });
    expect(within(dialog).queryByRole("status")).toBeNull();
    expect(within(dialog).queryByRole("button", { name: /Retry/i })).toBeNull();
    // The facet surface and the three Selects still render on empty data.
    expect(
      within(dialog).getByRole("checkbox", { name: "Untagged models" }),
    ).toBeTruthy();
    expect(within(dialog).getByRole("combobox", { name: "Sort" })).toBeTruthy();
  });

  it("keeps the three Selects labelled and free of the raw sentinels", async () => {
    renderPanel({
      open: true,
      state: baseState({ source: "own", sort: "rating" }),
    });

    const dialog = await screen.findByRole("dialog", { name: "Filters" });
    expect(
      within(dialog).getByRole("combobox", { name: "Status" }).textContent ?? "",
    ).toMatch(/Any status/i);
    expect(
      within(dialog).getByRole("combobox", { name: "Status" }).textContent ?? "",
    ).not.toMatch(/__any_status__/);
    expect(
      within(dialog).getByRole("combobox", { name: "Source" }).textContent ?? "",
    ).toMatch(/own/);
    expect(
      within(dialog).getByRole("combobox", { name: "Source" }).textContent ?? "",
    ).not.toMatch(/__any_source__/);
  });
});

describe("FiltersPanel — sheet a11y (AC-24)", () => {
  it("names the sheet through SheetTitle", async () => {
    renderPanel({ open: true });

    expect(await screen.findByRole("dialog", { name: "Filters" })).toBeTruthy();
  });

  it("does not render the dialog at all while closed", () => {
    renderPanel({ open: false });

    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("traps focus inside the sheet while it is open", async () => {
    render(<Harness />);
    fireEvent.click(triggerButton());

    const dialog = await screen.findByRole("dialog", { name: "Filters" });
    await waitFor(() => {
      expect(dialog.contains(document.activeElement)).toBe(true);
    });
  });

  it("closes on Escape and returns focus to the trigger", async () => {
    render(<Harness />);
    fireEvent.click(triggerButton());
    const dialog = await screen.findByRole("dialog", { name: "Filters" });

    fireEvent.keyDown(dialog, { key: "Escape" });

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    await waitFor(() => {
      expect(document.activeElement).toBe(triggerButton());
    });
  });
});

// A real controlled harness (not a spy) so open/close, the focus trap and the
// focus return can be exercised against actual state transitions — the shipped
// `@/ui/sheet` primitive owns all three (51.3 verified this against real DOM
// focus), so these tests ASSERT the behaviour rather than re-implementing it.
function Harness() {
  const [open, setOpen] = useState(false);
  return (
    <FiltersPanel
      state={baseState()}
      onChange={vi.fn()}
      groups={GROUPS}
      groupless={GROUPLESS}
      onToggleTag={vi.fn()}
      untaggedActive={false}
      onToggleUntagged={vi.fn()}
      open={open}
      onOpenChange={setOpen}
    />
  );
}
