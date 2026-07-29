import { useTranslation } from "react-i18next";

import { Button } from "@/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/ui/dialog";

// Story 52.2 — category delete, with the TWO independent 409 conflict sources
// kept as two distinct states (D-8). Collapsing them would offer a fix that
// provably cannot work: `detach=true` resolves `category_in_use` and does NOT
// resolve `category_has_children`, which the API checks first and
// unconditionally.
//
// This is one of the two places `destructive` is the correct colour on this
// surface (DESIGN.md: failed writes and the 409 delete path). Nothing on the
// curation side is ever destructive — every finding there is advisory.
export type DeleteConflict = "none" | "in_use" | "has_children";

export interface DeleteCategoryDialogProps {
  open: boolean;
  onOpenChange: (next: boolean) => void;
  categoryName: string;
  /** Assignment count, shown when the API reports `category_in_use`. */
  modelCount: number;
  conflict: DeleteConflict;
  pending: boolean;
  errorMessage: string | null;
  /** `detach` is only ever true after the admin explicitly confirms it. */
  onConfirm: (detach: boolean) => void;
}

export function DeleteCategoryDialog({
  open,
  onOpenChange,
  categoryName,
  modelCount,
  conflict,
  pending,
  errorMessage,
  onConfirm,
}: DeleteCategoryDialogProps) {
  const { t } = useTranslation();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {t("modules.admin.categories.delete.title", { name: categoryName })}
          </DialogTitle>
          <DialogDescription className="sr-only">
            {t("modules.admin.categories.delete.description")}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3 text-sm">
          {/* The first screen must not assert "no assigned models" for a category
              whose count is rendered in the very row the admin opened this from.
              `model_count` is already in hand, so the truthful branch is free —
              and stating up front that the delete will be refused is not a
              detach affordance: the first attempt still omits `detach` (D-8). */}
          {conflict === "none" ? (
            <p className="text-muted-foreground">
              {modelCount > 0
                ? t("modules.admin.categories.delete.confirm_assigned", { count: modelCount })
                : t("modules.admin.categories.delete.confirm_clean")}
            </p>
          ) : null}

          {conflict === "in_use" ? (
            <div
              className="flex flex-col gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3"
              role="alert"
            >
              {/* `model_count` counts only NON-deleted models (Decision AY) while
                  the 409 is raised over ALL assignment rows including those of
                  soft-deleted models — `delete_browse_category` documents exactly
                  this divergence. Naming "0 models are assigned" while offering a
                  destructive detach would understate what the detach removes, so
                  the zero case drops the count and says what detach actually costs. */}
              <p className="font-medium text-destructive">
                {modelCount > 0
                  ? t("modules.admin.categories.delete.in_use_title", { count: modelCount })
                  : t("modules.admin.categories.delete.in_use_title_hidden")}
              </p>
              <p className="text-muted-foreground">
                {modelCount > 0
                  ? t("modules.admin.categories.delete.in_use_body")
                  : t("modules.admin.categories.delete.in_use_body_hidden")}
              </p>
            </div>
          ) : null}

          {conflict === "has_children" ? (
            <div
              className="flex flex-col gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3"
              role="alert"
            >
              <p className="font-medium text-destructive">
                {t("modules.admin.categories.delete.has_children_title")}
              </p>
              {/* Deliberately offers NO detach action: `detach=true` does not
                  resolve this branch, so an affordance here would be a lie. */}
              <p className="text-muted-foreground">
                {t("modules.admin.categories.delete.has_children_body")}
              </p>
            </div>
          ) : null}

          {errorMessage ? (
            <p className="text-sm text-destructive" role="alert">
              {errorMessage}
            </p>
          ) : null}
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={pending}
          >
            {t("common.cancel")}
          </Button>
          {conflict === "none" ? (
            <Button type="button" variant="destructive" disabled={pending} onClick={() => onConfirm(false)}>
              {t("modules.admin.categories.delete.submit")}
            </Button>
          ) : null}
          {conflict === "in_use" ? (
            <Button type="button" variant="destructive" disabled={pending} onClick={() => onConfirm(true)}>
              {t("modules.admin.categories.delete.submit_detach")}
            </Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
