// Story 22.3 (TB-037 viewer + TB-022 consumer) — symmetric fullscreen image
// viewer. ONE component, prop-injected `renderImage`, mounted by both
// `/catalog/$modelId` (ModelGallery) and `/share/$token` (ShareCarousel).
// Designer spec (`22-3-designer-ux-spec.md`) is the binding source of truth
// for every layout / a11y / gesture decision below; this file extracts the
// implementation from that spec.
//
// What lives here:
//   - shadcn Dialog wrapper mirroring `Viewer3DModal` sizing (designer §1+§4)
//   - main image rendered via `renderImage` prop (the cookie-credential
//     boundary; auth tax lives at the prop, not in the viewer body)
//   - bottom thumb strip with active highlight
//   - top-left counter (only when total > 1)
//   - top-right close button + prev/next chevrons
//   - keyboard handler: ESC closes (Dialog default also covers this);
//     ArrowLeft/Right navigates
//   - mobile gestures (designer §5):
//       * tap-to-toggle overlay chrome  — IN-SCOPE
//       * swipe-LR between images       — IN-SCOPE
//       * pinch-to-zoom                 — DEFERRED (TB-042 candidate)
//       * swipe-down-to-close           — DEFERRED (TB-042 candidate)
//
// NOT included on purpose:
//   - no auth gate (both mounts have crossed their auth boundary already)
//   - no separate /catalog vs /share variants — one component, prop only
//   - no PhotoSwipe / yet-another-react-lightbox dep (boring tech bias per
//     designer §1; the surface is ~150 LOC, we already own focus-trap +
//     theme + i18n via shadcn Dialog)

import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Dialog, DialogContent, DialogTitle } from "@/ui/dialog";
import { cn } from "@/lib/utils";

import type { ImageFullscreenViewerProps } from "./types";

// Swipe-distance threshold (px) before we treat a touch drag as a
// horizontal-navigation gesture. 50px matches what the broader React
// ecosystem uses for carousel components (e.g. embla-carousel default)
// and is comfortably above accidental-thumb-drift noise.
const SWIPE_THRESHOLD_PX = 50;
// Maximum |y| drift permitted on a horizontal swipe — beyond this we
// assume the user is scrolling vertically (e.g. the thumb strip), not
// navigating. Designer §5 noted pinch + swipe-down-close are deferred;
// this disambiguation keeps the deferred work from getting tangled up.
const SWIPE_VERTICAL_TOLERANCE_PX = 60;

export default function ImageFullscreenViewer({
  sources,
  initialIndex,
  onClose,
  renderImage,
  // Story 22.3 round-2 (Codex P1): when the consumer supplies a
  // separate thumb renderer, use it for the strip. Defaults to
  // `renderImage`, preserving the single-renderer shape for the
  // simple /catalog/<id> mount. ShareCarousel injects
  // `LazyAnonymousImage` here so strip thumbs lazy-load on
  // IntersectionObserver instead of all fetching at viewer-open.
  renderThumb,
}: ImageFullscreenViewerProps) {
  const { t } = useTranslation();
  const renderThumbResolved = renderThumb ?? renderImage;

  // Clamp initialIndex defensively: a consumer passing an out-of-range
  // index (e.g. after deletion races) would otherwise render undefined.
  const safeInitial =
    sources.length === 0
      ? 0
      : Math.max(0, Math.min(initialIndex, sources.length - 1));
  const [activeIdx, setActiveIdx] = useState(safeInitial);

  // Mobile tap-to-toggle chrome — when false, hide counter/chevrons/close
  // so the user sees the image edge-to-edge. Re-shows on tap (and on every
  // arrow-key navigation, so keyboard users never lose the close button).
  const [chromeVisible, setChromeVisible] = useState(true);

  // Touch tracking for swipe-LR. We deliberately do NOT attach onMouseDown
  // — desktop users have chevrons + arrow keys; pointer drags would
  // conflict with click-to-toggle-chrome on track-pad clicks.
  const touchStart = useRef<{ x: number; y: number } | null>(null);

  // Cap activeIdx if the parent re-feeds a shorter sources array between
  // renders (e.g. on photo delete). Keep us pointing at a valid entry.
  const lastLen = useRef(sources.length);
  if (lastLen.current !== sources.length) {
    lastLen.current = sources.length;
    if (activeIdx >= sources.length && sources.length > 0) {
      setActiveIdx(sources.length - 1);
    }
  }

  const total = sources.length;
  const active = sources[activeIdx];
  const showNav = total > 1;

  // Scroll the active thumb into view whenever activeIdx changes so the
  // strip never desyncs from the main frame on long galleries. jsdom does
  // not ship `Element.prototype.scrollIntoView` — guard with typeof so the
  // viewer keeps rendering inside vitest, where the call is a no-op.
  const stripRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const strip = stripRef.current;
    if (strip === null) return;
    const thumb = strip.querySelector<HTMLButtonElement>(
      `[data-thumb-idx="${activeIdx}"]`,
    );
    if (thumb !== null && typeof thumb.scrollIntoView === "function") {
      thumb.scrollIntoView({ block: "nearest", inline: "center", behavior: "smooth" });
    }
  }, [activeIdx]);

  function step(delta: number) {
    if (total === 0) return;
    setActiveIdx((i) => (i + delta + total) % total);
    setChromeVisible(true);
  }

  const onKey = (e: React.KeyboardEvent<HTMLDivElement>) => {
    // ESC: let the Dialog default fire (it'll call our `onOpenChange`
    // closer). We don't intercept here.
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      e.stopPropagation();
      step(-1);
      return;
    }
    if (e.key === "ArrowRight") {
      e.preventDefault();
      e.stopPropagation();
      step(1);
      return;
    }
  };

  const onTouchStart = (e: React.TouchEvent<HTMLDivElement>) => {
    // Story 22.3 round-2 (Codex P2): ignore gestures that originate
    // inside the bottom thumb-strip — the strip is `overflow-x-auto`
    // and horizontal drag on it should scroll the strip, not navigate
    // between images. Without this guard, dragging the strip on
    // mobile/tablet calls step() and changes the active photo before
    // the user can scroll to later thumbnails.
    const strip = stripRef.current;
    if (strip !== null && e.target instanceof Node && strip.contains(e.target)) {
      touchStart.current = null;
      return;
    }
    const t0 = e.touches[0];
    if (t0 === undefined) return;
    touchStart.current = { x: t0.clientX, y: t0.clientY };
  };

  const onTouchEnd = (e: React.TouchEvent<HTMLDivElement>) => {
    const start = touchStart.current;
    touchStart.current = null;
    if (start === null) return;
    const t0 = e.changedTouches[0];
    if (t0 === undefined) return;
    const dx = t0.clientX - start.x;
    const dy = t0.clientY - start.y;
    // Disambiguation: if the vertical drift dominates, treat as scroll —
    // don't intercept. Pinch-zoom + swipe-down-close stay deferred.
    if (Math.abs(dy) > SWIPE_VERTICAL_TOLERANCE_PX) return;
    if (Math.abs(dx) < SWIPE_THRESHOLD_PX) {
      // Short tap — toggle chrome visibility (designer §5).
      setChromeVisible((v) => !v);
      return;
    }
    // Long horizontal swipe — navigate. dx < 0 = swipe-left = next image.
    if (total > 1) {
      step(dx < 0 ? 1 : -1);
    }
  };

  if (active === undefined) {
    // Sources empty — nothing to render. Parent should never open the
    // viewer in this state, but cover it for safety.
    return null;
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        showCloseButton={false}
        className="h-[95vh] w-[98vw] max-w-[98vw] p-0 outline-none bg-background/95 backdrop-blur-sm sm:max-w-[98vw]"
        onKeyDown={onKey}
      >
        <DialogTitle className="sr-only">
          {t("catalog.image_viewer.dialog_title")}
        </DialogTitle>

        <div
          data-testid="image-viewer-root"
          className="relative flex h-full w-full flex-col"
          onTouchStart={onTouchStart}
          onTouchEnd={onTouchEnd}
        >
          {/* Main frame fills available space; thumb strip sits below. */}
          <div className="relative flex flex-1 items-center justify-center overflow-hidden">
            {renderImage({
              src: active.fullUrl,
              alt: active.alt,
              className: "max-h-full max-w-full object-contain",
            })}

            {/* Chrome layer — counter, close, chevrons. Fades when
                `chromeVisible` is false (mobile tap-to-hide). */}
            <div
              className={cn(
                "pointer-events-none absolute inset-0 transition-opacity duration-150",
                chromeVisible ? "opacity-100" : "opacity-0",
              )}
              aria-hidden={!chromeVisible}
            >
              {showNav && (
                <div
                  data-testid="image-viewer-counter"
                  className="pointer-events-auto absolute left-3 top-3 rounded bg-background/60 px-2 py-1 text-sm text-muted-foreground"
                >
                  {t("catalog.image_viewer.counter", {
                    current: activeIdx + 1,
                    total,
                  })}
                </div>
              )}

              <button
                type="button"
                data-testid="image-viewer-close"
                onClick={() => onClose()}
                aria-label={t("catalog.image_viewer.close")}
                className="pointer-events-auto absolute right-3 top-3 grid h-10 w-10 place-items-center rounded-full bg-gallery-control/40 text-gallery-control-foreground transition-colors hover:bg-gallery-control/60"
              >
                <X className="h-5 w-5" />
              </button>

              {showNav && (
                <>
                  <button
                    type="button"
                    data-testid="image-viewer-prev"
                    onClick={() => step(-1)}
                    aria-label={t("catalog.image_viewer.prev")}
                    className="pointer-events-auto absolute left-3 top-1/2 grid h-12 w-12 -translate-y-1/2 place-items-center rounded-full bg-gallery-control/40 text-gallery-control-foreground transition-colors hover:bg-gallery-control/60"
                  >
                    <ChevronLeft className="h-6 w-6" />
                  </button>
                  <button
                    type="button"
                    data-testid="image-viewer-next"
                    onClick={() => step(1)}
                    aria-label={t("catalog.image_viewer.next")}
                    className="pointer-events-auto absolute right-3 top-1/2 grid h-12 w-12 -translate-y-1/2 place-items-center rounded-full bg-gallery-control/40 text-gallery-control-foreground transition-colors hover:bg-gallery-control/60"
                  >
                    <ChevronRight className="h-6 w-6" />
                  </button>
                </>
              )}
            </div>
          </div>

          {showNav && (
            <div
              ref={stripRef}
              data-testid="image-viewer-strip"
              className={cn(
                "flex h-20 shrink-0 items-center gap-1.5 overflow-x-auto bg-background/70 px-3 py-2 transition-opacity duration-150",
                chromeVisible ? "opacity-100" : "opacity-0",
              )}
              aria-hidden={!chromeVisible}
            >
              {sources.map((s, idx) => (
                <button
                  key={`${idx}-${s.thumbUrl}`}
                  type="button"
                  data-testid="image-viewer-thumb"
                  data-thumb-idx={idx}
                  onClick={() => {
                    setActiveIdx(idx);
                    setChromeVisible(true);
                  }}
                  aria-label={t("catalog.image_viewer.thumb_label", { index: idx + 1 })}
                  aria-current={idx === activeIdx ? "true" : undefined}
                  className={cn(
                    "size-16 shrink-0 overflow-hidden rounded",
                    idx === activeIdx
                      ? "ring-2 ring-primary"
                      : "opacity-70 hover:opacity-100",
                  )}
                >
                  {renderThumbResolved({
                    src: s.thumbUrl,
                    alt: "",
                    className: "size-full object-cover",
                  })}
                </button>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
