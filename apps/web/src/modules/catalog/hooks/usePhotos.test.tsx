import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { usePhotos } from "./usePhotos";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => fetchMock.mockReset());

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("usePhotos", () => {
  it("filters to image and print kinds and sorts by position NULLS LAST", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [
            { id: "a", model_id: "m", kind: "stl", original_name: "a.stl", storage_path: "", sha256: "", size_bytes: 0, mime_type: "", position: null, created_at: "2026-01-01" },
            { id: "b", model_id: "m", kind: "image", original_name: "b.png", storage_path: "", sha256: "", size_bytes: 0, mime_type: "", position: 2, created_at: "2026-01-02" },
            { id: "c", model_id: "m", kind: "image", original_name: "c.png", storage_path: "", sha256: "", size_bytes: 0, mime_type: "", position: 0, created_at: "2026-01-03" },
            { id: "d", model_id: "m", kind: "print", original_name: "d.jpg", storage_path: "", sha256: "", size_bytes: 0, mime_type: "", position: null, created_at: "2026-01-05" },
            { id: "e", model_id: "m", kind: "print", original_name: "e.jpg", storage_path: "", sha256: "", size_bytes: 0, mime_type: "", position: 1, created_at: "2026-01-04" },
          ],
        }),
        { status: 200 },
      ),
    );
    const { result } = renderHook(() => usePhotos("m"), { wrapper: wrap() });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.data!.map((f) => f.id)).toEqual(["c", "e", "b", "d"]);
    // c=pos0, e=pos1, b=pos2, d=null (created later wins tiebreak)
  });
});
