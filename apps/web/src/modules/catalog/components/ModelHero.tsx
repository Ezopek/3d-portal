import { MoreVertical, Pencil, Share2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { ModelDetail } from "@/lib/api-types";
import { DeleteModelDialog } from "@/modules/catalog/components/dialogs/DeleteModelDialog";
import { ShareLinkDialog } from "@/modules/catalog/components/dialogs/ShareLinkDialog";
import { RatingPopover } from "@/modules/catalog/components/popovers/RatingPopover";
import { StatusPopover } from "@/modules/catalog/components/popovers/StatusPopover";
import { EditDescriptionSheet } from "@/modules/catalog/components/sheets/EditDescriptionSheet";
import { EditTagsSheet } from "@/modules/catalog/components/sheets/EditTagsSheet";
import { RenderSheet } from "@/modules/catalog/components/sheets/RenderSheet";
import { TagGroupsSection } from "@/modules/catalog/components/TagGroupsSection";
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

export function ModelHero({ detail }: { detail: ModelDetail }) {
  const { t, i18n } = useTranslation();
  const { isAdmin, isAuthenticated } = useAuth();
  const [tagsOpen, setTagsOpen] = useState(false);
  const [descriptionOpen, setDescriptionOpen] = useState(false);
  const [renderSheetOpen, setRenderSheetOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);

  const preferPl = i18n.language.startsWith("pl");
  const title =
    preferPl && detail.name_pl !== null && detail.name_pl !== ""
      ? detail.name_pl
      : detail.name_en;

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
          <h1 className="text-xl font-semibold text-foreground">{title}</h1>
        </div>
        <div className="flex items-center gap-1">
          {isAuthenticated && (
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={t("share.dialog.title")}
              onClick={() => setShareOpen(true)}
            >
              <Share2 className="size-4" aria-hidden />
            </Button>
          )}
          {isAdmin && (
            <DropdownMenu>
              <DropdownMenuTrigger
                render={
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label={t("catalog.actions.modelActions")}
                  />
                }
              >
                <MoreVertical className="size-4" aria-hidden />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => setDescriptionOpen(true)}>
                  {t("catalog.actions.editDescription")}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setRenderSheetOpen(true)}>
                  {t("catalog.actions.rerender")}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setDeleteOpen(true)}>
                  {t("catalog.actions.delete")}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
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
        {isAdmin && (
          <button
            type="button"
            aria-label={t("catalog.actions.editTags")}
            onClick={() => setTagsOpen(true)}
            className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground opacity-50 hover:bg-accent hover:opacity-100"
          >
            <Pencil className="size-3" aria-hidden />
          </button>
        )}
      </div>
      <TagGroupsSection detail={detail} isAdmin={isAdmin} onAddTags={() => setTagsOpen(true)} />
      {isAdmin && (
        <>
          <EditTagsSheet detail={detail} open={tagsOpen} onOpenChange={setTagsOpen} isAdmin={isAdmin} />
          <EditDescriptionSheet
            detail={detail}
            open={descriptionOpen}
            onOpenChange={setDescriptionOpen}
          />
          <RenderSheet
            detail={detail}
            open={renderSheetOpen}
            onOpenChange={setRenderSheetOpen}
          />
          <DeleteModelDialog
            detail={detail}
            open={deleteOpen}
            onOpenChange={setDeleteOpen}
          />
        </>
      )}
      {isAuthenticated && (
        <ShareLinkDialog
          modelId={detail.id}
          modelName={title}
          open={shareOpen}
          onOpenChange={setShareOpen}
        />
      )}
    </div>
  );
}
