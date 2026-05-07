import { ChevronDown, ChevronUp, Check } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";

import { useFileIndex } from "../hooks/useFileIndex";
import type { StlFile } from "../types";

type Props = {
  files: readonly StlFile[];
  activeId: string;
  onSelect: (id: string) => void;
};

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FileSelector({ files, activeId, onSelect }: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const idx = useFileIndex(files);
  const active = idx.sorted.find((f) => f.id === activeId);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (q === "") return idx.sorted;
    return idx.sorted.filter((f) => f.name.toLowerCase().includes(q));
  }, [idx.sorted, query]);

  return (
    <div className="w-full max-w-full rounded-lg border border-border bg-card/85 backdrop-blur-md sm:min-w-[260px]">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-3 py-2 text-left"
        aria-expanded={open}
        aria-label={`${t("viewer3d.file_selector.label")}: ${active?.name ?? ""}`}
      >
        <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
          {t("viewer3d.file_selector.label")}
        </span>
        <span className="flex-1 truncate font-mono text-sm">{active?.name ?? "—"}</span>
        <span className="text-xs font-mono text-muted-foreground">
          {t("viewer3d.file_selector.position", {
            n: idx.positionOf(activeId),
            total: idx.sorted.length,
          })}
        </span>
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {open && (
        <div className="border-t border-border">
          <div className="p-2 border-b border-border">
            <input
              type="text"
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t("viewer3d.file_selector.search")}
              className="w-full rounded border border-input bg-background px-2 py-1 text-xs"
            />
          </div>
          <ul className="max-h-72 overflow-y-auto" role="listbox">
            {filtered.map((f) => (
              <li
                key={f.id}
                role="option"
                aria-selected={f.id === activeId}
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelect(f.id);
                    setOpen(false);
                    setQuery("");
                  }
                }}
                className={cn(
                  "flex cursor-pointer items-center gap-2 px-3 py-1.5 text-xs",
                  f.id === activeId
                    ? "bg-accent text-accent-foreground"
                    : "hover:bg-accent/50",
                )}
                onClick={() => {
                  onSelect(f.id);
                  setOpen(false);
                  setQuery("");
                }}
              >
                <span className="w-3">
                  {f.id === activeId ? <Check className="h-3 w-3" /> : null}
                </span>
                <span className="flex-1 truncate font-mono">{f.name}</span>
                <span className="text-muted-foreground">{fmtSize(f.size)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
