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
import { Input } from "@/ui/input";

// Generic display-name editor (Story 46.2), reused for tag rename and group
// rename. Presentational: the caller owns the mutation, success toast, and close;
// this dialog only collects `name_en` (required) + `name_pl` (nullable) and reports
// them. An emptied Polish field is reported as `null` so the caller can clear it.
export interface RenameEntityDialogProps {
  open: boolean;
  onOpenChange: (next: boolean) => void;
  title: string;
  /** Accessible description; rendered screen-reader-only for a11y parity with Move/Merge. */
  description?: string;
  initialNameEn: string;
  initialNamePl: string | null;
  pending: boolean;
  errorMessage: string | null;
  onSubmit: (values: { name_en: string; name_pl: string | null }) => void;
}

export function RenameEntityDialog({
  open,
  onOpenChange,
  title,
  description,
  initialNameEn,
  initialNamePl,
  pending,
  errorMessage,
  onSubmit,
}: RenameEntityDialogProps) {
  const { t } = useTranslation();
  const [nameEn, setNameEn] = useState(initialNameEn);
  const [namePl, setNamePl] = useState(initialNamePl ?? "");

  // Reset local edits whenever the dialog (re)opens so a prior aborted edit does
  // not leak into the next target.
  useEffect(() => {
    if (open) {
      setNameEn(initialNameEn);
      setNamePl(initialNamePl ?? "");
    }
  }, [open, initialNameEn, initialNamePl]);

  const canSubmit = nameEn.trim() !== "" && !pending;

  function handleSubmit() {
    if (!canSubmit) return;
    const trimmedPl = namePl.trim();
    onSubmit({ name_en: nameEn.trim(), name_pl: trimmedPl === "" ? null : trimmedPl });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description ? (
            <DialogDescription className="sr-only">{description}</DialogDescription>
          ) : null}
        </DialogHeader>
        <form
          className="flex flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit();
          }}
        >
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">{t("modules.admin.tagGroups.fields.name_en")}</span>
            <Input value={nameEn} onChange={(e) => setNameEn(e.target.value)} disabled={pending} />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">{t("modules.admin.tagGroups.fields.name_pl")}</span>
            <Input
              value={namePl}
              onChange={(e) => setNamePl(e.target.value)}
              disabled={pending}
              placeholder={t("modules.admin.tagGroups.fields.name_pl_placeholder")}
            />
          </label>
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
            <Button type="submit" disabled={!canSubmit}>
              {t("common.save")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
