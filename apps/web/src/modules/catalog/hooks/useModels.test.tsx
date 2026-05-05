import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useModels } from "./useModels";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => fetchMock.mockReset());

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

const EMPTY = { items: [], total: 0, offset: 0, limit: 48 };

describe("useModels", () => {
  it("calls /api/models with default sort=recent and limit=48 when no filters", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(EMPTY), { status: 200 }));
    renderHook(() => useModels({}), { wrapper: wrap() });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const url = fetchMock.mock.calls[0]?.[0] as string;
    expect(url).toBe("/api/models?sort=recent&offset=0&limit=48");
  });

  it("translates category to category_ids", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(EMPTY), { status: 200 }));
    renderHook(
      () => useModels({ category_id: "abc" }),
      { wrapper: wrap() },
    );
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const url = fetchMock.mock.calls[0]?.[0] as string;
    expect(url).toContain("category_ids=abc");
  });

  it("emits each id as repeated category_ids when caller passes an array", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(EMPTY), { status: 200 }));
    renderHook(
      () => useModels({ category_ids: ["root", "child-a", "child-b"] }),
      { wrapper: wrap() },
    );
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const url = fetchMock.mock.calls[0]?.[0] as string;
    expect(url).toContain("category_ids=root");
    expect(url).toContain("category_ids=child-a");
    expect(url).toContain("category_ids=child-b");
  });

  it("prefers category_ids over category_id when both are passed", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(EMPTY), { status: 200 }));
    renderHook(
      () => useModels({ category_id: "ignored", category_ids: ["a", "b"] }),
      { wrapper: wrap() },
    );
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const url = fetchMock.mock.calls[0]?.[0] as string;
    expect(url).toContain("category_ids=a");
    expect(url).toContain("category_ids=b");
    expect(url).not.toContain("category_ids=ignored");
  });

  it("translates tag_ids array to repeated tag_ids params", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(EMPTY), { status: 200 }));
    renderHook(
      () => useModels({ tag_ids: ["a", "b"] }),
      { wrapper: wrap() },
    );
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const url = fetchMock.mock.calls[0]?.[0] as string;
    expect(url).toContain("tag_ids=a");
    expect(url).toContain("tag_ids=b");
  });

  it("computes offset from page (1-indexed)", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(EMPTY), { status: 200 }));
    renderHook(() => useModels({ page: 3 }), { wrapper: wrap() });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const url = fetchMock.mock.calls[0]?.[0] as string;
    // page 3 with limit 48 → offset 96
    expect(url).toContain("offset=96");
  });

  it("includes status, source, q, sort when present", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(EMPTY), { status: 200 }));
    renderHook(
      () =>
        useModels({
          status: "printed",
          source: "printables",
          q: "dragon",
          sort: "name_asc",
        }),
      { wrapper: wrap() },
    );
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const url = fetchMock.mock.calls[0]?.[0] as string;
    expect(url).toContain("status=printed");
    expect(url).toContain("source=printables");
    expect(url).toContain("q=dragon");
    expect(url).toContain("sort=name_asc");
  });

  it("uses different cache keys for different filter sets", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify(EMPTY), { status: 200 }));
    const wrapper = wrap();
    renderHook(() => useModels({ q: "a" }), { wrapper });
    renderHook(() => useModels({ q: "b" }), { wrapper });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  });

  // Regression: changing a filter (e.g. typing into the catalog search box)
  // creates a new queryKey. Without `placeholderData: keepPreviousData` the
  // hook returns `data: undefined` for the new key while the request is in
  // flight, which causes CatalogList to render its loading branch and
  // unmount the search input — losing focus on every keystroke.
  it("keeps previous data while a new query is in flight", async () => {
    const FIRST = { items: [{ id: "m1" }], total: 1, offset: 0, limit: 48 };
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(FIRST), { status: 200 }),
    );
    let resolveSecond!: (r: Response) => void;
    fetchMock.mockImplementationOnce(
      () => new Promise<Response>((res) => {
        resolveSecond = res;
      }),
    );
    const wrapper = wrap();
    const { result, rerender } = renderHook(
      ({ q }: { q: string }) => useModels({ q }),
      { wrapper, initialProps: { q: "a" } },
    );
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.data?.items).toEqual([{ id: "m1" }]);

    rerender({ q: "ab" });

    // While the second fetch is pending, data must still be the previous
    // snapshot — not undefined.
    expect(result.current.data).toBeDefined();
    expect(result.current.data?.items).toEqual([{ id: "m1" }]);

    resolveSecond(new Response(JSON.stringify(EMPTY), { status: 200 }));
    await waitFor(() => expect(result.current.data?.items).toEqual([]));
  });
});
