import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { StatusPopover } from "./StatusPopover";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

beforeEach(() => {
  fetchMock.mockReset();
});

afterEach(() => cleanup());

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("StatusPopover", () => {
  it("renders the trigger and opens the menu on click", async () => {
    render(
      <StatusPopover modelId="m1" current="not_printed">
        <button>open</button>
      </StatusPopover>,
      { wrapper: wrap() },
    );
    fireEvent.click(screen.getByText("open"));
    await waitFor(() => expect(screen.getByText("printed")).toBeTruthy());
    // disabled current option
    expect(screen.getByText("not printed")).toBeTruthy();
  });

  it("PATCHes the model when a status item is clicked", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({}), { status: 200 }));
    render(
      <StatusPopover modelId="m1" current="not_printed">
        <button>open</button>
      </StatusPopover>,
      { wrapper: wrap() },
    );
    fireEvent.click(screen.getByText("open"));
    await waitFor(() => expect(screen.getByText("printed")).toBeTruthy());
    fireEvent.click(screen.getByText("printed"));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/models/m1");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("PATCH");
    expect(init.body).toBe(JSON.stringify({ status: "printed" }));
  });
});
