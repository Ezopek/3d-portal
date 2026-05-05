import { useEffect, useState } from "react";
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
  const existing = detail.notes.find((n) => n.kind === "description") ?? null;
  const [body, setBody] = useState(existing?.body ?? "");
  const upsert = useUpsertDescription();

  useEffect(() => {
    if (open) setBody(existing?.body ?? "");
  }, [open, existing?.body]);

  function save() {
    upsert.mutate(
      { modelId: detail.id, existingId: existing?.id ?? null, body },
      {
        onSuccess: () => {
          toast.success("Description saved");
          onOpenChange(false);
        },
        onError: (err) => toast.error(err.message),
      },
    );
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Edit description</SheetTitle>
        </SheetHeader>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={20}
          className="mt-4 w-full rounded border border-border bg-background p-2 text-sm"
        />
        <SheetFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={save} disabled={upsert.isPending}>
            Save
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
