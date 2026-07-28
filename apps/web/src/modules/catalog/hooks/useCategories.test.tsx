import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, expectTypeOf, it, vi } from "vitest";

import type { BrowseCategoryRead } from "@/lib/api-types";

import { useCategories } from "./useCategories";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

// `globals: false` in vitest.config.ts — @testing-library/react's auto-cleanup
// does NOT register, so a multi-`it` file must clean up by hand or the second
// block inherits the first's DOM (project-context §115).
afterEach(cleanup);
afterEach(() => fetchMock.mockReset());

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

// A real GET /api/categories body: flat, ordered by (position, slug), with a
// top-level and a child category (parent_id is a scalar FK — no nesting), an
// untranslated label, and the zero-model category the curation surface must
// still see (FR26-CAT-2). No casts.
const body: BrowseCategoryRead[] = [
  {
    id: "11111111-1111-4111-8111-111111111111",
    slug: "kitchen",
    name_en: "Kitchen",
    name_pl: "Kuchnia",
    position: 0,
    parent_id: null,
    description_en: "Kitchen gadgets",
    description_pl: "Gadżety kuchenne",
    model_count: 12,
  },
  {
    id: "22222222-2222-4222-8222-222222222222",
    slug: "kitchen-storage",
    name_en: "Storage",
    name_pl: null,
    position: 1,
    parent_id: "11111111-1111-4111-8111-111111111111",
    description_en: null,
    description_pl: null,
    model_count: 4,
  },
  {
    id: "44444444-4444-4444-8444-444444444444",
    slug: "unsorted",
    name_en: "Unsorted",
    name_pl: null,
    position: 2,
    parent_id: null,
    description_en: null,
    description_pl: null,
    model_count: 0,
  },
];

describe("useCategories", () => {
  it("fetches /api/categories and returns the typed flat list", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(body), { status: 200 }),
    );
    const { result } = renderHook(() => useCategories(), { wrapper: wrap() });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(fetchMock).toHaveBeenCalledWith("/api/categories", expect.any(Object));
    expect(result.current.data).toHaveLength(3);
    // top-level vs child: parent_id round-trips as a scalar FK, both cases
    expect(result.current.data?.[0]?.parent_id).toBeNull();
    expect(result.current.data?.[1]?.parent_id).toBe(
      "11111111-1111-4111-8111-111111111111",
    );
    // required, unconditional model_count — including the empty category
    expect(result.current.data?.[0]?.model_count).toBe(12);
    expect(result.current.data?.[2]?.model_count).toBe(0);
    // bilingual optionality round-trips
    expect(result.current.data?.[0]?.description_pl).toBe("Gadżety kuchenne");
    expect(result.current.data?.[1]?.name_pl).toBeNull();
  });

  it("is loading before the fetch resolves", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(body), { status: 200 }),
    );
    const { result } = renderHook(() => useCategories(), { wrapper: wrap() });
    expect(result.current.isLoading).toBe(true);
    await waitFor(() => expect(result.current.data).toBeDefined());
  });

  it("surfaces errors as isError (no local retry override)", async () => {
    fetchMock.mockResolvedValueOnce(new Response("{}", { status: 500 }));
    const { result } = renderHook(() => useCategories(), { wrapper: wrap() });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("serves both mounts from one fetch within staleTime (stable key + cache)", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(body), { status: 200 }),
    );
    const wrapper = wrap();
    const first = renderHook(() => useCategories(), { wrapper });
    await waitFor(() => expect(first.result.current.data).toBeDefined());
    const second = renderHook(() => useCategories(), { wrapper });
    await waitFor(() => expect(second.result.current.data).toBeDefined());
    expect(fetchMock).toHaveBeenCalledTimes(1);
    first.unmount();
    second.unmount();
  });

  it("types .data as BrowseCategoryRead[] | undefined", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(body), { status: 200 }),
    );
    const { result } = renderHook(() => useCategories(), { wrapper: wrap() });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expectTypeOf(result.current.data).toEqualTypeOf<
      BrowseCategoryRead[] | undefined
    >();
  });
});
