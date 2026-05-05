import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ModelDetail, TagRead } from "@/lib/api-types";

import { EditTagsSheet } from "./EditTagsSheet";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

beforeEach(() => {
  fetchMock.mockReset();
});

afterEach(() => cleanup());

function makeDetail(over: Partial<ModelDetail> = {}): ModelDetail {
  return {
    id: "m1",
    legacy_id: null,
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
    ...over,
  };
}

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

function Harness({ detail }: { detail: ModelDetail }) {
  const [open, setOpen] = useState(true);
  return <EditTagsSheet detail={detail} open={open} onOpenChange={setOpen} />;
}

describe("EditTagsSheet", () => {
  it("displays initial selected tags matching detail.tags", () => {
    const tag1 = makeTag({ id: "t1", slug: "resin" });
    const tag2 = makeTag({ id: "t2", slug: "pla" });
    const detail = makeDetail({ tags: [tag1, tag2] });
    render(<Harness detail={detail} />, { wrapper: wrap() });
    // getByText will throw if not found, so this assertion passes if found
    expect(screen.getByText("resin")).toBeDefined();
    expect(screen.getByText("pla")).toBeDefined();
  });

  it("calls useReplaceTags with the selected ids when save is clicked", async () => {
    const tag1 = makeTag({ id: "t1", slug: "resin" });
    const detail = makeDetail({ tags: [tag1] });
    // Mock the initial tags query
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify([tag1]), { status: 200 }),
    );
    render(<Harness detail={detail} />, { wrapper: wrap() });
    // Wait for initial query
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    fetchMock.mockClear();
    // Mock the replace tags response
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify([tag1]), { status: 200 }),
    );
    // Click save with the initial selection (tag1)
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/models/m1/tags");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("PUT");
    expect(init.body).toBe(JSON.stringify({ tag_ids: ["t1"] }));
  });

  it("calls useReplaceTags with selected ids when save is clicked", async () => {
    const tag1 = makeTag({ id: "t1", slug: "resin" });
    const detail = makeDetail({ tags: [tag1] });
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify([tag1]), { status: 200 }),
    );
    render(<Harness detail={detail} />, { wrapper: wrap() });
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    // The second call is the PUT to replace tags
    expect(fetchMock.mock.calls[1]?.[0]).toBe("/api/admin/models/m1/tags");
    const init = fetchMock.mock.calls[1]?.[1] as RequestInit;
    expect(init.method).toBe("PUT");
    expect(init.body).toBe(JSON.stringify({ tag_ids: ["t1"] }));
  });
});
