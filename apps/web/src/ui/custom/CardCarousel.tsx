import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

interface Props {
  modelId: string;
  /** Non-empty list of gallery file IDs (image/print kinds). */
  fileIds: readonly string[];
  alt: string;
}

// Time the next image is held under full blur before the bitmap swap.
// Sized to comfortably exceed the 200 ms blur transition so the swap
// happens while the picture is fully out-of-focus — even when the next
// image is already in the browser cache and `decode()` would otherwise
// resolve in a few ms. Without this, cached switches show the OLD image
// half-blurred, then a hard cut to the NEW image, then a redundant
// blur-and-unblur of the new image.
const HOLD_BEFORE_SWAP_MS = 260;

function urlFor(modelId: string, fileId: string): string {
  return `/api/models/${modelId}/files/${fileId}/content`;
}

/**
 * Mini-carousel rendered on catalog list cards when a model has multiple
 * gallery images. Consumes `gallery_file_ids` directly — no file-list fetch.
 *
 * Transition design (decode-before-swap):
 *   1. click → setActive(target). The dot UI updates immediately, the
 *      visible image stays on `displayed` (= last fully-rendered src).
 *   2. effect on [active] kicks in: setIsTransitioning(true) → blur fades
 *      in over the still-mounted OLD bitmap.
 *   3. in parallel: `new Image().decode()` pre-decodes the next bitmap
 *      off-DOM, and a `HOLD_BEFORE_SWAP_MS` timer ensures we never swap
 *      before the blur is fully on.
 *   4. once both resolve: setDisplayed(active) — the DOM <img> swaps src
 *      under the fully-blurred wrapper (visually invisible).
 *   5. two RAF ticks later (one for React commit, one for the paint of
 *      the new bitmap), setIsTransitioning(false) → blur fades out and
 *      reveals the NEW image cleanly.
 *
 * The card itself is wrapped in a `<Link>`, so arrow- and dot-button
 * handlers must call both `preventDefault` and `stopPropagation` to avoid
 * navigating to the detail page when the user just wants to switch image.
 */
export function CardCarousel({ modelId, fileIds, alt }: Props) {
  const [active, setActive] = useState(0);
  const [displayed, setDisplayed] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const total = fileIds.length;

  useEffect(() => {
    if (active === displayed) return;
    const targetId = fileIds[active];
    if (targetId === undefined) return;

    let cancelled = false;
    setIsTransitioning(true);

    const decoded = (() => {
      const img = new Image();
      img.src = urlFor(modelId, targetId);
      // .decode() resolves once the image is fully decoded into a
      // displayable bitmap; on reject (404, decode error) we still
      // proceed so the user isn't visually trapped on a stale image.
      return img.decode().catch(() => undefined);
    })();
    const held = new Promise<void>((resolve) =>
      setTimeout(resolve, HOLD_BEFORE_SWAP_MS),
    );

    Promise.all([decoded, held]).then(() => {
      if (cancelled) return;
      setDisplayed(active);
      // First RAF: React commits the new src to the DOM <img>.
      // Second RAF: the browser has painted the new bitmap (cache-hit
      // from the off-DOM decode means paint is essentially free). Only
      // now do we kick off the unblur, so the transition runs against
      // the stable, already-painted target.
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          if (!cancelled) setIsTransitioning(false);
        });
      });
    });

    return () => {
      cancelled = true;
    };
  }, [active, displayed, fileIds, modelId]);

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
      {/* The blur lives on a wrapper around the <img>, so the whole image
          window goes out-of-focus during a switch. scale-105 hides the
          soft halo blur would otherwise leak past the rounded corners. */}
      <div
        className={cn(
          "absolute inset-0 transition-[filter,transform] duration-200 will-change-[filter]",
          isTransitioning ? "scale-105 blur-[8px]" : "scale-100 blur-0",
        )}
      >
        <img
          src={urlFor(modelId, displayedId)}
          alt={alt}
          loading="lazy"
          decoding="async"
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
