import { useEffect, useState } from "react";
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

// A merge survivor candidate. The caller supplies every OTHER loaded tag (source
// excluded); confirming deletes the source and reassigns its models to the survivor.
export interface MergeTargetOption {
  id: string;
  label: string;
}

export interface MergeTagDialogProps {
  open: boolean;
  onOpenChange: (next: boolean) => void;
  sourceName: string;
  options: MergeTargetOption[];
  pending: boolean;
  errorMessage: string | null;
  onSubmit: (targetId: string) => void;
}

export function MergeTagDialog({
  open,
  onOpenChange,
  sourceName,
  options,
  pending,
  errorMessage,
  onSubmit,
}: MergeTagDialogProps) {
  const { t } = useTranslation();
  const [selectedId, setSelectedId] = useState(options[0]?.id ?? "");

  // The parent rebuilds `options` as a fresh array every render, so this effect
  // runs on every incidental parent re-render (e.g. a window-focus refetch). Keep
  // the user's current choice if it's still valid; only fall back to the first
  // option when the selected survivor has disappeared. Resetting unconditionally
  // would silently snap the selection back to options[0] mid-interaction and merge
  // into the wrong (destructive) target.
  useEffect(() => {
    if (open) setSelectedId((prev) => (options.some((o) => o.id === prev) ? prev : (options[0]?.id ?? "")));
  }, [open, options]);

  const canSubmit = selectedId !== "" && !pending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("modules.admin.tagGroups.merge.title")}</DialogTitle>
          <DialogDescription>
            {t("modules.admin.tagGroups.merge.description", { name: sourceName })}
          </DialogDescription>
        </DialogHeader>
        <form
          className="flex flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (selectedId !== "") onSubmit(selectedId);
          }}
        >
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">{t("modules.admin.tagGroups.merge.target_label")}</span>
            <select
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
              disabled={pending}
              aria-label={t("modules.admin.tagGroups.merge.target_label")}
              className="h-8 w-full rounded-lg border border-input bg-background px-2.5 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-50"
            >
              {options.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          <p className="rounded-md border border-destructive/40 bg-destructive/10 p-2 text-sm text-destructive">
            {t("modules.admin.tagGroups.merge.warning", { name: sourceName })}
          </p>
          {errorMessage ? (
            <p className="text-sm text-destructive" role="alert">
              {errorMessage}
            </p>
          ) : null}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={pending}
            >
              {t("common.cancel")}
            </Button>
            <Button type="submit" variant="destructive" disabled={!canSubmit}>
              {t("modules.admin.tagGroups.merge.submit")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
