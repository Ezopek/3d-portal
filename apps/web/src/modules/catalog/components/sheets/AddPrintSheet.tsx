import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import type { PrintRead } from "@/lib/api-types";
import { useCreatePrint } from "@/modules/catalog/hooks/mutations/useCreatePrint";
import { useUpdatePrint } from "@/modules/catalog/hooks/mutations/useUpdatePrint";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";
import { Sheet, SheetContent, SheetFooter, SheetHeader, SheetTitle } from "@/ui/sheet";

interface Props {
  modelId: string;
  print: PrintRead | null;
  open: boolean;
  onOpenChange: (next: boolean) => void;
}

export function AddPrintSheet({ modelId, print, open, onOpenChange }: Props) {
  const { t } = useTranslation();
  const [date, setDate] = useState(print?.printed_at ?? "");
  const [note, setNote] = useState(print?.note ?? "");
  const create = useCreatePrint(modelId);
  const update = useUpdatePrint(modelId, print?.id ?? "__noop");

  useEffect(() => {
    if (open) {
      setDate(print?.printed_at ?? "");
      setNote(print?.note ?? "");
    }
  }, [open, print]);

  function save() {
    const payload = {
      printed_at: date || null,
      note: note || null,
    };
    if (print === null) {
      create.mutate(
        { model_id: modelId, ...payload },
        {
          onSuccess: () => {
            toast.success(t("catalog.prints.added"));
            onOpenChange(false);
          },
          onError: (e) => toast.error(e.message),
        },
      );
    } else {
      update.mutate(payload, {
        onSuccess: () => {
          toast.success(t("catalog.prints.updated"));
          onOpenChange(false);
        },
        onError: (e) => toast.error(e.message),
      });
    }
  }

  const pending = create.isPending || update.isPending;
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle>
            {print === null ? t("catalog.prints.add") : t("catalog.prints.edit")}
          </SheetTitle>
        </SheetHeader>
        <div className="mt-4 space-y-3 px-4">
          <label className="block text-sm">
            {t("catalog.prints.date")}
            <Input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="mt-1"
            />
          </label>
          <label className="block text-sm">
            {t("catalog.prints.note")}
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={6}
              className="mt-1 w-full rounded border border-border bg-background p-2"
            />
          </label>
        </div>
        <SheetFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t("common.cancel")}
          </Button>
          <Button onClick={save} disabled={pending}>
            {t("common.save")}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
