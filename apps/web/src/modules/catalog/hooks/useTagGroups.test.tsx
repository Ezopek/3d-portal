import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, expectTypeOf, it, vi } from "vitest";

import type { TagGroupsResponse } from "@/lib/api-types";

import { useTagGroups } from "./useTagGroups";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => fetchMock.mockReset());

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

// A real 42.2 GET /api/tag-groups body: one populated group, one empty-tags[]
// group, a non-empty groupless list. Every tag carries a REQUIRED model_count
// (TagReadWithCount), and the groupless tag has group_id: null. No casts.
const body: TagGroupsResponse = {
  groups: [
    {
      id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      slug: "theme",
      name_en: "Theme",
      name_pl: "Motyw",
      position: 0,
      tags: [
        {
          id: "11111111-1111-1111-1111-111111111111",
          slug: "dragon",
          name_en: "Dragon",
          name_pl: "Smok",
          group_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
          group_position: 0,
          model_count: 7,
        },
      ],
    },
    {
      id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
      slug: "material",
      name_en: "Material",
      name_pl: "Materiał",
      position: 1,
      tags: [],
    },
  ],
  groupless: [
    {
      id: "22222222-2222-2222-2222-222222222222",
      slug: "misc",
      name_en: "Misc",
      name_pl: null,
      group_id: null,
      group_position: 0,
      model_count: 3,
    },
  ],
};

describe("useTagGroups", () => {
  it("fetches /api/tag-groups and returns the typed taxonomy", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(body), { status: 200 }),
    );
    const { result } = renderHook(() => useTagGroups(), { wrapper: wrap() });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(fetchMock).toHaveBeenCalledWith("/api/tag-groups", expect.any(Object));
    expect(result.current.data?.groups).toHaveLength(2);
    // populated group + its nested required model_count round-trips
    expect(result.current.data?.groups[0]?.tags).toHaveLength(1);
    expect(result.current.data?.groups[0]?.tags[0]?.model_count).toBe(7);
    // empty-tags[] group preserved
    expect(result.current.data?.groups[1]?.tags).toHaveLength(0);
    // groupless tag with group_id: null round-trips
    expect(result.current.data?.groupless).toHaveLength(1);
    expect(result.current.data?.groupless[0]?.group_id).toBeNull();
    expect(result.current.data?.groupless[0]?.model_count).toBe(3);
  });

  it("is loading before the fetch resolves", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(body), { status: 200 }),
    );
    const { result } = renderHook(() => useTagGroups(), { wrapper: wrap() });
    expect(result.current.isLoading).toBe(true);
    await waitFor(() => expect(result.current.data).toBeDefined());
  });

  it("surfaces errors as isError (no local retry override)", async () => {
    fetchMock.mockResolvedValueOnce(new Response("{}", { status: 500 }));
    const { result } = renderHook(() => useTagGroups(), { wrapper: wrap() });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("serves both mounts from one fetch within staleTime (stable key + cache)", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(body), { status: 200 }),
    );
    const wrapper = wrap();
    const first = renderHook(() => useTagGroups(), { wrapper });
    await waitFor(() => expect(first.result.current.data).toBeDefined());
    const second = renderHook(() => useTagGroups(), { wrapper });
    await waitFor(() => expect(second.result.current.data).toBeDefined());
    expect(fetchMock).toHaveBeenCalledTimes(1);
    first.unmount();
    second.unmount();
  });

  it("types .data as TagGroupsResponse | undefined", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(body), { status: 200 }),
    );
    const { result } = renderHook(() => useTagGroups(), { wrapper: wrap() });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expectTypeOf(result.current.data).toEqualTypeOf<TagGroupsResponse | undefined>();
  });
});
