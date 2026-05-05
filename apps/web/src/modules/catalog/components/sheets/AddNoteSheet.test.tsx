import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NoteRead } from "@/lib/api-types";

import { AddNoteSheet } from "./AddNoteSheet";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

beforeEach(() => {
  fetchMock.mockReset();
});

afterEach(() => cleanup());

function makeNote(over: Partial<NoteRead> = {}): NoteRead {
  return {
    id: "n1",
    model_id: "m1",
    kind: "operational",
    body: "watch the supports",
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

function Harness({ note }: { note: NoteRead | null }) {
  const [open, setOpen] = useState(true);
  return (
    <AddNoteSheet modelId="m1" note={note} open={open} onOpenChange={setOpen} />
  );
}

describe("AddNoteSheet", () => {
  it("starts with operational kind and empty body in create mode and POSTs on save", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(makeNote()), { status: 201 }));
    render(<Harness note={null} />, { wrapper: wrap() });

    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    expect(textarea.value).toBe("");

    fireEvent.change(textarea, { target: { value: "be careful with the bridge" } });
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/notes");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.body).toBe(
      JSON.stringify({
        model_id: "m1",
        kind: "operational",
        body: "be careful with the bridge",
      }),
    );
  });

  it("preloads body from existing note in edit mode and PATCHes on save", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(makeNote({ id: "n7" })), { status: 200 }),
    );
    render(
      <Harness note={makeNote({ id: "n7", kind: "ai_review", body: "looks good" })} />,
      { wrapper: wrap() },
    );

    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    expect(textarea.value).toBe("looks good");

    fireEvent.change(textarea, { target: { value: "needs another pass" } });
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/notes/n7");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("PATCH");
    expect(init.body).toBe(
      JSON.stringify({ kind: "ai_review", body: "needs another pass" }),
    );
  });

  it("falls back to operational when editing a description-kind note", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(makeNote({ id: "n9" })), { status: 200 }),
    );
    render(
      <Harness note={makeNote({ id: "n9", kind: "description", body: "x" })} />,
      { wrapper: wrap() },
    );
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.body).toBe(JSON.stringify({ kind: "operational", body: "x" }));
  });
});
