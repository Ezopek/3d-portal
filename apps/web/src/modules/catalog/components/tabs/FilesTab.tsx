import { useState } from "react";

import type { ModelFileKind, ModelFileRead } from "@/lib/api-types";
import { cn } from "@/lib/utils";
import { useSetFileRenderSelection } from "@/modules/catalog/hooks/mutations/useSetFileRenderSelection";
import { useAuth } from "@/shell/AuthContext";

type Visible = "stl" | "source" | "archive_3mf";

const CHIPS: { kind: Visible; label: string }[] = [
  { kind: "stl", label: "STL" },
  { kind: "source", label: "Source" },
  { kind: "archive_3mf", label: "3MF" },
];

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function isVisible(kind: ModelFileKind): kind is Visible {
  return kind === "stl" || kind === "source" || kind === "archive_3mf";
}

export function FilesTab({
  modelId,
  files,
}: {
  modelId: string;
  files: readonly ModelFileRead[];
}) {
  const [active, setActive] = useState<Visible>("stl");
  const { isAdmin } = useAuth();
  const setRenderSelection = useSetFileRenderSelection(modelId);
  const counts = new Map<Visible, number>();
  for (const f of files) {
    if (isVisible(f.kind)) counts.set(f.kind, (counts.get(f.kind) ?? 0) + 1);
  }
  const visible = files.filter((f) => f.kind === active);
  return (
    <div className="space-y-3 p-3">
      <div className="flex flex-wrap gap-2">
        {CHIPS.map((c) => (
          <button
            key={c.kind}
            type="button"
            onClick={() => setActive(c.kind)}
            className={cn(
              "rounded px-3 py-1 text-xs",
              c.kind === active
                ? "bg-accent text-accent-foreground"
                : "bg-muted text-muted-foreground hover:text-foreground",
            )}
          >
            {c.label} · {counts.get(c.kind) ?? 0}
          </button>
        ))}
      </div>
      {isAdmin && active === "stl" && visible.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Checked STLs feed the auto-render preview.
        </p>
      )}
      {visible.length === 0 ? (
        <p className="text-sm text-muted-foreground">no files</p>
      ) : (
        <ul className="divide-y divide-border rounded border border-border">
          {visible.map((f) => (
            <li key={f.id} className="flex items-center gap-3 p-2 text-sm">
              {isAdmin && f.kind === "stl" && (
                <input
                  type="checkbox"
                  aria-label={`include ${f.original_name} in renders`}
                  checked={f.selected_for_render}
                  disabled={setRenderSelection.isPending}
                  onChange={(e) =>
                    setRenderSelection.mutate({
                      fileId: f.id,
                      selected: e.currentTarget.checked,
                    })
                  }
                />
              )}
              <span className="font-mono text-xs">{f.kind}</span>
              <span className="flex-1 truncate">{f.original_name}</span>
              <span className="text-xs text-muted-foreground">
                {fmtSize(f.size_bytes)}
              </span>
              <a
                href={`/api/models/${modelId}/files/${f.id}/content?download=1`}
                className="rounded px-2 py-1 text-xs text-foreground hover:bg-accent"
              >
                ⬇
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
