import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import "@/locales/i18n";
import { ActivityTab } from "./ActivityTab";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

beforeEach(() => fetchMock.mockReset());
afterEach(() => cleanup());

const ID = "11111111-1111-1111-1111-111111111111";

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("ActivityTab", () => {
  it("renders empty state when items list is empty", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ items: [] }), { status: 200 }),
    );
    const { findByText } = render(<ActivityTab modelId={ID} />, { wrapper: wrap() });
    expect(await findByText(/no activity/i)).toBeTruthy();
  });

  it("renders one row per audit entry with action pill", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [
            {
              id: "a1",
              actor_user_id: null,
              action: "model.create",
              entity_type: "model",
              entity_id: ID,
              before_json: null,
              after_json: { name: "x" },
              at: "2026-05-04T12:34:56",
            },
            {
              id: "a2",
              actor_user_id: null,
              action: "model.update",
              entity_type: "model",
              entity_id: ID,
              before_json: null,
              after_json: null,
              at: "2026-05-04T12:00:00",
            },
          ],
        }),
        { status: 200 },
      ),
    );
    const { findAllByRole, getByText } = render(<ActivityTab modelId={ID} />, {
      wrapper: wrap(),
    });
    const items = await findAllByRole("listitem");
    expect(items.length).toBe(2);
    expect(getByText("model.create")).toBeTruthy();
    expect(getByText("model.update")).toBeTruthy();
  });
});
