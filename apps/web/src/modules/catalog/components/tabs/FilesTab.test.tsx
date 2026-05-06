import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, cleanup, fireEvent, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ModelFileRead } from "@/lib/api-types";

import { FilesTab } from "./FilesTab";

const mockUseAuth = vi.fn();
vi.mock("@/shell/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

beforeEach(() => {
  mockUseAuth.mockReturnValue({ isAdmin: false });
});

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

const MODEL_ID = "m1";
const FILES: ModelFileRead[] = [
  {
    id: "fa",
    model_id: MODEL_ID,
    kind: "stl",
    original_name: "a.stl",
    storage_path: "",
    sha256: "",
    size_bytes: 1024,
    mime_type: "",
    position: null,
    selected_for_render: true,
    created_at: "",
  },
  {
    id: "fb",
    model_id: MODEL_ID,
    kind: "stl",
    original_name: "b.stl",
    storage_path: "",
    sha256: "",
    size_bytes: 2048,
    mime_type: "",
    position: null,
    selected_for_render: false,
    created_at: "",
  },
  {
    id: "fc",
    model_id: MODEL_ID,
    kind: "source",
    original_name: "c.f3d",
    storage_path: "",
    sha256: "",
    size_bytes: 4096,
    mime_type: "",
    position: null,
    selected_for_render: false,
    created_at: "",
  },
  {
    id: "fd",
    model_id: MODEL_ID,
    kind: "archive_3mf",
    original_name: "d.3mf",
    storage_path: "",
    sha256: "",
    size_bytes: 8192,
    mime_type: "",
    position: null,
    selected_for_render: false,
    created_at: "",
  },
  {
    id: "fe",
    model_id: MODEL_ID,
    kind: "image",
    original_name: "e.png",
    storage_path: "",
    sha256: "",
    size_bytes: 512,
    mime_type: "",
    position: null,
    selected_for_render: false,
    created_at: "",
  },
];

describe("FilesTab", () => {
  it("defaults to STL kind and lists STL files only", () => {
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    expect(screen.getByText("a.stl")).toBeTruthy();
    expect(screen.getByText("b.stl")).toBeTruthy();
    expect(screen.queryByText("c.f3d")).toBeNull();
    expect(screen.queryByText("e.png")).toBeNull();
  });

  it("clicking Source chip switches to source files", () => {
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    fireEvent.click(screen.getByRole("button", { name: /source/i }));
    expect(screen.getByText("c.f3d")).toBeTruthy();
    expect(screen.queryByText("a.stl")).toBeNull();
  });

  it("download link points at the content endpoint", () => {
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    const link = screen
      .getAllByRole("link")
      .find((a) => a.getAttribute("href")?.includes("fa"));
    expect(link?.getAttribute("href")).toBe(
      `/api/models/${MODEL_ID}/files/fa/content?download=1`,
    );
  });

  it("renders an empty state when no files of the active kind", () => {
    render(<FilesTab modelId={MODEL_ID} files={[FILES[4]!]} />, { wrapper: wrap() });
    expect(document.body.textContent?.toLowerCase()).toContain("no files");
  });

  it("non-admin sees no render-selection checkboxes", () => {
    mockUseAuth.mockReturnValue({ isAdmin: false });
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    expect(screen.queryByLabelText(/include .* in renders/i)).toBeNull();
  });

  it("admin sees a checkbox per STL reflecting selected_for_render", () => {
    mockUseAuth.mockReturnValue({ isAdmin: true });
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    const a = screen.getByLabelText("include a.stl in renders") as HTMLInputElement;
    const b = screen.getByLabelText("include b.stl in renders") as HTMLInputElement;
    expect(a.checked).toBe(true);
    expect(b.checked).toBe(false);
  });

  it("toggling the admin checkbox PATCHes selected_for_render", async () => {
    mockUseAuth.mockReturnValue({ isAdmin: true });
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({}), { status: 200 }));
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    const b = screen.getByLabelText("include b.stl in renders");
    fireEvent.click(b);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const url = fetchMock.mock.calls[0]?.[0] as string;
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(url).toBe(`/api/admin/models/${MODEL_ID}/files/fb`);
    expect(init.method).toBe("PATCH");
    expect(init.body).toBe(JSON.stringify({ selected_for_render: true }));
  });

  it("admin sees a Re-render preview button when STLs are present", () => {
    mockUseAuth.mockReturnValue({ isAdmin: true });
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    expect(screen.getByRole("button", { name: /re-render preview/i })).toBeTruthy();
  });

  it("non-admin does not see the Re-render button", () => {
    mockUseAuth.mockReturnValue({ isAdmin: false });
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    expect(screen.queryByRole("button", { name: /re-render preview/i })).toBeNull();
  });

  it("clicking Re-render posts an empty selection so the worker uses persisted flags", async () => {
    mockUseAuth.mockReturnValue({ isAdmin: true });
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({ status: "queued", status_key: `render:status:${MODEL_ID}` }),
        { status: 202 },
      ),
    );
    render(<FilesTab modelId={MODEL_ID} files={FILES} />, { wrapper: wrap() });
    fireEvent.click(screen.getByRole("button", { name: /re-render preview/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const url = fetchMock.mock.calls[0]?.[0] as string;
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(url).toBe(`/api/admin/models/${MODEL_ID}/render`);
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ selected_stl_file_ids: [] }));
  });
});
