import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import "@/locales/i18n";
import type { ModelDetail } from "@/lib/api-types";

import { DeleteModelDialog } from "./DeleteModelDialog";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

beforeEach(() => {
  fetchMock.mockReset();
});

afterEach(() => cleanup());

function makeDetail(over: Partial<ModelDetail> = {}): ModelDetail {
  return {
    id: "m1",
    legacy_id: null,
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

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

function Harness({
  detail,
  onDeleted,
}: {
  detail: ModelDetail;
  onDeleted?: () => void;
}) {
  const [open, setOpen] = useState(true);
  return (
    <DeleteModelDialog
      detail={detail}
      open={open}
      onOpenChange={setOpen}
      onDeleted={onDeleted}
    />
  );
}

describe("DeleteModelDialog", () => {
  it("disables the Delete button until the typed name matches name_en exactly", () => {
    render(<Harness detail={makeDetail()} />, { wrapper: wrap() });
    const deleteBtn = screen.getByRole("button", { name: /^delete$/i });
    expect((deleteBtn as HTMLButtonElement).disabled).toBe(true);

    const input = screen.getByPlaceholderText("Dragon") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "drago" } });
    expect((deleteBtn as HTMLButtonElement).disabled).toBe(true);

    fireEvent.change(input, { target: { value: "Dragon" } });
    expect((deleteBtn as HTMLButtonElement).disabled).toBe(false);
  });

  it("fires a DELETE on the admin model endpoint when confirmed", async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    const onDeleted = vi.fn();
    render(<Harness detail={makeDetail()} onDeleted={onDeleted} />, {
      wrapper: wrap(),
    });
    const input = screen.getByPlaceholderText("Dragon") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Dragon" } });
    fireEvent.click(screen.getByRole("button", { name: /^delete$/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/models/m1");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("DELETE");
    await waitFor(() => expect(onDeleted).toHaveBeenCalledTimes(1));
  });
});
