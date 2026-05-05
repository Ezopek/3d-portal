import { useState } from "react";

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
  const [confirmText, setConfirmText] = useState("");
  const del = useDeleteModel(detail.id);
  const ok = confirmText === detail.name_en;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete model</DialogTitle>
          <DialogDescription>
            This soft-deletes the model. You can restore it later. Type the name (
            <code className="rounded bg-muted px-1">{detail.name_en}</code>) to confirm.
          </DialogDescription>
        </DialogHeader>
        <Input
          value={confirmText}
          onChange={(e) => setConfirmText(e.target.value)}
          placeholder={detail.name_en}
        />
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={!ok || del.isPending}
            onClick={() =>
              del.mutate(
                { hard: false },
                {
                  onSuccess: () => {
                    setConfirmText("");
                    onOpenChange(false);
                    onDeleted?.();
                  },
                },
              )
            }
          >
            Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
