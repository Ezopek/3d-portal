import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState, type ReactNode } from "react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { ModelDetail, TagListItem, TagRead, TagGroupsResponse } from "@/lib/api-types";
import i18n from "@/locales/i18n";

import { EditTagsSheet } from "./EditTagsSheet";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const GROUP_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const GROUP_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";
const STALE_GROUP_ID = "99999999-9999-9999-9999-999999999999";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

beforeAll(async () => {
  await i18n.changeLanguage("en");
});

beforeEach(() => {
  fetchMock.mockReset();
});

afterEach(async () => {
  cleanup();
  // Guard against a thrown assertion leaving the shared i18n singleton on
  // "pl" for later tests, since the language switch below isn't scoped by a
  // try/finally.
  await i18n.changeLanguage("en");
});

function makeDetail(over: Partial<ModelDetail> = {}): ModelDetail {
  return {
    id: "m1",
    slug: "dragon",
    name_en: "Dragon",
    name_pl: null,
    category_id: "c1",
    source: "printables",
    status: "not_printed",
    rating: null,
    thumbnail_file_id: null,
    date_added: "2026-04-12",
    deleted_at: null,
    created_at: "",
    updated_at: "",
    tags: [],
    category: {
      id: "c1",
      parent_id: null,
      slug: "c",
      name_en: "C",
      name_pl: null,
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

function makeTag(over: Partial<TagRead> = {}): TagRead {
  return {
    id: "t1",
    slug: "resin",
    name_en: "Resin",
    name_pl: null,
    group_id: null,
    group_position: 0,
    ...over,
  };
}

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

// Dispatches `fetchMock` by requested URL/method rather than positional call
// order, since EditTagsSheet now fires `useTags()` and `useTagGroups()`
// concurrently on every mount. `tagGroups: "pending"` never resolves (mirrors
// a query stuck in `isPending`); `"error"` resolves with a non-2xx status so
// the query lands in `isError` — both leave `useTagGroups().data` undefined,
// which is the only thing the component's fallback branch checks.
function setupFetch(opts: {
  tags?: TagListItem[];
  tagGroups?: TagGroupsResponse | "pending" | "error";
  createdTag?: TagRead;
  onCreate?: (init: RequestInit) => void;
  onPut?: (init: RequestInit) => void;
}) {
  const tags = opts.tags ?? [];
  const tagGroups = opts.tagGroups ?? { groups: [], groupless: [] };
  fetchMock.mockImplementation((url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    if (url.includes("/tag-groups")) {
      if (tagGroups === "pending") return new Promise<Response>(() => {});
      if (tagGroups === "error") {
        return Promise.resolve(new Response(JSON.stringify({}), { status: 500 }));
      }
      return Promise.resolve(new Response(JSON.stringify(tagGroups), { status: 200 }));
    }
    if (url.includes("/admin/models/") && method === "PUT") {
      opts.onPut?.(init as RequestInit);
      return Promise.resolve(new Response(JSON.stringify(tags), { status: 200 }));
    }
    if (url.includes("/admin/tags") && method === "POST") {
      opts.onCreate?.(init as RequestInit);
      return Promise.resolve(
        new Response(JSON.stringify(opts.createdTag ?? makeTag()), { status: 200 }),
      );
    }
    if (url.includes("/tags")) {
      return Promise.resolve(new Response(JSON.stringify(tags), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
  });
}

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

function Harness({ detail, isAdmin }: { detail: ModelDetail; isAdmin: boolean }) {
  const [open, setOpen] = useState(true);
  return <EditTagsSheet detail={detail} open={open} onOpenChange={setOpen} isAdmin={isAdmin} />;
}

describe("EditTagsSheet", () => {
  it("displays initial selected tags matching detail.tags", () => {
    setupFetch({ tags: [] });
    const tag1 = makeTag({ id: "t1", slug: "resin" });
    const tag2 = makeTag({ id: "t2", slug: "pla" });
    const detail = makeDetail({ tags: [tag1, tag2] });
    render(<Harness detail={detail} isAdmin={true} />, { wrapper: wrap() });
    // getByText will throw if not found, so this assertion passes if found
    expect(screen.getByText("resin")).toBeDefined();
    expect(screen.getByText("pla")).toBeDefined();
  });

  it("calls useReplaceTags with the selected ids when save is clicked", async () => {
    const tag1 = makeTag({ id: "t1", slug: "resin" });
    const detail = makeDetail({ tags: [tag1] });
    let putInit: RequestInit | undefined;
    setupFetch({ tags: [tag1], onPut: (init) => (putInit = init) });
    render(<Harness detail={detail} isAdmin={true} />, { wrapper: wrap() });
    // Wait for the initial tags query to resolve before clicking Save.
    await waitFor(() => expect(screen.getByText("resin")).toBeDefined());
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));
    await waitFor(() => expect(putInit).toBeDefined());
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/models/m1/tags",
      expect.objectContaining({ method: "PUT" }),
    );
    expect(putInit?.body).toBe(JSON.stringify({ tag_ids: ["t1"] }));
  });

  it("calls useReplaceTags with selected ids when save is clicked", async () => {
    const tag1 = makeTag({ id: "t1", slug: "resin" });
    const detail = makeDetail({ tags: [tag1] });
    let putInit: RequestInit | undefined;
    setupFetch({ tags: [tag1], onPut: (init) => (putInit = init) });
    render(<Harness detail={detail} isAdmin={true} />, { wrapper: wrap() });
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));
    await waitFor(() => expect(putInit).toBeDefined());
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/models/m1/tags",
      expect.objectContaining({ method: "PUT" }),
    );
    expect(putInit?.body).toBe(JSON.stringify({ tag_ids: ["t1"] }));
  });

  it("renders candidates spanning 2 groups plus one groupless candidate as 3 ordered sections", async () => {
    const tagInGroupB = makeTag({ id: "t-b", slug: "metal", group_id: GROUP_B });
    const tagInGroupA = makeTag({ id: "t-a", slug: "fantasy", group_id: GROUP_A });
    const tagGroupless = makeTag({ id: "t-none", slug: "loose", group_id: null });
    setupFetch({
      tags: [tagInGroupB, tagInGroupA, tagGroupless],
      tagGroups: tagGroupsResponse(),
    });
    const detail = makeDetail({ tags: [] });
    render(<Harness detail={detail} isAdmin={false} />, { wrapper: wrap() });

    await waitFor(() => expect(screen.getByText("Theme")).toBeTruthy());
    expect(screen.getByText("Material")).toBeTruthy();
    expect(screen.getByText("Ungrouped")).toBeTruthy();
    expect(screen.getByText("+ fantasy")).toBeTruthy();
    expect(screen.getByText("+ metal")).toBeTruthy();
    expect(screen.getByText("+ loose")).toBeTruthy();

    // Sections must appear in group `position` order (Theme=0, Material=1),
    // with Ungrouped trailing. `SheetContent` portals into `document.body`,
    // so assert against the document, not the local render container.
    const text = document.body.textContent ?? "";
    expect(text.indexOf("Theme")).toBeLessThan(text.indexOf("Material"));
    expect(text.indexOf("Material")).toBeLessThan(text.indexOf("Ungrouped"));
  });

  it("folds a candidate whose group_id matches no fetched group into Ungrouped", async () => {
    const orphan = makeTag({ id: "t-orphan", slug: "orphan", group_id: STALE_GROUP_ID });
    setupFetch({ tags: [orphan], tagGroups: tagGroupsResponse() });
    const detail = makeDetail({ tags: [] });
    render(<Harness detail={detail} isAdmin={false} />, { wrapper: wrap() });

    await waitFor(() => expect(screen.getByText("Ungrouped")).toBeTruthy());
    expect(screen.getByText("+ orphan")).toBeTruthy();
    expect(screen.queryByText("Theme")).toBeNull();
    expect(screen.queryByText("Material")).toBeNull();
  });

  it("renders candidates as a flat, header-less list while useTagGroups() is pending", async () => {
    const tag = makeTag({ id: "t1", slug: "resin", group_id: GROUP_A });
    setupFetch({ tags: [tag], tagGroups: "pending" });
    const detail = makeDetail({ tags: [] });
    render(<Harness detail={detail} isAdmin={false} />, { wrapper: wrap() });

    await waitFor(() => expect(screen.getByText("+ resin")).toBeTruthy());
    expect(screen.queryByText("Theme")).toBeNull();
    expect(screen.queryByText("Ungrouped")).toBeNull();
  });

  it("renders candidates as a flat, header-less list when useTagGroups() errors", async () => {
    const tag = makeTag({ id: "t1", slug: "resin", group_id: GROUP_A });
    setupFetch({ tags: [tag], tagGroups: "error" });
    const detail = makeDetail({ tags: [] });
    render(<Harness detail={detail} isAdmin={false} />, { wrapper: wrap() });

    await waitFor(() => expect(screen.getByText("+ resin")).toBeTruthy());
    expect(screen.queryByText("Theme")).toBeNull();
    expect(screen.queryByText("Ungrouped")).toBeNull();
  });

  it("shows the create-tag affordance for an admin when no candidates match the query", async () => {
    setupFetch({ tags: [] });
    const detail = makeDetail({ tags: [] });
    render(<Harness detail={detail} isAdmin={true} />, { wrapper: wrap() });

    fireEvent.change(screen.getByPlaceholderText("Search or create…"), {
      target: { value: "brandnew" },
    });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /create/i })).toBeTruthy(),
    );

    let createInit: RequestInit | undefined;
    setupFetch({ tags: [], createdTag: makeTag({ id: "new1", slug: "brandnew" }), onCreate: (init) => (createInit = init) });
    fireEvent.click(screen.getByRole("button", { name: /create/i }));
    await waitFor(() => expect(createInit).toBeDefined());
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/tags",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("never shows or triggers the create-tag affordance for a non-admin", async () => {
    setupFetch({ tags: [] });
    const detail = makeDetail({ tags: [] });
    render(<Harness detail={detail} isAdmin={false} />, { wrapper: wrap() });

    fireEvent.change(screen.getByPlaceholderText("Search or create…"), {
      target: { value: "brandnew" },
    });
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());

    expect(screen.queryByRole("button", { name: /create/i })).toBeNull();
    expect(fetchMock).not.toHaveBeenCalledWith(
      "/api/admin/tags",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("renders grouped candidate sections identically for a non-admin viewer", async () => {
    const tagInGroupA = makeTag({ id: "t-a", slug: "fantasy", group_id: GROUP_A });
    setupFetch({ tags: [tagInGroupA], tagGroups: tagGroupsResponse() });
    const detail = makeDetail({ tags: [] });
    render(<Harness detail={detail} isAdmin={false} />, { wrapper: wrap() });

    await waitFor(() => expect(screen.getByText("Theme")).toBeTruthy());
    const button = screen.getByText("+ fantasy");
    fireEvent.click(button);
    // Selecting a candidate moves it into the selected-chip row.
    await waitFor(() => expect(screen.getByText("fantasy")).toBeTruthy());
  });

  it("uses name_pl for a group label when the UI language is Polish and name_pl is non-empty", async () => {
    await i18n.changeLanguage("pl");
    const tagInGroupB = makeTag({ id: "t-b", slug: "metal", group_id: GROUP_B });
    setupFetch({ tags: [tagInGroupB], tagGroups: tagGroupsResponse() });
    const detail = makeDetail({ tags: [] });
    render(<Harness detail={detail} isAdmin={false} />, { wrapper: wrap() });

    await waitFor(() => expect(screen.getByText("Materiał")).toBeTruthy());
    expect(screen.queryByText("Material")).toBeNull();
  });
});
