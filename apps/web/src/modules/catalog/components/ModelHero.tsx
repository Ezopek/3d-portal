import { Fragment, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import type { CategoryNode, CategorySummary, ModelDetail } from "@/lib/api-types";
import { DeleteModelDialog } from "@/modules/catalog/components/dialogs/DeleteModelDialog";
import { RatingPopover } from "@/modules/catalog/components/popovers/RatingPopover";
import { StatusPopover } from "@/modules/catalog/components/popovers/StatusPopover";
import { EditDescriptionSheet } from "@/modules/catalog/components/sheets/EditDescriptionSheet";
import { EditTagsSheet } from "@/modules/catalog/components/sheets/EditTagsSheet";
import { useCategoriesTree } from "@/modules/catalog/hooks/useCategoriesTree";
import { useAuth } from "@/shell/AuthContext";
import { Button } from "@/ui/button";
import { SourceBadge } from "@/ui/custom/SourceBadge";
import { StatusBadge } from "@/ui/custom/StatusBadge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/ui/dropdown-menu";

const TAG_DISPLAY_LIMIT = 5;

function flattenCategoryTree(roots: readonly CategoryNode[]): Map<string, CategoryNode> {
  const map = new Map<string, CategoryNode>();
  const stack: CategoryNode[] = [...roots];
  while (stack.length > 0) {
    const node = stack.pop() as CategoryNode;
    map.set(node.id, node);
    for (const child of node.children) stack.push(child);
  }
  return map;
}

function buildAncestorChain(
  leaf: CategorySummary,
  byId: Map<string, CategoryNode>,
): CategorySummary[] {
  // Walk parent_id → root, then reverse so the first entry is the topmost ancestor
  // and the last entry is the immediate (leaf) category.
  const chain: CategorySummary[] = [leaf];
  const seen = new Set<string>([leaf.id]);
  let cursor: string | null = leaf.parent_id;
  while (cursor !== null) {
    if (seen.has(cursor)) break; // defensive: avoid cycles
    const parent = byId.get(cursor);
    if (parent === undefined) break;
    seen.add(parent.id);
    chain.unshift(parent);
    cursor = parent.parent_id;
  }
  return chain;
}

export function ModelHero({ detail }: { detail: ModelDetail }) {
  const { i18n } = useTranslation();
  const { isAdmin } = useAuth();
  const [tagsOpen, setTagsOpen] = useState(false);
  const [descriptionOpen, setDescriptionOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const tree = useCategoriesTree();

  const preferPl = i18n.language.startsWith("pl");
  const title =
    preferPl && detail.name_pl !== null && detail.name_pl !== ""
      ? detail.name_pl
      : detail.name_en;

  const ancestorChain = useMemo<CategorySummary[]>(() => {
    if (tree.data === undefined) return [detail.category];
    const byId = flattenCategoryTree(tree.data.roots);
    return buildAncestorChain(detail.category, byId);
  }, [tree.data, detail.category]);

  const labelFor = (cat: CategorySummary) =>
    preferPl && cat.name_pl !== null ? cat.name_pl : cat.name_en;
  const visibleTags = detail.tags.slice(0, TAG_DISPLAY_LIMIT);
  const overflow = detail.tags.length - visibleTags.length;

  const ratingLabel =
    detail.rating !== null ? (
      <span className="text-xs text-muted-foreground">★ {detail.rating.toFixed(1)}</span>
    ) : (
      <span className="text-xs text-muted-foreground">★ —</span>
    );

  return (
    <div className="border-b border-border bg-background p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-xs text-muted-foreground" data-testid="model-breadcrumb">
            <span>All</span>
            {ancestorChain.map((cat) => (
              <Fragment key={cat.id}>
                {" › "}
                <span>{labelFor(cat)}</span>
              </Fragment>
            ))}
          </div>
          <h1 className="mt-1 text-xl font-semibold text-foreground">{title}</h1>
        </div>
        {isAdmin && (
          <DropdownMenu>
            <DropdownMenuTrigger
              render={
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label="Model actions"
                />
              }
            >
              ⋮
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => setDescriptionOpen(true)}>
                Edit description
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setDeleteOpen(true)}>
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1">
        {isAdmin ? (
          <StatusPopover modelId={detail.id} current={detail.status}>
            <span className="cursor-pointer">
              <StatusBadge status={detail.status} />
            </span>
          </StatusPopover>
        ) : (
          <StatusBadge status={detail.status} />
        )}
        {isAdmin ? (
          <RatingPopover modelId={detail.id} current={detail.rating}>
            <span className="cursor-pointer">{ratingLabel}</span>
          </RatingPopover>
        ) : (
          detail.rating !== null && (
            <span className="text-xs text-muted-foreground">★ {detail.rating.toFixed(1)}</span>
          )
        )}
        <SourceBadge source={detail.source} />
        {visibleTags.map((tag) => (
          <span
            key={tag.id}
            data-testid="tag-chip"
            className="rounded bg-muted px-1.5 py-0.5 text-xs text-chip-foreground"
          >
            {tag.slug}
          </span>
        ))}
        {overflow > 0 && <span className="text-xs text-muted-foreground">+{overflow}</span>}
        {isAdmin && (
          <button
            type="button"
            aria-label="Edit tags"
            onClick={() => setTagsOpen(true)}
            className="text-xs text-muted-foreground opacity-50 hover:opacity-100"
          >
            ✏
          </button>
        )}
      </div>
      {isAdmin && (
        <>
          <EditTagsSheet detail={detail} open={tagsOpen} onOpenChange={setTagsOpen} />
          <EditDescriptionSheet
            detail={detail}
            open={descriptionOpen}
            onOpenChange={setDescriptionOpen}
          />
          <DeleteModelDialog
            detail={detail}
            open={deleteOpen}
            onOpenChange={setDeleteOpen}
          />
        </>
      )}
    </div>
  );
}
