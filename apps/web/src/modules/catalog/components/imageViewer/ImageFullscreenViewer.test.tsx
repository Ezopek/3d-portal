// Story 22.3 (TB-037 viewer) — vitest coverage for the symmetric fullscreen
// image viewer. We mount the default export DIRECTLY (not via the lazy
// barrel) so each test renders synchronously; the lazy barrel is exercised
// independently by `imageViewer.lazy.test.tsx` (chunk-split shape) +
// Playwright visual baselines (real-browser open-fullscreen flow).

import { act, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import "@/locales/i18n";
import ImageFullscreenViewer from "./ImageFullscreenViewer";
import type { ImageRenderer, ImageSource } from "./types";

const SOURCES: ImageSource[] = [
  { fullUrl: "/api/models/m1/files/a/content?variant=full", thumbUrl: "/api/models/m1/files/a/content?variant=thumb", alt: "alpha" },
  { fullUrl: "/api/models/m1/files/b/content?variant=full", thumbUrl: "/api/models/m1/files/b/content?variant=thumb", alt: "bravo" },
  { fullUrl: "/api/models/m1/files/c/content?variant=full", thumbUrl: "/api/models/m1/files/c/content?variant=thumb", alt: "charlie" },
];

// A plain renderer mirrors what /catalog/* passes; we capture invocations so
// tests can assert which `src` the viewer requested for the main frame vs
// the thumb strip.
function makePlainRenderer(): {
  render: ImageRenderer;
  calls: { src: string; alt: string }[];
} {
  const calls: { src: string; alt: string }[] = [];
  const renderFn: ImageRenderer = ({ src, alt, className }) => {
    calls.push({ src, alt });
    return <img src={src} alt={alt} className={className} data-testid="rendered-img" />;
  };
  return { render: renderFn, calls };
}

describe("ImageFullscreenViewer", () => {
  it("renders the initial image + counter at the requested index", () => {
    const { render: renderImage } = makePlainRenderer();
    render(
      <ImageFullscreenViewer
        sources={SOURCES}
        initialIndex={1}
        onClose={() => {}}
        renderImage={renderImage}
      />,
    );
    // Counter at top-left shows 2/3 (1-based for users, total = sources.length).
    expect(screen.getByTestId("image-viewer-counter").textContent).toBe("2 / 3");
    // Three thumbs in the strip.
    expect(screen.getAllByTestId("image-viewer-thumb")).toHaveLength(3);
    // The main image is the second source's fullUrl (initialIndex=1).
    const mains = screen.getAllByTestId("rendered-img");
    // First call is the main frame (full URL), subsequent are thumbs.
    expect(mains[0]?.getAttribute("src")).toBe(SOURCES[1]!.fullUrl);
  });

  it("ArrowRight + ArrowLeft + chevron click navigate; counter updates", () => {
    const { render: renderImage } = makePlainRenderer();
    render(
      <ImageFullscreenViewer
        sources={SOURCES}
        initialIndex={0}
        onClose={() => {}}
        renderImage={renderImage}
      />,
    );
    expect(screen.getByTestId("image-viewer-counter").textContent).toBe("1 / 3");

    // ArrowRight on the dialog root → counter 2/3.
    fireEvent.keyDown(screen.getByTestId("image-viewer-root"), { key: "ArrowRight" });
    expect(screen.getByTestId("image-viewer-counter").textContent).toBe("2 / 3");

    // ArrowLeft → back to 1/3.
    fireEvent.keyDown(screen.getByTestId("image-viewer-root"), { key: "ArrowLeft" });
    expect(screen.getByTestId("image-viewer-counter").textContent).toBe("1 / 3");

    // Click next chevron → 2/3 again.
    fireEvent.click(screen.getByTestId("image-viewer-next"));
    expect(screen.getByTestId("image-viewer-counter").textContent).toBe("2 / 3");

    // Click prev chevron → 1/3.
    fireEvent.click(screen.getByTestId("image-viewer-prev"));
    expect(screen.getByTestId("image-viewer-counter").textContent).toBe("1 / 3");

    // ArrowLeft at index 0 wraps to last (3/3).
    fireEvent.keyDown(screen.getByTestId("image-viewer-root"), { key: "ArrowLeft" });
    expect(screen.getByTestId("image-viewer-counter").textContent).toBe("3 / 3");
  });

  it("close button calls onClose", () => {
    const onClose = vi.fn();
    const { render: renderImage } = makePlainRenderer();
    render(
      <ImageFullscreenViewer
        sources={SOURCES}
        initialIndex={0}
        onClose={onClose}
        renderImage={renderImage}
      />,
    );
    fireEvent.click(screen.getByTestId("image-viewer-close"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("clicking a thumb switches the active index", () => {
    const { render: renderImage } = makePlainRenderer();
    render(
      <ImageFullscreenViewer
        sources={SOURCES}
        initialIndex={0}
        onClose={() => {}}
        renderImage={renderImage}
      />,
    );
    const thumbs = screen.getAllByTestId("image-viewer-thumb");
    expect(thumbs).toHaveLength(3);
    fireEvent.click(thumbs[2]!);
    expect(screen.getByTestId("image-viewer-counter").textContent).toBe("3 / 3");
  });

  it("hides counter + chevrons when only one source is provided", () => {
    const { render: renderImage } = makePlainRenderer();
    render(
      <ImageFullscreenViewer
        sources={[SOURCES[0]!]}
        initialIndex={0}
        onClose={() => {}}
        renderImage={renderImage}
      />,
    );
    // Counter only renders when total > 1.
    expect(screen.queryByTestId("image-viewer-counter")).toBeNull();
    // Chevrons hidden too.
    expect(screen.queryByTestId("image-viewer-prev")).toBeNull();
    expect(screen.queryByTestId("image-viewer-next")).toBeNull();
    // Close button still present (always visible per designer §4).
    expect(screen.getByTestId("image-viewer-close")).toBeTruthy();
  });
});

// ── Story 53.2 (E53 / FR26-VIEW-1) — mature viewer ─────────────────────────
// AC-7 bullet 1. This block EXTENDS the suite above; the five original `it`
// blocks are untouched.
//
// Scope note, deliberately narrow: jsdom has no layout engine, so every
// `getBoundingClientRect()` is all-zero and `offsetWidth` is 0 unless injected.
// A pan-clamp assertion written naively here would pass trivially and prove
// nothing. The clamp ARITHMETIC is therefore unit-tested against injected
// geometry in `zoom.test.ts`, real pixel geometry is asserted in
// `tests/visual/image-viewer-zoom.spec.ts`, and what follows is what jsdom CAN
// honestly prove: control semantics, accessible names, aria-hidden layering,
// focus, and state transitions.

const ZOOM_CONTROLS = [
  { testid: "image-viewer-zoom-in", label: "Zoom in" },
  { testid: "image-viewer-zoom-out", label: "Zoom out" },
  { testid: "image-viewer-zoom-reset", label: "Fit" },
] as const;

/** Nearest ancestor (inclusive) carrying `aria-hidden="true"`, or null. */
function ariaHiddenAncestor(el: Element | null): Element | null {
  let node: Element | null = el;
  while (node !== null) {
    if (node.getAttribute("aria-hidden") === "true") return node;
    node = node.parentElement;
  }
  return null;
}

/**
 * Mount the viewer and resolve its main image, which is what enables the zoom
 * controls (D-6 — they stay disabled until the image resolves). jsdom never
 * fetches resources, so the `load` event is dispatched explicitly; that
 * exercises the real capture-phase listener rather than working around it.
 * `naturalWidth` / `offsetWidth` are injected because jsdom reports 0 for both.
 */
function resolveActiveImage() {
  // The main frame renders before the thumb strip, so index 0 is the main image.
  const img = screen.getAllByTestId("rendered-img")[0] as HTMLImageElement;
  Object.defineProperty(img, "naturalWidth", { value: 2000, configurable: true });
  Object.defineProperty(img, "offsetWidth", { value: 500, configurable: true });
  fireEvent.load(img);
}

function mountResolvedViewer(sources: readonly ImageSource[] = SOURCES) {
  const { render: renderImage } = makePlainRenderer();
  const view = render(
    <ImageFullscreenViewer
      sources={sources}
      initialIndex={0}
      onClose={() => {}}
      renderImage={renderImage}
    />,
  );
  resolveActiveImage();
  return view;
}

const zoomLevel = () => screen.getByTestId("image-viewer-zoom-level").textContent;
const transform = () => screen.getByTestId("image-viewer-transform").getAttribute("style");

/** A short tap on the viewer root — the shipped tap-to-toggle-chrome gesture. */
function tap(x = 100, y = 100) {
  const root = screen.getByTestId("image-viewer-root");
  fireEvent.touchStart(root, { touches: [{ clientX: x, clientY: y }] });
  fireEvent.touchEnd(root, {
    touches: [],
    changedTouches: [{ clientX: x, clientY: y }],
  });
}

/** A horizontal drag on the viewer root, start -> end, with a move in between. */
function drag(fromX: number, toX: number, y = 200) {
  const root = screen.getByTestId("image-viewer-root");
  fireEvent.touchStart(root, { touches: [{ clientX: fromX, clientY: y }] });
  fireEvent.touchMove(root, { touches: [{ clientX: toX, clientY: y }] });
  fireEvent.touchEnd(root, {
    touches: [],
    changedTouches: [{ clientX: toX, clientY: y }],
  });
}

describe("ImageFullscreenViewer — Story 53.2 zoom toolbar", () => {
  it("renders three zoom controls, each with an accessible name (AC-2)", () => {
    mountResolvedViewer();
    // DESIGN.md:286 — three SEPARATE controls, and EXPERIENCE.md:211's
    // explicit Don't is "icon-only zoom controls with no accessible name".
    for (const { testid, label } of ZOOM_CONTROLS) {
      const control = screen.getByTestId(testid);
      expect(control.tagName).toBe("BUTTON");
      expect(control.getAttribute("aria-label")).toBe(label);
    }
    expect(screen.getByTestId("image-viewer-toolbar")).toBeTruthy();
  });

  it("keeps the zoom controls mounted and NOT aria-hidden while the chrome layer is hidden (AC-2)", () => {
    mountResolvedViewer();
    const toolbar = screen.getByTestId("image-viewer-toolbar");
    const close = screen.getByTestId("image-viewer-close");
    expect(ariaHiddenAncestor(close)).toBeNull();

    // Tap to hide chrome, then zoom in — mockup state C, "the load-bearing
    // state": chrome hidden AND zoomed, with the zoom controls still there.
    tap();
    fireEvent.click(screen.getByTestId("image-viewer-zoom-in"));

    // The chrome layer went aria-hidden...
    expect(ariaHiddenAncestor(close)).not.toBeNull();
    // ...but the toolbar did not, and is a SIBLING of that layer, not a child.
    expect(ariaHiddenAncestor(toolbar)).toBeNull();
    expect(toolbar.contains(close)).toBe(false);
    expect(ariaHiddenAncestor(close)?.contains(toolbar)).toBe(false);
    for (const { testid } of ZOOM_CONTROLS) {
      expect(screen.getByTestId(testid).isConnected).toBe(true);
    }
  });

  it("keeps the toolbar OUTSIDE the transform layer (AC-1)", () => {
    mountResolvedViewer();
    const layer = screen.getByTestId("image-viewer-transform");
    expect(layer.contains(screen.getByTestId("image-viewer-toolbar"))).toBe(false);
    expect(layer.contains(screen.getByTestId("image-viewer-close"))).toBe(false);
    // Only the renderer's own output lives inside it.
    expect(layer.querySelector('[data-testid="rendered-img"]')).not.toBeNull();

    fireEvent.click(screen.getByTestId("image-viewer-zoom-in"));
    // The transform moved; the toolbar and close carry no transform of their own.
    expect(transform()).toContain("scale(1.5)");
    expect(screen.getByTestId("image-viewer-toolbar").getAttribute("style")).toBeNull();
    expect(screen.getByTestId("image-viewer-close").getAttribute("style")).toBeNull();
  });

  it("gives the close control a >= 44x44 target (AC-4)", () => {
    mountResolvedViewer();
    const close = screen.getByTestId("image-viewer-close");
    // jsdom has no layout, so the real pixel measurement lives in
    // `tests/visual/image-viewer-zoom.spec.ts`. What is checkable here is the
    // Tailwind size class: `h-11 w-11` == 2.75rem == 44px ==
    // `{spacing.target-fullscreen-close}`, up from the shipped `h-10 w-10`.
    expect(close.className).toContain("h-11");
    expect(close.className).toContain("w-11");
    expect(close.className).not.toContain("h-10");
  });

  it("preserves every shipped a11y property (AC-4)", () => {
    mountResolvedViewer();
    // sr-only i18n DialogTitle.
    const title = document.querySelector(".sr-only");
    expect(title?.textContent).toBe("Photo gallery");
    expect(screen.getByTestId("image-viewer-close").getAttribute("aria-label")).toBe("Close");
    expect(screen.getByTestId("image-viewer-prev").getAttribute("aria-label")).toBe(
      "Previous photo",
    );
    expect(screen.getByTestId("image-viewer-next").getAttribute("aria-label")).toBe(
      "Next photo",
    );
    const thumbs = screen.getAllByTestId("image-viewer-thumb");
    expect(thumbs[0]?.getAttribute("aria-current")).toBe("true");
    expect(thumbs[1]?.getAttribute("aria-current")).toBeNull();
    expect(thumbs[0]?.getAttribute("aria-label")).toBe("Photo 1");
    // The strip follows chromeVisible; the toolbar never does.
    expect(screen.getByTestId("image-viewer-strip").getAttribute("aria-hidden")).toBe("false");
    tap();
    expect(screen.getByTestId("image-viewer-strip").getAttribute("aria-hidden")).toBe("true");
    expect(ariaHiddenAncestor(screen.getByTestId("image-viewer-toolbar"))).toBeNull();
  });

  it("traps focus inside the dialog while open (AC-7)", async () => {
    mountResolvedViewer();
    // Base UI moves focus into the popup asynchronously via its focus manager.
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 30));
    });
    const dialog = document.querySelector('[role="dialog"]');
    expect(dialog).not.toBeNull();
    expect(document.activeElement).not.toBe(document.body);
    expect(dialog?.contains(document.activeElement)).toBe(true);
  });

  it("returns focus to the gallery trigger on close (AC-7 / V-17)", async () => {
    function Harness() {
      const [open, setOpen] = useState(false);
      const { render: renderImage } = makePlainRenderer();
      return (
        <>
          <button
            type="button"
            data-testid="gallery-fullscreen-trigger"
            onClick={() => setOpen(true)}
          >
            open
          </button>
          {open ? (
            <ImageFullscreenViewer
              sources={SOURCES}
              initialIndex={0}
              onClose={() => setOpen(false)}
              renderImage={renderImage}
            />
          ) : null}
        </>
      );
    }
    render(<Harness />);
    const trigger = screen.getByTestId("gallery-fullscreen-trigger");
    trigger.focus();
    fireEvent.click(trigger);
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 30));
    });
    expect(document.activeElement).not.toBe(trigger);

    fireEvent.click(screen.getByTestId("image-viewer-close"));
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 30));
    });
    expect(screen.queryByTestId("image-viewer-root")).toBeNull();
    expect(document.activeElement).toBe(trigger);
  });

  it("makes +, - and 0 produce exactly the same state as the three buttons (AC-2)", () => {
    // Button path.
    const byButton = mountResolvedViewer();
    fireEvent.click(screen.getByTestId("image-viewer-zoom-in"));
    fireEvent.click(screen.getByTestId("image-viewer-zoom-in"));
    const zoomedByButton = { level: zoomLevel(), style: transform() };
    fireEvent.click(screen.getByTestId("image-viewer-zoom-out"));
    const steppedBackByButton = { level: zoomLevel(), style: transform() };
    fireEvent.click(screen.getByTestId("image-viewer-zoom-reset"));
    const resetByButton = { level: zoomLevel(), style: transform() };
    byButton.unmount();

    // Keyboard path, from a fresh mount.
    mountResolvedViewer();
    const root = () => screen.getByTestId("image-viewer-root");
    fireEvent.keyDown(root(), { key: "+" });
    fireEvent.keyDown(root(), { key: "+" });
    expect({ level: zoomLevel(), style: transform() }).toEqual(zoomedByButton);
    fireEvent.keyDown(root(), { key: "-" });
    expect({ level: zoomLevel(), style: transform() }).toEqual(steppedBackByButton);
    fireEvent.keyDown(root(), { key: "0" });
    expect({ level: zoomLevel(), style: transform() }).toEqual(resetByButton);

    // ...and the states are genuinely distinct, so the equality above is not
    // an artefact of nothing ever changing.
    expect(zoomedByButton.level).not.toBe(resetByButton.level);
    expect(zoomedByButton.style).not.toBe(resetByButton.style);
  });

  it("announces the zoom level politely and disables the right controls (AC-5, D-6, D-7)", () => {
    const { render: renderImage } = makePlainRenderer();
    render(
      <ImageFullscreenViewer
        sources={SOURCES}
        initialIndex={0}
        onClose={() => {}}
        renderImage={renderImage}
      />,
    );
    const region = screen.getByTestId("image-viewer-zoom-level");
    expect(region.getAttribute("aria-live")).toBe("polite");

    // Before the image resolves: all three controls disabled, and the disabled
    // state is ANNOUNCED via the live region rather than only dimmed — this is
    // also what finally wires the previously orphaned `loading` key (V-4).
    for (const { testid } of ZOOM_CONTROLS) {
      expect((screen.getByTestId(testid) as HTMLButtonElement).disabled).toBe(true);
    }
    expect(region.textContent).toBe("Loading full image…");

    const img = screen.getAllByTestId("rendered-img")[0] as HTMLImageElement;
    Object.defineProperty(img, "naturalWidth", { value: 2000, configurable: true });
    Object.defineProperty(img, "offsetWidth", { value: 500, configurable: true });
    fireEvent.load(img);

    // At rest: Zoom In live, Zoom Out and Reset disabled (mockup state A).
    expect((screen.getByTestId("image-viewer-zoom-in") as HTMLButtonElement).disabled).toBe(
      false,
    );
    expect((screen.getByTestId("image-viewer-zoom-out") as HTMLButtonElement).disabled).toBe(
      true,
    );
    expect((screen.getByTestId("image-viewer-zoom-reset") as HTMLButtonElement).disabled).toBe(
      true,
    );
    // An image resolving at 1.0 is NOT a zoom level change, so the region goes
    // quiet rather than announcing an unasked-for "Zoom 100%" (D-7 /
    // `EXPERIENCE.md:318` — zoom level *changes* announce).
    expect(region.textContent).toBe("");

    fireEvent.click(screen.getByTestId("image-viewer-zoom-in"));
    expect(region.textContent).toBe("Zoom 150%");
    expect((screen.getByTestId("image-viewer-zoom-out") as HTMLButtonElement).disabled).toBe(
      false,
    );
  });

  it("keeps close and toolbar reachable when the image fails (D-6)", () => {
    const { render: renderImage } = makePlainRenderer();
    render(
      <ImageFullscreenViewer
        sources={SOURCES}
        initialIndex={0}
        onClose={() => {}}
        renderImage={renderImage}
      />,
    );
    fireEvent.error(screen.getAllByTestId("rendered-img")[0] as HTMLImageElement);
    // A failed image never traps the user.
    expect((screen.getByTestId("image-viewer-close") as HTMLButtonElement).disabled).toBe(false);
    expect(screen.getByTestId("image-viewer-toolbar").isConnected).toBe(true);
    expect(ariaHiddenAncestor(screen.getByTestId("image-viewer-toolbar"))).toBeNull();
    // Nothing to zoom, so the zoom controls are inert rather than lying.
    for (const { testid } of ZOOM_CONTROLS) {
      expect((screen.getByTestId(testid) as HTMLButtonElement).disabled).toBe(true);
    }
  });

  it("navigates on a horizontal drag at scale 1.0 but pans and never navigates when zoomed (AC-3)", () => {
    mountResolvedViewer();
    expect(screen.getByTestId("image-viewer-counter").textContent).toBe("1 / 3");

    // Scale 1.0 — unchanged shipped behaviour: a 90px leftward drag navigates
    // (SWIPE_THRESHOLD_PX = 50, SWIPE_VERTICAL_TOLERANCE_PX = 60 both intact).
    drag(300, 210);
    expect(screen.getByTestId("image-viewer-counter").textContent).toBe("2 / 3");
    expect(transform()).toContain("translate3d(0px, 0px, 0)");

    // Navigation reset the zoom AND re-armed the pending state for the newly
    // active image, so resolve it before zooming (D-6).
    resolveActiveImage();
    // Zoom in, then repeat exactly the same drag.
    fireEvent.click(screen.getByTestId("image-viewer-zoom-in"));
    const counterBefore = screen.getByTestId("image-viewer-counter").textContent;
    drag(300, 210);
    // It PANNED...
    expect(transform()).toContain("translate3d(-90px, 0px, 0)");
    // ...and it did NOT navigate.
    expect(screen.getByTestId("image-viewer-counter").textContent).toBe(counterBefore);

    // Reset returns to 1.0, re-arms swipe navigation and drops the pan.
    fireEvent.click(screen.getByTestId("image-viewer-zoom-reset"));
    expect(transform()).toContain("scale(1)");
    expect(transform()).toContain("translate3d(0px, 0px, 0)");
    drag(300, 210);
    expect(screen.getByTestId("image-viewer-counter").textContent).toBe("3 / 3");
  });

  it("scales on a two-finger pinch and never navigates from it (AC-1, AC-3)", () => {
    mountResolvedViewer();
    const root = screen.getByTestId("image-viewer-root");
    expect(transform()).toContain("scale(1)");
    const counterBefore = screen.getByTestId("image-viewer-counter").textContent;

    // Two fingers 100px apart, spread to 300px => 3x the separation => 3x scale.
    const a = { clientX: 150, clientY: 300 };
    const b = { clientX: 250, clientY: 300 };
    fireEvent.touchStart(root, { touches: [a] });
    fireEvent.touchStart(root, { touches: [a, b] });
    fireEvent.touchMove(root, {
      touches: [
        { clientX: 50, clientY: 300 },
        { clientX: 350, clientY: 300 },
      ],
    });
    expect(transform()).toContain("scale(3)");

    // Releasing a pinch must not be read as a swipe, even though the first
    // finger travelled 100px horizontally — well past SWIPE_THRESHOLD_PX.
    fireEvent.touchEnd(root, { touches: [], changedTouches: [{ clientX: 50, clientY: 300 }] });
    expect(screen.getByTestId("image-viewer-counter").textContent).toBe(counterBefore);
    expect(transform()).toContain("scale(3)");

    // Reset brings it back and re-arms navigation.
    fireEvent.click(screen.getByTestId("image-viewer-zoom-reset"));
    expect(transform()).toContain("scale(1)");
  });

  it("clamps a pinch to the resolved max scale (AC-1 / D-4)", () => {
    mountResolvedViewer();
    const root = screen.getByTestId("image-viewer-root");
    // naturalWidth 2000 / offsetWidth 500 = 4, so resolveMaxScale = max(4, 4) = 4.
    const a = { clientX: 150, clientY: 300 };
    const b = { clientX: 250, clientY: 300 };
    fireEvent.touchStart(root, { touches: [a] });
    fireEvent.touchStart(root, { touches: [a, b] });
    // Spread 100px -> 1000px would be 10x; the clamp must hold it at 4x.
    fireEvent.touchMove(root, {
      touches: [
        { clientX: -300, clientY: 300 },
        { clientX: 700, clientY: 300 },
      ],
    });
    expect(transform()).toContain("scale(4)");
    fireEvent.touchEnd(root, { touches: [], changedTouches: [{ clientX: -300, clientY: 300 }] });
  });

  it("never navigates from a two-finger gesture on a still-loading image (AC-3)", () => {
    // Regression guard: the pinch snapshot is skipped while the image is
    // unresolved, but the gesture must STILL be disqualified from the tap and
    // swipe paths — otherwise a pinch on a slow-loading photo would navigate.
    const { render: renderImage } = makePlainRenderer();
    render(
      <ImageFullscreenViewer
        sources={SOURCES}
        initialIndex={0}
        onClose={() => {}}
        renderImage={renderImage}
      />,
    );
    const root = screen.getByTestId("image-viewer-root");
    expect(screen.getByTestId("image-viewer-counter").textContent).toBe("1 / 3");
    const a = { clientX: 300, clientY: 300 };
    const b = { clientX: 340, clientY: 300 };
    fireEvent.touchStart(root, { touches: [a] });
    fireEvent.touchStart(root, { touches: [a, b] });
    fireEvent.touchEnd(root, { touches: [], changedTouches: [{ clientX: 180, clientY: 300 }] });
    expect(screen.getByTestId("image-viewer-counter").textContent).toBe("1 / 3");
  });

  it("keeps panning continuously when a pinch drops to one finger (AC-1)", () => {
    mountResolvedViewer();
    const root = screen.getByTestId("image-viewer-root");
    const a = { clientX: 150, clientY: 300 };
    const b = { clientX: 250, clientY: 300 };
    fireEvent.touchStart(root, { touches: [a] });
    fireEvent.touchStart(root, { touches: [a, b] });
    fireEvent.touchMove(root, {
      touches: [
        { clientX: 100, clientY: 300 },
        { clientX: 300, clientY: 300 },
      ],
    });
    expect(transform()).toContain("scale(2)");
    const afterPinch = transform();

    // Lift the second finger; the first stays down at x=100.
    fireEvent.touchEnd(root, {
      touches: [{ clientX: 100, clientY: 300 }],
      changedTouches: [{ clientX: 300, clientY: 300 }],
    });
    // The transform must not jump on the finger lift itself.
    expect(transform()).toBe(afterPinch);

    // Continue dragging 40px right: the pan moves by exactly 40 from where the
    // pinch left it, rather than snapping back to the pre-pinch baseline.
    const panAfterPinch = Number(
      /translate3d\((-?[\d.]+)px/.exec(afterPinch ?? "")?.[1] ?? "NaN",
    );
    expect(Number.isNaN(panAfterPinch)).toBe(false);
    fireEvent.touchMove(root, { touches: [{ clientX: 140, clientY: 300 }] });
    expect(transform()).toContain(`translate3d(${panAfterPinch + 40}px,`);
    fireEvent.touchEnd(root, { touches: [], changedTouches: [{ clientX: 140, clientY: 300 }] });
  });

  it("does not toggle chrome or navigate on a toolbar-origin touch (AC-3 / D-2)", () => {
    mountResolvedViewer();
    const strip = screen.getByTestId("image-viewer-strip");
    expect(strip.getAttribute("aria-hidden")).toBe("false");

    // A touch that starts on the toolbar is a third origin case alongside
    // stripOrigin / thumbOrigin: the button's own onClick owns it.
    const zoomIn = screen.getByTestId("image-viewer-zoom-in");
    fireEvent.touchStart(zoomIn, { touches: [{ clientX: 200, clientY: 600 }] });
    fireEvent.touchEnd(zoomIn, {
      touches: [],
      changedTouches: [{ clientX: 200, clientY: 600 }],
    });
    expect(strip.getAttribute("aria-hidden")).toBe("false");
    expect(screen.getByTestId("image-viewer-counter").textContent).toBe("1 / 3");

    // A long horizontal drag that STARTS on the toolbar must not navigate either.
    fireEvent.touchStart(zoomIn, { touches: [{ clientX: 300, clientY: 600 }] });
    fireEvent.touchEnd(zoomIn, {
      touches: [],
      changedTouches: [{ clientX: 180, clientY: 600 }],
    });
    expect(screen.getByTestId("image-viewer-counter").textContent).toBe("1 / 3");
    expect(strip.getAttribute("aria-hidden")).toBe("false");
  });

  it("resets zoom when the active image changes (AC-1)", () => {
    mountResolvedViewer();
    fireEvent.click(screen.getByTestId("image-viewer-zoom-in"));
    expect(transform()).toContain("scale(1.5)");
    fireEvent.click(screen.getByTestId("image-viewer-next"));
    expect(screen.getByTestId("image-viewer-counter").textContent).toBe("2 / 3");
    expect(transform()).toContain("scale(1)");
    expect(transform()).toContain("translate3d(0px, 0px, 0)");
    // ...and the new image has not resolved yet, so the toolbar is disabled again.
    expect((screen.getByTestId("image-viewer-zoom-in") as HTMLButtonElement).disabled).toBe(
      true,
    );
  });

  // ── Code-review repairs (native `bmad-code-review`, 2026-07-29) ───────────

  it("leaves Ctrl / Cmd / Alt modified +, - and 0 to the browser (AC-2)", () => {
    mountResolvedViewer();
    const root = () => screen.getByTestId("image-viewer-root");
    // `fireEvent` returns false when the handler called `preventDefault()`.
    // Cancelling these would take page zoom away from exactly the low-vision
    // user this story exists for (WCAG 1.4.4).
    expect(fireEvent.keyDown(root(), { key: "+", ctrlKey: true })).toBe(true);
    expect(fireEvent.keyDown(root(), { key: "-", metaKey: true })).toBe(true);
    expect(fireEvent.keyDown(root(), { key: "0", altKey: true })).toBe(true);
    expect(transform()).toContain("scale(1)");

    // ...and the unmodified keys still act, so the guard is not just muting them.
    expect(fireEvent.keyDown(root(), { key: "+" })).toBe(false);
    expect(transform()).toContain("scale(1.5)");
  });

  it("announces zoom level CHANGES only, not every image that resolves (D-7)", () => {
    mountResolvedViewer();
    const region = () => screen.getByTestId("image-viewer-zoom-level");
    // `EXPERIENCE.md:318` announces zoom level *changes*. An image resolving at
    // 1.0 is not one, and announcing it would put one "Zoom 100%" between every
    // pair of arrow-key navigations for a screen-reader user.
    expect(region().textContent).toBe("");

    fireEvent.click(screen.getByTestId("image-viewer-zoom-in"));
    expect(region().textContent).toBe("Zoom 150%");

    fireEvent.click(screen.getByTestId("image-viewer-next"));
    expect(region().textContent).toBe("Loading full image…");
    resolveActiveImage();
    expect(region().textContent).toBe("");
  });

  it("keeps pinching when a resting third finger lifts (AC-1)", () => {
    mountResolvedViewer();
    const root = screen.getByTestId("image-viewer-root");
    const a = { clientX: 150, clientY: 300 };
    const b = { clientX: 250, clientY: 300 };
    fireEvent.touchStart(root, { touches: [a] });
    fireEvent.touchStart(root, { touches: [a, b] });
    fireEvent.touchStart(root, { touches: [a, b, { clientX: 400, clientY: 500 }] });

    // Lift the third finger — two fingers are still pinching. `onTouchStart`
    // will not fire again, so tearing the pinch down here would convert the
    // rest of the gesture into a single-pointer pan.
    fireEvent.touchEnd(root, {
      touches: [a, b],
      changedTouches: [{ clientX: 400, clientY: 500 }],
    });
    fireEvent.touchMove(root, {
      touches: [
        { clientX: 100, clientY: 300 },
        { clientX: 300, clientY: 300 },
      ],
    });
    expect(transform()).toContain("scale(2)");
    fireEvent.touchEnd(root, { touches: [], changedTouches: [{ clientX: 100, clientY: 300 }] });
  });

  it("pans after a pinch that opened with two coalesced fingers (AC-1)", () => {
    mountResolvedViewer();
    const root = screen.getByTestId("image-viewer-root");
    // Both fingers land in ONE touchstart, so no single-finger start ever ran
    // and there is no drag origin unless the release synthesises one.
    fireEvent.touchStart(root, {
      touches: [
        { clientX: 150, clientY: 300 },
        { clientX: 250, clientY: 300 },
      ],
    });
    fireEvent.touchMove(root, {
      touches: [
        { clientX: 100, clientY: 300 },
        { clientX: 300, clientY: 300 },
      ],
    });
    expect(transform()).toContain("scale(2)");
    const afterPinch = transform();
    const panAfterPinch = Number(
      /translate3d\((-?[\d.]+)px/.exec(afterPinch ?? "")?.[1] ?? "NaN",
    );
    expect(Number.isNaN(panAfterPinch)).toBe(false);

    fireEvent.touchEnd(root, {
      touches: [{ clientX: 100, clientY: 300 }],
      changedTouches: [{ clientX: 300, clientY: 300 }],
    });
    fireEvent.touchMove(root, { touches: [{ clientX: 140, clientY: 300 }] });
    expect(transform()).toContain(`translate3d(${panAfterPinch + 40}px,`);
    fireEvent.touchEnd(root, { touches: [], changedTouches: [{ clientX: 140, clientY: 300 }] });
  });

  it("does not let a swallowed toolbar tap complete a double-tap (D-3)", () => {
    mountResolvedViewer();
    const root = screen.getByTestId("image-viewer-root");
    const zoomInBtn = screen.getByTestId("image-viewer-zoom-in");
    const at = (x: number, y: number) => ({ clientX: x, clientY: y });

    // Tap 1 on the image arms the double-tap window.
    fireEvent.touchStart(root, { touches: [at(100, 100)] });
    fireEvent.touchEnd(root, { touches: [], changedTouches: [at(100, 100)] });
    // A tap on the toolbar is swallowed by the button's own onClick — and it
    // must BREAK the pending pair, not sit transparently between its halves.
    fireEvent.touchStart(zoomInBtn, { touches: [at(200, 600)] });
    fireEvent.touchEnd(zoomInBtn, { touches: [], changedTouches: [at(200, 600)] });
    // Tap 2 on the image, inside the window and slop of tap 1.
    fireEvent.touchStart(root, { touches: [at(100, 100)] });
    fireEvent.touchEnd(root, { touches: [], changedTouches: [at(100, 100)] });

    // Read as two independent taps, so no zoom was applied or thrown away.
    expect(transform()).toContain("scale(1)");
  });

  it("treats an already-failed cached image as an error, not as ready (D-6)", () => {
    // `complete` is true for an image that already FAILED, and its `error` event
    // fired before the viewer's listener existed — so `complete` alone would arm
    // the zoom controls over a broken image.
    const renderBroken: ImageRenderer = ({ src, alt, className }) => (
      <img
        src={src}
        alt={alt}
        className={className}
        data-testid="rendered-img"
        ref={(node) => {
          if (node === null) return;
          Object.defineProperty(node, "complete", { value: true, configurable: true });
          Object.defineProperty(node, "naturalWidth", { value: 0, configurable: true });
        }}
      />
    );
    render(
      <ImageFullscreenViewer
        sources={SOURCES}
        initialIndex={0}
        onClose={() => {}}
        renderImage={renderBroken}
      />,
    );
    for (const { testid } of ZOOM_CONTROLS) {
      expect((screen.getByTestId(testid) as HTMLButtonElement).disabled).toBe(true);
    }
    expect((screen.getByTestId("image-viewer-close") as HTMLButtonElement).disabled).toBe(false);
  });

  it("keeps the measured zoom ceiling when a resize cannot measure the image (D-4)", () => {
    const { render: renderImage } = makePlainRenderer();
    render(
      <ImageFullscreenViewer
        sources={SOURCES}
        initialIndex={0}
        onClose={() => {}}
        renderImage={renderImage}
      />,
    );
    const img = screen.getAllByTestId("rendered-img")[0] as HTMLImageElement;
    // A panorama: 10000 natural px laid out at 500 CSS px => a 20x ceiling.
    Object.defineProperty(img, "naturalWidth", { value: 10000, configurable: true });
    Object.defineProperty(img, "offsetWidth", { value: 500, configurable: true });
    fireEvent.load(img);
    for (let i = 0; i < 4; i += 1) {
      fireEvent.click(screen.getByTestId("image-viewer-zoom-in"));
    }
    expect(transform()).toContain("scale(5.0625)");

    // The renderer swaps in a placeholder mid-rotation, so the image is briefly
    // unmeasurable. "Unmeasurable" must not be read as "the 4x default" — that
    // would demote the ceiling AND drag the user's zoom down with it.
    Object.defineProperty(img, "offsetWidth", { value: 0, configurable: true });
    fireEvent(window, new Event("resize"));
    expect(transform()).toContain("scale(5.0625)");
  });

  it("drops a gesture that was in flight when the active image changed (AC-1)", () => {
    mountResolvedViewer();
    const root = screen.getByTestId("image-viewer-root");
    const a = { clientX: 150, clientY: 300 };
    const b = { clientX: 250, clientY: 300 };
    fireEvent.touchStart(root, { touches: [a] });
    fireEvent.touchStart(root, { touches: [a, b] });
    fireEvent.touchMove(root, {
      touches: [
        { clientX: 100, clientY: 300 },
        { clientX: 300, clientY: 300 },
      ],
    });
    expect(transform()).toContain("scale(2)");

    fireEvent.click(screen.getByTestId("image-viewer-next"));
    expect(transform()).toContain("scale(1)");
    // The pinch snapshot is ABSOLUTE (finger separation -> scale), so leaving it
    // armed would re-apply the previous photo's zoom to the new, still-loading
    // one — with all three controls disabled and no way back.
    fireEvent.touchMove(root, {
      touches: [
        { clientX: 50, clientY: 300 },
        { clientX: 350, clientY: 300 },
      ],
    });
    expect(transform()).toContain("scale(1)");
    fireEvent.touchEnd(root, { touches: [], changedTouches: [{ clientX: 50, clientY: 300 }] });
  });

  it("locks body scroll on open and restores it on close, without adding a second lock (AC-6)", async () => {
    // AC-6's stated pre-check: the lock would silently no-op if <html> were
    // already overflow-hidden/clip, so prove that is not our starting state.
    const initialOverflowY = getComputedStyle(document.documentElement).overflowY;
    expect(["hidden", "clip"]).not.toContain(initialOverflowY);
    const htmlStyleBefore = document.documentElement.getAttribute("style");
    const bodyStyleBefore = document.body.getAttribute("style");

    const view = mountResolvedViewer();
    // Base UI applies the lock from its own effect after the popup mounts, so
    // let that settle before reading.
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 30));
    });
    // The lock is Base UI's `Dialog.Root modal` default (V-2) — this file adds
    // no lock of its own, which is exactly what AC-6 asks to be proven.
    //
    // ELEMENT-AGNOSTIC on purpose. V-2 warns the lock lands on <html> OR <body>
    // depending on the overflow element and the platform's scrollbar mode, and
    // measurement confirms the two environments genuinely differ: jsdom sets
    // both, while real Chromium locks <body> alone and leaves <html> untouched
    // (see `tests/visual/image-viewer-zoom.spec.ts`). Pinning a specific
    // element here would encode a jsdom artefact as a product contract.
    const lockedOverflow = [
      document.documentElement.style.overflowY,
      document.documentElement.style.overflow,
      document.body.style.overflowY,
      document.body.style.overflow,
    ];
    expect(lockedOverflow).toContain("hidden");

    view.unmount();
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 30));
    });
    // Restored EXACTLY, inline styles included — not merely "not hidden".
    expect(document.documentElement.getAttribute("style")).toBe(htmlStyleBefore);
    expect(document.body.getAttribute("style")).toBe(bodyStyleBefore);
    expect(getComputedStyle(document.documentElement).overflowY).toBe(initialOverflowY);
  });
});
