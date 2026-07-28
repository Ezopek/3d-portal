import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, expectTypeOf, it, vi } from "vitest";

import type { BrowseCategoryRead } from "@/lib/api-types";

import { useCategoryBySlug } from "./useCategoryBySlug";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

// `globals: false` — manual cleanup is mandatory in a multi-`it` file
// (project-context §115).
afterEach(cleanup);
afterEach(() => fetchMock.mockReset());

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

const kitchen: BrowseCategoryRead = {
  id: "11111111-1111-4111-8111-111111111111",
  slug: "kitchen",
  name_en: "Kitchen",
  name_pl: "Kuchnia",
  position: 0,
  parent_id: null,
  description_en: "Kitchen gadgets",
  description_pl: "Gadżety kuchenne",
  model_count: 12,
};

const tools: BrowseCategoryRead = {
  id: "33333333-3333-4333-8333-333333333333",
  slug: "tools",
  name_en: "Tools",
  name_pl: null,
  position: 1,
  parent_id: null,
  description_en: null,
  description_pl: null,
  model_count: 0,
};

describe("useCategoryBySlug", () => {
  it("interpolates the slug into the PATH, not a query param", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(kitchen), { status: 200 }),
    );
    const { result } = renderHook(() => useCategoryBySlug("kitchen"), {
      wrapper: wrap(),
    });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/categories/kitchen",
      expect.any(Object),
    );
  });

  it("round-trips a single typed BrowseCategoryRead", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(kitchen), { status: 200 }),
    );
    const { result } = renderHook(() => useCategoryBySlug("kitchen"), {
      wrapper: wrap(),
    });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.data?.slug).toBe("kitchen");
    expect(result.current.data?.model_count).toBe(12);
    expect(result.current.data?.parent_id).toBeNull();
    expect(result.current.data?.description_en).toBe("Kitchen gadgets");
  });

  it("surfaces a 404 on an unknown slug as isError, with data left undefined", async () => {
    // Decision AY draws this distinction on purpose: `GET /api/categories/{slug}`
    // 404s, while `GET /api/models?category=<unknown>` degrades to an empty page.
    // The 404 must NOT be swallowed, defaulted, or retried into success.
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Browse category not found" }), {
        status: 404,
      }),
    );
    const { result } = renderHook(() => useCategoryBySlug("nope"), {
      wrapper: wrap(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("keys per slug — two slugs do not share a cache entry", async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify(kitchen), { status: 200 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(tools), { status: 200 }),
      );
    const wrapper = wrap();
    const first = renderHook(() => useCategoryBySlug("kitchen"), { wrapper });
    await waitFor(() => expect(first.result.current.data).toBeDefined());
    const second = renderHook(() => useCategoryBySlug("tools"), { wrapper });
    await waitFor(() => expect(second.result.current.data).toBeDefined());
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(first.result.current.data?.slug).toBe("kitchen");
    expect(second.result.current.data?.slug).toBe("tools");
    first.unmount();
    second.unmount();
  });

  it("types .data as BrowseCategoryRead | undefined", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(kitchen), { status: 200 }),
    );
    const { result } = renderHook(() => useCategoryBySlug("kitchen"), {
      wrapper: wrap(),
    });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expectTypeOf(result.current.data).toEqualTypeOf<
      BrowseCategoryRead | undefined
    >();
  });
});
