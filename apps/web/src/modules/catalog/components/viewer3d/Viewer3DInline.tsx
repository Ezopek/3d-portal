import { Suspense, useReducer, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/ui/button";

import { Viewer3DCanvas, type CanvasHandle } from "./Viewer3DCanvas";
import { ViewToolbar, type ToolMode } from "./controls/ViewToolbar";
import { FileSelector } from "./controls/FileSelector";
import { useFileIndex } from "./hooks/useFileIndex";
import { useStlGeometry } from "./hooks/useStlGeometry";
import type { ViewPreset } from "./lib/camera";
import {
  initialMeasureState,
  measureReducer,
  type MeasureAction,
} from "./measure/measureReducer";
import type { StlFile, Viewer3DProps } from "./types";

const AUTO_LOAD_BYTES = 5 * 1024 * 1024;

type Props = Viewer3DProps & {
  onExpand: (activeFileId: string) => void;
};

export default function Viewer3DInline({
  files,
  initialFileId,
  thumbnailUrl,
  onExpand,
}: Props) {
  const { t } = useTranslation();
  const idx = useFileIndex(files);
  const firstId = idx.sorted[0]?.id ?? "";
  const [activeId, setActiveId] = useState<string>(initialFileId ?? firstId);
  const activeFile = idx.sorted.find((f) => f.id === activeId);
  const shouldAutoLoad =
    thumbnailUrl === undefined && (activeFile?.size ?? 0) < AUTO_LOAD_BYTES;
  const [loaded, setLoaded] = useState<boolean>(shouldAutoLoad);

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      <FileSelector files={idx.sorted} activeId={activeId} onSelect={setActiveId} />
      <div className="relative aspect-square overflow-hidden rounded border border-border bg-muted/30 md:aspect-auto md:min-h-[280px]">
        {loaded ? (
          <Suspense
            fallback={<div className="p-3 text-xs">{t("viewer3d.loading")}</div>}
          >
            <CanvasLoader
              files={idx.sorted}
              fileId={activeId}
              onExpand={() => onExpand(activeId)}
            />
          </Suspense>
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
              onClick={() => setLoaded(true)}
              className="relative z-10"
            >
              {t("viewer3d.open_3d")}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

function CanvasLoader({
  files,
  fileId,
  onExpand,
}: {
  files: readonly StlFile[];
  fileId: string;
  onExpand: () => void;
}) {
  const { t } = useTranslation();
  const file = files.find((f) => f.id === fileId);
  const { geometry, error, isLoading } = useStlGeometry({
    modelId: file?.modelId ?? "",
    fileId,
  });
  const [preset, setPreset] = useState<ViewPreset>("iso");
  const [wireframe, setWireframe] = useState(false);
  const [mode, setMode] = useState<ToolMode>("orbit");
  const [state, dispatch] = useReducer(measureReducer, initialMeasureState);
  const handleRef = useRef<CanvasHandle | null>(null);

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
    a.download = `${file?.modelId ?? "model"}-${fileId}.png`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="absolute inset-0 flex flex-col">
      <div className="absolute right-2 top-2 z-10">
        <Button type="button" size="sm" variant="secondary" onClick={onExpand}>
          {t("viewer3d.tooltip.expand")}
        </Button>
      </div>
      <div className="flex-1">
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
      </div>
      <div className="border-t border-border p-2">
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
    </div>
  );
}
