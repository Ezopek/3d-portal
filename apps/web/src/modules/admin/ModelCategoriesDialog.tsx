import { useQueryClient } from "@tanstack/react-query";
import { TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import type { AuditLogEntry, BrowseCategoryAdminRead } from "@/lib/api-types";
import { useAuditLog } from "@/modules/catalog/hooks/useAuditLog";
import { useModel } from "@/modules/catalog/hooks/useModel";
import { useAuth } from "@/shell/AuthContext";
import { Button } from "@/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/ui/dialog";

import { mapCategoryApiError } from "./dialogs/apiErrorMessage";
import { useReplaceModelCategories } from "./hooks/useAdminCategories";

// The advisory norm from FR26-CAT-3. Above this the editor WARNS and still
// saves — there is no hard database maximum and no write-blocking enforcement,
// so a client-side block would be a lie about the contract.
const ADVISORY_MAX = 3;

// A replace-set write is audited as `entity_type="model"` / `action="model.update"`
// with `category_ids` in both `before` and `after` — the convention
// `replace_model_tags` established, deliberately reused rather than given its
// own M:N entity_type. So a plain model edit and a tag replace land under the
// SAME action, and only the `category_ids` key distinguishes a category write.
// Selecting on the action alone would mis-attribute those as category changes.
function latestCategoryWrite(entries: AuditLogEntry[] | undefined): AuditLogEntry | null {
  if (!entries) return null;
  for (const entry of entries) {
    if (entry.after_json !== null && "category_ids" in entry.after_json) return entry;
  }
  return null;
}

interface Props {
  modelId: string;
  modelName: string;
  categories: BrowseCategoryAdminRead[];
  open: boolean;
  onOpenChange: (next: boolean) => void;
  localize: (nameEn: string, namePl: string | null) => string;
}

export function ModelCategoriesDialog({
  modelId,
  modelName,
  categories,
  open,
  onOpenChange,
  localize,
}: Props) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const qc = useQueryClient();
  const detail = useModel(modelId);
  // `limit: 20` rather than 1: the newest row for this model may well be a tag
  // replace or a plain edit, so the category write we want can sit a few rows
  // down. 20 is generous enough to find it without paging.
  const audit = useAuditLog({ entity_type: "model", entity_id: modelId, limit: 20 });
  const replace = useReplaceModelCategories(modelId);

  const [selected, setSelected] = useState<string[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // CONCURRENCY HONESTY (D-3 / EXPERIENCE.md "Stale"). Under the accepted
  // explicit last-writer-wins posture (Decision AY) there is no precondition,
  // no revision and no conflict detection: a concurrent editor's change is
  // silently discarded. Re-fetching on open is the ONE mitigation the contract
  // actually supports — it shrinks the stale window, it does not close it. Do
  // not add a conflict banner or a merge prompt here; the API cannot detect
  // either, and the UI must not imply semantics it does not have.
  useEffect(() => {
    if (!open) return;
    setErrorMessage(null);
    void qc.invalidateQueries({ queryKey: ["sot", "models", modelId] });
    void qc.invalidateQueries({ queryKey: ["sot", "audit-log"] });
  }, [open, modelId, qc]);

  // Seed the checkboxes from the SERVER's answer, not from a value captured at
  // mount, so the re-fetch above is what the admin actually edits against.
  useEffect(() => {
    if (open && detail.data) setSelected(detail.data.categories.map((c) => c.id));
  }, [open, detail.data]);

  function toggle(id: string) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function save() {
    setErrorMessage(null);
    replace.mutate(selected, {
      onSuccess: () => {
        toast.success(t("modules.admin.categories.editor.toast.replaced"));
        onOpenChange(false);
      },
      onError: (err) => setErrorMessage(mapCategoryApiError(err, t)),
    });
  }

  const lastWrite = latestCategoryWrite(audit.data?.items);
  // Resolve the actor without a request: "you" when it is the current admin,
  // otherwise "another admin". Naming a different admin would need a paginated
  // /admin/users lookup for one label — not cheap, and not built (D-4).
  const lastWriterLabel =
    lastWrite === null
      ? null
      : lastWrite.actor_user_id !== null && lastWrite.actor_user_id === user?.id
        ? t("modules.admin.categories.editor.last_write_you", {
            at: lastWrite.at.slice(0, 16).replace("T", " "),
          })
        : lastWrite.actor_user_id !== null
          ? t("modules.admin.categories.editor.last_write_other", {
              at: lastWrite.at.slice(0, 16).replace("T", " "),
            })
          : t("modules.admin.categories.editor.last_write_unknown_actor", {
              at: lastWrite.at.slice(0, 16).replace("T", " "),
            });

  const overAdvisory = selected.length > ADVISORY_MAX;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("modules.admin.categories.editor.title")}</DialogTitle>
          <DialogDescription>{modelName}</DialogDescription>
        </DialogHeader>

        {/* Advisory garnish only. An absent, failed or category-less audit read
            renders NOTHING and blocks nothing — an error banner for a missing
            garnish would be noise on a fully usable editor. */}
        {lastWriterLabel !== null ? (
          <p className="text-xs text-muted-foreground" data-testid="category-last-write">
            {lastWriterLabel}
          </p>
        ) : null}

        {detail.isLoading ? (
          <div className="flex flex-col gap-2" aria-hidden="true" data-testid="model-categories-skeleton">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-8 animate-pulse rounded-md bg-muted" />
            ))}
          </div>
        ) : detail.isError ? (
          // Fails closed: never present an empty checkbox list as "this model has
          // no categories" when the read actually failed — saving from that state
          // would silently clear a set the admin never saw.
          <div className="flex flex-col items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3">
            <p className="text-sm font-medium text-destructive">
              {t("modules.admin.categories.editor.load_error")}
            </p>
            <Button
              variant="outline"
              size="sm"
              disabled={detail.isFetching}
              onClick={() => void detail.refetch()}
            >
              {t("common.retry")}
            </Button>
          </div>
        ) : (
          <div className="flex max-h-72 flex-col gap-1 overflow-y-auto">
            {categories.map((category) => {
              const checked = selected.includes(category.id);
              return (
                <label
                  key={category.id}
                  className="flex min-h-8 cursor-pointer items-center gap-2 rounded px-1 text-sm"
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggle(category.id)}
                    disabled={replace.isPending}
                    className="size-4 shrink-0 rounded border-input accent-primary"
                  />
                  <span className="flex-1">{localize(category.name_en, category.name_pl)}</span>
                </label>
              );
            })}
          </div>
        )}

        {/* FR26-CAT-3 — WARNING-level norm. The save button below stays enabled
            while this is visible; assigning 5 categories must succeed and
            produce a warning, not a 4xx and not a disabled control. */}
        {overAdvisory ? (
          <div
            className="flex items-start gap-2 rounded-md border border-border p-2 text-xs"
            data-testid="category-advisory"
          >
            <TriangleAlert className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden />
            <span>
              {t("modules.admin.categories.editor.advisory", { count: selected.length })}
            </span>
          </div>
        ) : null}

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
            disabled={replace.isPending}
          >
            {t("common.cancel")}
          </Button>
          {/* "Replace categories", never "Save changes": the call replaces a
              whole set and the last write wins silently. The verb states what
              the API does (EXPERIENCE.md Voice and Tone). */}
          <Button
            type="button"
            onClick={save}
            disabled={replace.isPending || detail.isLoading || detail.isError}
          >
            {t("modules.admin.categories.editor.submit")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
