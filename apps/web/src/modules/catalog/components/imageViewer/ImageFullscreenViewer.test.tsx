// Story 22.3 (TB-037 viewer) — vitest coverage for the symmetric fullscreen
// image viewer. We mount the default export DIRECTLY (not via the lazy
// barrel) so each test renders synchronously; the lazy barrel is exercised
// independently by `imageViewer.lazy.test.tsx` (chunk-split shape) +
// Playwright visual baselines (real-browser open-fullscreen flow).

import { act, createEvent, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

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

// ── Story 53.3 (E53 / FR26-VIEW-1, NFR26-A11Y-1) ───────────────────────────
// AC-3 (listener wiring only), AC-5, AC-6, AC-8. This block EXTENDS the two
// above; nothing already shipped is rewritten.
//
// The division of labour is unchanged and deliberate. jsdom has no layout
// engine, so every rect is all-zero: rotation GEOMETRY, clamp geometry, the
// 44x44 floor and the real focus contract all live in Playwright
// (`tests/visual/image-viewer-*.spec.ts`). What lives here is what only jsdom
// can do cheaply and honestly — state transitions, ARIA, event wiring, and
// timing driven by fake timers.

// Restated, NOT imported. A boundary test that imports the constant it pins
// would silently follow any change to it. These are the shipped values at
// `ImageFullscreenViewer.tsx` (`DOUBLE_TAP_WINDOW_MS`, `DOUBLE_TAP_SLOP_PX`,
// `IMAGE_READY_TIMEOUT_MS`); Story 53.3 PINS them and does not tune them.
const DOUBLE_TAP_WINDOW_MS = 300;
const DOUBLE_TAP_SLOP_PX = 44;
const IMAGE_READY_TIMEOUT_MS = 15_000;

/**
 * Story 53.3 D-9 — the double-tap window and slop both compare `e.timeStamp`,
 * and `fireEvent` cannot set it. Solved ONCE for the whole boundary matrix
 * rather than per test, which is exactly what `deferred-work.md` asked for.
 *
 * D-9 sketched `new Touch({...})` + `new TouchEvent(...)`, which is the right
 * idiom in Chromium (and is what the Playwright specs use). Probed this run:
 * jsdom ships `TouchEvent` but NOT the `Touch` constructor, so that literal
 * shape throws here. The DOM-testing-library event factory produces exactly
 * the plain-object touch list every other test in this file already
 * dispatches, and `timeStamp` — an own property shadowing
 * `Event.prototype`'s getter — is the only thing that needs overriding.
 */
function touchEndAt(el: Element, at: number, x: number, y: number) {
  const ev = createEvent.touchEnd(el, {
    touches: [],
    targetTouches: [],
    changedTouches: [{ clientX: x, clientY: y }],
  });
  Object.defineProperty(ev, "timeStamp", { value: at, configurable: true });
  fireEvent(el, ev);
}

/** One complete tap at a controlled timestamp. Press and release share the
 *  point, so it is never a drag and never a swipe. */
function tapAt(el: Element, at: number, x: number, y: number) {
  fireEvent.touchStart(el, { touches: [{ clientX: x, clientY: y }] });
  touchEndAt(el, at, x, y);
}

describe("ImageFullscreenViewer — Story 53.3 double-tap boundaries (AC-5, D-9)", () => {
  // Arbitrary epoch for the synthetic timestamps; only the DIFFERENCE matters.
  const T0 = 10_000;

  it("reads two taps ON the window boundary as a double-tap", () => {
    mountResolvedViewer();
    const root = screen.getByTestId("image-viewer-root");
    tapAt(root, T0, 100, 100);
    tapAt(root, T0 + DOUBLE_TAP_WINDOW_MS, 100, 100);
    // `doubleTapTarget` = ZOOM_STEP^2 = 2.25, i.e. two Zoom In presses.
    expect(transform()).toContain("scale(2.25)");
  });

  it("reads two taps ONE MILLISECOND past the window as two single taps", () => {
    mountResolvedViewer();
    const root = screen.getByTestId("image-viewer-root");
    tapAt(root, T0, 100, 100);
    tapAt(root, T0 + DOUBLE_TAP_WINDOW_MS + 1, 100, 100);
    // A regression that inverted or widened the comparison would zoom here.
    expect(transform()).toContain("scale(1)");
  });

  it("reads two taps ON the slop boundary as a double-tap", () => {
    mountResolvedViewer();
    const root = screen.getByTestId("image-viewer-root");
    tapAt(root, T0, 100, 100);
    tapAt(root, T0 + 50, 100 + DOUBLE_TAP_SLOP_PX, 100);
    expect(transform()).toContain("scale(2.25)");
  });

  it("reads two taps ONE PIXEL past the slop as two single taps", () => {
    mountResolvedViewer();
    const root = screen.getByTestId("image-viewer-root");
    tapAt(root, T0, 100, 100);
    tapAt(root, T0 + 50, 100 + DOUBLE_TAP_SLOP_PX + 1, 100);
    // A regression that dropped the slop check entirely would zoom here.
    expect(transform()).toContain("scale(1)");
  });
});

describe("ImageFullscreenViewer — Story 53.3 gesture arbitration + rotation wiring", () => {
  // `vitest.config.ts` sets no `restoreMocks`, and both spies below outlive
  // the assertion that can throw: `injectStripGeometry` never restores its
  // `getBoundingClientRect` spy at all, and the `addEventListener` spy is
  // restored AFTER an `expect` that may throw first. A red test would then
  // leave `window.addEventListener` wrapped for every later test in the file,
  // turning one failure into a cascade. This bounds both to their own test.
  afterEach(() => {
    vi.restoreAllMocks();
  });

  /** jsdom reports an all-zero rect for every element, so the coords-based
   *  `stripOrigin` guard (`ImageFullscreenViewer.tsx` `onTouchStart`) is
   *  unreachable without injecting the strip's geometry. Injected the same way
   *  `naturalWidth` / `offsetWidth` already are — never faked past the guard
   *  itself. */
  function injectStripGeometry(top = 400, bottom = 480): HTMLElement {
    const strip = screen.getByTestId("image-viewer-strip");
    vi.spyOn(strip, "getBoundingClientRect").mockReturnValue({
      top,
      bottom,
      left: 0,
      right: 400,
      width: 400,
      height: bottom - top,
      x: 0,
      y: top,
      toJSON: () => ({}),
    } as DOMRect);
    return strip;
  }

  it("keeps TB-043's four-cell strip matrix behaviourally identical at scale 1.0 (AC-5)", () => {
    mountResolvedViewer();
    const root = screen.getByTestId("image-viewer-root");
    const strip = injectStripGeometry();
    const chromeVisible = () => strip.getAttribute("aria-hidden") === "false";
    const counter = () => screen.getByTestId("image-viewer-counter").textContent;
    expect(chromeVisible()).toBe(true);
    expect(counter()).toBe("1 / 3");

    // Cell 1 — strip VISIBLE, TAP on a thumb. `thumbOrigin` defers the chrome
    // flip to the thumb's own onClick, so the touch itself must change nothing.
    const thumb = screen.getAllByTestId("image-viewer-thumb")[1] as HTMLElement;
    fireEvent.touchStart(thumb, { touches: [{ clientX: 120, clientY: 440 }] });
    fireEvent.touchEnd(thumb, { touches: [], changedTouches: [{ clientX: 120, clientY: 440 }] });
    expect(chromeVisible()).toBe(true);
    expect(counter()).toBe("1 / 3");

    // Cell 2 — strip VISIBLE, long horizontal DRAG originating in the strip.
    // That is the strip being scrolled, never a navigation.
    fireEvent.touchStart(root, { touches: [{ clientX: 300, clientY: 440 }] });
    fireEvent.touchEnd(root, { touches: [], changedTouches: [{ clientX: 180, clientY: 440 }] });
    expect(counter()).toBe("1 / 3");
    expect(chromeVisible()).toBe(true);

    // Hide the chrome with a tap on the image, so the two hidden-strip cells
    // start from the state they are about.
    tap();
    expect(chromeVisible()).toBe(false);

    // Cell 3 — strip HIDDEN, TAP inside the strip's bounds. The strip is
    // `pointer-events-none`, so the touch passes through to the viewer root and
    // must RESTORE the chrome rather than hitting the dead zone TB-043 closed.
    fireEvent.touchStart(root, { touches: [{ clientX: 120, clientY: 440 }] });
    fireEvent.touchEnd(root, { touches: [], changedTouches: [{ clientX: 120, clientY: 440 }] });
    expect(chromeVisible()).toBe(true);
    expect(counter()).toBe("1 / 3");

    // Cell 4 — strip HIDDEN, long horizontal DRAG inside the strip's bounds.
    tap();
    expect(chromeVisible()).toBe(false);
    fireEvent.touchStart(root, { touches: [{ clientX: 300, clientY: 440 }] });
    fireEvent.touchEnd(root, { touches: [], changedTouches: [{ clientX: 180, clientY: 440 }] });
    expect(counter()).toBe("1 / 3");
  });

  it("refits through the orientationchange listener and keeps the zoom level (AC-3)", () => {
    const addSpy = vi.spyOn(window, "addEventListener");
    mountResolvedViewer();
    // The viewer registers BOTH `resize` and `orientationchange`. Playwright's
    // `page.setViewportSize` fires only the former (V-5), so this second
    // registration is reachable from nowhere else in the suite.
    expect(addSpy.mock.calls.some(([type]) => type === "orientationchange")).toBe(true);
    addSpy.mockRestore();

    fireEvent.click(screen.getByTestId("image-viewer-zoom-in"));
    drag(300, 210);
    expect(transform()).toContain("scale(1.5)");
    expect(transform()).not.toContain("translate3d(0px, 0px, 0)");

    // NO geometry claim is made here: jsdom has no layout, so a pan-POSITION
    // assertion would pass against all-zero rects and prove nothing (§ 8, and
    // `zoom.test.ts`'s own "degenerates safely when the geometry is
    // unmeasurable"). What is honest is that the handler RAN — collapsing the
    // clamp's travel to zero makes that observable — and that the zoom LEVEL
    // survived the refit (`EXPERIENCE.md:262`).
    const img = screen.getAllByTestId("rendered-img")[0] as HTMLImageElement;
    Object.defineProperty(img, "offsetWidth", { value: 0, configurable: true });
    act(() => {
      fireEvent(window, new Event("orientationchange"));
    });
    expect(transform()).toContain("translate3d(0px, 0px, 0)");
    expect(transform()).toContain("scale(1.5)");
  });

  it("closes on Escape (AC-6)", async () => {
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
    // Base UI moves focus into the popup asynchronously and arms its dismiss
    // handlers with it.
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 30));
    });
    // Escape is Base UI's `useDismiss({ escapeKey: isTopmost })` — real, and
    // until this story asserted NOWHERE (V-9). The viewer's own `onKey`
    // deliberately does not intercept it.
    await act(async () => {
      fireEvent.keyDown(document, { key: "Escape" });
    });
    expect(onClose).toHaveBeenCalledTimes(1);
    // The RETURN-FOCUS half of AC-6 is asserted in Playwright, not here: 53.2
    // measured Base UI's focus manager behaving differently in real Chromium
    // than in jsdom, so a jsdom-only focus claim is not sufficient evidence
    // for a focus contract.
  });
});

describe("ImageFullscreenViewer — Story 53.3 readiness timeout + inline error (AC-8, D-5, D-6)", () => {
  /**
   * The `/share` failure this story closes. `AnonymousImage` renders a
   * placeholder `<div>` while it resolves its blob and SWALLOWS a rejection,
   * so on failure no `<img>` is ever mounted — and neither `load` nor `error`
   * can fire on an element that does not exist.
   *
   * V-21: no visual spec has ever opened the viewer from `/share`, and
   * reproducing this there would mean building a whole share harness for one
   * assertion. The defect is a property of the component's own PROP BOUNDARY —
   * a `renderImage` that returns something without an `<img>` in it — which is
   * one line here.
   */
  const renderWithoutImg: ImageRenderer = ({ alt }) => (
    <div data-testid="rendered-placeholder" aria-label={alt} />
  );

  function renderViewer(renderImage: ImageRenderer) {
    return render(
      <ImageFullscreenViewer
        sources={SOURCES}
        initialIndex={0}
        onClose={() => {}}
        renderImage={renderImage}
      />,
    );
  }

  /**
   * Model the `/share` renderer swapping its placeholder `<div>` for the real
   * `<img>` once `acquireShareBlob` resolves. It is a prop change only, so the
   * readiness effect (keyed on `activeIdx` + the frame node) does not re-run
   * and any armed watchdog survives the swap — which is exactly the state the
   * late-`load` and late-`error` cases below need.
   */
  function swapRenderer(
    view: ReturnType<typeof renderViewer>,
    renderImage: ImageRenderer,
  ) {
    view.rerender(
      <ImageFullscreenViewer
        sources={SOURCES}
        initialIndex={0}
        onClose={() => {}}
        renderImage={renderImage}
      />,
    );
  }

  it("turns a never-mounted <img> into a reported failure once the timeout elapses", () => {
    vi.useFakeTimers();
    try {
      renderViewer(renderWithoutImg);
      // The shipped defect: silently `loading` forever, all three controls
      // disabled, nothing ever announced.
      expect(screen.queryByTestId("rendered-img")).toBeNull();
      expect(screen.queryByTestId("image-viewer-error")).toBeNull();
      expect(zoomLevel()).toBe("Loading full image…");

      act(() => {
        vi.advanceTimersByTime(IMAGE_READY_TIMEOUT_MS);
      });

      expect(screen.getByTestId("image-viewer-error").textContent).toBe(
        "The photo could not be loaded.",
      );
      expect(zoomLevel()).toBe("The photo could not be loaded.");
      // A failed image never traps the user.
      expect((screen.getByTestId("image-viewer-close") as HTMLButtonElement).disabled).toBe(
        false,
      );
      expect(ariaHiddenAncestor(screen.getByTestId("image-viewer-toolbar"))).toBeNull();
    } finally {
      vi.useRealTimers();
    }
  });

  // Story 53.3 code review DN-2 (controller-accepted repair). The watchdog
  // used to arm on the ordinary `<img>` path as well, where `load`/`error`
  // answer for themselves — so a slow-but-valid photo was painted over with
  // the inline error and ANNOUNCED as failed at 15 s while it was still
  // downloading, and the recovery was silent. This pins the narrowed arm site
  // by its OBSERVABLE consequence (no error, still "loading") and by the
  // absence of the timer itself, so re-widening the branch fails here.
  it("never reports a slow-but-valid mounted <img> as failed (DN-2)", () => {
    vi.useFakeTimers();
    const setSpy = vi.spyOn(globalThis, "setTimeout");
    try {
      renderViewer(makePlainRenderer().render);
      expect(zoomLevel()).toBe("Loading full image…");
      // No watchdog is armed at all on this path.
      expect(
        setSpy.mock.calls.filter((call) => call[1] === IMAGE_READY_TIMEOUT_MS),
      ).toHaveLength(0);

      // Far past the old deadline, with the image still in flight: the viewer
      // must still say "loading", not "failed".
      act(() => {
        vi.advanceTimersByTime(IMAGE_READY_TIMEOUT_MS * 3);
      });
      expect(screen.queryByTestId("image-viewer-error")).toBeNull();
      expect(zoomLevel()).toBe("Loading full image…");
    } finally {
      setSpy.mockRestore();
      vi.useRealTimers();
    }
  });

  it("does not fire the timeout once the image has loaded", () => {
    vi.useFakeTimers();
    try {
      renderViewer(makePlainRenderer().render);
      const img = screen.getAllByTestId("rendered-img")[0] as HTMLImageElement;
      Object.defineProperty(img, "naturalWidth", { value: 2000, configurable: true });
      Object.defineProperty(img, "offsetWidth", { value: 500, configurable: true });

      act(() => {
        vi.advanceTimersByTime(IMAGE_READY_TIMEOUT_MS - 1);
      });
      act(() => {
        fireEvent.load(img);
      });
      // Far past the original deadline: a timer that was not cleared would
      // flip a perfectly good image to `error` under the user.
      act(() => {
        vi.advanceTimersByTime(IMAGE_READY_TIMEOUT_MS * 2);
      });
      expect(screen.queryByTestId("image-viewer-error")).toBeNull();
      expect((screen.getByTestId("image-viewer-zoom-in") as HTMLButtonElement).disabled).toBe(
        false,
      );
    } finally {
      vi.useRealTimers();
    }
  });

  it("lets a LATE load recover from a fired timeout", () => {
    vi.useFakeTimers();
    try {
      const view = renderViewer(renderWithoutImg);

      act(() => {
        vi.advanceTimersByTime(IMAGE_READY_TIMEOUT_MS);
      });
      expect(screen.getByTestId("image-viewer-error")).toBeTruthy();

      // The /share blob finally resolves and the renderer swaps its
      // placeholder for a real `<img>`. The readiness effect does NOT re-run
      // (its deps are unchanged), but the capture-phase listener lives on the
      // FRAME rather than on the element, so the late `load` still reaches it.
      swapRenderer(view, makePlainRenderer().render);
      const img = screen.getAllByTestId("rendered-img")[0] as HTMLImageElement;
      Object.defineProperty(img, "naturalWidth", { value: 2000, configurable: true });
      Object.defineProperty(img, "offsetWidth", { value: 500, configurable: true });

      // The watchdog REPORTS a stall; it does not permanently condemn the
      // image (D-5). A slow fetch that eventually lands must still be usable.
      act(() => {
        fireEvent.load(img);
      });
      expect(screen.queryByTestId("image-viewer-error")).toBeNull();
      expect((screen.getByTestId("image-viewer-zoom-in") as HTMLButtonElement).disabled).toBe(
        false,
      );
    } finally {
      vi.useRealTimers();
    }
  });

  it("does not let a timer armed for one image fire onto a later one", () => {
    vi.useFakeTimers();
    try {
      // Image 1 mounts NO `<img>` (so it arms the watchdog — DN-2 narrowed the
      // arm site to exactly this branch); image 2 mounts a real one.
      const perSource: ImageRenderer = ({ src, alt, className }) =>
        src === SOURCES[0]?.fullUrl ? (
          <div data-testid="rendered-placeholder" aria-label={alt} />
        ) : (
          <img src={src} alt={alt} className={className} data-testid="rendered-img" />
        );
      renderViewer(perSource);
      // Sit most of the way through image 1's window, then navigate.
      act(() => {
        vi.advanceTimersByTime(IMAGE_READY_TIMEOUT_MS - 1_000);
      });
      act(() => {
        fireEvent.click(screen.getByTestId("image-viewer-next"));
      });
      expect(screen.getByTestId("image-viewer-counter").textContent).toBe("2 / 3");

      const img = screen.getAllByTestId("rendered-img")[0] as HTMLImageElement;
      Object.defineProperty(img, "naturalWidth", { value: 2000, configurable: true });
      Object.defineProperty(img, "offsetWidth", { value: 500, configurable: true });
      act(() => {
        fireEvent.load(img);
      });

      // Cross image 1's ORIGINAL deadline. A leaked timer would report image
      // 2 as broken on image 1's schedule.
      act(() => {
        vi.advanceTimersByTime(2_000);
      });
      expect(screen.queryByTestId("image-viewer-error")).toBeNull();
      expect((screen.getByTestId("image-viewer-zoom-in") as HTMLButtonElement).disabled).toBe(
        false,
      );
    } finally {
      vi.useRealTimers();
    }
  });

  // AC-8 names FOUR teardown triggers — `load`, `error`, an `activeIdx`
  // change and unmount — and asks for each to be ASSERTED. This is the `load`
  // one, and until the second code review it was unasserted: PROVEN BY
  // MUTATION, deleting `clearReadyTimeout()` from `onLoad` left the suite at
  // 71 passed / 0 failed. The three cases that looked like they covered it are
  // all vacuous for this purpose — `does not fire the timeout once the image
  // has loaded` uses a mounted `<img>`, the branch DN-2 removed the arm from,
  // so there is no timer to clear; `lets a LATE load recover from a fired
  // timeout` advances past the deadline first, so `readyTimeout` is already
  // `undefined` and the call is a no-op; and `does not let a timer armed for
  // one image fire onto a later one` clears through the `activeIdx` cleanup.
  // The load has to arrive on a STILL-ARMED watchdog, i.e. before the clock is
  // advanced — which is exactly the /share late-blob shape.
  it("clears the readiness timeout when a late image loads", () => {
    vi.useFakeTimers();
    const setSpy = vi.spyOn(globalThis, "setTimeout");
    const clearSpy = vi.spyOn(globalThis, "clearTimeout");
    try {
      const view = renderViewer(renderWithoutImg);
      const watchdogIds = setSpy.mock.calls.flatMap((call, i) => {
        if (call[1] !== IMAGE_READY_TIMEOUT_MS) return [];
        const result = setSpy.mock.results[i];
        return result === undefined || result.type !== "return" ? [] : [result.value];
      });
      expect(watchdogIds).toHaveLength(1);

      // The blob resolves INSIDE the window, so the watchdog is still armed
      // when `load` fires. Nothing is advanced first.
      swapRenderer(view, makePlainRenderer().render);
      const img = screen.getAllByTestId("rendered-img")[0] as HTMLImageElement;
      Object.defineProperty(img, "naturalWidth", { value: 2000, configurable: true });
      Object.defineProperty(img, "offsetWidth", { value: 500, configurable: true });
      act(() => {
        fireEvent.load(img);
      });
      expect(clearSpy.mock.calls.map((call) => call[0])).toContain(watchdogIds[0]);

      // ...and the observable consequence: crossing the original deadline must
      // not condemn an image that has already answered for itself.
      act(() => {
        vi.advanceTimersByTime(IMAGE_READY_TIMEOUT_MS * 2);
      });
      expect(screen.queryByTestId("image-viewer-error")).toBeNull();
      expect((screen.getByTestId("image-viewer-zoom-in") as HTMLButtonElement).disabled).toBe(
        false,
      );
    } finally {
      setSpy.mockRestore();
      clearSpy.mockRestore();
      vi.useRealTimers();
    }
  });

  // The `error` teardown trigger — the cheapest of the four to get wrong
  // silently, because a watchdog that survives an `error` re-sets a state the
  // component is already in, so nothing observable breaks until the teardown
  // is refactored and the leak reaches a LATER image.
  it("clears the readiness timeout when the image reports an error", () => {
    vi.useFakeTimers();
    const setSpy = vi.spyOn(globalThis, "setTimeout");
    const clearSpy = vi.spyOn(globalThis, "clearTimeout");
    try {
      const view = renderViewer(renderWithoutImg);
      const watchdogIds = setSpy.mock.calls.flatMap((call, i) => {
        if (call[1] !== IMAGE_READY_TIMEOUT_MS) return [];
        const result = setSpy.mock.results[i];
        return result === undefined || result.type !== "return" ? [] : [result.value];
      });
      expect(watchdogIds).toHaveLength(1);

      // The `<img>` mounts late and then FAILS — the only shape in which an
      // `error` can reach a still-armed watchdog now that DN-2 has narrowed
      // the arm site to the never-mounted branch.
      swapRenderer(view, makePlainRenderer().render);
      act(() => {
        fireEvent.error(screen.getAllByTestId("rendered-img")[0] as HTMLImageElement);
      });
      expect(screen.getByTestId("image-viewer-error")).toBeTruthy();
      expect(clearSpy.mock.calls.map((call) => call[0])).toContain(watchdogIds[0]);

      // ...and the reported failure is stable: crossing the original deadline
      // must not re-enter the watchdog's own branch on an image that already
      // answered for itself.
      act(() => {
        vi.advanceTimersByTime(IMAGE_READY_TIMEOUT_MS * 2);
      });
      expect(screen.getByTestId("image-viewer-error")).toBeTruthy();
      expect(zoomLevel()).toBe("The photo could not be loaded.");
    } finally {
      setSpy.mockRestore();
      clearSpy.mockRestore();
      vi.useRealTimers();
    }
  });

  it("clears the readiness timeout on unmount", () => {
    vi.useFakeTimers();
    // Identified by its DELAY rather than by a global pending-timer count:
    // Base UI schedules timers of its own (focus manager, scroll-lock
    // restore) and those are not this story's to assert about. Measured this
    // run: one non-viewer timer survives unmount, so a `getTimerCount() === 0`
    // check would have been a false failure.
    const setSpy = vi.spyOn(globalThis, "setTimeout");
    const clearSpy = vi.spyOn(globalThis, "clearTimeout");
    try {
      const view = renderViewer(renderWithoutImg);
      const watchdogIds = setSpy.mock.calls.flatMap((call, i) => {
        if (call[1] !== IMAGE_READY_TIMEOUT_MS) return [];
        const result = setSpy.mock.results[i];
        return result === undefined || result.type !== "return" ? [] : [result.value];
      });
      expect(watchdogIds).toHaveLength(1);

      view.unmount();

      // A watchdog that outlives its own tree is a setState onto a closed
      // viewer — and, once this component is reopened, onto a LATER image.
      expect(clearSpy.mock.calls.map((call) => call[0])).toContain(watchdogIds[0]);
    } finally {
      setSpy.mockRestore();
      clearSpy.mockRestore();
      vi.useRealTimers();
    }
  });

  it("renders the inline error inside the frame, outside the transform layer, and traps nobody (D-6)", () => {
    renderViewer(makePlainRenderer().render);
    expect(screen.queryByTestId("image-viewer-error")).toBeNull();

    fireEvent.error(screen.getAllByTestId("rendered-img")[0] as HTMLImageElement);

    const error = screen.getByTestId("image-viewer-error");
    // The copy is the UX spine's, transcribed rather than translated
    // (mockup `key-viewer-chrome.html` state E).
    expect(error.textContent).toBe("The photo could not be loaded.");
    // Inside the frame, but OUTSIDE the transform layer, so it neither scales
    // nor pans with a zoom the user left applied.
    expect(screen.getByTestId("image-viewer-frame").contains(error)).toBe(true);
    expect(screen.getByTestId("image-viewer-transform").contains(error)).toBe(false);
    // ...and it never swallows a tap meant for the chrome beneath it.
    expect(error.className).toContain("pointer-events-none");
    // ⚠️ CONTRACT CHANGED BY STORY 54.2 / T14 (V-9), deliberately, and this
    // assertion is the inverse of what Story 53.3 shipped.
    //
    // 53.3 asserted `ariaHiddenAncestor(error)` was NULL — the chip was
    // deliberately left in the accessibility tree. The second 53.3 code review
    // then found the consequence and ledgered it with `Owner: Story 54.2`: the
    // chip's `t("catalog.image_viewer.error")` and the polite live region's
    // announcement (`:502`) are the SAME string, so a screen-reader user
    // browsing the open dialog meets the identical sentence twice.
    //
    // One sentence, one source. The always-mounted live region is the one that
    // must stay exposed — it is what ANNOUNCES the failure, and hiding it would
    // silence the error entirely. The visible chip is the sighted-user channel
    // for the same fact, so it becomes `aria-hidden`. Nothing is lost: the
    // information is still in the tree once, in the region that carries it.
    //
    // The rest of 53.3's D-6 contract is untouched and re-asserted below — the
    // chip still traps nobody, still never swallows a tap, and every control
    // beneath it stays reachable and operable.
    expect(ariaHiddenAncestor(error)).toBe(error);
    // DN-3 — the chip backdrop is `/60`, not `/40`. Pinned as a CLASS because
    // jsdom composites nothing and the real number is a pixel measurement: the
    // four `image-viewer-error-*` baselines carry the visual proof, this
    // catches a silent re-lowering long before a baseline diff would.
    expect(error.querySelector("span")?.className).toContain("bg-gallery-control/60");

    // The live region announces the failure instead of falling through to "".
    expect(zoomLevel()).toBe("The photo could not be loaded.");

    // Close / chevrons / strip / toolbar all stay reachable...
    for (const testid of ["image-viewer-close", "image-viewer-prev", "image-viewer-next"]) {
      expect((screen.getByTestId(testid) as HTMLButtonElement).disabled).toBe(false);
    }
    expect(screen.getByTestId("image-viewer-strip").getAttribute("aria-hidden")).toBe("false");
    expect(ariaHiddenAncestor(screen.getByTestId("image-viewer-toolbar"))).toBeNull();
    expect(screen.getAllByTestId("image-viewer-thumb")).toHaveLength(3);

    // ...and OPERABLE, not merely present: navigating away leaves the error
    // state behind with the image it belonged to.
    fireEvent.click(screen.getByTestId("image-viewer-next"));
    expect(screen.getByTestId("image-viewer-counter").textContent).toBe("2 / 3");
    expect(screen.queryByTestId("image-viewer-error")).toBeNull();
    expect(zoomLevel()).toBe("Loading full image…");
  });
});
