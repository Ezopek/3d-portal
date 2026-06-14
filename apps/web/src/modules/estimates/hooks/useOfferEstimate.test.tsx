import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { useOfferEstimate } from "@/modules/estimates/hooks/useOfferEstimate";

// AC-3: useOfferEstimate — calls GET /api/estimates?stl_hash=...&offer_id=...
// Uses cache key ["estimates", stlHash, { offerId }] (different from preset key).
// Does NOT send spoolman_filament_ref (OD-2 deferred).
describe("useOfferEstimate", () => {
  function wrapper({ children }: { children: ReactNode }) {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  }

  const FRESH_ESTIMATE = {
    status: "fresh",
    time_seconds: 3600,
    filament_g: 50.5,
    filament_mm: 16000,
    filament_cm3: 40,
    filament_cost: 3.0,
    currency: "PLN",
    computed_at: "2026-06-14T10:00:00Z",
    warnings: [],
    failure_reason: null,
    override_context: {
      material_class: "PLA",
      quality_tier: "standard",
      pinned_filament_name: null,
      custom_overrides_applied: false,
      purchase_url: null,
    },
    profile_selection_context: {
      estimate_profile_source: "default_material_profile",
      selected_material: "PLA",
      selected_spoolman_filament_ref: null,
      selected_filament_name: null,
      orca_filament_profile_name: null,
    },
    offer_id: "abc123",
  };

  it("calls the correct endpoint with offer_id and stl_hash", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(FRESH_ESTIMATE), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const { result } = renderHook(
      () => useOfferEstimate("a".repeat(64), "abc123"),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const url = fetchSpy.mock.calls[0]?.[0] as string;
    expect(url).toContain("/api/estimates");
    expect(url).toContain(`stl_hash=${"a".repeat(64)}`);
    expect(url).toContain("offer_id=abc123");
    // OD-2: spoolman_filament_ref must NOT be sent
    expect(url).not.toContain("spoolman_filament_ref");
    expect(result.current.data?.status).toBe("fresh");
    fetchSpy.mockRestore();
  });

  it("is disabled when offerId is empty", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const { result } = renderHook(
      () => useOfferEstimate("a".repeat(64), ""),
      { wrapper },
    );

    await new Promise<void>((r) => setTimeout(r, 50));
    expect(result.current.isPending).toBe(true);
    expect(result.current.isFetching).toBe(false);
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it("is disabled when stlHash is empty", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const { result } = renderHook(
      () => useOfferEstimate("", "abc123"),
      { wrapper },
    );

    await new Promise<void>((r) => setTimeout(r, 50));
    expect(result.current.isPending).toBe(true);
    expect(result.current.isFetching).toBe(false);
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });
});
