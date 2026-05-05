import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FilterRibbon } from "./FilterRibbon";

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
  { id: "t1", slug: "dragon", name_en: "Dragon", name_pl: "Smok" },
  { id: "t2", slug: "articulated", name_en: "Articulated", name_pl: null },
];

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
    fireEvent.click(screen.getByLabelText("remove tag dragon"));
    expect(calls.at(-1)?.tag_ids).toEqual([]);
  });

  it("offers status and source dropdowns", () => {
    render(
      withQuery(
        <FilterRibbon
          state={{ q: "", tag_ids: [], status: undefined, source: undefined, sort: "recent" }}
          tagsById={new Map()}
          onChange={() => {}}
        />,
      ),
    );
    expect(screen.getByLabelText(/status/i)).toBeTruthy();
    expect(screen.getByLabelText(/source/i)).toBeTruthy();
  });

  it("renders localized placeholder labels in unset status/source triggers", () => {
    render(
      withQuery(
        <FilterRibbon
          state={{ q: "", tag_ids: [], status: undefined, source: undefined, sort: "recent" }}
          tagsById={new Map()}
          onChange={() => {}}
        />,
      ),
    );
    const statusTrigger = screen.getByLabelText(/status/i);
    const sourceTrigger = screen.getByLabelText(/source/i);
    expect(statusTrigger.textContent ?? "").toMatch(/Any status/i);
    expect(sourceTrigger.textContent ?? "").toMatch(/Any source/i);
    // The raw sentinel must NOT appear in the trigger.
    expect(statusTrigger.textContent ?? "").not.toMatch(/__any_status__/);
    expect(sourceTrigger.textContent ?? "").not.toMatch(/__any_source__/);
  });

  it("shows the current sort value", () => {
    render(
      withQuery(
        <FilterRibbon
          state={{ q: "", tag_ids: [], status: undefined, source: undefined, sort: "name_asc" }}
          tagsById={new Map()}
          onChange={() => {}}
        />,
      ),
    );
    // The sort select displays its current value as a label
    expect(screen.getByLabelText(/sort/i).textContent ?? "").toMatch(/name_asc|A→Z|Name/i);
  });
});
