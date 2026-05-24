// Story 22.3 (TB-037 viewer) — vitest coverage for the symmetric fullscreen
// image viewer. We mount the default export DIRECTLY (not via the lazy
// barrel) so each test renders synchronously; the lazy barrel is exercised
// independently by `imageViewer.lazy.test.tsx` (chunk-split shape) +
// Playwright visual baselines (real-browser open-fullscreen flow).

import { fireEvent, render, screen } from "@testing-library/react";
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
