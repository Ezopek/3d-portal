import { useReducer, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/ui/dialog";

import { Viewer3DCanvas, type CanvasHandle } from "./Viewer3DCanvas";
import { ViewToolbar } from "./controls/ViewToolbar";
import { FileSelector } from "./controls/FileSelector";
import { MeasureSummary } from "./controls/MeasureSummary";
import { useFileIndex } from "./hooks/useFileIndex";
import { usePerfGuard } from "./hooks/usePerfGuard";
import { useStlGeometry } from "./hooks/useStlGeometry";
import type { ViewPreset } from "./lib/camera";
import {
  initialMeasureState,
  measureReducer,
  type MeasureAction,
} from "./measure/measureReducer";
import type { Viewer3DProps } from "./types";

export default function Viewer3DModal({ files, initialFileId, onClose }: Viewer3DProps) {
  const { t } = useTranslation();
  const idx = useFileIndex(files);
  const perf = usePerfGuard();
  const firstId = idx.sorted[0]?.id ?? "";
  const [activeId, setActiveId] = useState<string>(initialFileId ?? firstId);
  const file = idx.sorted.find((f) => f.id === activeId);
  const needsConfirm = perf.needsConfirmForSize(file?.size);
  const [confirmed, setConfirmed] = useState(false);
  // Reset confirmation when the user navigates to a different file.
  const lastSeenId = useRef(activeId);
  if (lastSeenId.current !== activeId) {
    lastSeenId.current = activeId;
    if (confirmed) setConfirmed(false);
  }
  const allowLoad = !needsConfirm || confirmed;
  const { geometry, error, isLoading } = useStlGeometry({
    modelId: allowLoad ? (file?.modelId ?? "") : "",
    fileId: allowLoad ? activeId : "",
  });
  const isLargeMesh = perf.isLargeMesh(geometry);
  const triangleCount = perf.triangleCount(geometry);

  const [preset, setPreset] = useState<ViewPreset>("iso");
  const [resetSignal, setResetSignal] = useState(0);
  const [wireframe, setWireframe] = useState(false);
  const [state, dispatch] = useReducer(measureReducer, initialMeasureState);
  const handleRef = useRef<CanvasHandle | null>(null);

  const onKey = (e: React.KeyboardEvent<HTMLDivElement>) => {
    // Cancel an in-progress measurement before letting Dialog catch Esc and
    // close the modal — user expectation is "Esc backs out of the smallest
    // operation in flight first".
    if (e.key === "Escape" && state.active.points.length > 0) {
      e.preventDefault();
      e.stopPropagation();
      dispatch({ type: "cancel-active" });
      return;
    }
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    const i = idx.sorted.findIndex((f) => f.id === activeId);
    if (i < 0) return;
    const next =
      e.key === "ArrowRight"
        ? Math.min(idx.sorted.length - 1, i + 1)
        : Math.max(0, i - 1);
    setActiveId(idx.sorted[next]?.id ?? activeId);
  };

  const screenshot = async () => {
    const blob = await handleRef.current?.takeScreenshot();
    if (blob === undefined || blob === null) return;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${file?.modelId ?? "model"}-${activeId}.png`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Dialog open onOpenChange={(open) => !open && onClose?.()}>
      <DialogContent
        className="h-[90vh] w-[95vw] max-w-[95vw] sm:max-w-[1400px] p-0 outline-none"
        onKeyDown={onKey}
      >
        <DialogTitle className="sr-only">
          {file?.name ?? t("viewer3d.dialog_title_fallback")}
        </DialogTitle>
        <div className="relative h-full">
          <div className="absolute left-1/2 top-3 z-10 -translate-x-1/2">
            <FileSelector
              files={idx.sorted}
              activeId={activeId}
              onSelect={setActiveId}
            />
          </div>
          {needsConfirm && !confirmed ? (
            <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
              <p className="text-base font-medium">
                {t("viewer3d.confirm_large.title")}
              </p>
              <p className="text-sm text-muted-foreground">
                {t("viewer3d.confirm_large.body", {
                  size: Math.round((file?.size ?? 0) / (1024 * 1024)),
                })}
              </p>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => onClose?.()}
                >
                  {t("common.cancel")}
                </Button>
                <Button
                  type="button"
                  variant="default"
                  size="sm"
                  onClick={() => setConfirmed(true)}
                >
                  {t("viewer3d.confirm_large.continue")}
                </Button>
              </div>
            </div>
          ) : error !== null ? (
            <div
              className="flex h-full items-center justify-center text-destructive"
              role="alert"
            >
              {t("viewer3d.fetch_error")}
            </div>
          ) : isLoading || geometry === null ? (
            <div className="flex h-full items-center justify-center text-sm">
              {t("viewer3d.loading")}
            </div>
          ) : (
            <>
              {isLargeMesh && (
                <div
                  role="status"
                  className="absolute right-3 top-3 z-10 rounded bg-warning/20 px-2 py-1 text-xs text-warning"
                >
                  {t("viewer3d.large_mesh_warning", {
                    formatted: triangleCount.toLocaleString(),
                  })}
                </div>
              )}
              <Viewer3DCanvas
                geometry={geometry}
                preset={preset}
                resetSignal={resetSignal}
                wireframe={wireframe}
                measureMode={state.mode}
                state={state}
                dispatch={dispatch as (a: MeasureAction) => void}
                damping={!isLargeMesh}
                onCanvasReady={(h) => {
                  handleRef.current = h;
                }}
              />
            </>
          )}
          <div className="absolute bottom-3 left-1/2 z-10 -translate-x-1/2">
            <ViewToolbar
              onPreset={setPreset}
              onReset={() => {
                setPreset("iso");
                setResetSignal((n) => n + 1);
                dispatch({ type: "clear" });
              }}
              wireframe={wireframe}
              onWireframe={setWireframe}
              onScreenshot={() => {
                void screenshot();
              }}
              measureOn={state.mode === "point-to-point"}
              onMeasureToggle={() =>
                dispatch({
                  type: "set-mode",
                  mode: state.mode === "off" ? "point-to-point" : "off",
                })
              }
            />
          </div>
          <div className="pointer-events-none absolute left-3 top-3 z-10 max-h-[40vh] max-w-[280px] overflow-y-auto">
            <MeasureSummary
              measurements={state.completed}
              onClear={() => dispatch({ type: "clear" })}
            />
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
