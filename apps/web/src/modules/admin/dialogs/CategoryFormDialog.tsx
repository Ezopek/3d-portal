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

// Story 52.2 — create/edit a browse category. One dialog, two modes, because
// the field set is identical apart from `slug`, which is create-only (the slug
// is the stable public address `/categories/{slug}`, so this surface does not
// offer to rewrite it and silently break every existing link).
//
// `inclusion_criterion` is a first-class field here, not an afterthought: it is
// the admission test FR26-GOV-1 requires every category to carry, and until
// Story 52.2's admin read shipped there was no way to see the current value at
// all. An emptied criterion is reported as `null` so the caller can CLEAR it —
// the API's documented null-semantics for this field.
export interface CategoryFormValues {
  slug: string;
  name_en: string;
  name_pl: string | null;
  inclusion_criterion: string | null;
}

export interface CategoryFormDialogProps {
  open: boolean;
  onOpenChange: (next: boolean) => void;
  mode: "create" | "edit";
  initial?: {
    slug: string;
    name_en: string;
    name_pl: string | null;
    inclusion_criterion: string | null;
  };
  pending: boolean;
  errorMessage: string | null;
  onSubmit: (values: CategoryFormValues) => void;
}

export function CategoryFormDialog({
  open,
  onOpenChange,
  mode,
  initial,
  pending,
  errorMessage,
  onSubmit,
}: CategoryFormDialogProps) {
  const { t } = useTranslation();
  const [slug, setSlug] = useState(initial?.slug ?? "");
  const [nameEn, setNameEn] = useState(initial?.name_en ?? "");
  const [namePl, setNamePl] = useState(initial?.name_pl ?? "");
  const [criterion, setCriterion] = useState(initial?.inclusion_criterion ?? "");

  // Reset on (re)open so an aborted edit never leaks into the next target —
  // the same guard RenameEntityDialog/CreateGroupDialog already apply.
  useEffect(() => {
    if (open) {
      setSlug(initial?.slug ?? "");
      setNameEn(initial?.name_en ?? "");
      setNamePl(initial?.name_pl ?? "");
      setCriterion(initial?.inclusion_criterion ?? "");
    }
  }, [open, initial]);

  const isCreate = mode === "create";
  const canSubmit = (!isCreate || slug.trim() !== "") && nameEn.trim() !== "" && !pending;

  function handleSubmit() {
    if (!canSubmit) return;
    const trimmedPl = namePl.trim();
    const trimmedCriterion = criterion.trim();
    onSubmit({
      slug: slug.trim(),
      name_en: nameEn.trim(),
      name_pl: trimmedPl === "" ? null : trimmedPl,
      inclusion_criterion: trimmedCriterion === "" ? null : trimmedCriterion,
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {isCreate
              ? t("modules.admin.categories.form.title_create")
              : t("modules.admin.categories.form.title_edit")}
          </DialogTitle>
          <DialogDescription className="sr-only">
            {t("modules.admin.categories.form.description")}
          </DialogDescription>
        </DialogHeader>
        <form
          className="flex flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit();
          }}
        >
          {isCreate ? (
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">{t("modules.admin.categories.fields.slug")}</span>
              <Input value={slug} onChange={(e) => setSlug(e.target.value)} disabled={pending} />
            </label>
          ) : null}
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">{t("modules.admin.categories.fields.name_en")}</span>
            <Input value={nameEn} onChange={(e) => setNameEn(e.target.value)} disabled={pending} />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">{t("modules.admin.categories.fields.name_pl")}</span>
            <Input
              value={namePl}
              onChange={(e) => setNamePl(e.target.value)}
              disabled={pending}
              placeholder={t("modules.admin.categories.fields.name_pl_placeholder")}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">{t("modules.admin.categories.fields.criterion")}</span>
            {/* Native textarea rather than a new `ui/` primitive: adding one
                would trigger the Visual Coverage Contract for a control used on
                exactly one surface. Classes mirror `ui/input.tsx`'s vocabulary. */}
            <textarea
              value={criterion}
              onChange={(e) => setCriterion(e.target.value)}
              disabled={pending}
              rows={2}
              placeholder={t("modules.admin.categories.fields.criterion_placeholder")}
              className="min-h-16 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
            />
            <span className="text-xs text-muted-foreground">
              {t("modules.admin.categories.fields.criterion_hint")}
            </span>
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
              {isCreate
                ? t("modules.admin.categories.form.submit_create")
                : t("common.save")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
