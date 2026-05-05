import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useCategoriesTree } from "./useCategoriesTree";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => fetchMock.mockReset());

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("useCategoriesTree", () => {
  it("fetches /api/categories and returns the tree", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          roots: [
            {
              id: "11111111-1111-1111-1111-111111111111",
              parent_id: null,
              slug: "decorations",
              name_en: "Decorations",
              name_pl: "Dekoracje",
              children: [],
            },
          ],
        }),
        { status: 200 },
      ),
    );
    const { result } = renderHook(() => useCategoriesTree(), { wrapper: wrap() });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(fetchMock).toHaveBeenCalledWith("/api/categories", expect.any(Object));
    expect(result.current.data?.roots).toHaveLength(1);
    expect(result.current.data?.roots[0]?.slug).toBe("decorations");
  });
});
