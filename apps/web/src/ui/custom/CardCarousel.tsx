import { ChevronLeft, ChevronRight } from "lucide-react";
import {
  type MouseEvent,
  type TouchEvent,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import type { PrintLike } from "@/lib/galleryCandidates";
import { useGallery } from "@/modules/catalog/hooks/useGallery";

interface Props {
  modelId: string;
  modelPath: string;
  prints: PrintLike[];
  initialThumbnailUrl: string | null;
  imageCount: number;
  alt: string;
}

const CARD_SRCSET_1X = 480;
const CARD_SRCSET_2X = 960;
const MAX_DOTS_VISIBLE = 7;
const SWIPE_THRESHOLD_PX = 40;
// After this many consecutive errors, give up early instead of cycling through
// all candidates — `pickGalleryCandidates` always appends 4 render fallbacks,
// and a user clicking through 4+ broken thumbnails is worse UX than just
// seeing the static thumbnail. This is in addition to `failedPaths` /
// `visibleList.length === 0`, which handle the case where every candidate
// is exhausted.
const MAX_CONSECUTIVE_GALLERY_ERRORS = 2;

function withWidth(url: string, width: number): string {
  const sep = url.includes("?") ? "&" : "?";
  return `${url}${sep}w=${width}`;
}

export function CardCarousel(props: Props) {
  const { modelId, modelPath, prints, initialThumbnailUrl, imageCount, alt } = props;
  const model = useMemo(
    () => ({ id: modelId, path: modelPath, prints }),
    [modelId, modelPath, prints],
  );
  const gallery = useGallery(model);

  const [index, setIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [touchStart, setTouchStart] = useState<{ x: number; y: number } | null>(null);
  const [failedPaths, setFailedPaths] = useState<ReadonlySet<string>>(new Set());
  const [errorCount, setErrorCount] = useState(0);

  const list = gallery.images;
  // If the lazy list arrived, derive the visible list by filtering out paths
  // that have errored. If everything errored or we exceed the retry budget,
  // give up and fall through to the initial thumbnail.
  const visibleList = useMemo(() => {
    if (list === undefined) return undefined;
    return list.filter((c) => !failedPaths.has(c.path));
  }, [list, failedPaths]);

  const galleryExhausted =
    errorCount >= MAX_CONSECUTIVE_GALLERY_ERRORS ||
    (list !== undefined && visibleList !== undefined && visibleList.length === 0);
  const total = list?.length ?? imageCount;
  const visibleCount = Math.min(total, MAX_DOTS_VISIBLE);

  const currentUrl = useMemo(() => {
    if (galleryExhausted) return initialThumbnailUrl ?? "";
    if (visibleList !== undefined) {
      const entry = visibleList[index];
      if (entry !== undefined) return entry.url;
    }
    return initialThumbnailUrl ?? "";
  }, [visibleList, index, initialThumbnailUrl, galleryExhausted]);

  const stop = (e: MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const advance = useCallback(
    (delta: number) => {
      if (list === undefined) {
        gallery.activate();
        // Pre-list: clamp to imageCount - 1 to avoid runaway index on rapid clicks.
        setIndex((i) => {
          const cap = Math.max(0, imageCount - 1);
          return Math.min(cap, Math.max(0, i + delta));
        });
        setIsLoading(true);
        return;
      }
      const len = visibleList?.length ?? 0;
      if (len <= 0) return;
      setIndex((i) => (((i + delta) % len) + len) % len);
      setIsLoading(true);
    },
    [list, gallery, imageCount, visibleList],
  );

  // When the lazy list arrives (or shrinks via errors), snap index back into
  // bounds against the visible (post-filter) list length.
  useEffect(() => {
    if (visibleList !== undefined && index >= visibleList.length) {
      setIndex(0);
    }
  }, [visibleList, index]);

  const handleNext = (e: MouseEvent) => {
    stop(e);
    advance(1);
  };
  const handlePrev = (e: MouseEvent) => {
    stop(e);
    advance(-1);
  };
  const handleDot = (e: MouseEvent, target: number) => {
    stop(e);
    if (list === undefined) gallery.activate();
    setIndex(target);
    setIsLoading(true);
  };

  const handleTouchStart = (e: TouchEvent) => {
    if (e.touches.length !== 1) {
      setTouchStart(null);
      return;
    }
    const t = e.touches[0];
    if (t === undefined) return;
    setTouchStart({ x: t.clientX, y: t.clientY });
  };
  const handleTouchEnd = (e: TouchEvent) => {
    if (touchStart === null) return;
    const t = e.changedTouches[0];
    if (t === undefined) {
      setTouchStart(null);
      return;
    }
    const dx = t.clientX - touchStart.x;
    const dy = t.clientY - touchStart.y;
    // Reject vertical-dominant gestures (likely scroll, not swipe).
    if (Math.abs(dy) > Math.abs(dx)) {
      setTouchStart(null);
      return;
    }
    if (Math.abs(dx) > SWIPE_THRESHOLD_PX) advance(dx < 0 ? 1 : -1);
    setTouchStart(null);
  };

  const onImgLoaded = () => setIsLoading(false);
  const onImgError = () => {
    setIsLoading(false);
    // Once we've fallen back to the initial thumbnail, additional onError
    // events shouldn't keep ticking the counter — the budget only applies
    // while we're still attempting gallery candidates.
    if (!galleryExhausted) {
      setErrorCount((n) => n + 1);
    }
    if (visibleList !== undefined && visibleList.length > 0) {
      const failed = visibleList[index];
      if (failed !== undefined) {
        setFailedPaths((prev) => new Set(prev).add(failed.path));
      }
      // The useEffect on visibleList length will normalise the index.
    }
  };

  // Hide the carousel chrome entirely if everything has errored — degrade to
  // the initial thumbnail with no arrows/dots.
  const showCarouselChrome = imageCount >= 2 && !galleryExhausted;

  return (
    <div
      className="group relative aspect-square bg-muted"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {currentUrl !== "" ? (
        <img
          src={withWidth(currentUrl, CARD_SRCSET_1X)}
          srcSet={`${withWidth(currentUrl, CARD_SRCSET_1X)} 1x, ${withWidth(currentUrl, CARD_SRCSET_2X)} 2x`}
          alt={alt}
          loading="lazy"
          onLoad={onImgLoaded}
          onError={onImgError}
          className={`h-full w-full object-cover transition-[filter] duration-150 ${
            isLoading ? "blur-[4px]" : "blur-0"
          }`}
        />
      ) : (
        <div className="grid h-full place-items-center text-muted-foreground">
          <span className="text-xs">no preview</span>
        </div>
      )}

      {showCarouselChrome && (
        <>
          <button
            type="button"
            aria-label="previous image"
            onClick={handlePrev}
            className="pointer-coarse:hidden absolute inset-y-0 left-0 hidden items-center justify-center px-1 transition-opacity group-hover:flex md:px-2"
          >
            <span className="rounded-full bg-background/70 p-1 backdrop-blur">
              <ChevronLeft className="size-4" aria-hidden />
            </span>
          </button>
          <button
            type="button"
            aria-label="next image"
            onClick={handleNext}
            className="pointer-coarse:hidden absolute inset-y-0 right-0 hidden items-center justify-center px-1 transition-opacity group-hover:flex md:px-2"
          >
            <span className="rounded-full bg-background/70 p-1 backdrop-blur">
              <ChevronRight className="size-4" aria-hidden />
            </span>
          </button>

          <div className="pointer-events-auto absolute inset-x-0 bottom-1 flex items-center justify-center gap-1">
            {Array.from({ length: visibleCount }).map((_, i) => {
              const active = i === Math.min(index, visibleCount - 1);
              return (
                <button
                  type="button"
                  key={i}
                  aria-label={`go to image ${i + 1}`}
                  aria-current={active ? "true" : undefined}
                  onClick={(e) => handleDot(e, i)}
                  className={`size-1.5 rounded-full transition-colors ${
                    active ? "bg-foreground/90" : "bg-foreground/30"
                  }`}
                />
              );
            })}
            {total > MAX_DOTS_VISIBLE && (
              <span className="ml-1 rounded-full bg-background/70 px-1 text-[10px] text-foreground/80 backdrop-blur">
                +{total - MAX_DOTS_VISIBLE}
              </span>
            )}
          </div>
        </>
      )}
    </div>
  );
}
