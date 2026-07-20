import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import type { ModelDetail, TagListItem } from "@/lib/api-types";
import { useTags } from "@/modules/catalog/hooks/useTags";
import { useTagGroups } from "@/modules/catalog/hooks/useTagGroups";
import { useCreateTag } from "@/modules/catalog/hooks/mutations/useCreateTag";
import { useReplaceTags } from "@/modules/catalog/hooks/mutations/useReplaceTags";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";
import { Sheet, SheetContent, SheetFooter, SheetHeader, SheetTitle } from "@/ui/sheet";

// Sentinel ids for the candidate-section list — same convention as
// TagGroupsSection/FacetSidebar's own (independently-defined) sentinels. Real
// group ids are backend-issued UUIDs, so neither collides.
const FLAT_ID = "__flat__";
const GROUPLESS_ID = "__groupless__";

interface Section {
  id: string;
  label: string | null;
  tags: TagListItem[];
}

interface Props {
  detail: ModelDetail;
  open: boolean;
  onOpenChange: (next: boolean) => void;
  isAdmin: boolean;
}

export function EditTagsSheet({ detail, open, onOpenChange, isAdmin }: Props) {
  const { t: translate, i18n } = useTranslation();
  const [selected, setSelected] = useState<string[]>(detail.tags.map((t) => t.id));
  const [query, setQuery] = useState("");
  const tags = useTags(query);
  const tagGroups = useTagGroups();
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
    if (!isAdmin) return;
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

  const preferPl = i18n.language.startsWith("pl");
  // Empty string is a valid `name_pl` per the API type; treat it like null so
  // a pl-locale group never renders a blank label (mirrors FacetSidebar's
  // `labelOf`).
  const labelOf = (item: { name_en: string; name_pl: string | null }) =>
    preferPl && item.name_pl ? item.name_pl : item.name_en;

  let sections: Section[];
  if (tagGroups.data === undefined) {
    // Facet metadata hasn't loaded (or failed) — fall back to the flat,
    // header-less list so selection/save keep working regardless.
    sections = candidates.length > 0 ? [{ id: FLAT_ID, label: null, tags: candidates }] : [];
  } else {
    const sortedGroups = [...tagGroups.data.groups].sort((a, b) => a.position - b.position);
    const knownGroupIds = new Set(sortedGroups.map((g) => g.id));
    sections = sortedGroups
      .map((g) => ({
        id: g.id,
        label: labelOf(g),
        tags: candidates.filter((tag) => tag.group_id === g.id),
      }))
      .filter((s) => s.tags.length > 0);
    // A candidate's group_id can reference a group that's been deleted/renamed
    // (or the cached tag-groups response predates it) — fold those orphans
    // into "Ungrouped" instead of silently dropping them.
    const groupless = candidates.filter(
      (tag) => tag.group_id === null || !knownGroupIds.has(tag.group_id),
    );
    if (groupless.length > 0) {
      sections.push({
        id: GROUPLESS_ID,
        label: translate("catalog.filters.ungrouped"),
        tags: groupless,
      });
    }
  }

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
            {sections.map((section) => (
              <div key={section.id}>
                {section.label !== null && (
                  <span className="block px-2 pt-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {section.label}
                  </span>
                )}
                {section.tags.map((tag) => (
                  <button
                    key={tag.id}
                    type="button"
                    onClick={() => toggle(tag.id)}
                    className="block w-full rounded px-2 py-1 text-left text-xs hover:bg-accent"
                  >
                    + {tag.slug}
                  </button>
                ))}
              </div>
            ))}
            {isAdmin && candidates.length === 0 && query.length > 0 && (
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
