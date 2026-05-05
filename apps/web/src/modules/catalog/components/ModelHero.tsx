import { useTranslation } from "react-i18next";

import type { ModelDetail } from "@/lib/api-types";
import { SourceBadge } from "@/ui/custom/SourceBadge";
import { StatusBadge } from "@/ui/custom/StatusBadge";

const TAG_DISPLAY_LIMIT = 5;

export function ModelHero({ detail }: { detail: ModelDetail }) {
  const { i18n } = useTranslation();
  const preferPl = i18n.language.startsWith("pl");
  const title =
    preferPl && detail.name_pl !== null && detail.name_pl !== ""
      ? detail.name_pl
      : detail.name_en;
  const catName =
    preferPl && detail.category.name_pl !== null
      ? detail.category.name_pl
      : detail.category.name_en;
  const visibleTags = detail.tags.slice(0, TAG_DISPLAY_LIMIT);
  const overflow = detail.tags.length - visibleTags.length;
  return (
    <div className="border-b border-border bg-background p-4">
      <div className="text-xs text-muted-foreground">
        All › <span>{catName}</span>
      </div>
      <h1 className="mt-1 text-xl font-semibold text-foreground">{title}</h1>
      <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1">
        <StatusBadge status={detail.status} />
        {detail.rating !== null && (
          <span className="text-xs text-muted-foreground">★ {detail.rating.toFixed(1)}</span>
        )}
        <SourceBadge source={detail.source} />
        {visibleTags.map((tag) => (
          <span
            key={tag.id}
            data-testid="tag-chip"
            className="rounded bg-muted px-1.5 py-0.5 text-xs text-chip-foreground"
          >
            {tag.slug}
          </span>
        ))}
        {overflow > 0 && <span className="text-xs text-muted-foreground">+{overflow}</span>}
      </div>
    </div>
  );
}
