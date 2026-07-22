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

// Create an empty facet group (Story 46.2). Slug is required here (unlike rename,
// where slugs are immutable). Presentational: the caller owns the mutation, the
// `position` (appended at end), the success toast, and close.
export interface CreateGroupDialogProps {
  open: boolean;
  onOpenChange: (next: boolean) => void;
  pending: boolean;
  errorMessage: string | null;
  onSubmit: (values: { slug: string; name_en: string; name_pl: string | null }) => void;
}

export function CreateGroupDialog({
  open,
  onOpenChange,
  pending,
  errorMessage,
  onSubmit,
}: CreateGroupDialogProps) {
  const { t } = useTranslation();
  const [slug, setSlug] = useState("");
  const [nameEn, setNameEn] = useState("");
  const [namePl, setNamePl] = useState("");

  useEffect(() => {
    if (open) {
      setSlug("");
      setNameEn("");
      setNamePl("");
    }
  }, [open]);

  const canSubmit = slug.trim() !== "" && nameEn.trim() !== "" && !pending;

  function handleSubmit() {
    if (!canSubmit) return;
    const trimmedPl = namePl.trim();
    onSubmit({
      slug: slug.trim(),
      name_en: nameEn.trim(),
      name_pl: trimmedPl === "" ? null : trimmedPl,
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("modules.admin.tagGroups.create.title")}</DialogTitle>
          <DialogDescription className="sr-only">
            {t("modules.admin.tagGroups.create.description")}
          </DialogDescription>
        </DialogHeader>
        <form
          className="flex flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit();
          }}
        >
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">{t("modules.admin.tagGroups.fields.slug")}</span>
            <Input value={slug} onChange={(e) => setSlug(e.target.value)} disabled={pending} />
          </label>
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
              {t("modules.admin.tagGroups.create.submit")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
