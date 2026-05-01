import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { Card, CardContent } from "@/ui/card";

import type { ModelListItem } from "@/modules/catalog/types";

import { CardCarousel } from "./CardCarousel";
import { SourceBadge } from "./SourceBadge";
import { StatusBadge } from "./StatusBadge";

export function ModelCard({ model }: { model: ModelListItem }) {
  const { i18n } = useTranslation();
  const primary = i18n.language.startsWith("pl") ? model.name_pl : model.name_en;
  const secondary = i18n.language.startsWith("pl") ? model.name_en : model.name_pl;
  const topTags = model.tags.slice(0, 2);
  return (
    <Link to="/catalog/$id" params={{ id: model.id }}>
      <Card className="overflow-hidden border-border bg-card transition-colors hover:border-ring">
        {model.image_count >= 2 ? (
          <CardCarousel
            modelId={model.id}
            // ModelListItem doesn't carry model.path or prints[]. The CardCarousel/useGallery
            // pair uses pickGalleryCandidates' empty-prints fallback path, which discovers
            // prints/*.{png,jpg,webp} from the lazy /files response.
            modelPath=""
            prints={[]}
            initialThumbnailUrl={model.thumbnail_url}
            imageCount={model.image_count}
            alt={primary}
          />
        ) : (
          <div className="aspect-square bg-muted">
            {model.thumbnail_url !== null ? (
              <img
                src={`${model.thumbnail_url}?w=480`}
                srcSet={`${model.thumbnail_url}?w=480 1x, ${model.thumbnail_url}?w=960 2x`}
                alt={primary}
                className="h-full w-full object-cover"
                loading="lazy"
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
            <p className="line-clamp-1 text-xs text-muted-foreground">{secondary}</p>
          </div>
          {topTags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {topTags.map((tag) => (
                <span
                  key={tag}
                  data-testid="tag-chip"
                  className="rounded bg-muted px-1.5 py-0.5 text-xs text-chip-foreground"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
