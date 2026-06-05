import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api";
import {
  importRejectionCategory,
  useImportProfile,
} from "@/modules/admin/hooks/useImportProfile";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => fetchMock.mockReset());

const PRINTER_REF = "creality-k1-max-microswiss-hf";

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  }
  return { qc, Wrapper };
}

function newFile() {
  return new File([JSON.stringify({ machine: {}, process: {}, filament: {} })], "triple.json", {
    type: "application/json",
  });
}

describe("useImportProfile (Story 33.2 — AC-17)", () => {
  it("POSTs multipart FormData to the import endpoint with the CSRF header, no JSON type", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ status: "offerable" }), { status: 201 }));
    const { Wrapper } = wrap();
    const { result } = renderHook(() => useImportProfile(PRINTER_REF), { wrapper: Wrapper });

    result.current.mutate({ file: newFile(), material_class: "TPU", quality_tier: "standard" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/profiles/import");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
    const form = init.body as FormData;
    expect(form.get("printer_ref")).toBe(PRINTER_REF);
    expect(form.get("material_class")).toBe("TPU");
    expect(form.get("quality_tier")).toBe("standard");
    // CSRF header present; multipart body must NOT be stamped application/json.
    const headers = init.headers as Headers;
    expect(headers.get("X-Portal-Client")).toBe("web");
    expect(headers.get("Content-Type")).toBeNull();
  });

  it("includes portal_label only when provided", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({}), { status: 201 }));
    const { Wrapper } = wrap();
    const { result } = renderHook(() => useImportProfile(PRINTER_REF), { wrapper: Wrapper });
    result.current.mutate({
      file: newFile(),
      material_class: "PLA",
      quality_tier: "standard",
      portal_label: "Rosa Flex",
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const form = (fetchMock.mock.calls[0]?.[1] as RequestInit).body as FormData;
    expect(form.get("portal_label")).toBe("Rosa Flex");
  });

  it("invalidates the ['admin','profiles'] query on success (AC-17)", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({}), { status: 201 }));
    const { qc, Wrapper } = wrap();
    const invalidate = vi.spyOn(qc, "invalidateQueries");
    const { result } = renderHook(() => useImportProfile(PRINTER_REF), { wrapper: Wrapper });

    result.current.mutate({ file: newFile(), material_class: "TPU", quality_tier: "standard" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["admin", "profiles"] });
  });

  it("does NOT auto-retry the write — exactly one POST on a 422 rejection", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: { reason_category: "invalid_partial", message: "x" } }), {
        status: 422,
      }),
    );
    const { Wrapper } = wrap();
    const { result } = renderHook(() => useImportProfile(PRINTER_REF), { wrapper: Wrapper });
    result.current.mutate({ file: newFile(), material_class: "PETG", quality_tier: "strong" });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("importRejectionCategory", () => {
  it("extracts reason_category from a structured ApiError body", () => {
    const err = new ApiError(422, { detail: { reason_category: "incompatible_for_material", message: "x" } }, "422");
    expect(importRejectionCategory(err)).toBe("incompatible_for_material");
  });

  it("returns null for a non-ApiError or an unstructured body", () => {
    expect(importRejectionCategory(new Error("boom"))).toBeNull();
    expect(importRejectionCategory(new ApiError(500, null, "500"))).toBeNull();
    expect(importRejectionCategory(new ApiError(422, { detail: {} }, "422"))).toBeNull();
  });
});
