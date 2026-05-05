import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NoteRead } from "@/lib/api-types";

import { OperationalNotesTab } from "./OperationalNotesTab";

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
  mockUseAuth.mockReturnValue({ isAdmin: false });
});

afterEach(() => {
  cleanup();
  mockUseAuth.mockReset();
});

const MODEL_ID = "m1";

function note(kind: NoteRead["kind"], body: string, id: string): NoteRead {
  return {
    id,
    model_id: MODEL_ID,
    kind,
    body,
    author_id: null,
    created_at: "",
    updated_at: "",
  };
}

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("OperationalNotesTab", () => {
  it("renders operational, ai_review, other notes (not description)", () => {
    render(
      <OperationalNotesTab
        modelId={MODEL_ID}
        notes={[
          note("description", "should NOT show", "n0"),
          note("operational", "tip 1", "n1"),
          note("ai_review", "AI says", "n2"),
          note("other", "misc", "n3"),
        ]}
      />,
      { wrapper: wrap() },
    );
    expect(screen.getByText("tip 1")).toBeTruthy();
    expect(screen.getByText("AI says")).toBeTruthy();
    expect(screen.getByText("misc")).toBeTruthy();
    expect(screen.queryByText("should NOT show")).toBeNull();
  });

  it("renders kind labels", () => {
    render(
      <OperationalNotesTab modelId={MODEL_ID} notes={[note("operational", "x", "n1")]} />,
      { wrapper: wrap() },
    );
    expect(document.body.textContent?.toLowerCase()).toContain("operational");
  });

  it("renders empty state when no non-description notes", () => {
    render(
      <OperationalNotesTab modelId={MODEL_ID} notes={[note("description", "x", "n1")]} />,
      { wrapper: wrap() },
    );
    expect(document.body.textContent?.toLowerCase()).toContain("no notes");
  });

  it("does not show + Add note or per-card affordances for non-admin", () => {
    mockUseAuth.mockReturnValue({ isAdmin: false });
    render(
      <OperationalNotesTab modelId={MODEL_ID} notes={[note("operational", "tip", "n1")]} />,
      { wrapper: wrap() },
    );
    expect(screen.queryByRole("button", { name: /add note/i })).toBeNull();
    expect(screen.queryByLabelText("Edit note")).toBeNull();
    expect(screen.queryByLabelText("Delete note")).toBeNull();
  });

  it("renders + Add note and per-card affordances for admin", () => {
    mockUseAuth.mockReturnValue({ isAdmin: true });
    render(
      <OperationalNotesTab modelId={MODEL_ID} notes={[note("operational", "tip", "n1")]} />,
      { wrapper: wrap() },
    );
    expect(screen.getByRole("button", { name: /add note/i })).toBeTruthy();
    expect(screen.getByLabelText("Edit note")).toBeTruthy();
    expect(screen.getByLabelText("Delete note")).toBeTruthy();
  });

  it("DELETEs the note after confirm", async () => {
    mockUseAuth.mockReturnValue({ isAdmin: true });
    vi.stubGlobal("confirm", vi.fn(() => true));
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    render(
      <OperationalNotesTab modelId={MODEL_ID} notes={[note("operational", "tip", "n1")]} />,
      { wrapper: wrap() },
    );
    fireEvent.click(screen.getByLabelText("Delete note"));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/notes/n1");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("DELETE");
    vi.unstubAllGlobals();
    vi.stubGlobal("fetch", fetchMock);
  });
});
