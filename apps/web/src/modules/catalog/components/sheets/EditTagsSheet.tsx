import { useEffect, useState } from "react";
import { toast } from "sonner";

import type { ModelDetail } from "@/lib/api-types";
import { useTags } from "@/modules/catalog/hooks/useTags";
import { useCreateTag } from "@/modules/catalog/hooks/mutations/useCreateTag";
import { useReplaceTags } from "@/modules/catalog/hooks/mutations/useReplaceTags";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";
import { Sheet, SheetContent, SheetFooter, SheetHeader, SheetTitle } from "@/ui/sheet";

interface Props {
  detail: ModelDetail;
  open: boolean;
  onOpenChange: (next: boolean) => void;
}

export function EditTagsSheet({ detail, open, onOpenChange }: Props) {
  const [selected, setSelected] = useState<string[]>(detail.tags.map((t) => t.id));
  const [query, setQuery] = useState("");
  const tags = useTags(query);
  const replace = useReplaceTags(detail.id);
  const create = useCreateTag();

  useEffect(() => {
    if (open) setSelected(detail.tags.map((t) => t.id));
  }, [open, detail.tags]);

  function toggle(id: string) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function save() {
    replace.mutate(selected, {
      onSuccess: () => {
        toast.success("Tags saved");
        onOpenChange(false);
      },
      onError: (e) => toast.error(e.message),
    });
  }

  function createAndSelect() {
    const slug = query.trim().toLowerCase().replace(/\s+/g, "-");
    if (slug === "") return;
    create.mutate(
      { slug, name_en: query },
      {
        onSuccess: (newTag) => {
          setSelected((prev) => [...prev, newTag.id]);
          setQuery("");
          toast.success(`Tag "${newTag.slug}" created`);
        },
        onError: (e) => toast.error(e.message),
      },
    );
  }

  const candidates = (tags.data ?? []).filter((t) => !selected.includes(t.id));
  const selectedLookup = new Map((tags.data ?? []).map((t) => [t.id, t]));
  // Keep already-known names for selected ids that aren't in the fresh `tags.data`
  for (const t of detail.tags) selectedLookup.set(t.id, t);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Edit tags</SheetTitle>
        </SheetHeader>
        <div className="mt-4 space-y-3">
          <div className="flex flex-wrap gap-1">
            {selected.map((id) => {
              const t = selectedLookup.get(id);
              return (
                <span
                  key={id}
                  className="flex items-center gap-1 rounded bg-accent px-2 py-0.5 text-xs"
                >
                  {t?.slug ?? id.slice(0, 6)}
                  <button
                    type="button"
                    aria-label={`remove ${t?.slug ?? id}`}
                    onClick={() => toggle(id)}
                  >
                    ×
                  </button>
                </span>
              );
            })}
            {selected.length === 0 && (
              <span className="text-xs text-muted-foreground">No tags</span>
            )}
          </div>
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search or create…"
          />
          <div className="max-h-48 space-y-1 overflow-y-auto">
            {candidates.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => toggle(t.id)}
                className="block w-full rounded px-2 py-1 text-left text-xs hover:bg-accent"
              >
                + {t.slug}
              </button>
            ))}
            {candidates.length === 0 && query.length > 0 && (
              <Button variant="outline" size="sm" onClick={createAndSelect}>
                + Create &quot;{query}&quot;
              </Button>
            )}
          </div>
        </div>
        <SheetFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={save} disabled={replace.isPending}>
            Save
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
