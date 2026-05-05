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
 * The card itself is wrapped in a `<Link>`, so dot-button handlers must
 * call both `preventDefault` and `stopPropagation` to avoid navigating to
 * the detail page when the user just wants to switch the active image.
 */
export function CardCarousel({ modelId, fileIds, alt }: Props) {
  const [active, setActive] = useState(0);
  const total = fileIds.length;
  const activeId = fileIds[active] ?? fileIds[0];

  return (
    <div className="relative aspect-square overflow-hidden bg-muted">
      <img
        src={`/api/models/${modelId}/files/${activeId}/content`}
        alt={alt}
        loading="lazy"
        className="h-full w-full object-cover"
      />
      {total > 1 && (
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
                setActive(i);
              }}
              className={cn(
                "h-1.5 w-1.5 rounded-full transition-colors",
                i === active ? "bg-white" : "bg-white/40 hover:bg-white/70",
              )}
            />
          ))}
        </div>
      )}
    </div>
  );
}
