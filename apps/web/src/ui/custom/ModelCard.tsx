import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { ModelSummary } from "@/lib/api-types";
import { Card, CardContent } from "@/ui/card";

import { CardCarousel } from "./CardCarousel";
import { SourceBadge } from "./SourceBadge";
import { StatusBadge } from "./StatusBadge";

export function ModelCard({ model }: { model: ModelSummary }) {
  const { i18n } = useTranslation();
  const [imageLoaded, setImageLoaded] = useState(false);
  const primary = i18n.language.startsWith("pl") && model.name_pl !== null ? model.name_pl : model.name_en;
  const secondary =
    i18n.language.startsWith("pl") ? model.name_en : (model.name_pl ?? "");
  const topTags = model.tags.slice(0, 2);
  const linkId = model.id;
  const thumbUrl =
    model.thumbnail_file_id !== null
      ? `/api/models/${model.id}/files/${model.thumbnail_file_id}/content`
      : null;
  const showCarousel =
    model.image_count >= 2 && model.gallery_file_ids.length >= 2;
  return (
    <Link to="/catalog/$id" params={{ id: linkId }}>
      <Card className="overflow-hidden border-border bg-card transition-colors hover:border-ring">
        {showCarousel ? (
          <CardCarousel
            modelId={model.id}
            fileIds={model.gallery_file_ids}
            alt={primary}
          />
        ) : (
          <div
            className={`aspect-square bg-muted ${
              thumbUrl !== null && !imageLoaded ? "animate-pulse" : ""
            }`}
          >
            {thumbUrl !== null ? (
              <img
                src={thumbUrl}
                alt={primary}
                className="h-full w-full object-cover"
                loading="lazy"
                onLoad={() => setImageLoaded(true)}
              />
            ) : (
              <div className="grid h-full place-items-center text-muted-foreground">
                <span className="text-xs">no preview</span>
              </div>
            )}
          </div>
        )}
        <CardContent className="space-y-2 p-3">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <StatusBadge status={model.status} />
            <SourceBadge source={model.source} />
          </div>
          <div>
            <p className="line-clamp-1 text-sm font-medium text-card-foreground">{primary}</p>
            {secondary !== "" && (
              <p className="line-clamp-1 text-xs text-muted-foreground">{secondary}</p>
            )}
          </div>
          {topTags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {topTags.map((tag) => (
                <span
                  key={tag.id}
                  data-testid="tag-chip"
                  className="rounded bg-muted px-1.5 py-0.5 text-xs text-chip-foreground"
                >
                  {tag.slug}
                </span>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
