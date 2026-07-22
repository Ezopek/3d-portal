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

import { normalizeTagText } from "../duplicateTags";

// One selectable survivor candidate for a duplicate cluster. `name_en` (raw,
// unlocalized) is carried alongside the display `label` because the default
// survivor's tie-break rule is defined over the normalized English name, not
// the locale-dependent display label.
export interface MergeDuplicatesCandidate {
  id: string;
  label: string;
  name_en: string;
  model_count: number;
}

export interface MergeDuplicatesDialogProps {
  open: boolean;
  onOpenChange: (next: boolean) => void;
  candidates: MergeDuplicatesCandidate[];
  pending: boolean;
  errorMessage: string | null;
  onSubmit: (survivorId: string) => void;
}

// Default survivor = highest model_count; tie-break: alphabetical by
// normalized name_en (frozen intent-contract boundary rule).
function pickDefaultSurvivor(candidates: MergeDuplicatesCandidate[]): string {
  let best: MergeDuplicatesCandidate | undefined;
  for (const candidate of candidates) {
    if (
      best === undefined ||
      candidate.model_count > best.model_count ||
      (candidate.model_count === best.model_count &&
        normalizeTagText(candidate.name_en) < normalizeTagText(best.name_en))
    ) {
      best = candidate;
    }
  }
  return best?.id ?? "";
}

// Review finding (dev-repair): two cluster members can share the exact same
// localized label (the most common real duplicate is a tag typed twice with
// identical text) — the visible `model_count` column distinguishes them for
// sighted users, but the radio's accessible name did not, making the choice
// unreachable via screen reader. Only append a disambiguator when a genuine
// collision exists, so the common (non-colliding) case keeps its plain label.
function disambiguatedLabel(
  candidate: MergeDuplicatesCandidate,
  index: number,
  all: MergeDuplicatesCandidate[],
): string {
  const collides = all.filter((c) => c.label === candidate.label).length > 1;
  return collides ? `${candidate.label} (${index + 1})` : candidate.label;
}

export function MergeDuplicatesDialog({
  open,
  onOpenChange,
  candidates,
  pending,
  errorMessage,
  onSubmit,
}: MergeDuplicatesDialogProps) {
  const { t } = useTranslation();
  const [selectedId, setSelectedId] = useState(() => pickDefaultSurvivor(candidates));

  // Mirrors MergeTagDialog/MoveTagDialog's options-refresh fix: `candidates` is a
  // fresh array every render (re-derived live from currently-loaded tags by id),
  // so keep the admin's current choice if it's still among the live candidates;
  // only re-seed the default when the selection has disappeared — e.g. a cluster
  // member gets merged away by a concurrent action while the dialog is open.
  useEffect(() => {
    if (open) {
      setSelectedId((prev) =>
        candidates.some((c) => c.id === prev) ? prev : pickDefaultSurvivor(candidates),
      );
    }
  }, [open, candidates]);

  const canSubmit = selectedId !== "" && candidates.length >= 2 && !pending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("modules.admin.tagGroups.duplicates.dialog.title")}</DialogTitle>
          <DialogDescription>
            {t("modules.admin.tagGroups.duplicates.dialog.description")}
          </DialogDescription>
        </DialogHeader>
        <form
          className="flex flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (canSubmit) onSubmit(selectedId);
          }}
        >
          <fieldset className="flex flex-col gap-2">
            <legend className="text-sm font-medium">
              {t("modules.admin.tagGroups.duplicates.dialog.survivor_label")}
            </legend>
            {candidates.map((candidate, index) => (
              <label
                key={candidate.id}
                className="flex items-center gap-2 rounded-md border border-input px-2.5 py-1.5 text-sm has-[:checked]:border-ring"
              >
                <input
                  type="radio"
                  name="merge-duplicates-survivor"
                  aria-label={disambiguatedLabel(candidate, index, candidates)}
                  value={candidate.id}
                  checked={selectedId === candidate.id}
                  onChange={() => setSelectedId(candidate.id)}
                  disabled={pending}
                />
                <span>{candidate.label}</span>
                <span className="ml-auto text-xs tabular-nums text-muted-foreground">
                  {t("modules.admin.tagGroups.model_count", { count: candidate.model_count })}
                </span>
              </label>
            ))}
          </fieldset>
          <p className="rounded-md border border-destructive/40 bg-destructive/10 p-2 text-sm text-destructive">
            {t("modules.admin.tagGroups.duplicates.dialog.warning")}
          </p>
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
            <Button type="submit" variant="destructive" disabled={!canSubmit}>
              {t("modules.admin.tagGroups.duplicates.dialog.submit")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
