import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useAuditLog } from "./useAuditLog";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => fetchMock.mockReset());

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

const ID = "11111111-1111-1111-1111-111111111111";

describe("useAuditLog", () => {
  it("requests with entity_type, entity_id, and limit query params", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ items: [] }), { status: 200 }),
    );
    renderHook(
      () => useAuditLog({ entity_type: "model", entity_id: ID, limit: 25 }),
      { wrapper: wrap() },
    );
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const url = fetchMock.mock.calls[0]?.[0] as string;
    expect(url).toContain("/api/admin/audit-log?");
    expect(url).toContain("entity_type=model");
    expect(url).toContain(`entity_id=${ID}`);
    expect(url).toContain("limit=25");
  });
});
