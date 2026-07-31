import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import "@/locales/i18n";
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
    slug: "x",
    name_en: "X",
    name_pl: null,
    source: "printables",
    status: "not_printed",
    rating: null,
    thumbnail_file_id: "f1",
    date_added: "2026-01-01",
    deleted_at: null,
    created_at: "",
    updated_at: "",
    tags: [],
    files: [],
    prints: [],
    notes: [],
    categories: [],
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

  it("dropping files on the upload zone POSTs them and toggles the dragging state", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ items: [] }), { status: 200 }),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "f-new", model_id: ID, kind: "image" }), { status: 201 }),
    );
    const { findByTestId } = render(<PhotosTab detail={makeDetail()} />, { wrapper: wrap() });
    const zone = await findByTestId("photo-upload-zone");
    expect(zone.getAttribute("data-dragging")).toBe("false");

    // dragOver / dragEnter must flip the visual state — proves preventDefault
    // is wired up (a missed preventDefault would let the browser open the file).
    fireEvent.dragEnter(zone);
    expect(zone.getAttribute("data-dragging")).toBe("true");

    const file = new File(["x"], "drop.png", { type: "image/png" });
    fireEvent.drop(zone, { dataTransfer: { files: [file] } });
    expect(zone.getAttribute("data-dragging")).toBe("false");

    await new Promise((r) => setTimeout(r, 0));
    const uploadCall = fetchMock.mock.calls.find(
      (c) => typeof c[0] === "string" && c[0].includes(`/api/admin/models/${ID}/files`),
    );
    expect(uploadCall).toBeTruthy();
    expect((uploadCall?.[1] as RequestInit).method).toBe("POST");
  });

  // -- Story 54.2 / AC-2 (V-1) — SC 2.5.7 + SC 2.5.8 on the reorder affordance --
  //
  // Before this story the ONLY way to reorder a photo was a drag: the sensor
  // set was `PointerSensor` + `TouchSensor` with no keyboard sensor anywhere in
  // the repo, and the handle's `<button>` carried no sizing box at all, so its
  // border box was the 16x16 `size-4` icon.
  //
  // The remediation is a single-pointer move-up / move-down pair, NOT a
  // `KeyboardSensor`. That choice is load-bearing: SC 2.5.7 asks for a path
  // "achieved by a SINGLE POINTER without dragging", so a keyboard-only
  // alternative does not discharge it — and the story's own § 1 names "a touch
  // user with limited dexterity" alongside the keyboard user. Buttons serve
  // both; a keyboard sensor serves only one.

  it("offers a single-pointer reorder path that needs no drag (AC-2 / SC 2.5.7)", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ items: PHOTOS }), { status: 200 }),
    );
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({}), { status: 200 }));
    const { findAllByTestId } = render(<PhotosTab detail={makeDetail()} />, {
      wrapper: wrap(),
    });
    const rows = await findAllByTestId("photo-row");
    expect(rows).toHaveLength(2);

    // Row 1 cannot move up and row 2 cannot move down — the ends are disabled
    // rather than absent, so the control set does not reflow as items move.
    const up = await findAllByTestId("photo-move-up");
    const down = await findAllByTestId("photo-move-down");
    expect((up[0] as HTMLButtonElement).disabled).toBe(true);
    expect((down[1] as HTMLButtonElement).disabled).toBe(true);

    // A plain click — no pointer path, no drag — commits the new order.
    fireEvent.click(down[0] as HTMLButtonElement);
    await new Promise((r) => setTimeout(r, 0));

    const reorderCall = fetchMock.mock.calls.find(
      (c) => typeof c[0] === "string" && c[0].includes(`/api/admin/models/${ID}/photos/reorder`),
    );
    expect(reorderCall, "moving a photo down must POST the reorder endpoint").toBeTruthy();
    expect(JSON.parse((reorderCall?.[1] as RequestInit).body as string)).toEqual({
      ordered_ids: ["f2", "f1"],
    });
  });

  it("gives every reorder control a >=24x24 sizing box and a translated name (AC-2 / SC 2.5.8)", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ items: PHOTOS }), { status: 200 }),
    );
    const { findAllByTestId } = render(<PhotosTab detail={makeDetail()} />, {
      wrapper: wrap(),
    });

    // jsdom does not lay out, so the RENDERED box is measured in Chromium by
    // `tests/visual/a11y-target-size.spec.ts` (D-1). What is pinned here is the
    // sizing box being DECLARED at all — the defect V-1 recorded was a button
    // with no padding, no `min-h`/`min-w` and no box, whose border box was the
    // 16x16 icon. A class assertion catches that coming back long before a
    // Chromium probe would need to run.
    for (const testid of ["photo-drag-handle", "photo-move-up", "photo-move-down"]) {
      const controls = await findAllByTestId(testid);
      expect(controls.length, `${testid} renders`).toBeGreaterThan(0);
      for (const control of controls) {
        expect(control.className, `${testid} declares a >=24px box`).toContain("min-h-6");
        expect(control.className, `${testid} declares a >=24px box`).toContain("min-w-6");
        expect(control.getAttribute("aria-label"), `${testid} is named`).toBeTruthy();
      }
    }
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
