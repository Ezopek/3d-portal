import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import "@/locales/i18n";
import { DescriptionPanel } from "./DescriptionPanel";
import type { ModelDetail, NoteRead } from "@/lib/api-types";

const mockUseAuth = vi.fn();
vi.mock("@/shell/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

afterEach(() => {
  cleanup();
  mockUseAuth.mockReset();
});

beforeEach(() => {
  mockUseAuth.mockReturnValue({ isAdmin: false });
});

const MODEL_ID = "m1";

function note(over: Partial<NoteRead> = {}): NoteRead {
  return {
    id: "n1",
    model_id: MODEL_ID,
    kind: "description",
    body: "Articulated dragon for Bambu A1.",
    author_id: null,
    created_at: "",
    updated_at: "",
    ...over,
  };
}

function makeDetail(notes: NoteRead[] = []): ModelDetail {
  return {
    id: MODEL_ID,
    legacy_id: null,
    slug: "dragon",
    name_en: "Dragon",
    name_pl: null,
    category_id: "c1",
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
      id: "c1",
      parent_id: null,
      slug: "c",
      name_en: "C",
      name_pl: null,
    },
    files: [],
    prints: [],
    notes,
    external_links: [],
    gallery_file_ids: [],
    image_count: 0,
  };
}

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("DescriptionPanel", () => {
  it("renders the description body", () => {
    render(<DescriptionPanel detail={makeDetail([note()])} />, { wrapper: wrap() });
    expect(screen.getByText(/Articulated dragon/)).toBeTruthy();
  });

  it("ignores non-description notes", () => {
    render(
      <DescriptionPanel
        detail={makeDetail([note({ kind: "operational", body: "tip" })])}
      />,
      { wrapper: wrap() },
    );
    expect(document.body.textContent).not.toContain("tip");
  });

  it("renders fallback when no description", () => {
    render(<DescriptionPanel detail={makeDetail()} />, { wrapper: wrap() });
    expect(document.body.textContent?.toLowerCase()).toContain("no description");
  });

  it("does not render the edit affordance for non-admin", () => {
    mockUseAuth.mockReturnValue({ isAdmin: false });
    render(<DescriptionPanel detail={makeDetail([note()])} />, { wrapper: wrap() });
    expect(screen.queryByLabelText(/edit description/i)).toBeNull();
  });

  it("renders the edit affordance for admin and opens the sheet on click", async () => {
    mockUseAuth.mockReturnValue({ isAdmin: true });
    render(<DescriptionPanel detail={makeDetail([note()])} />, { wrapper: wrap() });
    const editBtn = screen.getByLabelText(/edit description/i);
    expect(editBtn).toBeTruthy();
    fireEvent.click(editBtn);
    // Sheet opens — it renders a textbox with the body preloaded
    const textarea = await waitFor(
      () => screen.getByRole("textbox") as HTMLTextAreaElement,
    );
    expect(textarea.value).toBe("Articulated dragon for Bambu A1.");
  });
});
