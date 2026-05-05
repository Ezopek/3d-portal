import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { PrintRead } from "@/lib/api-types";

import { AddPrintSheet } from "./AddPrintSheet";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

beforeEach(() => {
  fetchMock.mockReset();
});

afterEach(() => cleanup());

function makePrint(over: Partial<PrintRead> = {}): PrintRead {
  return {
    id: "p1",
    model_id: "m1",
    photo_file_id: null,
    printed_at: "2026-04-01",
    note: "first attempt",
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

function Harness({ print }: { print: PrintRead | null }) {
  const [open, setOpen] = useState(true);
  return (
    <AddPrintSheet
      modelId="m1"
      print={print}
      open={open}
      onOpenChange={setOpen}
    />
  );
}

describe("AddPrintSheet", () => {
  it("starts blank in create mode and POSTs a new print on save", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(makePrint()), { status: 201 }));
    render(<Harness print={null} />, { wrapper: wrap() });

    const dateInput = document.querySelector("input[type=date]") as HTMLInputElement;
    expect(dateInput.value).toBe("");
    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    expect(textarea.value).toBe("");

    fireEvent.change(dateInput, { target: { value: "2026-05-01" } });
    fireEvent.change(textarea, { target: { value: "second attempt" } });
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/models/m1/prints");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.body).toBe(
      JSON.stringify({
        model_id: "m1",
        printed_at: "2026-05-01",
        note: "second attempt",
      }),
    );
  });

  it("preloads existing values in edit mode and PATCHes the print on save", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(makePrint({ id: "p1" })), { status: 200 }),
    );
    render(<Harness print={makePrint({ id: "p1" })} />, { wrapper: wrap() });

    const dateInput = document.querySelector("input[type=date]") as HTMLInputElement;
    expect(dateInput.value).toBe("2026-04-01");
    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    expect(textarea.value).toBe("first attempt");

    fireEvent.change(textarea, { target: { value: "rewrote it" } });
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/prints/p1");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("PATCH");
    expect(init.body).toBe(
      JSON.stringify({ printed_at: "2026-04-01", note: "rewrote it" }),
    );
  });

  it("sends nulls when fields are cleared", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(makePrint()), { status: 201 }));
    render(<Harness print={null} />, { wrapper: wrap() });
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.body).toBe(
      JSON.stringify({ model_id: "m1", printed_at: null, note: null }),
    );
  });
});
