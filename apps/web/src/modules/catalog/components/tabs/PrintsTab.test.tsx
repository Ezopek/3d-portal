import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import "@/locales/i18n";
import type { PrintRead } from "@/lib/api-types";

import { PrintsTab } from "./PrintsTab";

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
const PRINT: PrintRead = {
  id: "p1",
  model_id: MODEL_ID,
  photo_file_id: "img1",
  printed_at: "2026-04-30",
  note: "Printed in PETG 0.2mm",
  created_at: "",
  updated_at: "",
};

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("PrintsTab", () => {
  it("renders each print with date and note", () => {
    render(<PrintsTab modelId={MODEL_ID} prints={[PRINT]} />, { wrapper: wrap() });
    expect(screen.getByText(/2026-04-30/)).toBeTruthy();
    expect(screen.getByText(/PETG/)).toBeTruthy();
  });

  it("renders thumbnail img when photo_file_id is set", () => {
    render(<PrintsTab modelId={MODEL_ID} prints={[PRINT]} />, { wrapper: wrap() });
    const img = document.querySelector("img") as HTMLImageElement;
    expect(img.getAttribute("src")).toBe(
      `/api/models/${MODEL_ID}/files/img1/content`,
    );
  });

  it("renders empty state when no prints", () => {
    render(<PrintsTab modelId={MODEL_ID} prints={[]} />, { wrapper: wrap() });
    expect(document.body.textContent?.toLowerCase()).toContain("no prints");
  });

  it("does not show + Add print or per-card edit buttons for non-admin", () => {
    mockUseAuth.mockReturnValue({ isAdmin: false });
    render(<PrintsTab modelId={MODEL_ID} prints={[PRINT]} />, { wrapper: wrap() });
    expect(screen.queryByRole("button", { name: /add print/i })).toBeNull();
    expect(screen.queryByLabelText("Edit print")).toBeNull();
    expect(screen.queryByLabelText("Delete print")).toBeNull();
  });

  it("renders + Add print and per-card affordances for admin", () => {
    mockUseAuth.mockReturnValue({ isAdmin: true });
    render(<PrintsTab modelId={MODEL_ID} prints={[PRINT]} />, { wrapper: wrap() });
    expect(screen.getByRole("button", { name: /add print/i })).toBeTruthy();
    expect(screen.getByLabelText("Edit print")).toBeTruthy();
    expect(screen.getByLabelText("Delete print")).toBeTruthy();
  });

  it("DELETEs the print after confirm", async () => {
    mockUseAuth.mockReturnValue({ isAdmin: true });
    vi.stubGlobal("confirm", vi.fn(() => true));
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    render(<PrintsTab modelId={MODEL_ID} prints={[PRINT]} />, { wrapper: wrap() });
    fireEvent.click(screen.getByLabelText("Delete print"));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/prints/p1");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("DELETE");
    vi.unstubAllGlobals();
    vi.stubGlobal("fetch", fetchMock);
  });
});
