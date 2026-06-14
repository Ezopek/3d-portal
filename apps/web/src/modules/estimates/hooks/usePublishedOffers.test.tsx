import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { usePublishedOffers } from "@/modules/estimates/hooks/usePublishedOffers";

// AC-2: usePublishedOffers — calls GET /api/profiles/offers/published?material=...
// and is disabled when !isAuthenticated or !hasStlFiles.
describe("usePublishedOffers", () => {
  function wrapper({ children }: { children: ReactNode }) {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  }

  it("calls the correct endpoint with the material param when enabled", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          offers: [
            {
              offer_id: "abc123",
              portal_label: "Test Offer",
              quality_tier: "standard",
              compatible_material_categories: ["PLA"],
              printer_name: "K1 Max",
            },
          ],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    const { result } = renderHook(
      () => usePublishedOffers("PLA", { isAuthenticated: true, hasStlFiles: true }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const url = fetchSpy.mock.calls[0]?.[0] as string;
    expect(url).toContain("/api/profiles/offers/published");
    expect(url).toContain("material=PLA");
    expect(result.current.data?.offers).toHaveLength(1);
    expect(result.current.data?.offers[0]?.offer_id).toBe("abc123");
    fetchSpy.mockRestore();
  });

  it("is disabled when isAuthenticated is false", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const { result } = renderHook(
      () => usePublishedOffers("PLA", { isAuthenticated: false, hasStlFiles: true }),
      { wrapper },
    );

    await new Promise<void>((r) => setTimeout(r, 50));
    expect(result.current.isPending).toBe(true);
    expect(result.current.isFetching).toBe(false);
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it("is disabled when hasStlFiles is false", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const { result } = renderHook(
      () => usePublishedOffers("PLA", { isAuthenticated: true, hasStlFiles: false }),
      { wrapper },
    );

    await new Promise<void>((r) => setTimeout(r, 50));
    expect(result.current.isPending).toBe(true);
    expect(result.current.isFetching).toBe(false);
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });
});
