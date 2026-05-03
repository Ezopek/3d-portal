import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FileList } from "./FileList";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

const isAdminMock = vi.fn();
vi.mock("@/lib/auth", () => ({
  isAdmin: () => isAdminMock(),
  readToken: () => ({ token: "tok" }),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      const map: Record<string, string> = {
        "catalog.empty": "No models match the filter.",
        "catalog.actions.download": "Download",
        "catalog.renderSelection.badgeAuto": "auto",
        "catalog.renderSelection.apply": "Apply & re-render",
        "catalog.renderSelection.applied": "Selection saved, render in progress",
        "catalog.renderSelection.errorTooMany": "Too many files (max 16)",
        "catalog.renderSelection.errorGeneric": "Could not save selection",
        "catalog.renderSelection.statusDefault": "Selected: 0 (default)",
        "catalog.renderSelection.statusSingle": "Selected: 1",
        "catalog.renderSelection.statusGroup": `Selected: ${opts?.count ?? "?"} → group render`,
      };
      return map[key] ?? key;
    },
  }),
}));

afterEach(() => {
  cleanup();
  fetchMock.mockReset();
  isAdminMock.mockReset();
});

function Wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const FILES_RESPONSE = { files: ["files/a.stl", "files/b.stl", "files/c.stl"] };
const SELECTION_EMPTY = { paths: [], available_stls: FILES_RESPONSE.files };

describe("FileList — member view", () => {
  it("renders rows without checkboxes", async () => {
    isAdminMock.mockReturnValue(false);
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(FILES_RESPONSE), { status: 200 }),
    );
    render(<FileList modelId="001" />, { wrapper: Wrapper });
    await waitFor(() => expect(screen.queryByText("files/a.stl")).toBeTruthy());
    expect(screen.queryByRole("checkbox")).toBeNull();
  });
});

describe("FileList — admin view", () => {
  it("shows checkboxes and the auto badge on the first file when selection empty", async () => {
    isAdminMock.mockReturnValue(true);
    fetchMock.mockImplementation(async (url: string) => {
      if (url.includes("render-selection")) {
        return new Response(JSON.stringify(SELECTION_EMPTY), { status: 200 });
      }
      return new Response(JSON.stringify(FILES_RESPONSE), { status: 200 });
    });
    render(<FileList modelId="001" />, { wrapper: Wrapper });
    await waitFor(() => expect(screen.getAllByRole("checkbox").length).toBe(3));
    expect(screen.queryByText("auto")).toBeTruthy();
  });

  it("enables Apply only after a checkbox is toggled", async () => {
    isAdminMock.mockReturnValue(true);
    fetchMock.mockImplementation(async (url: string) => {
      if (url.includes("render-selection")) {
        return new Response(JSON.stringify(SELECTION_EMPTY), { status: 200 });
      }
      return new Response(JSON.stringify(FILES_RESPONSE), { status: 200 });
    });
    render(<FileList modelId="001" />, { wrapper: Wrapper });
    const apply = await screen.findByRole("button", { name: /apply/i });
    expect((apply as HTMLButtonElement).disabled).toBe(true);
    await userEvent.click(screen.getAllByRole("checkbox")[0]);
    expect((apply as HTMLButtonElement).disabled).toBe(false);
  });

  it("disables Apply and shows helper text when 17 boxes are checked", async () => {
    isAdminMock.mockReturnValue(true);
    const big = { files: Array.from({ length: 17 }, (_, i) => `files/p${i}.stl`) };
    fetchMock.mockImplementation(async (url: string) => {
      if (url.includes("render-selection")) {
        return new Response(JSON.stringify({ paths: [], available_stls: big.files }), { status: 200 });
      }
      return new Response(JSON.stringify(big), { status: 200 });
    });
    render(<FileList modelId="001" />, { wrapper: Wrapper });
    await waitFor(() => expect(screen.getAllByRole("checkbox").length).toBe(17));
    for (const cb of screen.getAllByRole("checkbox")) {
      await userEvent.click(cb);
    }
    const apply = screen.getByRole("button", { name: /apply/i });
    expect((apply as HTMLButtonElement).disabled).toBe(true);
    expect(screen.queryByText(/max 16/i)).toBeTruthy();
  });
});
