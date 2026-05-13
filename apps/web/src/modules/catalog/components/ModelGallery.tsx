import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import type { ModelFileRead } from "@/lib/api-types";
import { cn } from "@/lib/utils";

function isImage(f: ModelFileRead): boolean {
  return f.kind === "image" || f.kind === "print";
}

function srcFor(modelId: string, fileId: string): string {
  return `/api/models/${modelId}/files/${fileId}/content`;
}

/**
 * Push the chosen catalog thumbnail to the front of the gallery so the
 * default-active image matches what users see in the list view. Admin order
 * (`position`) is preserved for the remainder.
 */
function withThumbnailFirst(
  images: readonly ModelFileRead[],
  thumbnailFileId: string | null,
): readonly ModelFileRead[] {
  if (thumbnailFileId === null) return images;
  const idx = images.findIndex((i) => i.id === thumbnailFileId);
  if (idx <= 0) return images;
  const reordered = [...images];
  const [thumb] = reordered.splice(idx, 1);
  return thumb !== undefined ? [thumb, ...reordered] : images;
}

export function ModelGallery({
  modelId,
  files,
  thumbnailFileId = null,
}: {
  modelId: string;
  files: readonly ModelFileRead[];
  thumbnailFileId?: string | null;
}) {
  const { t } = useTranslation();
  const images = withThumbnailFirst(files.filter(isImage), thumbnailFileId);
  const [activeId, setActiveId] = useState<string | null>(images[0]?.id ?? null);
  const [imageLoaded, setImageLoaded] = useState(false);
  // Reset blur-up state when the active image changes so subsequent picks
  // also show the loading transition.
  useEffect(() => {
    setImageLoaded(false);
  }, [activeId]);
  if (images.length === 0) {
    return (
      <div className="grid aspect-[4/3] place-items-center rounded bg-muted text-sm text-muted-foreground">
        {t("catalog.no_preview")}
      </div>
    );
  }
  const activeIdx = Math.max(
    0,
    images.findIndex((i) => i.id === activeId),
  );
  const active = images[activeIdx] ?? images[0]!;
  const total = images.length;

  function step(delta: number) {
    const next = images[(activeIdx + delta + total) % total];
    if (next !== undefined) setActiveId(next.id);
  }

  return (
    <div className="space-y-2">
      <div className="group relative aspect-[4/3] overflow-hidden rounded bg-muted">
        <img
          data-testid="gallery-main"
          src={srcFor(modelId, active.id)}
          alt={active.original_name}
          onLoad={() => setImageLoaded(true)}
          onError={() => setImageLoaded(true)}
          className={cn(
            "absolute inset-0 h-full w-full object-contain transition duration-150 will-change-[filter,opacity]",
            imageLoaded
              ? "scale-100 blur-0 opacity-100"
              : "scale-105 blur-[8px] opacity-25",
          )}
        />
        {total > 1 && (
          <>
            <button
              type="button"
              aria-label={t("catalog.gallery.previousImage")}
              data-testid="gallery-prev"
              onClick={() => step(-1)}
              className="absolute left-2 top-1/2 -translate-y-1/2 grid h-9 w-9 place-items-center rounded-full bg-gallery-control/40 text-gallery-control-foreground opacity-0 transition-opacity hover:bg-gallery-control/60 focus-visible:opacity-100 group-hover:opacity-100"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
            <button
              type="button"
              aria-label={t("catalog.gallery.nextImage")}
              data-testid="gallery-next"
              onClick={() => step(1)}
              className="absolute right-2 top-1/2 -translate-y-1/2 grid h-9 w-9 place-items-center rounded-full bg-gallery-control/40 text-gallery-control-foreground opacity-0 transition-opacity hover:bg-gallery-control/60 focus-visible:opacity-100 group-hover:opacity-100"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
            <div className="pointer-events-none absolute right-2 top-2 rounded bg-gallery-control/50 px-1.5 py-0.5 text-xs text-gallery-control-foreground">
              {activeIdx + 1} / {total}
            </div>
          </>
        )}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {images.map((img, idx) => (
          <button
            key={img.id}
            type="button"
            data-testid="gallery-thumb"
            aria-label={t("catalog.gallery.thumbN", { n: idx + 1, total })}
            aria-pressed={img.id === active.id}
            onClick={() => setActiveId(img.id)}
            className={`aspect-square overflow-hidden rounded ${
              img.id === active.id ? "ring-2 ring-ring" : "opacity-70 hover:opacity-100"
            }`}
          >
            <img
              src={srcFor(modelId, img.id)}
              alt={img.original_name}
              loading="lazy"
              className="h-full w-full object-cover"
            />
          </button>
        ))}
      </div>
    </div>
  );
}
