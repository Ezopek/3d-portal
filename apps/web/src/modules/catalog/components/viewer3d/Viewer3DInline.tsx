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
import type { StlFile, ToolMode } from "./types";

const AUTO_LOAD_BYTES = 5 * 1024 * 1024;

export type Viewer3DInlineProps = {
  /** Single STL file scoped to this inline mount (one per expanded row). */
  file: StlFile;
  /** When set, shown as a placeholder behind an "Open 3D" button until the
   * user clicks. Without it, files smaller than AUTO_LOAD_BYTES auto-load. */
  thumbnailUrl?: string;
  onExpand: () => void;
};

export default function Viewer3DInline({
  file,
  thumbnailUrl,
  onExpand,
}: Viewer3DInlineProps) {
  const { t } = useTranslation();
  const perf = usePerfGuard();
  const shouldAutoLoad =
    thumbnailUrl === undefined &&
    file.size < AUTO_LOAD_BYTES &&
    !perf.needsConfirmForSize(file.size);
  const [loaded, setLoaded] = useState<boolean>(shouldAutoLoad);
  const needsConfirm = loaded && perf.needsConfirmForSize(file.size);
  const [confirmed, setConfirmed] = useState(false);
  const sizeMb = Math.round(file.size / (1024 * 1024));

  return (
    <div className="relative aspect-square w-full overflow-hidden rounded border border-border bg-muted/30 md:aspect-auto md:min-h-[280px]">
      {loaded && (!needsConfirm || confirmed) ? (
        <CanvasLoader file={file} onExpand={onExpand} />
      ) : loaded && needsConfirm ? (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 p-3 text-center">
          <p className="text-sm font-medium">
            {t("viewer3d.confirm_large.title")}
          </p>
          <p className="text-xs text-muted-foreground">
            {t("viewer3d.confirm_large.body", { size: sizeMb })}
          </p>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setLoaded(false)}
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
      ) : (
        <div className="absolute inset-0 flex items-center justify-center">
          {thumbnailUrl !== undefined && (
            <img
              src={thumbnailUrl}
              alt={t("viewer3d.placeholder_alt")}
              className="absolute inset-0 h-full w-full object-contain opacity-60"
            />
          )}
          <Button
            type="button"
            variant="default"
            size="sm"
            onClick={() => {
              setLoaded(true);
              setConfirmed(false);
            }}
            className="relative z-10"
          >
            {t("viewer3d.open_3d")}
          </Button>
        </div>
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
  const [wireframe, setWireframe] = useState(false);
  const [mode, setMode] = useState<ToolMode>("orbit");
  const [state, dispatch] = useReducer(measureReducer, initialMeasureState);
  const handleRef = useRef<CanvasHandle | null>(null);

  const onKey = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape" && state.active.points.length > 0) {
      e.preventDefault();
      dispatch({ type: "cancel-active" });
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
          wireframe={wireframe}
          toolMode={mode}
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
