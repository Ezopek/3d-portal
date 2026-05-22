import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import type { ModelDetail } from "@/lib/api-types";
import { useUpsertDescription } from "@/modules/catalog/hooks/mutations/useUpsertDescription";
import { Button } from "@/ui/button";
import { Sheet, SheetContent, SheetFooter, SheetHeader, SheetTitle } from "@/ui/sheet";

interface Props {
  detail: ModelDetail;
  open: boolean;
  onOpenChange: (next: boolean) => void;
}

export function EditDescriptionSheet({ detail, open, onOpenChange }: Props) {
  const { t } = useTranslation();
  const existing = detail.notes.find((n) => n.kind === "description") ?? null;
  // Initiative 10 Story 16.2 revised — bilingual editor. Seed each textarea
  // from its OWN localized field. Do NOT fall back from body_en to legacy
  // `body`: the legacy field is language-ambiguous (pre-bilingual catalog
  // has a mix of EN and PL content) and Story 16.1's migration backfilled
  // body → body_en wholesale, so the legacy body for any post-migration
  // row already lives in body_en (or is null if the row was post-migration
  // empty). For pre-migration legacy rows we deliberately surface empty
  // textareas — the operator's intent in opening the editor is to populate
  // the bilingual fields cleanly, not inherit potentially-mislabeled
  // legacy text into the wrong locale slot (Codex P2 2026-05-22).
  const [bodyPl, setBodyPl] = useState(existing?.body_pl ?? "");
  const [bodyEn, setBodyEn] = useState(existing?.body_en ?? "");
  const upsert = useUpsertDescription();

  useEffect(() => {
    if (open) {
      setBodyPl(existing?.body_pl ?? "");
      setBodyEn(existing?.body_en ?? "");
    }
  }, [open, existing?.body_en, existing?.body_pl]);

  function save() {
    upsert.mutate(
      {
        modelId: detail.id,
        existingId: existing?.id ?? null,
        body_pl: bodyPl,
        body_en: bodyEn,
      },
      {
        onSuccess: () => {
          toast.success(t("catalog.actions.description_saved"));
          onOpenChange(false);
        },
        onError: (err) => toast.error(err.message),
      },
    );
  }

  const bothEmpty = bodyPl.trim() === "" && bodyEn.trim() === "";

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>{t("catalog.actions.editDescription")}</SheetTitle>
        </SheetHeader>
        <div className="mt-4 space-y-4">
          <label className="block space-y-1">
            <span className="text-sm font-medium">
              {t("catalog.description.body_en")}
            </span>
            <textarea
              value={bodyEn}
              onChange={(e) => setBodyEn(e.target.value)}
              rows={10}
              aria-label={t("catalog.description.body_en")}
              className="w-full rounded border border-border bg-background p-2 text-sm"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-sm font-medium">
              {t("catalog.description.body_pl")}
            </span>
            <textarea
              value={bodyPl}
              onChange={(e) => setBodyPl(e.target.value)}
              rows={10}
              aria-label={t("catalog.description.body_pl")}
              className="w-full rounded border border-border bg-background p-2 text-sm"
            />
          </label>
          <p className="text-xs text-muted-foreground">
            {t("catalog.description.bilingual_hint")}
          </p>
        </div>
        <SheetFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t("common.cancel")}
          </Button>
          <Button onClick={save} disabled={upsert.isPending || bothEmpty}>
            {upsert.isPending ? t("common.saving") : t("common.save")}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
