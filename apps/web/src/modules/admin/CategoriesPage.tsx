import { ArrowDown, ArrowUp, MoreHorizontal, Plus } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { ApiError } from "@/lib/api";
import type { BrowseCategoryAdminRead } from "@/lib/api-types";
import { useModels } from "@/modules/catalog/hooks/useModels";
import { Button } from "@/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/ui/dropdown-menu";

import { AdminTabs } from "./AdminTabs";
import { mapCategoryApiError } from "./dialogs/apiErrorMessage";
import { CategoryFormDialog, type CategoryFormValues } from "./dialogs/CategoryFormDialog";
import { DeleteCategoryDialog, type DeleteConflict } from "./dialogs/DeleteCategoryDialog";
import {
  useAdminCategories,
  useCreateBrowseCategory,
  useDeleteBrowseCategory,
  useUpdateBrowseCategory,
  type BrowseCategoryPatchBody,
} from "./hooks/useAdminCategories";
import { ModelCategoriesDialog } from "./ModelCategoriesDialog";

// Locale-aware naming, module-local by the same intentional-duplication rule
// TagGroupsPage / ModelCategoriesSection / BrowseCategoryList already record:
// prefer `name_pl` only when the active locale is Polish AND it is non-empty.
// Not extracted into a shared util — see the story's D-6.
function useLocalizedName() {
  const { i18n } = useTranslation();
  const preferPl = i18n.language.startsWith("pl");
  return (nameEn: string, namePl: string | null): string =>
    preferPl && namePl !== null && namePl !== "" ? namePl : nameEn;
}

interface CategoryActions {
  onEdit: (category: BrowseCategoryAdminRead) => void;
  onMoveUp: (category: BrowseCategoryAdminRead) => void;
  onMoveDown: (category: BrowseCategoryAdminRead) => void;
  onDelete: (category: BrowseCategoryAdminRead) => void;
}

function CategoryRow({
  category,
  isFirst,
  isLast,
  reorderPending,
  actions,
}: {
  category: BrowseCategoryAdminRead;
  isFirst: boolean;
  isLast: boolean;
  reorderPending: boolean;
  actions: CategoryActions;
}) {
  const { t } = useTranslation();
  const localize = useLocalizedName();
  const name = localize(category.name_en, category.name_pl);
  return (
    <li
      className="flex items-start gap-3 rounded-md border border-border bg-card px-3 py-2.5"
      data-testid={`browse-category-${category.slug}`}
    >
      <span className="w-5 pt-0.5 text-xs tabular-nums text-muted-foreground">
        {category.position}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-2">
          <span className="text-sm font-medium text-card-foreground">{name}</span>
          <span className="font-mono text-xs text-muted-foreground">{category.slug}</span>
        </div>
        {/* The criterion renders IN THE LIST because it IS the admission test:
            an admin comparing two categories must see both at once, not open
            two dialogs (DESIGN.md). Single line, truncated. A category without
            one renders nothing here — no placeholder, no dash: FR26-GOV-1 is a
            governance norm this screen surfaces, not a field it enforces. */}
        {category.inclusion_criterion !== null && category.inclusion_criterion !== "" ? (
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {category.inclusion_criterion}
          </p>
        ) : null}
      </div>
      <span className="pt-0.5 text-xs tabular-nums text-muted-foreground">
        {t("modules.admin.categories.model_count", { count: category.model_count })}
      </span>
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={t("modules.admin.categories.actions.category_menu", { name })}
            />
          }
        >
          <MoreHorizontal className="size-4" aria-hidden />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={() => actions.onEdit(category)}>
            {t("modules.admin.categories.actions.edit")}
          </DropdownMenuItem>
          <DropdownMenuItem
            disabled={isFirst || reorderPending}
            onClick={() => actions.onMoveUp(category)}
          >
            <ArrowUp className="size-4" aria-hidden />
            {t("modules.admin.categories.actions.move_up")}
          </DropdownMenuItem>
          <DropdownMenuItem
            disabled={isLast || reorderPending}
            onClick={() => actions.onMoveDown(category)}
          >
            <ArrowDown className="size-4" aria-hidden />
            {t("modules.admin.categories.actions.move_down")}
          </DropdownMenuItem>
          <DropdownMenuItem variant="destructive" onClick={() => actions.onDelete(category)}>
            {t("modules.admin.categories.actions.delete")}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </li>
  );
}

type DialogState =
  | { kind: "create" }
  | { kind: "edit"; category: BrowseCategoryAdminRead }
  | { kind: "delete"; category: BrowseCategoryAdminRead; conflict: DeleteConflict }
  | { kind: "assign"; modelId: string; modelName: string }
  | null;

export function CategoriesPage() {
  const { t } = useTranslation();
  const query = useAdminCategories();
  const localize = useLocalizedName();

  // The curation queue (FR26-CAT-2). A zero-category model is a VALID, publicly
  // visible state — this list is curation work, never a defect report. There is
  // no client-side derivation available: `ModelSummary` carries no categories by
  // ratified design, so the backend `uncategorized` filter is the only source.
  const uncategorized = useModels({ uncategorized: true, sort: "name_asc" });

  const createCategory = useCreateBrowseCategory();
  const updateCategory = useUpdateBrowseCategory();
  const deleteCategory = useDeleteBrowseCategory();

  const [dialog, setDialog] = useState<DialogState>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const data = query.data;

  function openDialog(next: NonNullable<DialogState>) {
    setErrorMessage(null);
    setDialog(next);
  }
  function closeDialog() {
    setDialog(null);
    setErrorMessage(null);
  }
  function onWriteError(err: unknown) {
    setErrorMessage(mapCategoryApiError(err, t));
  }

  // Adjacent-position swap, copied from the shipped TagGroupsPage reorder with
  // its compensating rollback intact (D-7). Sequential, never Promise.all: if
  // the SECOND patch fails after the first landed, the first is restored so the
  // server never persists two categories sharing a `position` — which would
  // make the (position, slug) order silently slug-tie-broken.
  async function reorder(category: BrowseCategoryAdminRead, direction: "up" | "down") {
    if (!data) return;
    const index = data.findIndex((c) => c.id === category.id);
    const otherIndex = direction === "up" ? index - 1 : index + 1;
    const current = data[index];
    const other = data[otherIndex];
    if (!current || !other) return; // boundary guard (buttons are already disabled)
    try {
      await updateCategory.mutateAsync({ id: current.id, body: { position: other.position } });
      try {
        await updateCategory.mutateAsync({ id: other.id, body: { position: current.position } });
      } catch (err) {
        await updateCategory
          .mutateAsync({ id: current.id, body: { position: current.position } })
          .catch(() => {});
        throw err;
      }
      toast.success(t("modules.admin.categories.toast.reordered"));
    } catch {
      toast.error(t("modules.admin.categories.toast.reorder_failed"));
    }
  }

  const actions: CategoryActions = {
    onEdit: (category) => openDialog({ kind: "edit", category }),
    onMoveUp: (category) => void reorder(category, "up"),
    onMoveDown: (category) => void reorder(category, "down"),
    onDelete: (category) => openDialog({ kind: "delete", category, conflict: "none" }),
  };

  function submitCreate(values: CategoryFormValues) {
    if (!data) return;
    createCategory.mutate(
      { ...values, position: data.length },
      {
        onSuccess: () => {
          toast.success(t("modules.admin.categories.toast.created"));
          closeDialog();
        },
        onError: onWriteError,
      },
    );
  }

  function submitEdit(category: BrowseCategoryAdminRead, values: CategoryFormValues) {
    // Only changed fields travel; the PATCH is `extra="forbid"` and uses
    // `exclude_unset`, so an untouched field must not be sent at all.
    const body: BrowseCategoryPatchBody = {};
    if (values.name_en !== category.name_en) body.name_en = values.name_en;
    if (values.name_pl !== category.name_pl) body.name_pl = values.name_pl;
    if (values.inclusion_criterion !== category.inclusion_criterion) {
      body.inclusion_criterion = values.inclusion_criterion;
    }
    if (Object.keys(body).length === 0) {
      closeDialog();
      return;
    }
    updateCategory.mutate(
      { id: category.id, body },
      {
        onSuccess: () => {
          toast.success(t("modules.admin.categories.toast.updated"));
          closeDialog();
        },
        onError: onWriteError,
      },
    );
  }

  // `detach` is NEVER implicit. The first attempt always omits it; a 409 is
  // re-rendered as the matching conflict state and the admin decides again.
  // The two 409 sources stay distinct because `detach=true` resolves only one
  // of them (D-8) — offering it against `category_has_children` would offer a
  // fix that provably cannot work.
  function submitDelete(category: BrowseCategoryAdminRead, detach: boolean) {
    deleteCategory.mutate(
      { id: category.id, detach },
      {
        onSuccess: () => {
          toast.success(t("modules.admin.categories.toast.deleted"));
          closeDialog();
        },
        onError: (err) => {
          if (err instanceof ApiError && err.status === 409) {
            const detail = typeof err.body === "string" ? err.body : JSON.stringify(err.body ?? "");
            const conflict: DeleteConflict = detail.includes("category_has_children")
              ? "has_children"
              : "in_use";
            setErrorMessage(null);
            setDialog({ kind: "delete", category, conflict });
            return;
          }
          onWriteError(err);
        },
      },
    );
  }

  const queueItems = uncategorized.data?.items ?? [];

  return (
    <div className="flex flex-col gap-4 p-4">
      <AdminTabs activeTab="categories" />

      <header className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-foreground">
            {t("modules.admin.categories.title")}
          </h1>
          <p className="text-xs text-muted-foreground">
            {t("modules.admin.categories.description")}
          </p>
        </div>
        {data ? (
          <Button size="sm" onClick={() => openDialog({ kind: "create" })}>
            <Plus className="size-4" aria-hidden />
            {t("modules.admin.categories.actions.create")}
          </Button>
        ) : null}
      </header>

      {data ? (
        // Prefer already-loaded data over a background-refetch error, mirroring
        // TagGroupsPage: a transient refetch failure must not hide still-valid rows.
        data.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("modules.admin.categories.empty")}</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {data.map((category, i) => (
              <CategoryRow
                key={category.id}
                category={category}
                isFirst={i === 0}
                isLast={i === data.length - 1}
                reorderPending={updateCategory.isPending}
                actions={actions}
              />
            ))}
          </ul>
        )
      ) : query.isError ? (
        // Fails closed: never fabricate an empty/green state on a failed read.
        <div className="flex flex-col items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-4">
          <p className="text-sm font-medium text-destructive">
            {t("modules.admin.categories.error_title")}
          </p>
          <Button
            variant="outline"
            size="sm"
            disabled={query.isFetching}
            onClick={() => void query.refetch()}
          >
            {t("common.retry")}
          </Button>
        </div>
      ) : (
        <div className="flex flex-col gap-2" aria-hidden="true" data-testid="categories-skeleton">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-md bg-muted" />
          ))}
        </div>
      )}

      <section className="flex flex-col gap-2" data-testid="curation-queue">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {/* No count until one has actually been read: `?? 0` rendered
              "Needs curation (0)" over an unresolved query, which is the same
              fabricated-green-state the category list's skeleton exists to
              prevent 40 lines above. */}
          {uncategorized.data
            ? t("modules.admin.categories.queue.title", { count: uncategorized.data.total })
            : t("modules.admin.categories.queue.title_pending")}
        </h2>
        {/* A zero-category model is normal and stays public — this queue is
            curation work, never an error list. Nothing here is destructive. */}
        <p className="text-xs text-muted-foreground">
          {t("modules.admin.categories.queue.description")}
        </p>
        {uncategorized.isError && !uncategorized.data ? (
          <div className="flex flex-col items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3">
            <p className="text-sm font-medium text-destructive">
              {t("modules.admin.categories.queue.error")}
            </p>
            <Button
              variant="outline"
              size="sm"
              disabled={uncategorized.isFetching}
              onClick={() => void uncategorized.refetch()}
            >
              {t("common.retry")}
            </Button>
          </div>
        ) : !uncategorized.data ? (
          // Loading: an empty <ul> here read as a cleared queue. Same aria-hidden
          // pulse the category list uses, for the same fails-closed reason.
          <div className="flex flex-col gap-2" aria-hidden="true" data-testid="queue-skeleton">
            {Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="h-10 animate-pulse rounded-md bg-muted" />
            ))}
          </div>
        ) : queueItems.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            {t("modules.admin.categories.queue.empty")}
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {queueItems.map((model) => (
              <li
                key={model.id}
                className="flex items-center justify-between gap-2 rounded-md border border-border bg-card px-3 py-2"
                data-testid={`curation-model-${model.slug}`}
              >
                <span className="min-w-0 flex-1 truncate text-sm text-card-foreground">
                  {localize(model.name_en, model.name_pl)}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!data}
                  onClick={() =>
                    openDialog({
                      kind: "assign",
                      modelId: model.id,
                      modelName: localize(model.name_en, model.name_pl),
                    })
                  }
                >
                  {t("modules.admin.categories.queue.assign")}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {dialog?.kind === "create" ? (
        <CategoryFormDialog
          open
          onOpenChange={(next) => !next && closeDialog()}
          mode="create"
          pending={createCategory.isPending}
          errorMessage={errorMessage}
          onSubmit={submitCreate}
        />
      ) : null}

      {dialog?.kind === "edit" ? (
        <CategoryFormDialog
          open
          onOpenChange={(next) => !next && closeDialog()}
          mode="edit"
          initial={dialog.category}
          pending={updateCategory.isPending}
          errorMessage={errorMessage}
          onSubmit={(values) => submitEdit(dialog.category, values)}
        />
      ) : null}

      {dialog?.kind === "delete" ? (
        <DeleteCategoryDialog
          open
          onOpenChange={(next) => !next && closeDialog()}
          categoryName={localize(dialog.category.name_en, dialog.category.name_pl)}
          modelCount={dialog.category.model_count}
          conflict={dialog.conflict}
          pending={deleteCategory.isPending}
          errorMessage={errorMessage}
          onConfirm={(detach) => submitDelete(dialog.category, detach)}
        />
      ) : null}

      {dialog?.kind === "assign" && data ? (
        <ModelCategoriesDialog
          modelId={dialog.modelId}
          modelName={dialog.modelName}
          categories={data}
          open
          onOpenChange={(next) => !next && closeDialog()}
          localize={localize}
        />
      ) : null}
    </div>
  );
}
