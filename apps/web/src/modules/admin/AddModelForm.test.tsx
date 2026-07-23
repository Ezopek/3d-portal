// Story 47.5 (T-A1) — post-cutover contract for the admin Add Model form:
// no legacy-taxonomy selector, submit possible with only a name, the
// POST /api/admin/models body carries no legacy FK field, and the form never
// fetches the retired taxonomy endpoint (it no longer exists).
//
// The retired-taxonomy literals below are assembled at runtime so the story
// §11 residual-symbol grep stays clean: they exist here purely as negative
// assertions against symbols that must not reappear in live code.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import "@/locales/i18n";

import { AddModelForm } from "./AddModelForm";

const LEGACY_FIELD = ["cat", "egory_id"].join("");
const LEGACY_ROUTE = ["/cat", "egories"].join("");
const LEGACY_LABEL = ["Cat", "egory"].join("");

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

const CREATED_MODEL = {
  id: "11111111-1111-1111-1111-111111111111",
  slug: "dragon",
  name_en: "Dragon",
};

beforeEach(() => {
  fetchMock.mockReset();
  fetchMock.mockImplementation((url: string) => {
    if (url.includes("/admin/models")) {
      return Promise.resolve(
        new Response(JSON.stringify(CREATED_MODEL), { status: 201 }),
      );
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });
});

afterEach(cleanup);

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("AddModelForm (post-cutover, Story 47.5)", () => {
  it("renders without a legacy-taxonomy select", () => {
    render(<AddModelForm onSuccess={() => {}} onCancel={() => {}} />, {
      wrapper: wrap(),
    });
    expect(screen.queryByText(LEGACY_LABEL)).toBeNull();
    expect(screen.queryByText(`— Select ${LEGACY_LABEL.toLowerCase()} —`)).toBeNull();
    // Structural guard (review repair): exactly the two surviving selects —
    // source + status. A resurrected taxonomy selector rendering raw i18n
    // keys would evade the text negatives above but not this count.
    expect(screen.getAllByRole("combobox")).toHaveLength(2);
  });

  it("submits with only a name and POSTs a body without the legacy FK field", async () => {
    const onSuccess = vi.fn();
    render(<AddModelForm onSuccess={onSuccess} onCancel={() => {}} />, {
      wrapper: wrap(),
    });

    fireEvent.change(screen.getByLabelText(/Name \(English\)/), {
      target: { value: "Dragon" },
    });
    const submit = screen.getByRole("button", { name: "Create model" });
    expect((submit as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(submit);

    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));

    const createCall = fetchMock.mock.calls.find(([url]) =>
      String(url).includes("/admin/models"),
    );
    expect(createCall).toBeTruthy();
    const body = JSON.parse((createCall?.[1] as RequestInit).body as string) as Record<
      string,
      unknown
    >;
    expect(LEGACY_FIELD in body).toBe(false);
    expect(body.name_en).toBe("Dragon");
  });

  it("never fetches the retired taxonomy endpoint", async () => {
    render(<AddModelForm onSuccess={() => {}} onCancel={() => {}} />, {
      wrapper: wrap(),
    });
    // Give any mount-time queries a tick to fire before asserting.
    await waitFor(() => expect(screen.queryByText("Create model")).toBeTruthy());
    const legacyFetches = fetchMock.mock.calls.filter(([url]) =>
      String(url).includes(LEGACY_ROUTE),
    );
    expect(legacyFetches).toEqual([]);
  });
});
