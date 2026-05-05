import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { ModelDetail } from "@/lib/api-types";
import { DeleteModelDialog } from "@/modules/catalog/components/dialogs/DeleteModelDialog";
import { RatingPopover } from "@/modules/catalog/components/popovers/RatingPopover";
import { StatusPopover } from "@/modules/catalog/components/popovers/StatusPopover";
import { EditDescriptionSheet } from "@/modules/catalog/components/sheets/EditDescriptionSheet";
import { EditTagsSheet } from "@/modules/catalog/components/sheets/EditTagsSheet";
import { useAuth } from "@/shell/AuthContext";
import { Button } from "@/ui/button";
import { SourceBadge } from "@/ui/custom/SourceBadge";
import { StatusBadge } from "@/ui/custom/StatusBadge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/ui/dropdown-menu";

const TAG_DISPLAY_LIMIT = 5;

export function ModelHero({ detail }: { detail: ModelDetail }) {
  const { i18n } = useTranslation();
  const { isAdmin } = useAuth();
  const [tagsOpen, setTagsOpen] = useState(false);
  const [descriptionOpen, setDescriptionOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

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

  const ratingLabel =
    detail.rating !== null ? (
      <span className="text-xs text-muted-foreground">★ {detail.rating.toFixed(1)}</span>
    ) : (
      <span className="text-xs text-muted-foreground">★ —</span>
    );

  return (
    <div className="border-b border-border bg-background p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-xs text-muted-foreground">
            All › <span>{catName}</span>
          </div>
          <h1 className="mt-1 text-xl font-semibold text-foreground">{title}</h1>
        </div>
        {isAdmin && (
          <DropdownMenu>
            <DropdownMenuTrigger
              render={
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label="Model actions"
                />
              }
            >
              ⋮
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => setDescriptionOpen(true)}>
                Edit description
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setDeleteOpen(true)}>
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1">
        {isAdmin ? (
          <StatusPopover modelId={detail.id} current={detail.status}>
            <span className="cursor-pointer">
              <StatusBadge status={detail.status} />
            </span>
          </StatusPopover>
        ) : (
          <StatusBadge status={detail.status} />
        )}
        {isAdmin ? (
          <RatingPopover modelId={detail.id} current={detail.rating}>
            <span className="cursor-pointer">{ratingLabel}</span>
          </RatingPopover>
        ) : (
          detail.rating !== null && (
            <span className="text-xs text-muted-foreground">★ {detail.rating.toFixed(1)}</span>
          )
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
        {isAdmin && (
          <button
            type="button"
            aria-label="Edit tags"
            onClick={() => setTagsOpen(true)}
            className="text-xs text-muted-foreground opacity-50 hover:opacity-100"
          >
            ✏
          </button>
        )}
      </div>
      {isAdmin && (
        <>
          <EditTagsSheet detail={detail} open={tagsOpen} onOpenChange={setTagsOpen} />
          <EditDescriptionSheet
            detail={detail}
            open={descriptionOpen}
            onOpenChange={setDescriptionOpen}
          />
          <DeleteModelDialog
            detail={detail}
            open={deleteOpen}
            onOpenChange={setDeleteOpen}
          />
        </>
      )}
    </div>
  );
}
