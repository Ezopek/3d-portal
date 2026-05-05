import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import "@/locales/i18n";

import { ModelHero } from "./ModelHero";
import type { ModelDetail } from "@/lib/api-types";

const mockUseAuth = vi.fn();
vi.mock("@/shell/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

beforeEach(() => {
  fetchMock.mockReset();
  fetchMock.mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
  mockUseAuth.mockReturnValue({ isAdmin: false });
});

afterEach(() => {
  cleanup();
  mockUseAuth.mockReset();
});

function makeDetail(over: Partial<ModelDetail> = {}): ModelDetail {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    legacy_id: "001",
    slug: "dragon",
    name_en: "Dragon",
    name_pl: "Smok",
    category_id: "22222222-2222-2222-2222-222222222222",
    source: "printables",
    status: "printed",
    rating: 4.5,
    thumbnail_file_id: null,
    date_added: "2026-04-12",
    deleted_at: null,
    created_at: "2026-04-12T00:00:00Z",
    updated_at: "2026-04-12T00:00:00Z",
    tags: [
      { id: "t1", slug: "dragon", name_en: "Dragon", name_pl: null },
      { id: "t2", slug: "articulated", name_en: "Articulated", name_pl: null },
      { id: "t3", slug: "cool", name_en: "Cool", name_pl: null },
      { id: "t4", slug: "petg", name_en: "PETG", name_pl: null },
      { id: "t5", slug: "supports-off", name_en: "Supports off", name_pl: null },
      { id: "t6", slug: "extra", name_en: "Extra", name_pl: null },
    ],
    category: {
      id: "22222222-2222-2222-2222-222222222222",
      parent_id: null,
      slug: "decorations",
      name_en: "Decorations",
      name_pl: "Dekoracje",
    },
    files: [],
    prints: [],
    notes: [],
    external_links: [],
    ...over,
  };
}

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("ModelHero", () => {
  it("renders breadcrumb with category and title", () => {
    render(<ModelHero detail={makeDetail()} />, { wrapper: wrap() });
    expect(screen.getByText("Decorations")).toBeTruthy();
    expect(screen.getByText("Dragon")).toBeTruthy();
  });

  it("renders status badge, rating, source, top tags", () => {
    render(<ModelHero detail={makeDetail()} />, { wrapper: wrap() });
    expect(document.body.textContent?.toLowerCase()).toContain("printed");
    expect(document.body.textContent).toContain("4.5");
    expect(document.body.textContent?.toLowerCase()).toContain("printables");
    // top 5 tag chips
    expect(screen.getAllByTestId("tag-chip").length).toBe(5);
  });

  it("shows overflow indicator when more than 5 tags", () => {
    render(<ModelHero detail={makeDetail()} />, { wrapper: wrap() });
    expect(document.body.textContent).toContain("+1");
  });

  it("does not render rating when null", () => {
    render(<ModelHero detail={makeDetail({ rating: null })} />, { wrapper: wrap() });
    expect(document.body.textContent).not.toMatch(/★\s*\d/);
  });

  it("does not render admin affordances for non-admin", () => {
    mockUseAuth.mockReturnValue({ isAdmin: false });
    render(<ModelHero detail={makeDetail()} />, { wrapper: wrap() });
    expect(screen.queryByLabelText("Edit tags")).toBeNull();
    expect(screen.queryByLabelText("Model actions")).toBeNull();
  });

  it("renders the edit-tags pencil for admin and opens EditTagsSheet on click", async () => {
    mockUseAuth.mockReturnValue({ isAdmin: true });
    render(<ModelHero detail={makeDetail()} />, { wrapper: wrap() });
    const editBtn = screen.getByLabelText("Edit tags");
    expect(editBtn).toBeTruthy();
    fireEvent.click(editBtn);
    await waitFor(() => expect(screen.getByText("Edit tags")).toBeTruthy());
  });

  it("renders the actions ⋮ menu for admin", () => {
    mockUseAuth.mockReturnValue({ isAdmin: true });
    render(<ModelHero detail={makeDetail()} />, { wrapper: wrap() });
    expect(screen.getByLabelText("Model actions")).toBeTruthy();
  });
});
