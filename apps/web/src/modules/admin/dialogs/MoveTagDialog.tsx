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

// One selectable target container. `groupId: null` is the Ungrouped option; the
// caller (TagGroupsPage) excludes the tag's current container from `options` and
// computes the explicit `group_position` (target tag count) once a target is picked.
export interface MoveTargetOption {
  key: string;
  label: string;
  groupId: string | null;
}

export interface MoveTagDialogProps {
  open: boolean;
  onOpenChange: (next: boolean) => void;
  tagName: string;
  options: MoveTargetOption[];
  pending: boolean;
  errorMessage: string | null;
  onSubmit: (groupId: string | null) => void;
}

export function MoveTagDialog({
  open,
  onOpenChange,
  tagName,
  options,
  pending,
  errorMessage,
  onSubmit,
}: MoveTagDialogProps) {
  const { t } = useTranslation();
  const firstKey = options[0]?.key ?? "";
  const [selectedKey, setSelectedKey] = useState(firstKey);

  // `options` is a fresh array on every parent render; preserve the user's current
  // target across incidental re-renders and only re-seed when it has disappeared,
  // so a background refetch can't silently move the tag into the wrong group.
  useEffect(() => {
    if (open) setSelectedKey((prev) => (options.some((o) => o.key === prev) ? prev : (options[0]?.key ?? "")));
  }, [open, options]);

  const selected = options.find((o) => o.key === selectedKey);
  const canSubmit = selected !== undefined && !pending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("modules.admin.tagGroups.move.title")}</DialogTitle>
          <DialogDescription>
            {t("modules.admin.tagGroups.move.description", { name: tagName })}
          </DialogDescription>
        </DialogHeader>
        <form
          className="flex flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (selected) onSubmit(selected.groupId);
          }}
        >
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">{t("modules.admin.tagGroups.move.target_label")}</span>
            <select
              value={selectedKey}
              onChange={(e) => setSelectedKey(e.target.value)}
              disabled={pending}
              aria-label={t("modules.admin.tagGroups.move.target_label")}
              className="h-8 w-full rounded-lg border border-input bg-background px-2.5 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-50"
            >
              {options.map((o) => (
                <option key={o.key} value={o.key}>
                  {o.label}
                </option>
              ))}
            </select>
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
              {t("modules.admin.tagGroups.move.submit")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
