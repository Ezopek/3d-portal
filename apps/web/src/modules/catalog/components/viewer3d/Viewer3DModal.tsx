import { useEffect, useMemo, useReducer, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/ui/dialog";

import { Viewer3DCanvas, type CanvasHandle } from "./Viewer3DCanvas";
import { FileSelector } from "./controls/FileSelector";
import { MeasureSummary } from "./controls/MeasureSummary";
import { StepBanner } from "./controls/StepBanner";
import { ViewToolbar } from "./controls/ViewToolbar";
import { useFileIndex } from "./hooks/useFileIndex";
import { usePerfGuard } from "./hooks/usePerfGuard";
import { usePlanePrep } from "./hooks/usePlanePrep";
import { useStlGeometry } from "./hooks/useStlGeometry";
import type { ViewPreset } from "./lib/camera";
import { readMeshTokens } from "./lib/readMeshTokens";
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
import {
  initialMeasureState,
  measureReducer,
  type MeasureAction,
} from "./measure/measureReducer";
import type { Plane, Viewer3DProps } from "./types";

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

  const needsWelding =
    state.mode === "point-to-plane" || state.mode === "plane-to-plane";
  const cacheKey = file !== undefined ? `${file.modelId}/${file.id}` : "";
  const prep = usePlanePrep(geometry, cacheKey, needsWelding);
  const tokens = useMemo(() => readMeshTokens(), []);

  // File switch: clear measurements; preserve mode + tolerance.
  const lastFileId = useRef(activeId);
  useEffect(() => {
    if (lastFileId.current !== activeId) {
      lastFileId.current = activeId;
      dispatch({ type: "clear" });
    }
  }, [activeId]);

  // Live tolerance update — re-flood + re-fit on the seed when tolerance
  // changes while a plane is active.
  useEffect(() => {
    if (state.active.stage !== "have-plane" || prep.welded === null) return;
    const seed = state.active.plane.seedTriangleId;
    const cluster = floodFill(prep.welded, seed, state.toleranceDeg);
    const plane = fitPlane(prep.welded, [...cluster], seed);
    dispatch({ type: "replace-active-plane", plane });
    // state.active is intentionally read via .stage / .plane.seedTriangleId
    // rather than depended on — re-running on every active mutation would
    // create a feedback loop with replace-active-plane.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.toleranceDeg, prep.welded]);

  // p2pl second-click completion: when a new p2pl entry lands with a
  // placeholder distance, compute it from the snapshot and patch.
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
    // Esc cancel ladder — innermost first.
    if (e.key === "Escape") {
      // 1. Welding in flight → cancel weld, drop out of plane mode.
      if (prep.loading) {
        e.preventDefault();
        e.stopPropagation();
        prep.cancel();
        dispatch({ type: "set-mode", mode: "off" });
        return;
      }
      // 2. An in-progress measurement → cancel just the active step.
      if (state.active.stage !== "empty") {
        e.preventDefault();
        e.stopPropagation();
        dispatch({ type: "cancel-active" });
        return;
      }
      // 3. Measure mode is on → leave measure mode (still keep modal open).
      if (state.mode !== "off") {
        e.preventDefault();
        e.stopPropagation();
        dispatch({ type: "set-mode", mode: "off" });
        return;
      }
      // 4. else fall through to Dialog (close modal).
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
              <StepBanner
                mode={state.mode}
                stage={state.active.stage}
                loading={prep.loading}
                error={prep.error}
                onDismissError={() => {
                  prep.cancel();
                  dispatch({ type: "set-mode", mode: "off" });
                }}
                position="modal"
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
                {prep.welded !== null &&
                  state.active.stage === "have-plane" && (
                    <ClusterOverlay
                      welded={prep.welded}
                      triangleIds={state.active.plane.triangleIds}
                      color={tokens.cluster}
                      opacity={0.45}
                    />
                  )}
                {prep.welded !== null &&
                  state.completed.map((m) => {
                    if (m.kind === "p2p") return null;
                    const planeA = m.kind === "p2pl" ? m.plane : m.planeA;
                    const planeB = m.kind === "pl2pl" ? m.planeB : null;
                    return (
                      <group key={m.id}>
                        <ClusterOverlay
                          welded={prep.welded!}
                          triangleIds={planeA.triangleIds}
                          color={tokens.cluster}
                          opacity={0.3}
                        />
                        {planeB !== null && (
                          <ClusterOverlay
                            welded={prep.welded!}
                            triangleIds={planeB.triangleIds}
                            color={tokens.cluster}
                            opacity={0.3}
                          />
                        )}
                      </group>
                    );
                  })}
              </Viewer3DCanvas>
            </>
          )}
          <div className="absolute bottom-3 left-1/2 z-10 -translate-x-1/2">
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
          </div>
          <div className="pointer-events-none absolute left-3 top-3 z-10 max-h-[40vh] max-w-[280px] overflow-y-auto">
            <MeasureSummary
              measurements={state.completed}
              onClear={() => dispatch({ type: "clear" })}
              onDelete={(id) => dispatch({ type: "delete-measurement", id })}
            />
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
