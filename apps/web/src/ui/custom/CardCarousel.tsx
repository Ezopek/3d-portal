import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

interface Props {
  modelId: string;
  /** Non-empty list of gallery file IDs (image/print kinds). */
  fileIds: readonly string[];
  alt: string;
}

/**
 * Mini-carousel rendered on catalog list cards when a model has multiple
 * gallery images. Consumes `gallery_file_ids` directly — no file-list fetch.
 *
 * The card itself is wrapped in a `<Link>`, so arrow- and dot-button
 * handlers must call both `preventDefault` and `stopPropagation` to avoid
 * navigating to the detail page when the user just wants to switch image.
 */
// Held minimum so the blur is perceivable even when the next image is in
// the browser cache and `load` fires near-instantly. Without this the
// transition flickers: blur → unblur on the OLD image, then a hard swap
// to the new one.
const MIN_BLUR_VISIBLE_MS = 220;

export function CardCarousel({ modelId, fileIds, alt }: Props) {
  const [active, setActive] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const total = fileIds.length;
  const activeId = fileIds[active] ?? fileIds[0];
  const blurStartRef = useRef(0);
  const unblurTimerRef = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (unblurTimerRef.current !== null) clearTimeout(unblurTimerRef.current);
    },
    [],
  );

  function trigger(nextIndex: number) {
    if (nextIndex === active) return;
    if (unblurTimerRef.current !== null) {
      clearTimeout(unblurTimerRef.current);
      unblurTimerRef.current = null;
    }
    blurStartRef.current = performance.now();
    setIsLoading(true);
    setActive(nextIndex);
  }

  function step(delta: number, e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    trigger((((active + delta) % total) + total) % total);
  }

  function handleLoaded() {
    if (!isLoading) return;
    const elapsed = performance.now() - blurStartRef.current;
    const remaining = Math.max(0, MIN_BLUR_VISIBLE_MS - elapsed);
    if (remaining === 0) {
      setIsLoading(false);
    } else {
      unblurTimerRef.current = window.setTimeout(() => {
        setIsLoading(false);
        unblurTimerRef.current = null;
      }, remaining);
    }
  }

  return (
    <div className="group relative aspect-square overflow-hidden bg-muted">
      {/* The blur lives on a wrapper around the <img>, so the whole image
          window is visibly out-of-focus during a switch. The browser keeps
          the old bitmap painted while the new one decodes (no `key` on the
          img), so the swap happens silently behind the blur. We hold the
          blur for at least MIN_BLUR_VISIBLE_MS to mask the swap even when
          the new image is already cached. */}
      <div
        className={cn(
          "absolute inset-0 transition-[filter,transform] duration-200 will-change-[filter]",
          isLoading ? "scale-105 blur-[8px]" : "scale-100 blur-0",
        )}
      >
        <img
          src={`/api/models/${modelId}/files/${activeId}/content`}
          alt={alt}
          loading="lazy"
          decoding="async"
          onLoad={handleLoaded}
          onError={handleLoaded}
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
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  trigger(i);
                }}
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
