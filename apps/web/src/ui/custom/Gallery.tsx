import { Star } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { GalleryImage } from "@/lib/galleryCandidates";

export type { GalleryImage };

interface Props {
  images: GalleryImage[];
  currentDefaultPath?: string | null;
  onSetDefault?: (path: string) => void;
  onClearDefault?: () => void;
}

export function Gallery({ images, currentDefaultPath, onSetDefault, onClearDefault }: Props) {
  const { t } = useTranslation();
  const [active, setActive] = useState(0);
  if (images.length === 0) {
    return (
      <div className="mx-auto aspect-square w-full max-w-[70vh] rounded-md bg-muted text-center text-sm text-muted-foreground">
        <div className="grid h-full place-items-center">{t("catalog.no_preview")}</div>
      </div>
    );
  }
  const safe = images[active] ?? images[0]!;
  const adminControls = onSetDefault !== undefined;

  return (
    <div>
      <div className="relative mx-auto aspect-square w-full max-w-[70vh] overflow-hidden rounded-md bg-muted">
        <img src={safe.url} alt="" className="h-full w-full object-contain" />
        {adminControls && (
          <StarBadge
            active={safe.path === currentDefaultPath}
            onClick={() => {
              if (safe.path === currentDefaultPath) {
                onClearDefault?.();
              } else {
                onSetDefault!(safe.path);
              }
            }}
            tooltipActive={t("catalog.current_default_thumbnail")}
            tooltipInactive={t("catalog.set_default_thumbnail")}
          />
        )}
      </div>
      {images.length > 1 && (
        <div className="mt-2 flex gap-2 overflow-x-auto">
          {images.map((img, i) => (
            <button
              key={img.path}
              type="button"
              onClick={() => setActive(i)}
              className={`relative size-16 shrink-0 overflow-hidden rounded ${
                i === active ? "ring-2 ring-ring" : ""
              }`}
            >
              <img src={img.url} alt="" className="h-full w-full object-cover" />
              {adminControls && img.path === currentDefaultPath && (
                <Star
                  className="absolute right-0.5 top-0.5 size-4 fill-yellow-400 stroke-yellow-500"
                  aria-hidden
                />
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

interface StarBadgeProps {
  active: boolean;
  onClick: () => void;
  tooltipActive: string;
  tooltipInactive: string;
}

function StarBadge({ active, onClick, tooltipActive, tooltipInactive }: StarBadgeProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={active ? tooltipActive : tooltipInactive}
      className="absolute right-2 top-2 grid size-9 place-items-center rounded-full bg-background/80 backdrop-blur transition-colors hover:bg-background"
    >
      <Star
        className={`size-5 ${active ? "fill-yellow-400 stroke-yellow-500" : "stroke-current"}`}
        aria-hidden
      />
    </button>
  );
}
