import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { presetKey, type PrintIntentPresetInput } from "@/modules/estimates/lib/preset";
import { useRecomputeEstimate } from "./useRecomputeEstimate";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => fetchMock.mockReset());

const STL = "a".repeat(64);
const PRINTER = "p1s";
const PRESET: PrintIntentPresetInput = {
  material_class: "PLA",
  quality_tier: "standard",
  spoolman_filament_ref: null,
};

function okResponse() {
  return new Response(
    JSON.stringify({
      enqueued: true,
      estimate: {
        status: "queued",
        time_seconds: null,
        filament_g: null,
        filament_mm: null,
        filament_cm3: null,
        filament_cost: null,
        currency: null,
        computed_at: null,
        warnings: [],
        failure_reason: null,
        override_context: {
          material_class: "PLA",
          quality_tier: "standard",
          pinned_filament_name: null,
          custom_overrides_applied: false,
          purchase_url: null,
        },
      },
    }),
    { status: 200 },
  );
}

function wrap(qc: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("useRecomputeEstimate", () => {
  it("POSTs the preset-resolution inputs to /api/estimates/recompute", async () => {
    fetchMock.mockResolvedValueOnce(okResponse());
    const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    const { result } = renderHook(
      () => useRecomputeEstimate(STL, PRESET, PRINTER),
      { wrapper: wrap(qc) },
    );
    result.current.mutate();
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/estimates/recompute");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("POST");
    // The body carries the SAME resolution inputs as the read; no Orca key, no bundle_hash.
    expect(JSON.parse(init.body as string)).toEqual({
      stl_hash: STL,
      material_class: "PLA",
      quality_tier: "standard",
      printer_ref: PRINTER,
    });
  });

  it("includes spoolman_filament_ref only when the preset pins a filament", async () => {
    fetchMock.mockResolvedValueOnce(okResponse());
    const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    const pinned: PrintIntentPresetInput = {
      ...PRESET,
      spoolman_filament_ref: "Bambu Lab\x1fPLA\x1fMatte White",
    };
    const { result } = renderHook(
      () => useRecomputeEstimate(STL, pinned, PRINTER),
      { wrapper: wrap(qc) },
    );
    result.current.mutate();
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(JSON.parse(init.body as string).spoolman_filament_ref).toBe(
      "Bambu Lab\x1fPLA\x1fMatte White",
    );
  });

  it("invalidates the EXACT estimate query key on success (forces a refetch)", async () => {
    fetchMock.mockResolvedValueOnce(okResponse());
    const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    const invalidateSpy = vi.spyOn(qc, "invalidateQueries");
    const { result } = renderHook(
      () => useRecomputeEstimate(STL, PRESET, PRINTER),
      { wrapper: wrap(qc) },
    );
    result.current.mutate();
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["estimates", STL, presetKey(PRESET), PRINTER],
    });
  });
});
