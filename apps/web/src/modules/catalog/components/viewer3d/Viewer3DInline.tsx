import { useReducer, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/ui/button";

import { Viewer3DCanvas, type CanvasHandle } from "./Viewer3DCanvas";
import { ViewToolbar } from "./controls/ViewToolbar";
import { MeasureSummary } from "./controls/MeasureSummary";
import { usePerfGuard } from "./hooks/usePerfGuard";
import { useStlGeometry } from "./hooks/useStlGeometry";
import type { ViewPreset } from "./lib/camera";
import {
  initialMeasureState,
  measureReducer,
  type MeasureAction,
} from "./measure/measureReducer";
import type { StlFile } from "./types";

export type Viewer3DInlineProps = {
  /** Single STL file scoped to this inline mount (one per expanded row). */
  file: StlFile;
  onExpand: () => void;
};

export default function Viewer3DInline({ file, onExpand }: Viewer3DInlineProps) {
  const { t } = useTranslation();
  const perf = usePerfGuard();
  // Expanding the row IS the user's "load this STL" gesture, so the canvas
  // mounts immediately. The only gate left is the >50 MB confirm dialog.
  const needsConfirm = perf.needsConfirmForSize(file.size);
  const [confirmed, setConfirmed] = useState(false);
  const sizeMb = Math.round(file.size / (1024 * 1024));

  return (
    <div className="relative aspect-square w-full overflow-hidden rounded border border-border bg-muted/30 md:aspect-auto md:min-h-[280px]">
      {needsConfirm && !confirmed ? (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 p-3 text-center">
          <p className="text-sm font-medium">
            {t("viewer3d.confirm_large.title")}
          </p>
          <p className="text-xs text-muted-foreground">
            {t("viewer3d.confirm_large.body", { size: sizeMb })}
          </p>
          <Button
            type="button"
            variant="default"
            size="sm"
            onClick={() => setConfirmed(true)}
          >
            {t("viewer3d.confirm_large.continue")}
          </Button>
        </div>
      ) : (
        <CanvasLoader file={file} onExpand={onExpand} />
      )}
    </div>
  );
}

function CanvasLoader({
  file,
  onExpand,
}: {
  file: StlFile;
  onExpand: () => void;
}) {
  const { t } = useTranslation();
  const { geometry, error, isLoading } = useStlGeometry({
    modelId: file.modelId,
    fileId: file.id,
  });
  const perf = usePerfGuard();
  const isLargeMesh = perf.isLargeMesh(geometry);
  const triangleCount = perf.triangleCount(geometry);
  const [preset, setPreset] = useState<ViewPreset>("iso");
  const [resetSignal, setResetSignal] = useState(0);
  const [wireframe, setWireframe] = useState(false);
  const [state, dispatch] = useReducer(measureReducer, initialMeasureState);
  const handleRef = useRef<CanvasHandle | null>(null);

  const onKey = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape" && state.active.stage !== "empty") {
      e.preventDefault();
      e.stopPropagation();
      dispatch({ type: "cancel-active" });
      return;
    }
  };

  if (error !== null)
    return (
      <div className="p-3 text-sm text-destructive" role="alert">
        {t("viewer3d.fetch_error")}
      </div>
    );
  if (isLoading || geometry === null)
    return <div className="p-3 text-xs">{t("viewer3d.loading")}</div>;

  const screenshot = async () => {
    const blob = await handleRef.current?.takeScreenshot();
    if (blob === undefined || blob === null) return;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${file.modelId}-${file.id}.png`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      className="absolute inset-0 flex flex-col"
      onKeyDown={onKey}
      tabIndex={-1}
    >
      <div className="absolute right-2 top-2 z-10">
        <Button type="button" size="sm" variant="secondary" onClick={onExpand}>
          {t("viewer3d.tooltip.expand")}
        </Button>
      </div>
      {isLargeMesh && (
        <div
          role="status"
          className="absolute left-2 top-2 z-10 rounded bg-warning/20 px-2 py-1 text-[10px] text-warning"
        >
          {t("viewer3d.large_mesh_warning", {
            formatted: triangleCount.toLocaleString(),
          })}
        </div>
      )}
      <div className="flex-1">
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
      </div>
      <div className="space-y-2 border-t border-border p-2">
        <ViewToolbar
          onReset={() => {
            setPreset("iso");
            setResetSignal((n) => n + 1);
            dispatch({ type: "cancel-active" });
          }}
          wireframe={wireframe}
          onWireframe={setWireframe}
          onScreenshot={() => {
            void screenshot();
          }}
          mode={state.mode}
          onMode={(m) => dispatch({ type: "set-mode", mode: m })}
          toleranceDeg={state.toleranceDeg}
          onTolerance={(v) => dispatch({ type: "set-tolerance", value: v })}
        />
        <details className="text-xs">
          <summary className="cursor-pointer text-muted-foreground">
            {t("viewer3d.measure.summary_title")} ({state.completed.length})
          </summary>
          <div className="mt-1">
            <MeasureSummary
              measurements={state.completed}
              onClear={() => dispatch({ type: "clear" })}
            />
          </div>
        </details>
      </div>
    </div>
  );
}
