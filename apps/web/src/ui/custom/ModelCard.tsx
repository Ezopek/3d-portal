import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { Card, CardContent } from "@/ui/card";

import type { ModelListItem } from "@/modules/catalog/types";

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
        <div className="aspect-square bg-muted">
          {model.thumbnail_url !== null ? (
            <img src={model.thumbnail_url} alt={primary} className="h-full w-full object-cover" loading="lazy" />
          ) : (
            <div className="grid h-full place-items-center text-muted-foreground">
              <span className="text-xs">no preview</span>
            </div>
          )}
        </div>
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
                <span key={tag} className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
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
