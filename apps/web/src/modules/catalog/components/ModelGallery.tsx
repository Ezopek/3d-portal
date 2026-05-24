import { ChevronLeft, ChevronRight, Maximize2 } from "lucide-react";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import type { ModelFileRead } from "@/lib/api-types";
import { cn } from "@/lib/utils";
// Story 22.3 (TB-037 viewer) — symmetric fullscreen image viewer mount.
// Imported via the lazy barrel so the viewer body is code-split out of the
// catalog detail route's initial chunk per [[feedback_lazy_import_discipline]].
// Wrapped in <Suspense fallback={null}> below.
import {
  ImageFullscreenViewer,
  type ImageSource,
} from "@/modules/catalog/components/imageViewer";

function isImage(f: ModelFileRead): boolean {
  return f.kind === "image" || f.kind === "print";
}

function srcFor(modelId: string, fileId: string): string {
  return `/api/models/${modelId}/files/${fileId}/content`;
}

// Story 22.2 (FR16-CAROUSEL-TIER-1) — catalog detail main frame requests
// the gallery tier variant (~150-500 KB). Story 22.1 (commit a04a61f)
// shipped backend variant routing on the authenticated
// /api/models/<id>/files/<fid>/content endpoint; it falls back silently
// to the original blob when the `.gallery.webp` sibling is missing,
// keeping rollout backward-compatible while the .190 backfill runs.
//
// Thumbnail strip below intentionally stays on the un-varianted srcFor
// for this story (operator scope: main frame only). A follow-up story
// could migrate the strip to `?variant=thumb` to mirror CardCarousel
// (Story 13.2) and avoid pulling original blobs at thumb resolution.
function galleryUrlFor(modelId: string, fileId: string): string {
  return `${srcFor(modelId, fileId)}?variant=gallery`;
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
  // Memoise the filtered + reordered image list so downstream `useMemo`
  // deps stay reference-stable across renders (also flags identity to the
  // exhaustive-deps lint).
  const images = useMemo(
    () => withThumbnailFirst(files.filter(isImage), thumbnailFileId),
    [files, thumbnailFileId],
  );
  const [activeId, setActiveId] = useState<string | null>(images[0]?.id ?? null);
  const [imageLoaded, setImageLoaded] = useState(false);
  // Story 22.3 — fullscreen viewer mount state. Hooks placed above the
  // early return so they fire on every render path (rules-of-hooks). The
  // heavy `ImageFullscreenViewer` module only resolves the first time the
  // user opens fullscreen (lazy barrel).
  const [fullscreenOpen, setFullscreenOpen] = useState(false);
  const viewerSources = useMemo<ImageSource[]>(
    () =>
      images.map((img) => ({
        // ?variant=full requests the original blob (Story 22.1 router
        // collapses ?variant=full to the un-varianted path; the explicit
        // query string keeps the URL stable across re-renders for cache
        // dedupe purposes).
        fullUrl: `${srcFor(modelId, img.id)}?variant=full`,
        thumbUrl: `${srcFor(modelId, img.id)}?variant=thumb`,
        alt: img.original_name,
      })),
    [images, modelId],
  );
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
        <button
          type="button"
          data-testid="gallery-fullscreen-trigger"
          onClick={() => setFullscreenOpen(true)}
          aria-label={t("catalog.image_viewer.trigger_label")}
          className="absolute inset-0 block h-full w-full cursor-zoom-in"
        >
          <img
            data-testid="gallery-main"
            src={galleryUrlFor(modelId, active.id)}
            alt={active.original_name}
            onLoad={() => setImageLoaded(true)}
            onError={() => setImageLoaded(true)}
            className={cn(
              "h-full w-full object-contain transition duration-150 will-change-[filter,opacity]",
              imageLoaded
                ? "scale-100 blur-0 opacity-100"
                : "scale-105 blur-[8px] opacity-25",
            )}
          />
        </button>
        <button
          type="button"
          data-testid="gallery-fullscreen-icon"
          onClick={() => setFullscreenOpen(true)}
          aria-label={t("catalog.image_viewer.trigger_label")}
          title={t("catalog.image_viewer.trigger_tooltip")}
          className="absolute right-2 top-2 grid h-9 w-9 place-items-center rounded-full bg-gallery-control/40 text-gallery-control-foreground transition-opacity hover:bg-gallery-control/60 focus-visible:opacity-100 sm:opacity-0 sm:group-hover:opacity-100"
        >
          <Maximize2 className="h-4 w-4" />
        </button>
        {total > 1 && (
          <>
            <button
              type="button"
              aria-label={t("catalog.gallery.previousImage")}
              data-testid="gallery-prev"
              onClick={() => step(-1)}
              className="absolute left-2 top-1/2 -translate-y-1/2 grid h-9 w-9 place-items-center rounded-full bg-gallery-control/40 text-gallery-control-foreground transition-opacity hover:bg-gallery-control/60 focus-visible:opacity-100 sm:opacity-0 sm:group-hover:opacity-100"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
            <button
              type="button"
              aria-label={t("catalog.gallery.nextImage")}
              data-testid="gallery-next"
              onClick={() => step(1)}
              className="absolute right-2 top-1/2 -translate-y-1/2 grid h-9 w-9 place-items-center rounded-full bg-gallery-control/40 text-gallery-control-foreground transition-opacity hover:bg-gallery-control/60 focus-visible:opacity-100 sm:opacity-0 sm:group-hover:opacity-100"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
            {/* Counter moved to bottom-right to leave top-right for the
                Story 22.3 Maximize2 fullscreen trigger (designer §2). */}
            <div className="pointer-events-none absolute bottom-2 right-2 rounded bg-gallery-control/50 px-1.5 py-0.5 text-xs text-gallery-control-foreground">
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
      {fullscreenOpen && (
        <Suspense fallback={null}>
          <ImageFullscreenViewer
            sources={viewerSources}
            initialIndex={activeIdx}
            onClose={() => setFullscreenOpen(false)}
            renderImage={({ src, alt, className }) => (
              <img src={src} alt={alt} className={className} />
            )}
          />
        </Suspense>
      )}
    </div>
  );
}
