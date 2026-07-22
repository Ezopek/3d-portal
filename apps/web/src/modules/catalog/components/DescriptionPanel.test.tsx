import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import i18n from "i18next";
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
    body_pl: null,
    body_en: null,
    author_id: null,
    created_at: "",
    updated_at: "",
    ...over,
  };
}

function makeDetail(notes: NoteRead[] = []): ModelDetail {
  return {
    id: MODEL_ID,
    slug: "dragon",
    name_en: "Dragon",
    name_pl: null,
    source: "printables",
    status: "not_printed",
    rating: null,
    thumbnail_file_id: null,
    date_added: "2026-04-12",
    deleted_at: null,
    created_at: "",
    updated_at: "",
    tags: [],
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
    render(
      <DescriptionPanel
        detail={makeDetail([
          note({ body_en: "english from sheet" }),
        ])}
      />,
      { wrapper: wrap() },
    );
    const editBtn = screen.getByLabelText(/edit description/i);
    expect(editBtn).toBeTruthy();
    fireEvent.click(editBtn);
    // Sheet opens — Story 16.2 revised: bilingual editor preloads the
    // English textarea from body_en (NOT from legacy body, which is
    // language-ambiguous per Codex P2 fix-up 2026-05-22).
    const en = await waitFor(
      () => screen.getByLabelText(/english description/i) as HTMLTextAreaElement,
    );
    expect(en.value).toBe("english from sheet");
  });

  // Initiative 10 Story 16.1 (Decision L) — bilingual fallback chain.
  describe("bilingual fallback (Story 16.1)", () => {
    afterEach(async () => {
      await i18n.changeLanguage("en");
    });

    it("renders body_en when locale is en and body_en is set", async () => {
      await i18n.changeLanguage("en");
      render(
        <DescriptionPanel
          detail={makeDetail([
            note({ body: "legacy", body_pl: "polski tekst", body_en: "english text" }),
          ])}
        />,
        { wrapper: wrap() },
      );
      expect(screen.getByText("english text")).toBeTruthy();
      expect(screen.queryByText("polski tekst")).toBeNull();
      expect(screen.queryByText("legacy")).toBeNull();
    });

    it("renders body_pl when locale is pl and body_pl is set", async () => {
      await i18n.changeLanguage("pl");
      render(
        <DescriptionPanel
          detail={makeDetail([
            note({ body: "legacy", body_pl: "polski tekst", body_en: "english text" }),
          ])}
        />,
        { wrapper: wrap() },
      );
      expect(screen.getByText("polski tekst")).toBeTruthy();
      expect(screen.queryByText("english text")).toBeNull();
    });

    it("falls back to body_en when locale is pl but body_pl is null", async () => {
      await i18n.changeLanguage("pl");
      render(
        <DescriptionPanel
          detail={makeDetail([
            note({ body: "legacy", body_pl: null, body_en: "english only" }),
          ])}
        />,
        { wrapper: wrap() },
      );
      expect(screen.getByText("english only")).toBeTruthy();
      expect(screen.queryByText("legacy")).toBeNull();
    });

    it("falls back to legacy body when both body_pl and body_en are null", () => {
      render(
        <DescriptionPanel
          detail={makeDetail([
            note({ body: "legacy content", body_pl: null, body_en: null }),
          ])}
        />,
        { wrapper: wrap() },
      );
      expect(screen.getByText("legacy content")).toBeTruthy();
    });
  });
});
