import { render, screen, cleanup, fireEvent, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import "@/locales/i18n";
import { ModelGallery } from "./ModelGallery";
import type { ModelFileRead } from "@/lib/api-types";

afterEach(() => cleanup());

const MODEL_ID = "11111111-1111-1111-1111-111111111111";
const FILES: ModelFileRead[] = [
  {
    id: "f1",
    model_id: MODEL_ID,
    kind: "stl",
    original_name: "x.stl",
    storage_path: "x",
    sha256: "",
    size_bytes: 0,
    mime_type: "model/stl",
    position: null,
    selected_for_render: false,
    created_at: "",
  },
  {
    id: "f2",
    model_id: MODEL_ID,
    kind: "image",
    original_name: "iso.png",
    storage_path: "y",
    sha256: "",
    size_bytes: 0,
    mime_type: "image/png",
    position: null,
    selected_for_render: false,
    created_at: "",
  },
  {
    id: "f3",
    model_id: MODEL_ID,
    kind: "print",
    original_name: "print.jpg",
    storage_path: "z",
    sha256: "",
    size_bytes: 0,
    mime_type: "image/jpeg",
    position: null,
    selected_for_render: false,
    created_at: "",
  },
];

describe("ModelGallery", () => {
  it("renders 'no preview' when no image/print files", () => {
    render(<ModelGallery modelId={MODEL_ID} files={[FILES[0]!]} />);
    expect(screen.getByText("no preview")).toBeTruthy();
  });

  it("renders main image from first image/print file", () => {
    render(<ModelGallery modelId={MODEL_ID} files={FILES} />);
    const main = screen.getByTestId("gallery-main") as HTMLImageElement;
    // Story 22.2 — main frame consumes the gallery tier variant.
    expect(main.getAttribute("src")).toBe(
      `/api/models/${MODEL_ID}/files/f2/content?variant=gallery`,
    );
  });

  it("renders thumbnail strip with all image/print files", () => {
    render(<ModelGallery modelId={MODEL_ID} files={FILES} />);
    const thumbs = screen.getAllByTestId("gallery-thumb");
    expect(thumbs).toHaveLength(2);
  });

  it("clicking a thumbnail switches the main image", () => {
    render(<ModelGallery modelId={MODEL_ID} files={FILES} />);
    const thumbs = screen.getAllByTestId("gallery-thumb");
    fireEvent.click(thumbs[1]!);
    const main = screen.getByTestId("gallery-main") as HTMLImageElement;
    // Story 22.2 — main frame consumes the gallery tier variant.
    expect(main.getAttribute("src")).toBe(
      `/api/models/${MODEL_ID}/files/f3/content?variant=gallery`,
    );
  });
});

// Story 54.2 / AC-1 + T13 (V-8) — the duplicate accessible name.
//
// `ModelGallery.tsx:130` (the full-frame trigger) and `:151` (the corner icon)
// BOTH rendered `aria-label={t("catalog.image_viewer.trigger_label")}`, and the
// corner one is hidden with `sm:opacity-0` — opacity, not `display`,
// `visibility` or `aria-hidden` — so both were always in the accessibility
// tree and a screen-reader user heard the same name twice, one after the other,
// for one function. Pre-existing since Story 22.3 (`812c7bd`); Story 54.1
// renamed the string but did not remove the duplicate.
//
// `apps/web/tests/i18n.test.ts:153-167` structurally CANNOT see this: it
// asserts that no two KEYS share a VALUE, which says nothing about one key
// rendered onto two controls.
//
// Fix shape: one named control, one decorative twin. The full-frame button
// keeps the name and the tab stop; the corner icon becomes `aria-hidden` and
// `tabIndex={-1}`. Nothing is lost — the corner button's `onClick` is
// byte-identical to the full-frame button's, and the full-frame button covers
// the whole image, so the function stays keyboard-operable (SC 2.1.1) and
// pointer-operable from either target.
describe("ModelGallery accessible names (Story 54.2 V-8)", () => {
  it("exposes the fullscreen trigger label exactly ONCE", () => {
    render(<ModelGallery modelId={MODEL_ID} files={FILES} />);
    expect(
      screen.getAllByRole("button", { name: "Open fullscreen" }),
    ).toHaveLength(1);
  });

  it("keeps the decorative corner icon out of the tree and out of the tab order", () => {
    render(<ModelGallery modelId={MODEL_ID} files={FILES} />);
    const icon = screen.getByTestId("gallery-fullscreen-icon");
    expect(icon.getAttribute("aria-hidden")).toBe("true");
    expect(icon.getAttribute("tabindex")).toBe("-1");
    // ...but it still opens the viewer for a pointer user.
    expect(icon.getAttribute("aria-label")).toBeNull();
  });
});

// The production defect, at the surface it was reported on: `portal_access`
// expires (10 min max-age) while the lightbox stays open, and the next
// `?variant=full` load 401s with nothing able to refresh it. Ten such 401s
// were logged 2026-08-02 19:36:41-19:36:55 while the operator navigated the
// viewer on a physical Pixel 9 Pro, against a refresh session that was still
// valid. The fix is the renderer the viewer is handed — the viewer itself,
// its `renderImage`/`renderThumb` boundary and the `/share` credentialless
// path are all untouched.
describe("ModelGallery lightbox — access-session expiry recovery", () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let fetchMock: any;
  let revokeSpy: ReturnType<typeof vi.fn>;

  function imageResponse(): Response {
    return new Response(new Blob(["jpeg"], { type: "image/jpeg" }), {
      status: 200,
      headers: { "Content-Type": "image/jpeg" },
    });
  }

  beforeEach(() => {
    fetchMock = vi.spyOn(globalThis, "fetch");
    revokeSpy = vi.fn();
    Object.defineProperty(URL, "createObjectURL", {
      value: vi.fn(() => "blob:recovered/1"),
      configurable: true,
    });
    Object.defineProperty(URL, "revokeObjectURL", { value: revokeSpy, configurable: true });
  });
  afterEach(() => fetchMock.mockRestore());

  async function openViewer(): Promise<HTMLImageElement> {
    render(<ModelGallery modelId={MODEL_ID} files={FILES} />);
    fireEvent.click(screen.getByTestId("gallery-fullscreen-trigger"));
    // The viewer is code-split behind the lazy barrel + <Suspense>.
    const images = await screen.findAllByTestId("authed-image");
    return images[0] as HTMLImageElement; // main frame renders before the strip
  }

  it("recovers the expired full-resolution frame without a reload", async () => {
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "access_expired" }), { status: 401 }))
      .mockResolvedValueOnce(new Response("{}", { status: 200 })) // /api/auth/refresh
      .mockResolvedValueOnce(imageResponse());

    const main = await openViewer();
    const fullUrl = `/api/models/${MODEL_ID}/files/f2/content?variant=full`;
    expect(main.getAttribute("src")).toBe(fullUrl);
    expect(fetchMock).not.toHaveBeenCalled(); // healthy session issues nothing

    fireEvent.error(main);

    await waitFor(() =>
      expect(screen.getAllByTestId("authed-image")[0]?.getAttribute("src")).toBe(
        "blob:recovered/1",
      ),
    );
    const urls = fetchMock.mock.calls.map((c: unknown[]) => String(c[0]));
    expect(urls.filter((u: string) => u === fullUrl)).toHaveLength(2);
    expect(urls.filter((u: string) => u.includes("/api/auth/refresh"))).toHaveLength(1);
    expect(urls.some((u: string) => u.includes("/api/share"))).toBe(false);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.credentials).toBe("include");
  });

  it("closing the viewer mid-session revokes the recovered object URL", async () => {
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "access_expired" }), { status: 401 }))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))
      .mockResolvedValueOnce(imageResponse());

    const main = await openViewer();
    fireEvent.error(main);
    await waitFor(() =>
      expect(screen.getAllByTestId("authed-image")[0]?.getAttribute("src")).toBe(
        "blob:recovered/1",
      ),
    );

    fireEvent.click(screen.getByTestId("image-viewer-close"));
    await waitFor(() => expect(revokeSpy).toHaveBeenCalledWith("blob:recovered/1"));
  });
});
