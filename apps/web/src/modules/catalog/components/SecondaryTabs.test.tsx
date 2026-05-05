import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ModelDetail } from "@/lib/api-types";

import { SecondaryTabs } from "./SecondaryTabs";

const mockUseAuth = vi.fn();
vi.mock("@/shell/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

beforeEach(() => {
  fetchMock.mockReset();
  fetchMock.mockResolvedValue(new Response(JSON.stringify({ items: [] }), { status: 200 }));
});

afterEach(() => {
  cleanup();
  mockUseAuth.mockReset();
});

function makeDetail(over: Partial<ModelDetail> = {}): ModelDetail {
  return {
    id: "m1",
    legacy_id: null,
    slug: "x",
    name_en: "X",
    name_pl: null,
    category_id: "c",
    source: "printables",
    status: "not_printed",
    rating: null,
    thumbnail_file_id: null,
    date_added: "2026-04-12",
    deleted_at: null,
    created_at: "",
    updated_at: "",
    tags: [],
    category: {
      id: "c",
      parent_id: null,
      slug: "c",
      name_en: "C",
      name_pl: null,
    },
    files: [],
    prints: [],
    notes: [],
    external_links: [],
    gallery_file_ids: [],
    image_count: 0,
    ...over,
  };
}

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("SecondaryTabs", () => {
  it("renders the three read-only tabs for non-admin (no Photos tab)", () => {
    mockUseAuth.mockReturnValue({ isAdmin: false });
    render(<SecondaryTabs detail={makeDetail()} />, { wrapper: wrap() });
    expect(screen.getByRole("tab", { name: /files/i })).toBeTruthy();
    expect(screen.getByRole("tab", { name: /prints/i })).toBeTruthy();
    expect(screen.getByRole("tab", { name: /operational/i })).toBeTruthy();
    expect(screen.queryByRole("tab", { name: /photos/i })).toBeNull();
  });

  it("activates Prints when its tab is clicked", () => {
    mockUseAuth.mockReturnValue({ isAdmin: false });
    render(
      <SecondaryTabs
        detail={makeDetail({
          prints: [
            {
              id: "p1",
              model_id: "m1",
              photo_file_id: null,
              printed_at: "2026-04-30",
              note: "ok",
              created_at: "",
              updated_at: "",
            },
          ],
        })}
      />,
      { wrapper: wrap() },
    );
    fireEvent.click(screen.getByRole("tab", { name: /prints/i }));
    expect(screen.getByText("ok")).toBeTruthy();
  });

  it("renders the Photos and Activity tabs for admin users", () => {
    mockUseAuth.mockReturnValue({ isAdmin: true });
    render(<SecondaryTabs detail={makeDetail()} />, { wrapper: wrap() });
    expect(screen.getByRole("tab", { name: /photos/i })).toBeTruthy();
    expect(screen.getByRole("tab", { name: /activity/i })).toBeTruthy();
  });
});
