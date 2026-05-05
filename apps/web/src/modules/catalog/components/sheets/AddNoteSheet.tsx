import { useEffect, useState } from "react";
import { toast } from "sonner";

import type { NoteKind, NoteRead } from "@/lib/api-types";
import { useCreateNote } from "@/modules/catalog/hooks/mutations/useCreateNote";
import { useUpdateNote } from "@/modules/catalog/hooks/mutations/useUpdateNote";
import { Button } from "@/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/ui/select";
import { Sheet, SheetContent, SheetFooter, SheetHeader, SheetTitle } from "@/ui/sheet";

const KINDS: NoteKind[] = ["operational", "ai_review", "other"];

interface Props {
  modelId: string;
  note: NoteRead | null;
  open: boolean;
  onOpenChange: (next: boolean) => void;
}

export function AddNoteSheet({ modelId, note, open, onOpenChange }: Props) {
  const [kind, setKind] = useState<NoteKind>(
    (note?.kind === "description" ? "operational" : note?.kind) ?? "operational",
  );
  const [body, setBody] = useState(note?.body ?? "");
  const create = useCreateNote(modelId);
  const update = useUpdateNote(modelId, note?.id ?? "__noop");

  useEffect(() => {
    if (open) {
      setKind((note?.kind === "description" ? "operational" : note?.kind) ?? "operational");
      setBody(note?.body ?? "");
    }
  }, [open, note]);

  function save() {
    if (note === null) {
      create.mutate(
        { model_id: modelId, kind, body },
        {
          onSuccess: () => {
            toast.success("Note added");
            onOpenChange(false);
          },
          onError: (e) => toast.error(e.message),
        },
      );
    } else {
      update.mutate(
        { kind, body },
        {
          onSuccess: () => {
            toast.success("Note updated");
            onOpenChange(false);
          },
          onError: (e) => toast.error(e.message),
        },
      );
    }
  }

  const pending = create.isPending || update.isPending;
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle>{note === null ? "Add note" : "Edit note"}</SheetTitle>
        </SheetHeader>
        <div className="mt-4 space-y-3 px-4">
          <label className="block text-sm">
            Kind
            <Select value={kind} onValueChange={(v) => setKind(v as NoteKind)}>
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {KINDS.map((k) => (
                  <SelectItem key={k} value={k}>
                    {k}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </label>
          <label className="block text-sm">
            Body
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={10}
              className="mt-1 w-full rounded border border-border bg-background p-2"
            />
          </label>
        </div>
        <SheetFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={save} disabled={pending}>
            Save
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
