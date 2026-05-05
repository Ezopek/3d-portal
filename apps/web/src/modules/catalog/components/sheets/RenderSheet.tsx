import { useState } from "react";
import { toast } from "sonner";

import type { ModelDetail } from "@/lib/api-types";
import { useTriggerRender } from "@/modules/catalog/hooks/mutations/useTriggerRender";
import { Button } from "@/ui/button";
import { Sheet, SheetContent, SheetFooter, SheetHeader, SheetTitle } from "@/ui/sheet";

interface Props {
  detail: ModelDetail;
  open: boolean;
  onOpenChange: (next: boolean) => void;
}

export function RenderSheet({ detail, open, onOpenChange }: Props) {
  const stls = detail.files.filter((f) => f.kind === "stl");
  const [selected, setSelected] = useState<Set<string>>(
    new Set(stls[0] ? [stls[0].id] : []),
  );
  const trigger = useTriggerRender(detail.id);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function submit() {
    trigger.mutate(
      { selected_stl_file_ids: [...selected] },
      {
        onSuccess: () => {
          toast.success("Render queued");
          onOpenChange(false);
        },
        onError: (e) => toast.error(e.message),
      },
    );
  }

  if (stls.length === 0) {
    return (
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent side="right" className="w-full sm:max-w-md">
          <SheetHeader>
            <SheetTitle>Re-render</SheetTitle>
          </SheetHeader>
          <p className="mt-4 px-4 text-sm text-muted-foreground">
            This model has no STL files; nothing to render.
          </p>
        </SheetContent>
      </Sheet>
    );
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Re-render this model</SheetTitle>
        </SheetHeader>
        <div className="mt-4 space-y-2 px-4">
          <p className="text-sm text-muted-foreground">
            Pick the STL file(s) to render. Worker generates 4 views (iso, front, side, top)
            and replaces existing auto-renders. Photos you uploaded yourself are kept.
          </p>
          <ul className="space-y-1">
            {stls.map((f) => (
              <li
                key={f.id}
                className="flex items-center gap-2 rounded border border-border p-2 text-sm"
              >
                <input
                  type="checkbox"
                  id={`render-stl-${f.id}`}
                  checked={selected.has(f.id)}
                  onChange={() => toggle(f.id)}
                />
                <label htmlFor={`render-stl-${f.id}`} className="flex-1 truncate">
                  {f.original_name}
                </label>
              </li>
            ))}
          </ul>
        </div>
        <SheetFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={trigger.isPending || selected.size === 0}>
            Re-render
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
