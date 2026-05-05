import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { RatingPopover } from "./RatingPopover";

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

describe("RatingPopover", () => {
  it("renders ★ options and a Clear option when opened", async () => {
    render(
      <RatingPopover modelId="m1" current={3}>
        <button>open</button>
      </RatingPopover>,
      { wrapper: wrap() },
    );
    fireEvent.click(screen.getByText("open"));
    await waitFor(() => expect(screen.getByText("Clear")).toBeTruthy());
    expect(screen.getByText("★")).toBeTruthy();
    expect(screen.getByText("★★★★★")).toBeTruthy();
  });

  it("PATCHes the rating when a value is clicked", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({}), { status: 200 }));
    render(
      <RatingPopover modelId="m1" current={null}>
        <button>open</button>
      </RatingPopover>,
      { wrapper: wrap() },
    );
    fireEvent.click(screen.getByText("open"));
    await waitFor(() => expect(screen.getByText("★★★★")).toBeTruthy());
    fireEvent.click(screen.getByText("★★★★"));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/models/m1");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("PATCH");
    expect(init.body).toBe(JSON.stringify({ rating: 4 }));
  });
});
