import { Box, ChevronDown, ChevronRight, Download } from "lucide-react";
import { Suspense, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import type { ModelFileKind, ModelFileRead } from "@/lib/api-types";
import { cn } from "@/lib/utils";
import { useSetFileRenderSelection } from "@/modules/catalog/hooks/mutations/useSetFileRenderSelection";
import { useTriggerRender } from "@/modules/catalog/hooks/mutations/useTriggerRender";
import {
  Viewer3DInline,
  Viewer3DModal,
  type StlFile,
} from "@/modules/catalog/components/viewer3d";
import { useFileIndex } from "@/modules/catalog/components/viewer3d/hooks/useFileIndex";
import { useAuth } from "@/shell/AuthContext";
import { Button } from "@/ui/button";

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
  const { t } = useTranslation();
  const [active, setActive] = useState<Visible>("stl");
  const { isAdmin } = useAuth();
  const setRenderSelection = useSetFileRenderSelection(modelId);
  const triggerRender = useTriggerRender(modelId);

  const stlFiles: StlFile[] = useMemo(
    () =>
      files
        .filter((f) => f.kind === "stl")
        .map((f) => ({
          id: f.id,
          modelId,
          name: f.original_name,
          size: f.size_bytes,
        })),
    [files, modelId],
  );
  const stlIndex = useFileIndex(stlFiles);
  const stlById = useMemo(() => {
    const m = new Map<string, StlFile>();
    for (const f of stlFiles) m.set(f.id, f);
    return m;
  }, [stlFiles]);

  const counts = new Map<Visible, number>();
  for (const f of files) {
    if (isVisible(f.kind)) counts.set(f.kind, (counts.get(f.kind) ?? 0) + 1);
  }
  const visible = files.filter((f) => f.kind === active);
  const [expandedFileId, setExpandedFileId] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalInitialId, setModalInitialId] = useState<string | undefined>(
    undefined,
  );

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
                ? "bg-primary/10 text-primary font-medium"
                : "bg-muted text-muted-foreground hover:text-foreground",
            )}
          >
            {c.label} · {counts.get(c.kind) ?? 0}
          </button>
        ))}
      </div>

      {modalOpen && (
        <Suspense fallback={null}>
          <Viewer3DModal
            files={stlFiles}
            initialFileId={modalInitialId}
            onClose={() => setModalOpen(false)}
          />
        </Suspense>
      )}

      {isAdmin && active === "stl" && visible.length > 0 && (
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">
            {t("catalog.actions.checkedHelp")}
          </p>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={triggerRender.isPending || setRenderSelection.isPending}
            onClick={() =>
              triggerRender.mutate(
                { selected_stl_file_ids: [] },
                {
                  onSuccess: () => toast.success("Render queued"),
                  onError: (e) => toast.error(e.message),
                },
              )
            }
          >
            {triggerRender.isPending
              ? t("catalog.actions.queueing")
              : t("catalog.actions.rerenderPreview")}
          </Button>
        </div>
      )}
      {visible.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("catalog.empty.files")}</p>
      ) : (
        <ul className="divide-y divide-border rounded border border-border">
          {visible.map((f) => {
            const isStl = f.kind === "stl";
            const isExpanded = isStl && expandedFileId === f.id;
            const stlFile = stlById.get(f.id);
            return (
              <li key={f.id} className="text-sm">
                <div className="flex items-center gap-3 p-2">
                  {isAdmin && isStl && (
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
                  {isStl && (
                    <span className="w-6 shrink-0 font-mono text-xs text-muted-foreground">
                      {stlIndex.positionOf(f.id)}
                    </span>
                  )}
                  <span className="font-mono text-xs">{f.kind}</span>
                  <span className="flex-1 truncate">{f.original_name}</span>
                  <span className="text-xs text-muted-foreground">
                    {fmtSize(f.size_bytes)}
                  </span>
                  {isStl && stlFile !== undefined && (
                    <button
                      type="button"
                      aria-expanded={isExpanded}
                      aria-controls={`viewer-row-${f.id}`}
                      aria-label={`Toggle 3D preview for ${f.original_name}`}
                      onClick={() =>
                        setExpandedFileId(isExpanded ? null : f.id)
                      }
                      className="flex items-center gap-1 rounded px-2 py-1 text-xs text-foreground hover:bg-accent"
                    >
                      {isExpanded ? (
                        <ChevronDown className="h-3.5 w-3.5" />
                      ) : (
                        <ChevronRight className="h-3.5 w-3.5" />
                      )}
                      <Box className="h-3.5 w-3.5" />
                    </button>
                  )}
                  <a
                    href={`/api/models/${modelId}/files/${f.id}/content?download=1`}
                    className="flex items-center rounded px-2 py-1 text-xs text-foreground hover:bg-accent"
                    aria-label={t("catalog.actions.download")}
                  >
                    <Download className="size-3.5" aria-hidden />
                  </a>
                </div>
                {isExpanded && stlFile !== undefined && (
                  <div
                    id={`viewer-row-${f.id}`}
                    className="border-t border-border bg-muted/10 p-3"
                  >
                    <Suspense
                      fallback={<div className="text-xs">{t("viewer3d.loading_viewer")}</div>}
                    >
                      <Viewer3DInline
                        file={stlFile}
                        onExpand={() => {
                          setModalInitialId(f.id);
                          setModalOpen(true);
                        }}
                      />
                    </Suspense>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
