import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import "@/locales/i18n";

import { RenderSheet } from "./RenderSheet";
import type { ModelDetail } from "@/lib/api-types";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

afterEach(() => {
  cleanup();
  fetchMock.mockReset();
});

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

function makeDetail(files: ModelDetail["files"]): ModelDetail {
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
    date_added: "2026-01-01",
    deleted_at: null,
    created_at: "",
    updated_at: "",
    tags: [],
    category: { id: "c", parent_id: null, slug: "c", name_en: "C", name_pl: null },
    files,
    prints: [],
    notes: [],
    external_links: [],
    gallery_file_ids: [],
    image_count: 0,
  };
}

const STL_A = {
  id: "fa",
  model_id: "m1",
  kind: "stl" as const,
  original_name: "a.stl",
  storage_path: "x",
  sha256: "x",
  size_bytes: 10,
  mime_type: "model/stl",
  position: null,
  created_at: "",
};
const STL_B = { ...STL_A, id: "fb", original_name: "b.stl" };

describe("RenderSheet", () => {
  it("renders one row per STL file", () => {
    render(
      <RenderSheet
        detail={makeDetail([STL_A, STL_B])}
        open={true}
        onOpenChange={() => {}}
      />,
      { wrapper: wrap() },
    );
    expect(screen.getByText("a.stl")).toBeTruthy();
    expect(screen.getByText("b.stl")).toBeTruthy();
  });

  it("preselects the first STL", () => {
    render(
      <RenderSheet
        detail={makeDetail([STL_A, STL_B])}
        open={true}
        onOpenChange={() => {}}
      />,
      { wrapper: wrap() },
    );
    const a = screen.getByLabelText("a.stl") as HTMLInputElement;
    const b = screen.getByLabelText("b.stl") as HTMLInputElement;
    expect(a.checked).toBe(true);
    expect(b.checked).toBe(false);
  });

  it("submits selected ids on Re-render click", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({ status: "queued", status_key: "render:status:m1" }),
        { status: 202 },
      ),
    );
    render(
      <RenderSheet
        detail={makeDetail([STL_A, STL_B])}
        open={true}
        onOpenChange={() => {}}
      />,
      { wrapper: wrap() },
    );
    fireEvent.click(screen.getByLabelText("b.stl"));
    fireEvent.click(screen.getByRole("button", { name: /re-render/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const body = JSON.parse(
      (fetchMock.mock.calls[0]?.[1] as RequestInit).body as string,
    );
    expect(new Set(body.selected_stl_file_ids)).toEqual(new Set(["fa", "fb"]));
  });

  it("renders a no-STL message when model has no STLs", () => {
    render(
      <RenderSheet detail={makeDetail([])} open={true} onOpenChange={() => {}} />,
      {
        wrapper: wrap(),
      },
    );
    expect(screen.getByText(/no STL files/i)).toBeTruthy();
  });
});
