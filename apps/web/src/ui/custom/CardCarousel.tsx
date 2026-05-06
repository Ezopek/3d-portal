import { ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";

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
export function CardCarousel({ modelId, fileIds, alt }: Props) {
  const [active, setActive] = useState(0);
  // Start in loading state so the first paint shows the blur skeleton —
  // not just transitions between images.
  const [isLoading, setIsLoading] = useState(true);
  const total = fileIds.length;
  const activeId = fileIds[active] ?? fileIds[0];

  function step(delta: number, e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    setIsLoading(true);
    setActive((prev) => (prev + delta + total) % total);
  }

  return (
    <div
      className={cn(
        "group relative aspect-square overflow-hidden bg-muted",
        isLoading && "animate-pulse",
      )}
    >
      {/* No `key` on src changes: keep the previous image visible while the
          next one decodes, otherwise React unmounts the <img> and we see a
          flash of bg-muted (and a blurred alt-text) before the new image
          arrives. The browser fires `load` on src changes, so onLoad still
          drops the blur as expected. */}
      <img
        src={`/api/models/${modelId}/files/${activeId}/content`}
        alt={alt}
        loading="lazy"
        decoding="async"
        onLoad={() => setIsLoading(false)}
        onError={() => setIsLoading(false)}
        className={cn(
          "h-full w-full object-cover transition-[filter] duration-150",
          isLoading ? "blur-[4px]" : "blur-0",
        )}
      />
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
                  if (i !== active) setIsLoading(true);
                  setActive(i);
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
