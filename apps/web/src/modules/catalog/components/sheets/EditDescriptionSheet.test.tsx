import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import "@/locales/i18n";
import type { ModelDetail, NoteRead } from "@/lib/api-types";

import { EditDescriptionSheet } from "./EditDescriptionSheet";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

beforeEach(() => {
  fetchMock.mockReset();
});

afterEach(() => cleanup());

function makeDetail(over: Partial<ModelDetail> = {}): ModelDetail {
  return {
    id: "m1",
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
    notes: [],
    external_links: [],
    gallery_file_ids: [],
    image_count: 0,
    ...over,
  };
}

function makeNote(over: Partial<NoteRead> = {}): NoteRead {
  return {
    id: "n1",
    model_id: "m1",
    kind: "description",
    body: "existing body",
    body_pl: null,
    body_en: null,
    author_id: null,
    created_at: "",
    updated_at: "",
    ...over,
  };
}

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

function Harness({ detail }: { detail: ModelDetail }) {
  const [open, setOpen] = useState(true);
  return <EditDescriptionSheet detail={detail} open={open} onOpenChange={setOpen} />;
}

describe("EditDescriptionSheet (Story 16.2 revised — bilingual editor)", () => {
  it("preloads the English textarea from existing body_en (or legacy body)", () => {
    const detail = makeDetail({
      notes: [makeNote({ body: "legacy", body_en: "english text" })],
    });
    render(<Harness detail={detail} />, { wrapper: wrap() });
    const en = screen.getByLabelText(/english description/i) as HTMLTextAreaElement;
    expect(en.value).toBe("english text");
  });

  it("falls back to legacy body for English when body_en is null", () => {
    const detail = makeDetail({
      notes: [makeNote({ body: "hello world", body_en: null, body_pl: null })],
    });
    render(<Harness detail={detail} />, { wrapper: wrap() });
    const en = screen.getByLabelText(/english description/i) as HTMLTextAreaElement;
    expect(en.value).toBe("hello world");
  });

  it("preloads the Polish textarea from body_pl", () => {
    const detail = makeDetail({
      notes: [makeNote({ body: "", body_pl: "polski tekst" })],
    });
    render(<Harness detail={detail} />, { wrapper: wrap() });
    const pl = screen.getByLabelText(/polish description/i) as HTMLTextAreaElement;
    expect(pl.value).toBe("polski tekst");
  });

  it("starts empty when the model has no description note", () => {
    render(<Harness detail={makeDetail()} />, { wrapper: wrap() });
    const en = screen.getByLabelText(/english description/i) as HTMLTextAreaElement;
    const pl = screen.getByLabelText(/polish description/i) as HTMLTextAreaElement;
    expect(en.value).toBe("");
    expect(pl.value).toBe("");
  });

  it("PATCHes the existing note with bilingual fields when saved", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(makeNote({ body: "updated en" })), { status: 200 }),
    );
    const detail = makeDetail({ notes: [makeNote({ id: "note-99", body: "old" })] });
    render(<Harness detail={detail} />, { wrapper: wrap() });
    const en = screen.getByLabelText(/english description/i) as HTMLTextAreaElement;
    const pl = screen.getByLabelText(/polish description/i) as HTMLTextAreaElement;
    fireEvent.change(en, { target: { value: "updated en" } });
    fireEvent.change(pl, { target: { value: "zaktualizowane pl" } });
    fireEvent.click(screen.getByRole("button", { name: /save|zapisz/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/notes/note-99");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("PATCH");
    expect(init.body).toBe(
      JSON.stringify({
        body: "updated en",
        body_pl: "zaktualizowane pl",
        body_en: "updated en",
      }),
    );
  });

  it("POSTs a new description note to /api/admin/models/{id}/notes when none exists", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(makeNote({ body: "fresh" })), { status: 201 }),
    );
    render(<Harness detail={makeDetail()} />, { wrapper: wrap() });
    const en = screen.getByLabelText(/english description/i) as HTMLTextAreaElement;
    fireEvent.change(en, { target: { value: "fresh" } });
    fireEvent.click(screen.getByRole("button", { name: /save|zapisz/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/models/m1/notes");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.body).toBe(
      JSON.stringify({
        kind: "description",
        body: "fresh",
        body_pl: null,
        body_en: "fresh",
      }),
    );
  });
});
