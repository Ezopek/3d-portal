import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ModelDetail } from "@/lib/api-types";

import { PhotosTab } from "./PhotosTab";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);
vi.stubGlobal("confirm", vi.fn(() => true));

afterEach(() => {
  cleanup();
  fetchMock.mockReset();
});

beforeEach(() => fetchMock.mockReset());

const ID = "m1";

function makeDetail(over: Partial<ModelDetail> = {}): ModelDetail {
  return {
    id: ID,
    legacy_id: null,
    slug: "x",
    name_en: "X",
    name_pl: null,
    category_id: "c",
    source: "printables",
    status: "not_printed",
    rating: null,
    thumbnail_file_id: "f1",
    date_added: "2026-01-01",
    deleted_at: null,
    created_at: "",
    updated_at: "",
    tags: [],
    category: { id: "c", parent_id: null, slug: "c", name_en: "C", name_pl: null },
    files: [],
    prints: [],
    notes: [],
    external_links: [],
    gallery_file_ids: [],
    image_count: 0,
    ...over,
  };
}

const PHOTOS = [
  {
    id: "f1",
    model_id: ID,
    kind: "image" as const,
    original_name: "iso.png",
    storage_path: "",
    sha256: "",
    size_bytes: 1024,
    mime_type: "image/png",
    position: 0,
    created_at: "",
  },
  {
    id: "f2",
    model_id: ID,
    kind: "image" as const,
    original_name: "front.png",
    storage_path: "",
    sha256: "",
    size_bytes: 2048,
    mime_type: "image/png",
    position: 1,
    created_at: "",
  },
];

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("PhotosTab", () => {
  it("renders empty state when no photos", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ items: [] }), { status: 200 }),
    );
    const { findByText } = render(<PhotosTab detail={makeDetail()} />, { wrapper: wrap() });
    expect(await findByText(/no photos/i)).toBeTruthy();
  });

  it("renders one row per photo", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ items: PHOTOS }), { status: 200 }),
    );
    const { findAllByTestId } = render(<PhotosTab detail={makeDetail()} />, { wrapper: wrap() });
    const rows = await findAllByTestId("photo-row");
    expect(rows.length).toBe(2);
  });

  it("clicking 'Set as thumbnail' fires the mutation", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ items: PHOTOS }), { status: 200 }),
    );
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({}), { status: 200 }));
    const { findByText } = render(
      <PhotosTab detail={makeDetail({ thumbnail_file_id: "f2" })} />,
      { wrapper: wrap() },
    );
    const setBtn = await findByText(/Set as thumbnail/i);
    fireEvent.click(setBtn);
    await new Promise((r) => setTimeout(r, 0));
    const url = fetchMock.mock.calls[1]?.[0];
    expect(url).toContain(`/api/admin/models/${ID}/thumbnail`);
  });
});
