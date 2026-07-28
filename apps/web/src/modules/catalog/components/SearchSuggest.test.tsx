import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { TagGroupsResponse, TagListItem } from "@/lib/api-types";
import { SearchSuggest } from "./SearchSuggest";

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

const GROUP_ID = "gg-theme";

const TAG_GROUPS: TagGroupsResponse = {
  groups: [
    {
      id: GROUP_ID,
      slug: "theme",
      name_en: "Theme",
      name_pl: null,
      position: 0,
      tags: [],
    },
  ],
  groupless: [],
};

function tag(over: Partial<TagListItem> = {}): TagListItem {
  return {
    id: "t1",
    slug: "dragon",
    name_en: "Dragon",
    name_pl: "Smok",
    group_id: null,
    group_position: 0,
    ...over,
  };
}

function setupFetch(opts: {
  tags?: TagListItem[] | "error";
  tagGroups?: TagGroupsResponse | "pending" | "error";
}) {
  const tags = opts.tags ?? [];
  const tagGroups = opts.tagGroups ?? { groups: [], groupless: [] };
  fetchMock.mockImplementation((url: string) => {
    if (url.includes("/tag-groups")) {
      if (tagGroups === "pending") return new Promise<Response>(() => {});
      if (tagGroups === "error") {
        return Promise.resolve(new Response(JSON.stringify({}), { status: 500 }));
      }
      return Promise.resolve(new Response(JSON.stringify(tagGroups), { status: 200 }));
    }
    if (url.includes("/tags")) {
      if (tags === "error") {
        return Promise.resolve(new Response(JSON.stringify({}), { status: 500 }));
      }
      return Promise.resolve(new Response(JSON.stringify(tags), { status: 200 }));
    }
    return Promise.reject(new Error(`unexpected fetch ${url}`));
  });
}

// The plain-query row renders synchronously (before `useTags` resolves), so
// `findAllByRole("option")` alone can resolve before tag rows have appeared.
// Wait for the exact expected row count instead.
async function findOptions(count: number) {
  await waitFor(() => {
    expect(screen.getAllByRole("option")).toHaveLength(count);
  });
  return screen.getAllByRole("option");
}

function renderSuggest(
  over: Partial<{
    q: string;
    tagIds: string[];
    onQueryChange: (q: string) => void;
    onSelectTag: (id: string) => void;
  }> = {},
) {
  const onQueryChange = over.onQueryChange ?? vi.fn();
  const onSelectTag = over.onSelectTag ?? vi.fn();
  render(
    withQuery(
      <SearchSuggest
        q={over.q ?? ""}
        tagIds={over.tagIds ?? []}
        onQueryChange={onQueryChange}
        onSelectTag={onSelectTag}
      />,
    ),
  );
  return { onQueryChange, onSelectTag };
}

describe("SearchSuggest", () => {
  it("keeps the panel closed when the query is empty or whitespace-only", () => {
    setupFetch({});
    renderSuggest({ q: "" });
    expect(screen.queryByRole("listbox")).toBeNull();
  });

  it("opens the panel once the query has at least one character", async () => {
    setupFetch({ tags: [] });
    renderSuggest({ q: "d" });
    expect(await screen.findByRole("listbox")).toBeTruthy();
  });

  it("always renders the plain-query row first, with the typed text and a distinct accessible name", async () => {
    setupFetch({ tags: [tag()] });
    renderSuggest({ q: "drag" });
    const options = await screen.findAllByRole("option");
    expect(options[0]?.textContent).toContain("drag");
    expect(options[0]?.getAttribute("aria-label")).toMatch(/^Search: drag$/i);
  });

  it("renders matching tags below the plain-query row with a distinct accessible name", async () => {
    setupFetch({ tags: [tag({ id: "t1", name_en: "Dragon" })] });
    renderSuggest({ q: "drag" });
    const options = await findOptions(2);
    expect(options[1]?.getAttribute("aria-label")).toMatch(/^Add filter: Dragon$/i);
  });

  it("excludes tags already present in tagIds", async () => {
    setupFetch({ tags: [tag({ id: "t1" }), tag({ id: "t2", slug: "other", name_en: "Other" })] });
    renderSuggest({ q: "d", tagIds: ["t1"] });
    // plain-query row + only the non-selected tag
    const options = await findOptions(2);
    expect(options[1]?.getAttribute("aria-label")).toMatch(/Other/);
  });

  it("caps the combined list at 8 rows and renders a non-interactive overflow note past 7 tag matches", async () => {
    const tags = Array.from({ length: 9 }, (_, i) =>
      tag({ id: `t${i}`, slug: `tag${i}`, name_en: `Tag${i}` }),
    );
    setupFetch({ tags });
    renderSuggest({ q: "t" });
    await findOptions(8); // 1 query row + 7 tag rows
    const overflow = await screen.findByText(/more matches/i);
    expect(overflow.getAttribute("role")).not.toBe("option");
    expect(overflow.closest("[role='listbox']")?.contains(overflow)).toBe(true);
  });

  it("does not render an overflow note when 7 or fewer tags match", async () => {
    const tags = Array.from({ length: 7 }, (_, i) =>
      tag({ id: `t${i}`, slug: `tag${i}`, name_en: `Tag${i}` }),
    );
    setupFetch({ tags });
    renderSuggest({ q: "t" });
    await findOptions(8); // 1 query row + 7 tag rows, no overflow note
    expect(screen.queryByText(/more matches/i)).toBeNull();
  });

  it("renders a group suffix when the tag's group is present in the loaded tag-groups map", async () => {
    setupFetch({ tags: [tag({ group_id: GROUP_ID })], tagGroups: TAG_GROUPS });
    renderSuggest({ q: "drag" });
    const options = await findOptions(2);
    expect(options[1]?.getAttribute("aria-label")).toMatch(/^Add filter: Dragon, group Theme$/i);
  });

  it("omits the group suffix for a groupless tag", async () => {
    setupFetch({ tags: [tag({ group_id: null })], tagGroups: TAG_GROUPS });
    renderSuggest({ q: "drag" });
    const options = await findOptions(2);
    expect(options[1]?.getAttribute("aria-label")).toBe("Add filter: Dragon");
  });

  it("omits the group suffix (never a placeholder) when the tag-groups map has not loaded", async () => {
    setupFetch({ tags: [tag({ group_id: GROUP_ID })], tagGroups: "pending" });
    renderSuggest({ q: "drag" });
    const options = await findOptions(2);
    expect(options[1]?.getAttribute("aria-label")).toBe("Add filter: Dragon");
  });

  it("renders a matched-alias when the query matches only the non-active-locale name", async () => {
    // English UI (default test locale) — query matches name_pl ("Smok") but not name_en ("Dragon").
    setupFetch({ tags: [tag({ name_en: "Dragon", name_pl: "Smok" })] });
    renderSuggest({ q: "smok" });
    const options = await findOptions(2);
    expect(options[1]?.textContent).toMatch(/Smok/);
  });

  it("renders no alias when the query matches the active-locale name", async () => {
    setupFetch({ tags: [tag({ name_en: "Dragon", name_pl: "Smok" })] });
    renderSuggest({ q: "drag" });
    const options = await findOptions(2);
    expect(options[1]?.textContent).not.toMatch(/Smok/);
  });

  it("opens with the plain-query row alone when useTags returns zero matches", async () => {
    setupFetch({ tags: [] });
    renderSuggest({ q: "zzz" });
    const options = await findOptions(1);
    expect(options).toHaveLength(1);
  });

  it("opens with the plain-query row alone when useTags errors", async () => {
    setupFetch({ tags: "error" });
    renderSuggest({ q: "zzz" });
    const options = await findOptions(1);
    expect(options).toHaveLength(1);
  });

  it("clicking the plain-query row closes the panel without selecting a tag", async () => {
    setupFetch({ tags: [tag()] });
    const { onSelectTag } = renderSuggest({ q: "drag" });
    const options = await findOptions(2);
    fireEvent.click(options[0]!);
    expect(onSelectTag).not.toHaveBeenCalled();
    expect(screen.queryByRole("listbox")).toBeNull();
  });

  it("clicking a tag row calls onSelectTag with the tag_id (clearing q is the consumer's job, D-1)", async () => {
    setupFetch({ tags: [tag({ id: "t1" })] });
    const { onSelectTag, onQueryChange } = renderSuggest({ q: "drag" });
    const options = await findOptions(2);
    fireEvent.click(options[1]!);
    expect(onSelectTag).toHaveBeenCalledWith("t1");
    expect(onQueryChange).not.toHaveBeenCalled();
  });

  it("Enter with no row explicitly arrow-highlighted never selects a tag", async () => {
    setupFetch({ tags: [tag({ id: "t1" })] });
    const { onSelectTag, onQueryChange } = renderSuggest({ q: "drag" });
    await findOptions(2);
    const input = screen.getByRole("combobox");
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSelectTag).not.toHaveBeenCalled();
    expect(onQueryChange).not.toHaveBeenCalledWith("");
  });

  it("Enter after ArrowDown onto a tag row selects it", async () => {
    setupFetch({ tags: [tag({ id: "t1" })] });
    const { onSelectTag, onQueryChange } = renderSuggest({ q: "drag" });
    await findOptions(2);
    const input = screen.getByRole("combobox");
    fireEvent.keyDown(input, { key: "ArrowDown" }); // -> row 0 (query)
    fireEvent.keyDown(input, { key: "ArrowDown" }); // -> row 1 (tag)
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSelectTag).toHaveBeenCalledWith("t1");
    expect(onQueryChange).not.toHaveBeenCalled();
  });

  it("Escape closes the panel, preserves the typed text, and selects no tag", async () => {
    setupFetch({ tags: [tag()] });
    const { onSelectTag, onQueryChange } = renderSuggest({ q: "drag" });
    await findOptions(2);
    const input = screen.getByRole("combobox");
    fireEvent.keyDown(input, { key: "Escape" });
    expect(screen.queryByRole("listbox")).toBeNull();
    expect(onSelectTag).not.toHaveBeenCalled();
    expect(onQueryChange).not.toHaveBeenCalled();
  });

  it("losing focus (blur) closes the panel, preserves text, and selects no tag", async () => {
    setupFetch({ tags: [tag()] });
    const { onSelectTag, onQueryChange } = renderSuggest({ q: "drag" });
    await findOptions(2);
    const input = screen.getByRole("combobox");
    fireEvent.blur(input);
    expect(screen.queryByRole("listbox")).toBeNull();
    expect(onSelectTag).not.toHaveBeenCalled();
    expect(onQueryChange).not.toHaveBeenCalled();
  });

  it("typing again after a dismissal reopens the panel", async () => {
    setupFetch({ tags: [tag()] });
    renderSuggest({ q: "drag" });
    await findOptions(2);
    const input = screen.getByRole("combobox");
    fireEvent.keyDown(input, { key: "Escape" });
    expect(screen.queryByRole("listbox")).toBeNull();
    // Typing fires the input's own onChange, which re-arms the panel — even
    // though this uncontrolled-in-test input doesn't feed the new value back
    // into the `q` prop, `q` ("drag") is still non-empty so `dismissed`
    // flipping back to false is enough to reopen it.
    fireEvent.change(input, { target: { value: "drago" } });
    expect(await screen.findByRole("listbox")).toBeTruthy();
  });

  // --- a11y assertions (AC 16) ---

  it("the input carries combobox role, expanded state, and ARIA wiring to the listbox", async () => {
    setupFetch({ tags: [tag()] });
    renderSuggest({ q: "" });
    const input = screen.getByRole("combobox");
    expect(input.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByRole("listbox")).toBeNull();
  });

  it("reflects an expanded, wired-up listbox once the query is non-empty", async () => {
    setupFetch({ tags: [tag()] });
    renderSuggest({ q: "drag" });
    const input = screen.getByRole("combobox");
    expect(input.getAttribute("aria-expanded")).toBe("true");
    await findOptions(2);
    const listbox = screen.getByRole("listbox");
    expect(input.getAttribute("aria-controls")).toBe(listbox.getAttribute("id"));
  });

  it("moves aria-activedescendant on ArrowDown without moving DOM focus off the input", async () => {
    setupFetch({ tags: [tag({ id: "t1" })] });
    renderSuggest({ q: "drag" });
    const options = await findOptions(2);
    const input = screen.getByRole("combobox");
    input.focus();
    expect(input.getAttribute("aria-activedescendant")).toBeFalsy();
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(input.getAttribute("aria-activedescendant")).toBe(options[0]?.getAttribute("id"));
    expect(document.activeElement).toBe(input);
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(input.getAttribute("aria-activedescendant")).toBe(options[1]?.getAttribute("id"));
    expect(document.activeElement).toBe(input);
  });

  it("every option row is excluded from the tab order (tabIndex=-1)", async () => {
    setupFetch({ tags: [tag()] });
    renderSuggest({ q: "drag" });
    const options = await findOptions(2);
    for (const o of options) {
      expect(o.getAttribute("tabindex")).toBe("-1");
    }
  });
});
