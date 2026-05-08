import { useEffect, useReducer, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/ui/button";

import { Viewer3DCanvas, type CanvasHandle } from "./Viewer3DCanvas";
import { MeasureSummary } from "./controls/MeasureSummary";
import { StepBanner } from "./controls/StepBanner";
import { ViewToolbar } from "./controls/ViewToolbar";
import { usePerfGuard } from "./hooks/usePerfGuard";
import { usePlanePrep } from "./hooks/usePlanePrep";
import { useStlGeometry } from "./hooks/useStlGeometry";
import type { ViewPreset } from "./lib/camera";
import { ClusterOverlay } from "./measure/ClusterOverlay";
import { uniqueClusterVerts } from "./measure/clusterVerts";
import { fitPlane } from "./measure/fitting";
import { floodFill } from "./measure/floodFill";
import {
  anglePlanes,
  distancePointToPlane,
  minVertexPairDistance,
  perpendicularPlaneDistance,
} from "./measure/geometry";
import { displayIndex, pickTangent } from "./measure/labelTangent";
import {
  initialMeasureState,
  measureReducer,
  type MeasureAction,
} from "./measure/measureReducer";
import { RimOverlay } from "./measure/RimOverlay";
import { allocateColorIndex, paletteFor } from "./lib/palette";
import type { Plane, StlFile } from "./types";

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

  const needsWelding =
    state.mode === "point-to-plane" ||
    state.mode === "plane-to-plane" ||
    state.mode === "diameter";
  // Key by geometry instance — see Viewer3DModal for the rationale (avoids
  // weldCache poisoning when activeId changes before useStlGeometry refreshes).
  const cacheKey = geometry?.uuid ?? "";
  const prep = usePlanePrep(geometry, cacheKey, needsWelding);

  // Live tolerance update — see Modal for the dep-array rationale.
  useEffect(() => {
    if (state.active.stage !== "have-plane" || prep.welded === null) return;
    const seed = state.active.plane.seedTriangleId;
    const cluster = floodFill(prep.welded, seed, state.toleranceDeg);
    const plane = fitPlane(prep.welded, [...cluster], seed);
    dispatch({ type: "replace-active-plane", plane });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.toleranceDeg, prep.welded]);

  // p2pl second-click completion patch.
  const lastCompletedLength = useRef(state.completed.length);
  useEffect(() => {
    if (state.completed.length === lastCompletedLength.current) return;
    lastCompletedLength.current = state.completed.length;
    const last = state.completed[state.completed.length - 1];
    if (last === undefined) return;
    if (last.kind === "p2pl" && last.distanceMm === 0) {
      const d = distancePointToPlane(
        last.point,
        last.plane.centroid,
        last.plane.normal,
      );
      dispatch({ type: "patch-last-p2pl", distanceMm: d });
    }
  }, [state.completed.length, state.completed]);

  const onPickPlane = (plane: Plane) => {
    if (state.mode === "off") return;
    if (state.active.stage !== "have-plane") {
      dispatch({ type: "click-plane", plane });
      return;
    }
    if (state.mode !== "plane-to-plane" || prep.welded === null) return;
    const planeA = state.active.plane;
    const planeB = plane;
    const angleDeg = anglePlanes(planeA.normal, planeB.normal);
    let distanceMm: number;
    let pl2plKind: "parallel" | "closest";
    let approximate = false;
    if (angleDeg <= 5) {
      distanceMm = perpendicularPlaneDistance(
        planeA.centroid,
        planeA.normal,
        planeB.centroid,
      );
      pl2plKind = "parallel";
    } else {
      pl2plKind = "closest";
      const aVerts = uniqueClusterVerts(prep.welded, planeA.triangleIds);
      const bVerts = uniqueClusterVerts(prep.welded, planeB.triangleIds);
      if (aVerts.length * bVerts.length <= 1_000_000) {
        distanceMm = minVertexPairDistance(aVerts, bVerts);
      } else {
        distanceMm = planeA.centroid.distanceTo(planeB.centroid);
        approximate = true;
      }
    }
    dispatch({ type: "click-plane", plane });
    dispatch({
      type: "patch-last-pl2pl",
      distanceMm,
      angleDeg,
      pl2plKind,
      approximate,
    });
  };

  const onKey = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key.toLowerCase() === "d") {
      const ae = document.activeElement;
      const isTextInput =
        ae instanceof HTMLInputElement ||
        ae instanceof HTMLTextAreaElement ||
        (ae !== null && (ae as HTMLElement).getAttribute("contenteditable") === "true");
      if (isTextInput) return;
      e.preventDefault();
      e.stopPropagation();
      dispatch({ type: "set-mode", mode: state.mode === "diameter" ? "off" : "diameter" });
      return;
    }
    if (e.key !== "Escape") return;
    if (prep.loading) {
      e.preventDefault();
      e.stopPropagation();
      prep.cancel();
      dispatch({ type: "set-mode", mode: "off" });
      return;
    }
    if (state.active.stage !== "empty") {
      e.preventDefault();
      e.stopPropagation();
      dispatch({ type: "cancel-active" });
      return;
    }
    if (state.mode !== "off") {
      e.preventDefault();
      e.stopPropagation();
      dispatch({ type: "set-mode", mode: "off" });
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
      <div className="flex-1 relative">
        <StepBanner
          mode={state.mode}
          stage={state.active.stage}
          loading={prep.loading}
          error={prep.error}
          onDismissError={() => {
            prep.cancel();
            dispatch({ type: "set-mode", mode: "off" });
          }}
          position="inline"
        />
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
          welded={prep.welded}
          toleranceDeg={state.toleranceDeg}
          onPickPlane={onPickPlane}
        >
          {prep.welded !== null && state.active.stage === "have-plane" && (
            <ClusterOverlay
              welded={prep.welded}
              triangleIds={state.active.plane.triangleIds}
              color={paletteFor(allocateColorIndex(state.completed), "sel1")}
              opacity={0.45}
            />
          )}
          {state.completed.map((m) => {
              if (m.kind === "p2p") return null;
              if (m.kind === "diameter") {
                const sel1 = paletteFor(m.colorIndex, "sel1");
                const tangent = pickTangent(m.rim.axis);
                const labelText = m.weak
                  ? `#${displayIndex(m, state.completed)} ${t("viewer3d.measure.diameter.weak", { value: m.diameterMm.toFixed(1) })}`
                  : `#${displayIndex(m, state.completed)} ${t("viewer3d.measure.diameter.format", { value: m.diameterMm.toFixed(1) })}`;
                return (
                  <RimOverlay
                    key={m.id}
                    rim={m.rim}
                    color={sel1}
                    label={labelText}
                    labelTangent={tangent}
                  />
                );
              }
              if (prep.welded === null) return null;
              const planeA = m.kind === "p2pl" ? m.plane : m.planeA;
              const planeB = m.kind === "pl2pl" ? m.planeB : null;
              const colorA = paletteFor(m.colorIndex, "sel1");
              const colorB = paletteFor(m.colorIndex, "sel2");
              return (
                <group key={m.id}>
                  <ClusterOverlay
                    welded={prep.welded!}
                    triangleIds={planeA.triangleIds}
                    color={colorA}
                    opacity={0.3}
                  />
                  {planeB !== null && (
                    <ClusterOverlay
                      welded={prep.welded!}
                      triangleIds={planeB.triangleIds}
                      color={colorB}
                      opacity={0.3}
                    />
                  )}
                </group>
              );
            })}
        </Viewer3DCanvas>
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
              onDelete={(id) => dispatch({ type: "delete-measurement", id })}
            />
          </div>
        </details>
      </div>
    </div>
  );
}
