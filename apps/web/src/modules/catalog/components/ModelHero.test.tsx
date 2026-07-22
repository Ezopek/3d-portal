import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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

// TagGroupsSection has its own dedicated, router-mounted test file
// (TagGroupsSection.test.tsx) covering the I/O matrix; here it's mocked so
// this suite stays router-free, and we just assert it's mounted with the
// right props.
interface TagGroupsSectionProps {
  detail: ModelDetail;
  isAdmin: boolean;
  onAddTags: () => void;
}
const mockTagGroupsSection = vi.fn<(props: TagGroupsSectionProps) => null>(() => null);
vi.mock("@/modules/catalog/components/TagGroupsSection", () => ({
  TagGroupsSection: (props: TagGroupsSectionProps) => mockTagGroupsSection(props),
}));

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

beforeEach(() => {
  fetchMock.mockReset();
  // Path-aware default: `/tag-groups` needs a valid `TagGroupsResponse` shape
  // (the real, unmocked `EditTagsSheet` fires `useTagGroups()` on every
  // mount); every other unmatched request (e.g. `/tags`) keeps the bare-array
  // shape existing tests rely on.
  fetchMock.mockImplementation((url: string) => {
    if (url.includes("/tag-groups")) {
      return Promise.resolve(
        new Response(JSON.stringify({ groups: [], groupless: [] }), { status: 200 }),
      );
    }
    return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
  });
  mockUseAuth.mockReturnValue({ isAdmin: false });
  mockTagGroupsSection.mockClear();
});

afterEach(() => {
  cleanup();
  mockUseAuth.mockReset();
});

function makeDetail(over: Partial<ModelDetail> = {}): ModelDetail {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    slug: "dragon",
    name_en: "Dragon",
    name_pl: "Smok",
    source: "printables",
    status: "printed",
    rating: 4.5,
    thumbnail_file_id: null,
    date_added: "2026-04-12",
    deleted_at: null,
    created_at: "2026-04-12T00:00:00Z",
    updated_at: "2026-04-12T00:00:00Z",
    tags: [
      { id: "t1", slug: "dragon", name_en: "Dragon", name_pl: null, group_id: null, group_position: 0 },
      { id: "t2", slug: "articulated", name_en: "Articulated", name_pl: null, group_id: null, group_position: 0 },
      { id: "t3", slug: "cool", name_en: "Cool", name_pl: null, group_id: null, group_position: 0 },
      { id: "t4", slug: "petg", name_en: "PETG", name_pl: null, group_id: null, group_position: 0 },
      { id: "t5", slug: "supports-off", name_en: "Supports off", name_pl: null, group_id: null, group_position: 0 },
      { id: "t6", slug: "extra", name_en: "Extra", name_pl: null, group_id: null, group_position: 0 },
    ],
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

describe("ModelHero", () => {
  it("renders the title without the retired taxonomy breadcrumb (Story 47.5)", () => {
    render(<ModelHero detail={makeDetail()} />, { wrapper: wrap() });
    expect(screen.getByText("Dragon")).toBeTruthy();
    expect(screen.queryByTestId("model-breadcrumb")).toBeNull();
  });

  it("renders status badge, rating, source", () => {
    render(<ModelHero detail={makeDetail()} />, { wrapper: wrap() });
    expect(document.body.textContent?.toLowerCase()).toContain("printed");
    expect(document.body.textContent).toContain("4.5");
    expect(document.body.textContent?.toLowerCase()).toContain("printables");
  });

  it("mounts TagGroupsSection with the model detail, admin flag, and an onAddTags handler that opens the tags sheet", () => {
    mockUseAuth.mockReturnValue({ isAdmin: true });
    const detail = makeDetail();
    render(<ModelHero detail={detail} />, { wrapper: wrap() });
    expect(mockTagGroupsSection).toHaveBeenCalledTimes(1);
    const call = mockTagGroupsSection.mock.calls[0];
    if (call === undefined) throw new Error("TagGroupsSection was not called");
    const [props] = call;
    expect(props.detail).toBe(detail);
    expect(props.isAdmin).toBe(true);
    expect(typeof props.onAddTags).toBe("function");
    // onAddTags reuses ModelHero's existing tagsOpen state, opening the same
    // EditTagsSheet the pencil button opens (no new sheet built).
    act(() => props.onAddTags());
    expect(screen.getByText("Edit tags")).toBeTruthy();
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

  it("admin sees Re-render in the ⋮ menu", async () => {
    mockUseAuth.mockReturnValue({ isAdmin: true });
    render(<ModelHero detail={makeDetail()} />, { wrapper: wrap() });
    const kebab = screen.getByLabelText("Model actions");
    fireEvent.click(kebab);
    expect(await screen.findByText(/re-render/i)).toBeTruthy();
  });
});
