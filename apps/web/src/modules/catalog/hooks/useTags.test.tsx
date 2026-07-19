import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, expectTypeOf, it, vi } from "vitest";

import type { TagListItem } from "@/lib/api-types";

import { useTags } from "./useTags";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => fetchMock.mockReset());

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("useTags", () => {
  it("fetches /api/tags without query when called with no args", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify([]), { status: 200 }),
    );
    const { result } = renderHook(() => useTags(), { wrapper: wrap() });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(fetchMock).toHaveBeenCalledWith("/api/tags?limit=50", expect.any(Object));
  });

  it("passes q parameter when given", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify([]), { status: 200 }),
    );
    const { result } = renderHook(() => useTags("dragon"), { wrapper: wrap() });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(fetchMock).toHaveBeenCalledWith("/api/tags?q=dragon&limit=50", expect.any(Object));
  });

  it("uses different cache keys for different queries", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
    const wrapper = wrap();
    renderHook(() => useTags(), { wrapper });
    renderHook(() => useTags("dragon"), { wrapper });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  });

  it("returns TagListItem[] carrying group_id/group_position + optional model_count", async () => {
    const item: TagListItem = {
      id: "11111111-1111-1111-1111-111111111111",
      slug: "dragon",
      name_en: "Dragon",
      name_pl: "Smok",
      group_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      group_position: 0,
      model_count: 4,
    };
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify([item]), { status: 200 }),
    );
    const { result } = renderHook(() => useTags(), { wrapper: wrap() });
    await waitFor(() => expect(result.current.data).toBeDefined());
    // Primary, framework-independent re-type proof: model_count is the ONLY
    // structural difference between TagRead and TagListItem — this member-access
    // is a tsc compile error while useTags still returns TagRead[], GREEN after.
    expect(result.current.data?.[0]?.model_count).toBe(4);
    // Confirmation via expect-type strict DeepBrand equality (discriminates the
    // extra optional key that mutual assignability alone would not).
    expectTypeOf(result.current.data).toEqualTypeOf<TagListItem[] | undefined>();
  });
});
