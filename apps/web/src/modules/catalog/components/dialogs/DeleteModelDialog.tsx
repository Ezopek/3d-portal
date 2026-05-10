import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { ModelDetail } from "@/lib/api-types";
import { useDeleteModel } from "@/modules/catalog/hooks/mutations/useDeleteModel";
import { Button } from "@/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/ui/dialog";
import { Input } from "@/ui/input";

interface Props {
  detail: ModelDetail;
  open: boolean;
  onOpenChange: (next: boolean) => void;
  onDeleted?: () => void;
}

export function DeleteModelDialog({ detail, open, onOpenChange, onDeleted }: Props) {
  const { t } = useTranslation();
  const [confirmText, setConfirmText] = useState("");
  const del = useDeleteModel(detail.id);
  const ok = confirmText === detail.name_en;

  // Single close handler so EVERY close path (Cancel button, Escape,
  // overlay click, programmatic) clears the input. P2-6 fix: previously
  // Cancel called onOpenChange(false) directly, bypassing the clear logic
  // wrapped in Dialog.onOpenChange — typing the name then clicking Cancel
  // left it primed for the next open. Caught by Codex review of f631beb.
  function handleClose() {
    setConfirmText("");
    onOpenChange(false);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) handleClose();
        else onOpenChange(true);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("catalog.deleteDialog.title")}</DialogTitle>
          <DialogDescription>
            {t("catalog.deleteDialog.description")}{" "}
            <code className="rounded bg-muted px-1">{detail.name_en}</code>
          </DialogDescription>
        </DialogHeader>
        <Input
          value={confirmText}
          onChange={(e) => setConfirmText(e.target.value)}
          placeholder={detail.name_en}
        />
        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            {t("common.cancel")}
          </Button>
          <Button
            variant="destructive"
            disabled={!ok || del.isPending}
            onClick={() =>
              del.mutate(
                { hard: false },
                {
                  onSuccess: () => {
                    handleClose();
                    onDeleted?.();
                  },
                },
              )
            }
          >
            {t("catalog.actions.delete")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
