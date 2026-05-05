import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import type { CategoryNode, CategoryTree } from "@/lib/api-types";
import { cn } from "@/lib/utils";

const STORAGE_KEY = "catalog:tree-expand";

interface Props {
  tree: CategoryTree;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  /**
   * When true, the sidebar omits its desktop-only `hidden lg:block` wrapper and
   * adapts layout for being slotted inside a Sheet/drawer on mobile.
   */
  mobile?: boolean;
}

function totalCount(tree: CategoryTree): number {
  return tree.roots.reduce((acc, root) => acc + root.model_count, 0);
}

export function CategoryTreeSidebar({ tree, selectedId, onSelect, mobile = false }: Props) {
  const { t, i18n } = useTranslation();
  const [expanded, setExpanded] = useState<Set<string>>(() => loadExpanded());

  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify([...expanded]));
  }, [expanded]);

  function toggle(slug: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      return next;
    });
  }

  const asideClassName = mobile
    ? "w-full bg-card p-4"
    : "hidden w-60 shrink-0 border-r border-border bg-card p-4 lg:block";

  return (
    <aside className={asideClassName}>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {t("catalog.filters.category")}
      </h3>
      <button
        type="button"
        aria-label="select all categories"
        onClick={() => onSelect(null)}
        className={cn(
          "flex w-full items-center justify-between rounded px-2 py-1 text-left text-sm",
          selectedId === null ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground",
        )}
      >
        <span>{t("common.all")}</span>
        <span className="text-xs">{totalCount(tree)}</span>
      </button>
      <ul className="mt-1 space-y-0.5">
        {tree.roots.map((root) => (
          <TreeRow
            key={root.id}
            node={root}
            depth={0}
            expanded={expanded}
            toggle={toggle}
            selectedId={selectedId}
            onSelect={onSelect}
            preferPl={i18n.language.startsWith("pl")}
          />
        ))}
      </ul>
    </aside>
  );
}

interface RowProps {
  node: CategoryNode;
  depth: number;
  expanded: Set<string>;
  toggle: (slug: string) => void;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  preferPl: boolean;
}

function TreeRow({ node, depth, expanded, toggle, selectedId, onSelect, preferPl }: RowProps) {
  const isExpanded = expanded.has(node.slug);
  const hasChildren = node.children.length > 0;
  const label = preferPl && node.name_pl !== null ? node.name_pl : node.name_en;
  const count = node.model_count;
  return (
    <li>
      <div className="flex items-center gap-1" style={{ paddingLeft: depth * 12 }}>
        {hasChildren ? (
          <button
            type="button"
            aria-label={`expand ${node.slug}`}
            onClick={() => toggle(node.slug)}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            {isExpanded ? "▾" : "▸"}
          </button>
        ) : (
          <span className="w-4" />
        )}
        <button
          type="button"
          onClick={() => onSelect(node.id)}
          className={cn(
            "flex flex-1 items-center justify-between rounded px-2 py-1 text-left text-sm",
            selectedId === node.id
              ? "bg-accent text-accent-foreground"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          <span>{label}</span>
          <span className="text-xs">{count}</span>
        </button>
      </div>
      {hasChildren && isExpanded && (
        <ul className="space-y-0.5">
          {node.children.map((child) => (
            <TreeRow
              key={child.id}
              node={child}
              depth={depth + 1}
              expanded={expanded}
              toggle={toggle}
              selectedId={selectedId}
              onSelect={onSelect}
              preferPl={preferPl}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

function loadExpanded(): Set<string> {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw === null) return new Set();
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return new Set();
    return new Set(parsed.filter((s): s is string => typeof s === "string"));
  } catch {
    return new Set();
  }
}
