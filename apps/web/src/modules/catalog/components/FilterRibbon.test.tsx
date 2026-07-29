import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, cleanup, fireEvent, waitFor, within } from "@testing-library/react";
import { useState, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FilterRibbon, type FilterRibbonState } from "./FilterRibbon";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => {
  cleanup();
  fetchMock.mockReset();
});

function withQuery(node: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{node}</QueryClientProvider>;
}

const TAGS = [
  { id: "t1", slug: "dragon", name_en: "Dragon", name_pl: "Smok", group_id: null, group_position: 0 },
  { id: "t2", slug: "articulated", name_en: "Articulated", name_pl: null, group_id: null, group_position: 0 },
];

// Story 52.1 D-1 — `FilterRibbon` is now purely ACTIVE-CONSTRAINT DISPLAY:
// search, selected-tag chips, match-mode toggle. The status/source/sort
// Selects, the `+ tag` picker, the mobile Filters sheet and the `(n)` badge all
// live in `FiltersPanel` and are covered by `FiltersPanel.test.tsx`.
describe("FilterRibbon", () => {
  it("renders the search input and current value", () => {
    render(
      withQuery(
        <FilterRibbon
          state={{ q: "dragon", tag_ids: [], status: undefined, source: undefined, sort: "recent" }}
          tagsById={new Map()}
          onChange={() => {}}
        />,
      ),
    );
    const input = screen.getByPlaceholderText(/search/i) as HTMLInputElement;
    expect(input.value).toBe("dragon");
  });

  it("calls onChange when q changes", () => {
    const calls: { q?: string }[] = [];
    render(
      withQuery(
        <FilterRibbon
          state={{ q: "", tag_ids: [], status: undefined, source: undefined, sort: "recent" }}
          tagsById={new Map()}
          onChange={(s) => calls.push(s)}
        />,
      ),
    );
    const input = screen.getByPlaceholderText(/search/i);
    fireEvent.change(input, { target: { value: "drag" } });
    expect(calls.length).toBeGreaterThan(0);
    expect(calls.at(-1)?.q).toBe("drag");
  });

  it("renders selected tag chips with their slug labels and a remove control", () => {
    const tagsById = new Map(TAGS.map((t) => [t.id, t]));
    const calls: { tag_ids?: string[] }[] = [];
    render(
      withQuery(
        <FilterRibbon
          state={{ q: "", tag_ids: ["t1"], status: undefined, source: undefined, sort: "recent" }}
          tagsById={tagsById}
          onChange={(s) => calls.push(s)}
        />,
      ),
    );
    expect(screen.getByText("dragon")).toBeTruthy();
    fireEvent.click(screen.getByLabelText(/remove tag dragon/i));
    expect(calls.at(-1)?.tag_ids).toEqual([]);
  });

  // AC-4 / AC-12 — the three controls this story removed from the ribbon. Each
  // is asserted ABSENT here and PRESENT in `FiltersPanel.test.tsx`, so the
  // consolidation cannot silently leave two write paths behind.
  it("no longer renders the status/source/sort Selects — they live in the Filters panel", () => {
    render(
      withQuery(
        <FilterRibbon
          state={{ q: "", tag_ids: [], status: undefined, source: undefined, sort: "name_asc" }}
          tagsById={new Map()}
          onChange={() => {}}
        />,
      ),
    );
    expect(screen.queryByRole("combobox", { name: /status/i })).toBeNull();
    expect(screen.queryByRole("combobox", { name: /source/i })).toBeNull();
    expect(screen.queryByRole("combobox", { name: /sort/i })).toBeNull();
  });

  it("no longer renders the + tag picker path", () => {
    render(
      withQuery(
        <FilterRibbon
          state={{ q: "", tag_ids: [], status: undefined, source: undefined, sort: "recent" }}
          tagsById={new Map()}
          onChange={() => {}}
        />,
      ),
    );
    expect(screen.queryByRole("button", { name: /^\+\s*tag$/i })).toBeNull();
    expect(screen.queryByRole("dialog", { name: /add tags|dodaj tagi/i })).toBeNull();
  });

  it("no longer renders a Filters trigger or an (n) badge of its own", () => {
    render(
      withQuery(
        <FilterRibbon
          state={{ q: "", tag_ids: ["t1"], status: "printed", source: undefined, sort: "recent" }}
          tagsById={new Map(TAGS.map((t) => [t.id, t]))}
          onChange={() => {}}
        />,
      ),
    );
    expect(screen.queryByRole("button", { name: /^Filters/i })).toBeNull();
    expect(screen.queryByTestId("filters-trigger-badge")).toBeNull();
  });

  it("does not render the AND/OR toggle with zero tags", () => {
    render(
      withQuery(
        <FilterRibbon
          state={{ q: "", tag_ids: [], status: undefined, source: undefined, sort: "recent" }}
          tagsById={new Map()}
          onChange={() => {}}
        />,
      ),
    );
    expect(screen.queryByRole("group", { name: /tag match/i })).toBeNull();
  });

  it("does not render the AND/OR toggle with a single tag", () => {
    const tagsById = new Map(TAGS.map((t) => [t.id, t]));
    render(
      withQuery(
        <FilterRibbon
          state={{ q: "", tag_ids: ["t1"], status: undefined, source: undefined, sort: "recent" }}
          tagsById={tagsById}
          onChange={() => {}}
        />,
      ),
    );
    expect(screen.queryByRole("group", { name: /tag match/i })).toBeNull();
  });

  it("renders the AND/OR toggle with two tags, All pressed by default", () => {
    const tagsById = new Map(TAGS.map((t) => [t.id, t]));
    render(
      withQuery(
        <FilterRibbon
          state={{ q: "", tag_ids: ["t1", "t2"], status: undefined, source: undefined, sort: "recent" }}
          tagsById={tagsById}
          onChange={() => {}}
        />,
      ),
    );
    const group = screen.getByRole("group", { name: /tag match/i });
    const allBtn = within(group).getByRole("button", { name: /^All$/i });
    const anyBtn = within(group).getByRole("button", { name: /^Any$/i });
    expect(allBtn.getAttribute("aria-pressed")).toBe("true");
    expect(anyBtn.getAttribute("aria-pressed")).toBe("false");
  });

  it("fires onChange once with tag_match: any when Any is clicked", () => {
    const tagsById = new Map(TAGS.map((t) => [t.id, t]));
    const calls: { tag_match?: string }[] = [];
    render(
      withQuery(
        <FilterRibbon
          state={{ q: "", tag_ids: ["t1", "t2"], status: undefined, source: undefined, sort: "recent" }}
          tagsById={tagsById}
          onChange={(s) => calls.push(s)}
        />,
      ),
    );
    const group = screen.getByRole("group", { name: /tag match/i });
    fireEvent.click(within(group).getByRole("button", { name: /^Any$/i }));
    expect(calls.length).toBe(1);
    expect(calls[0]?.tag_match).toBe("any");
  });

  it("fires onChange with tag_match: all when All is clicked while set to any", () => {
    const tagsById = new Map(TAGS.map((t) => [t.id, t]));
    const calls: { tag_match?: string }[] = [];
    render(
      withQuery(
        <FilterRibbon
          state={{ q: "", tag_ids: ["t1", "t2"], tag_match: "any", status: undefined, source: undefined, sort: "recent" }}
          tagsById={tagsById}
          onChange={(s) => calls.push(s)}
        />,
      ),
    );
    const group = screen.getByRole("group", { name: /tag match/i });
    fireEvent.click(within(group).getByRole("button", { name: /^All$/i }));
    expect(calls.length).toBe(1);
    expect(calls[0]?.tag_match).toBe("all");
  });

  it("reflects the tag_match prop in aria-pressed", () => {
    const tagsById = new Map(TAGS.map((t) => [t.id, t]));
    render(
      withQuery(
        <FilterRibbon
          state={{ q: "", tag_ids: ["t1", "t2"], tag_match: "any", status: undefined, source: undefined, sort: "recent" }}
          tagsById={tagsById}
          onChange={() => {}}
        />,
      ),
    );
    const group = screen.getByRole("group", { name: /tag match/i });
    expect(within(group).getByRole("button", { name: /^Any$/i }).getAttribute("aria-pressed")).toBe("true");
    expect(within(group).getByRole("button", { name: /^All$/i }).getAttribute("aria-pressed")).toBe("false");
  });

  // Story 50.3 — the inline SearchSuggest combobox. Story 52.1 adds NO
  // behaviour here: selecting a suggested tag still only touches tag_ids/q, and
  // status/source/sort still ride through untouched (they are simply written by
  // a different surface now).
  it("selecting a suggested tag updates tag_ids and q, leaving status/source/sort untouched", async () => {
    fetchMock.mockImplementation((url: string) => {
      if (url.includes("/tag-groups")) {
        return Promise.resolve(
          new Response(JSON.stringify({ groups: [], groupless: [] }), { status: 200 }),
        );
      }
      return Promise.resolve(new Response(JSON.stringify(TAGS), { status: 200 }));
    });
    const calls: Array<{ q: string; tag_ids: string[]; source?: string; sort: string }> = [];
    function Harness() {
      const [state, setState] = useState<FilterRibbonState>({
        q: "",
        tag_ids: [],
        status: undefined,
        source: "printables",
        sort: "name_asc",
      });
      return (
        <FilterRibbon
          state={state}
          tagsById={new Map()}
          onChange={(s) => {
            calls.push(s);
            setState(s);
          }}
        />
      );
    }
    render(withQuery(<Harness />));
    const input = screen.getByPlaceholderText(/search/i);
    fireEvent.change(input, { target: { value: "drag" } });
    await waitFor(() => {
      expect(screen.getAllByRole("option").length).toBeGreaterThan(1);
    });
    const tagOption = screen.getByRole("option", { name: /add filter: dragon/i });
    fireEvent.click(tagOption);
    const last = calls.at(-1)!;
    expect(last.tag_ids).toEqual(["t1"]);
    expect(last.q).toBe("");
    expect(last.source).toBe("printables");
    expect(last.sort).toBe("name_asc");
  });
});
