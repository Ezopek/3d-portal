import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

interface Props {
  modelId: string;
  /** Non-empty list of gallery file IDs (image/print kinds). */
  fileIds: readonly string[];
  alt: string;
}

// Time the next image is held under full blur before the bitmap swap.
// Sized to slightly exceed the 150 ms blur transition so the swap
// happens while the picture is fully out-of-focus — even when the next
// image is already in the browser cache and `decode()` would otherwise
// resolve in a few ms.
const HOLD_BEFORE_SWAP_MS = 170;

function urlFor(modelId: string, fileId: string): string {
  return `/api/models/${modelId}/files/${fileId}/content`;
}

/**
 * Mini-carousel rendered on catalog list cards when a model has multiple
 * gallery images. Consumes `gallery_file_ids` directly — no file-list fetch.
 *
 * Two visual paths share the same wrapper transition (blur + scale +
 * opacity to 25 %):
 *
 *   1. First paint: `isTransitioning` starts true so the still-loading
 *      img fades in instead of popping over the muted background. The
 *      DOM <img>'s onLoad clears the blur once the bitmap is painted.
 *
 *   2. User-initiated switch (decode-before-swap):
 *      - click → `active` updates immediately (drives the dot UI)
 *      - effect on [active] flips `isTransitioning` on, pre-decodes the
 *        next bitmap off-DOM via `new Image().decode()`, and waits a
 *        minimum hold so the blur is always perceivable.
 *      - both done: `displayed` is advanced, the DOM <img> swaps src
 *        beneath the now-fully-on blur.
 *      - two RAFs later (commit + paint) the unblur fires.
 *      - `inTransitionRef` gates the <img>'s onLoad: a stale load event
 *        for the in-flight or just-replaced image must not race the
 *        controlled fade-out.
 *
 * The card itself is wrapped in a `<Link>`, so arrow- and dot-button
 * handlers must call both `preventDefault` and `stopPropagation` to avoid
 * navigating to the detail page when the user just wants to switch image.
 */
export function CardCarousel({ modelId, fileIds, alt }: Props) {
  const [active, setActive] = useState(0);
  const [displayed, setDisplayed] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(true);
  const inTransitionRef = useRef(false);
  const total = fileIds.length;

  useEffect(() => {
    if (active === displayed) return;
    const targetId = fileIds[active];
    if (targetId === undefined) return;

    let cancelled = false;
    inTransitionRef.current = true;
    setIsTransitioning(true);

    const decoded = (() => {
      const img = new Image();
      img.src = urlFor(modelId, targetId);
      // Optional chaining handles environments without HTMLImageElement.decode
      // (jsdom in unit tests; some older browsers / image MIME types). A
      // missing decode degrades the cross-fade to "show the new src as soon
      // as the timer + held promise resolve", which is acceptable.
      return (img.decode?.() ?? Promise.resolve()).catch(() => undefined);
    })();
    const held = new Promise<void>((resolve) =>
      setTimeout(resolve, HOLD_BEFORE_SWAP_MS),
    );

    Promise.all([decoded, held]).then(() => {
      if (cancelled) return;
      setDisplayed(active);
      // Two RAFs: first lets React commit the new src to the DOM, second
      // runs after the browser has painted the new bitmap. Only then do
      // we kick off the unblur.
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          if (cancelled) return;
          inTransitionRef.current = false;
          setIsTransitioning(false);
        });
      });
    });

    return () => {
      cancelled = true;
    };
    // The effect re-runs only on `active` changes (= the user picked a
    // different image). Including `displayed` here would cancel the
    // in-flight transition the moment we successfully swap the src and
    // pin the blur on forever. `fileIds` and `modelId` are read once via
    // closure at the start of the transition; rapid prop-reference
    // churn from the parent must not interrupt an in-progress fade.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  function handleImageLoaded() {
    // Ignore <img> load events while a user-initiated transition is in
    // flight: that path drops `isTransitioning` itself once the swap is
    // committed and painted. Honouring stale onLoads here would either
    // clear the blur before the swap (showing the OLD image sharp) or
    // duplicate the unblur trigger. For the very first paint and any
    // standalone re-render, this is the path that releases the skeleton.
    if (inTransitionRef.current) return;
    setIsTransitioning(false);
  }

  function move(target: number, e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (target === active) return;
    setActive(target);
  }

  function step(delta: number, e: React.MouseEvent) {
    move((((active + delta) % total) + total) % total, e);
  }

  const displayedId = fileIds[displayed] ?? fileIds[0]!;

  return (
    <div className="group relative aspect-square overflow-hidden bg-muted">
      <div
        className={cn(
          "absolute inset-0 transition duration-150 will-change-[filter,opacity]",
          isTransitioning
            ? "scale-105 blur-[8px] opacity-25"
            : "scale-100 blur-0 opacity-100",
        )}
      >
        <img
          src={urlFor(modelId, displayedId)}
          alt={alt}
          loading="lazy"
          decoding="async"
          onLoad={handleImageLoaded}
          onError={handleImageLoaded}
          className="h-full w-full object-cover"
        />
      </div>
      {total > 1 && (
        <>
          <button
            type="button"
            aria-label="previous image"
            data-testid="card-carousel-prev"
            onClick={(e) => step(-1, e)}
            className="absolute left-1 top-1/2 -translate-y-1/2 grid h-8 w-8 place-items-center rounded-full bg-black/40 text-white opacity-0 transition-opacity hover:bg-black/60 focus-visible:opacity-100 group-hover:opacity-100"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <button
            type="button"
            aria-label="next image"
            data-testid="card-carousel-next"
            onClick={(e) => step(1, e)}
            className="absolute right-1 top-1/2 -translate-y-1/2 grid h-8 w-8 place-items-center rounded-full bg-black/40 text-white opacity-0 transition-opacity hover:bg-black/60 focus-visible:opacity-100 group-hover:opacity-100"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
          <div
            data-testid="card-carousel-dots"
            className="absolute inset-x-0 bottom-1 flex justify-center gap-1"
          >
            {fileIds.map((id, i) => (
              <button
                key={id}
                type="button"
                aria-label={`go to image ${i + 1}`}
                onClick={(e) => move(i, e)}
                className={cn(
                  "h-1.5 w-1.5 rounded-full transition-colors",
                  i === active ? "bg-white" : "bg-white/40 hover:bg-white/70",
                )}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
