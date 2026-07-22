import { ArrowDown, ArrowUp, MoreHorizontal, Plus } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import type { TagGroupRead, TagGroupsResponse, TagReadWithCount } from "@/lib/api-types";
import { useTagGroups } from "@/modules/catalog/hooks/useTagGroups";
import { useCreateTagGroup } from "@/modules/catalog/hooks/mutations/useCreateTagGroup";
import { useMergeTags } from "@/modules/catalog/hooks/mutations/useMergeTags";
import { useUpdateTag, type TagPatchBody } from "@/modules/catalog/hooks/mutations/useUpdateTag";
import {
  useUpdateTagGroup,
  type TagGroupPatchBody,
} from "@/modules/catalog/hooks/mutations/useUpdateTagGroup";
import { Button } from "@/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/ui/dropdown-menu";

import { AdminTabs } from "./AdminTabs";
import { mapApiError } from "./dialogs/apiErrorMessage";
import { CreateGroupDialog } from "./dialogs/CreateGroupDialog";
import { MergeTagDialog, type MergeTargetOption } from "./dialogs/MergeTagDialog";
import { MoveTagDialog, type MoveTargetOption } from "./dialogs/MoveTagDialog";
import { RenameEntityDialog } from "./dialogs/RenameEntityDialog";

// TAG-GROUPS-1 (Story 46.1) — locale-aware group/tag naming follows the same
// `preferPl` fallback used by ModelHero (apps/web/src/modules/catalog/components/ModelHero.tsx:67-80):
// prefer name_pl only when the active locale is Polish AND name_pl is non-null/non-empty.
function useLocalizedName() {
  const { i18n } = useTranslation();
  const preferPl = i18n.language.startsWith("pl");
  return (nameEn: string, namePl: string | null): string =>
    preferPl && namePl !== null && namePl !== "" ? namePl : nameEn;
}

// Story 46.2 — per-tag write actions surfaced from each row's action menu.
interface TagActions {
  onRename: (tag: TagReadWithCount) => void;
  onMove: (tag: TagReadWithCount) => void;
  onMerge: (tag: TagReadWithCount) => void;
}

function TagRow({ tag, actions }: { tag: TagReadWithCount; actions: TagActions }) {
  const { t } = useTranslation();
  const localize = useLocalizedName();
  const name = localize(tag.name_en, tag.name_pl);
  return (
    <li className="flex items-center justify-between gap-2 rounded-md border border-border bg-card px-3 py-2">
      <span className="text-sm text-card-foreground">{name}</span>
      <div className="flex items-center gap-2">
        <span className="text-xs tabular-nums text-muted-foreground">
          {t("modules.admin.tagGroups.model_count", { count: tag.model_count })}
        </span>
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label={t("modules.admin.tagGroups.actions.tag_menu", { name })}
              />
            }
          >
            <MoreHorizontal className="size-4" aria-hidden />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => actions.onRename(tag)}>
              {t("modules.admin.tagGroups.actions.rename")}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => actions.onMove(tag)}>
              {t("modules.admin.tagGroups.actions.move")}
            </DropdownMenuItem>
            <DropdownMenuItem variant="destructive" onClick={() => actions.onMerge(tag)}>
              {t("modules.admin.tagGroups.actions.merge")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </li>
  );
}

interface GroupActions {
  onRename: (group: TagGroupRead) => void;
  onMoveUp: (group: TagGroupRead) => void;
  onMoveDown: (group: TagGroupRead) => void;
}

function GroupSection({
  group,
  isFirst,
  isLast,
  reorderPending,
  groupActions,
  tagActions,
}: {
  group: TagGroupRead;
  isFirst: boolean;
  isLast: boolean;
  reorderPending: boolean;
  groupActions: GroupActions;
  tagActions: TagActions;
}) {
  const { t } = useTranslation();
  const localize = useLocalizedName();
  const name = localize(group.name_en, group.name_pl);
  return (
    <section className="flex flex-col gap-2" data-testid={`tag-group-${group.slug}`}>
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-foreground">{name}</h2>
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label={t("modules.admin.tagGroups.actions.group_menu", { name })}
              />
            }
          >
            <MoreHorizontal className="size-4" aria-hidden />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => groupActions.onRename(group)}>
              {t("modules.admin.tagGroups.actions.rename")}
            </DropdownMenuItem>
            <DropdownMenuItem
              disabled={isFirst || reorderPending}
              onClick={() => groupActions.onMoveUp(group)}
            >
              <ArrowUp className="size-4" aria-hidden />
              {t("modules.admin.tagGroups.actions.move_up")}
            </DropdownMenuItem>
            <DropdownMenuItem
              disabled={isLast || reorderPending}
              onClick={() => groupActions.onMoveDown(group)}
            >
              <ArrowDown className="size-4" aria-hidden />
              {t("modules.admin.tagGroups.actions.move_down")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      {group.tags.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("modules.admin.tagGroups.group_empty")}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {group.tags.map((tag) => (
            <TagRow key={tag.id} tag={tag} actions={tagActions} />
          ))}
        </ul>
      )}
    </section>
  );
}

function GrouplessSection({
  tags,
  tagActions,
}: {
  tags: TagReadWithCount[];
  tagActions: TagActions;
}) {
  const { t } = useTranslation();
  // I/O Matrix "No groupless tags" row — omitted entirely, not rendered empty.
  if (tags.length === 0) return null;
  return (
    <section className="flex flex-col gap-2" data-testid="tag-group-ungrouped">
      <h2 className="text-sm font-semibold text-foreground">
        {t("modules.admin.tagGroups.ungrouped_title")}
      </h2>
      <ul className="flex flex-col gap-2">
        {tags.map((tag) => (
          <TagRow key={tag.id} tag={tag} actions={tagActions} />
        ))}
      </ul>
    </section>
  );
}

// Story 46.2 — which write dialog (if any) is open, and against which target.
type DialogState =
  | { kind: "rename-tag"; tag: TagReadWithCount }
  | { kind: "rename-group"; group: TagGroupRead }
  | { kind: "move"; tag: TagReadWithCount }
  | { kind: "merge"; tag: TagReadWithCount }
  | { kind: "create" }
  | null;

const UNGROUPED_KEY = "__ungrouped__";

function allTags(data: TagGroupsResponse): TagReadWithCount[] {
  return [...data.groups.flatMap((g) => g.tags), ...data.groupless];
}

export function TagGroupsPage() {
  const { t } = useTranslation();
  const query = useTagGroups();
  const localize = useLocalizedName();

  const updateTag = useUpdateTag();
  const mergeTags = useMergeTags();
  const createGroup = useCreateTagGroup();
  const updateGroup = useUpdateTagGroup();

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
    setErrorMessage(mapApiError(err, t));
  }

  const tagActions: TagActions = {
    onRename: (tag) => openDialog({ kind: "rename-tag", tag }),
    onMove: (tag) => openDialog({ kind: "move", tag }),
    onMerge: (tag) => openDialog({ kind: "merge", tag }),
  };

  async function reorder(group: TagGroupRead, direction: "up" | "down") {
    if (!data) return;
    const groups = data.groups;
    const index = groups.findIndex((g) => g.id === group.id);
    const otherIndex = direction === "up" ? index - 1 : index + 1;
    const current = groups[index];
    const other = groups[otherIndex];
    if (!current || !other) return; // boundary guard (buttons are already disabled)
    // Adjacent-swap the stored `position`. Run the two PATCHes sequentially so a
    // mid-swap failure leaves at most one applied write; if the second PATCH fails
    // after the first landed, compensate by restoring `current` to its original
    // position so the server never persists two groups sharing a `position` (which
    // would be an inconsistent, slug-tie-broken order). Either way the error toast
    // fires and the list re-syncs from the server via the hook's invalidation.
    try {
      await updateGroup.mutateAsync({ id: current.id, body: { position: other.position } });
      try {
        await updateGroup.mutateAsync({ id: other.id, body: { position: current.position } });
      } catch (err) {
        // Best-effort rollback of the first write; swallow its own failure so the
        // original error still surfaces as the reorder-failed toast + refetch.
        await updateGroup
          .mutateAsync({ id: current.id, body: { position: current.position } })
          .catch(() => {});
        throw err;
      }
      toast.success(t("modules.admin.tagGroups.toast.reordered"));
    } catch {
      toast.error(t("modules.admin.tagGroups.toast.reorder_failed"));
    }
  }

  const groupActions: GroupActions = {
    onRename: (group) => openDialog({ kind: "rename-group", group }),
    onMoveUp: (group) => void reorder(group, "up"),
    onMoveDown: (group) => void reorder(group, "down"),
  };

  function submitRenameTag(tag: TagReadWithCount, values: { name_en: string; name_pl: string | null }) {
    const body: TagPatchBody = {};
    if (values.name_en !== tag.name_en) body.name_en = values.name_en;
    if (values.name_pl !== tag.name_pl) body.name_pl = values.name_pl;
    if (Object.keys(body).length === 0) {
      closeDialog();
      return;
    }
    updateTag.mutate(
      { id: tag.id, body },
      {
        onSuccess: () => {
          toast.success(t("modules.admin.tagGroups.toast.tag_renamed"));
          closeDialog();
        },
        onError: onWriteError,
      },
    );
  }

  function submitRenameGroup(group: TagGroupRead, values: { name_en: string; name_pl: string | null }) {
    const body: TagGroupPatchBody = {};
    if (values.name_en !== group.name_en) body.name_en = values.name_en;
    if (values.name_pl !== group.name_pl) body.name_pl = values.name_pl;
    if (Object.keys(body).length === 0) {
      closeDialog();
      return;
    }
    updateGroup.mutate(
      { id: group.id, body },
      {
        onSuccess: () => {
          toast.success(t("modules.admin.tagGroups.toast.group_renamed"));
          closeDialog();
        },
        onError: onWriteError,
      },
    );
  }

  function submitMove(tag: TagReadWithCount, groupId: string | null) {
    if (!data) return;
    // CRITICAL (42.4): send group_position explicitly = target container's current
    // tag count so the moved tag appends at the end (never a silent position-0 clash).
    const group_position =
      groupId === null
        ? data.groupless.length
        : (data.groups.find((g) => g.id === groupId)?.tags.length ?? 0);
    updateTag.mutate(
      { id: tag.id, body: { group_id: groupId, group_position } },
      {
        onSuccess: () => {
          toast.success(t("modules.admin.tagGroups.toast.moved"));
          closeDialog();
        },
        onError: onWriteError,
      },
    );
  }

  function submitMerge(tag: TagReadWithCount, targetId: string) {
    mergeTags.mutate(
      { from_id: tag.id, to_id: targetId },
      {
        onSuccess: () => {
          toast.success(t("modules.admin.tagGroups.toast.merged"));
          closeDialog();
        },
        onError: onWriteError,
      },
    );
  }

  function submitCreate(values: { slug: string; name_en: string; name_pl: string | null }) {
    if (!data) return;
    createGroup.mutate(
      { ...values, position: data.groups.length },
      {
        onSuccess: () => {
          toast.success(t("modules.admin.tagGroups.toast.group_created"));
          closeDialog();
        },
        onError: onWriteError,
      },
    );
  }

  function moveOptions(tag: TagReadWithCount): MoveTargetOption[] {
    if (!data) return [];
    const options: MoveTargetOption[] = [];
    for (const g of data.groups) {
      if (g.id === tag.group_id) continue; // exclude current container
      options.push({ key: g.id, label: localize(g.name_en, g.name_pl), groupId: g.id });
    }
    if (tag.group_id !== null) {
      options.push({
        key: UNGROUPED_KEY,
        label: t("modules.admin.tagGroups.ungrouped_title"),
        groupId: null,
      });
    }
    return options;
  }

  function mergeOptions(tag: TagReadWithCount): MergeTargetOption[] {
    if (!data) return [];
    return allTags(data)
      .filter((x) => x.id !== tag.id)
      .map((x) => ({ id: x.id, label: localize(x.name_en, x.name_pl) }));
  }

  const onDialogOpenChange = (next: boolean) => {
    if (!next) closeDialog();
  };

  return (
    <div className="flex flex-col gap-4 p-4">
      <AdminTabs activeTab="tag-groups" />

      <header className="flex flex-col gap-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex flex-col gap-1">
            <h1 className="text-lg font-semibold text-foreground">
              {t("modules.admin.tagGroups.title")}
            </h1>
            <p className="text-xs text-muted-foreground">
              {t("modules.admin.tagGroups.description")}
            </p>
          </div>
          {data ? (
            <Button size="sm" onClick={() => openDialog({ kind: "create" })}>
              <Plus className="size-4" aria-hidden />
              {t("modules.admin.tagGroups.actions.create_group")}
            </Button>
          ) : null}
        </div>
      </header>

      {data ? (
        // Prefer showing already-loaded data over a background-refetch error (mirrors
        // TanStack Query's stale-while-error convention): a transient refetch failure
        // must not hide previously-successful, still-valid tag groups.
        data.groups.length === 0 && data.groupless.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("modules.admin.tagGroups.empty")}</p>
        ) : (
          <>
            {data.groups.map((group, i) => (
              <GroupSection
                key={group.id}
                group={group}
                isFirst={i === 0}
                isLast={i === data.groups.length - 1}
                reorderPending={updateGroup.isPending}
                groupActions={groupActions}
                tagActions={tagActions}
              />
            ))}
            <GrouplessSection tags={data.groupless} tagActions={tagActions} />
          </>
        )
      ) : query.isError ? (
        // Fails-closed: never fabricate an empty/green state on a failed read (mirrors QueuesPage).
        <div className="flex flex-col items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-4">
          <p className="text-sm font-medium text-destructive">
            {t("modules.admin.tagGroups.error_title")}
          </p>
          <Button
            variant="outline"
            size="sm"
            disabled={query.isFetching}
            onClick={() => void query.refetch()}
          >
            {t("modules.admin.tagGroups.retry")}
          </Button>
        </div>
      ) : (
        <div className="flex flex-col gap-3" aria-hidden="true" data-testid="tag-groups-skeleton">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-md bg-muted" />
          ))}
        </div>
      )}

      {dialog?.kind === "rename-tag" ? (
        <RenameEntityDialog
          open
          onOpenChange={onDialogOpenChange}
          title={t("modules.admin.tagGroups.rename.title_tag")}
          description={t("modules.admin.tagGroups.rename.description")}
          initialNameEn={dialog.tag.name_en}
          initialNamePl={dialog.tag.name_pl}
          pending={updateTag.isPending}
          errorMessage={errorMessage}
          onSubmit={(values) => submitRenameTag(dialog.tag, values)}
        />
      ) : null}

      {dialog?.kind === "rename-group" ? (
        <RenameEntityDialog
          open
          onOpenChange={onDialogOpenChange}
          title={t("modules.admin.tagGroups.rename.title_group")}
          description={t("modules.admin.tagGroups.rename.description")}
          initialNameEn={dialog.group.name_en}
          initialNamePl={dialog.group.name_pl}
          pending={updateGroup.isPending}
          errorMessage={errorMessage}
          onSubmit={(values) => submitRenameGroup(dialog.group, values)}
        />
      ) : null}

      {dialog?.kind === "move" ? (
        <MoveTagDialog
          open
          onOpenChange={onDialogOpenChange}
          tagName={localize(dialog.tag.name_en, dialog.tag.name_pl)}
          options={moveOptions(dialog.tag)}
          pending={updateTag.isPending}
          errorMessage={errorMessage}
          onSubmit={(groupId) => submitMove(dialog.tag, groupId)}
        />
      ) : null}

      {dialog?.kind === "merge" ? (
        <MergeTagDialog
          open
          onOpenChange={onDialogOpenChange}
          sourceName={localize(dialog.tag.name_en, dialog.tag.name_pl)}
          options={mergeOptions(dialog.tag)}
          pending={mergeTags.isPending}
          errorMessage={errorMessage}
          onSubmit={(targetId) => submitMerge(dialog.tag, targetId)}
        />
      ) : null}

      {dialog?.kind === "create" ? (
        <CreateGroupDialog
          open
          onOpenChange={onDialogOpenChange}
          pending={createGroup.isPending}
          errorMessage={errorMessage}
          onSubmit={submitCreate}
        />
      ) : null}
    </div>
  );
}
