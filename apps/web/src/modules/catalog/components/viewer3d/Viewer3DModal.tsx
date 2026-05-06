import { useReducer, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Dialog, DialogContent, DialogTitle } from "@/ui/dialog";

import { Viewer3DCanvas, type CanvasHandle } from "./Viewer3DCanvas";
import { ViewToolbar, type ToolMode } from "./controls/ViewToolbar";
import { FileSelector } from "./controls/FileSelector";
import { MeasureSummary } from "./controls/MeasureSummary";
import { useFileIndex } from "./hooks/useFileIndex";
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
  const firstId = idx.sorted[0]?.id ?? "";
  const [activeId, setActiveId] = useState<string>(initialFileId ?? firstId);
  const file = idx.sorted.find((f) => f.id === activeId);
  const { geometry, error, isLoading } = useStlGeometry({
    modelId: file?.modelId ?? "",
    fileId: activeId,
  });

  const [preset, setPreset] = useState<ViewPreset>("iso");
  const [wireframe, setWireframe] = useState(false);
  const [mode, setMode] = useState<ToolMode>("orbit");
  const [state, dispatch] = useReducer(measureReducer, initialMeasureState);
  const handleRef = useRef<CanvasHandle | null>(null);

  const onKey = (e: React.KeyboardEvent<HTMLDivElement>) => {
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
        className="h-[90vh] w-[95vw] max-w-[1400px] p-0 outline-none"
        onKeyDown={onKey}
      >
        <DialogTitle className="sr-only">{file?.name ?? "3D viewer"}</DialogTitle>
        <div className="relative h-full">
          <div className="absolute left-1/2 top-3 z-10 -translate-x-1/2">
            <FileSelector
              files={idx.sorted}
              activeId={activeId}
              onSelect={setActiveId}
            />
          </div>
          {error !== null ? (
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
            <Viewer3DCanvas
              geometry={geometry}
              preset={preset}
              wireframe={wireframe}
              measureMode={state.mode}
              state={state}
              dispatch={dispatch as (a: MeasureAction) => void}
              onCanvasReady={(h) => {
                handleRef.current = h;
              }}
            />
          )}
          <div className="absolute bottom-3 left-1/2 z-10 -translate-x-1/2">
            <ViewToolbar
              mode={mode}
              onMode={setMode}
              onPreset={setPreset}
              onReset={() => setPreset("iso")}
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
          <div className="absolute bottom-3 right-3 z-10 max-w-[280px]">
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
