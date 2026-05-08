import { Canvas, useThree, type ThreeEvent } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { BufferGeometry, Mesh } from "three";
import {
  Box3,
  Color,
  MOUSE,
  MeshStandardMaterial,
  PerspectiveCamera,
  Vector3,
} from "three";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { framingDistance, viewPresets, type ViewPreset } from "./lib/camera";
import { allocateColorIndex, paletteFor } from "./lib/palette";
import { readMeshTokens } from "./lib/readMeshTokens";
import type { WeldedMesh } from "./lib/welder";
import { ClusterOverlay } from "./measure/ClusterOverlay";
import type { Rim } from "./measure/circleFit";
import { detectRim } from "./measure/detectRim";
import { fitPlane } from "./measure/fitting";
import { floodFill } from "./measure/floodFill";
import { MeasureOverlay } from "./measure/MeasureOverlay";
import type { MeasureAction } from "./measure/measureReducer";
import { RimOverlay } from "./measure/RimOverlay";
import type { MeasureMode, MeasureState, Plane } from "./types";

const FOV_DEG = 50;
const MARGIN = 1.15;

export type CanvasHandle = {
  takeScreenshot: () => Promise<Blob | null>;
};

type Props = {
  geometry: BufferGeometry;
  preset: ViewPreset;
  /** Increment to force a re-frame even when preset has not changed
   * (e.g. user dragged the camera around and clicks "Reset view"). */
  resetSignal: number;
  wireframe: boolean;
  measureMode: MeasureMode;
  state: MeasureState;
  dispatch: (action: MeasureAction) => void;
  /** Disable OrbitControls damping (saves CPU on huge meshes). */
  damping?: boolean;
  onCanvasReady?: (handle: CanvasHandle) => void;
  welded?: WeldedMesh | null;
  toleranceDeg?: number;
  onPickPlane?: (plane: Plane) => void;
  children?: ReactNode;
};

// Three.js OrbitControls mouse mapping — left rotates, right pans, middle
// dollies. Both rotate AND pan stay enabled simultaneously so the user
// never has to flip a mode toggle to switch between them.
const MOUSE_BUTTONS = {
  LEFT: MOUSE.ROTATE,
  MIDDLE: MOUSE.DOLLY,
  RIGHT: MOUSE.PAN,
};

function FrameAndControls({
  geometry,
  preset,
  resetSignal,
}: {
  geometry: BufferGeometry;
  preset: ViewPreset;
  resetSignal: number;
}) {
  const { camera, controls } = useThree() as unknown as {
    camera: PerspectiveCamera;
    controls: { target: Vector3; update: () => void } | null;
  };
  useEffect(() => {
    geometry.computeBoundingBox();
    const box = geometry.boundingBox ?? new Box3();
    const center = new Vector3();
    box.getCenter(center);
    const dist = framingDistance(box, { fovDeg: FOV_DEG, margin: MARGIN });
    const dir = viewPresets[preset].clone().multiplyScalar(dist);
    camera.position.copy(center).add(dir);
    camera.lookAt(center);
    if (controls !== null) {
      controls.target.copy(center);
      controls.update();
    }
    // resetSignal is read so a Reset click forces re-frame even when the
    // preset value hasn't changed (e.g. user is already on iso, drags the
    // camera around, then clicks Reset).
    void resetSignal;
  }, [geometry, preset, resetSignal, camera, controls]);
  return null;
}

export function Viewer3DCanvas({
  geometry,
  preset,
  resetSignal,
  wireframe,
  measureMode,
  state,
  dispatch,
  damping = true,
  onCanvasReady,
  welded = null,
  toleranceDeg = 1,
  onPickPlane,
  children,
}: Props) {
  const { t } = useTranslation();
  const tokens = useMemo(() => readMeshTokens(), []);
  const material = useMemo(
    () =>
      new MeshStandardMaterial({
        color: tokens.paint,
        metalness: 0,
        roughness: 0.8,
        wireframe,
      }),
    [tokens.paint, wireframe],
  );
  const meshRef = useRef<Mesh>(null);

  // Hover preview: show a faint cluster overlay under the cursor in plane
  // modes so the user sees which face flood-fill would grab BEFORE clicking.
  // Only active when the next click is a plane pick — for p2pl have-plane
  // (next click = point), suppress the preview to avoid misleading users.
  const [hoveredPlane, setHoveredPlane] = useState<Plane | null>(null);
  const hoveredTriRef = useRef<number | null>(null);
  const hoverRafRef = useRef<number | null>(null);

  // Diameter hover preview: show which rim would be captured if the user
  // clicks at the current cursor position.
  const [hoveredRim, setHoveredRim] = useState<Rim | null>(null);
  const lastNoRimToastRef = useRef<number>(0);
  const NO_RIM_TOAST_DEBOUNCE_MS = 2000;
  const expectsPlaneClick =
    state.mode === "plane-to-plane" ||
    (state.mode === "point-to-plane" && state.active.stage === "empty");

  const handleMeshClick = (e: ThreeEvent<MouseEvent>) => {
    if (state.mode === "off") return;
    e.stopPropagation();
    if (state.mode === "diameter") {
      if (welded === null || welded === undefined) return;
      if (typeof e.faceIndex !== "number") return;
      const weldedTri = welded.sourceToWelded[e.faceIndex];
      if (weldedTri === undefined || weldedTri === 0xffffffff) return;
      // Synchronous re-detect from click event (P1.3 in spec v2/v3).
      const rim = detectRim(weldedTri, e.point.clone(), welded, welded.graph);
      if (rim !== null) {
        dispatch({ type: "click-rim", rim });
        setHoveredRim(null);
        return;
      }
      // No rim. Toast — but suppress while prep is in flight (loading welded).
      // welded is non-null here (guard above), so isPrepping is always false
      // at this point; kept for documentation clarity.
      const isPrepping = welded === null;
      const now = performance.now();
      if (!isPrepping && now - lastNoRimToastRef.current > NO_RIM_TOAST_DEBOUNCE_MS) {
        toast(t("viewer3d.measure.diameter.no_rim"));
        lastNoRimToastRef.current = now;
      }
      return;
    }
    if (state.mode === "point-to-point") {
      dispatch({ type: "click-mesh", point: e.point.clone() });
      return;
    }
    if (
      state.mode === "point-to-plane" &&
      state.active.stage === "have-plane"
    ) {
      // Second click in p2pl = a point on geometry. Parent computes the
      // distance and dispatches the patch.
      dispatch({ type: "click-mesh", point: e.point.clone() });
      return;
    }
    // First plane click (p2pl empty stage) or any pl2pl click = plane pick.
    if (welded === null || welded === undefined) return;
    if (typeof e.faceIndex !== "number") return;
    const weldedTri = welded.sourceToWelded[e.faceIndex];
    if (weldedTri === undefined || weldedTri === 0xffffffff) return;
    const cluster = floodFill(welded, weldedTri, toleranceDeg);
    const plane = fitPlane(welded, [...cluster], weldedTri);
    onPickPlane?.(plane);
    // Clear hover preview after a click — the active overlay (0.45) takes
    // over visually; leaving the 0.20 preview around looks like a stale
    // ghost until the next pointer move.
    setHoveredPlane(null);
    hoveredTriRef.current = null;
    // measureMode is consumed via the state alias above; keep referenced so
    // the prop stays part of the public Canvas API.
    void measureMode;
  };

  const handleMeshPointerMove = (e: ThreeEvent<PointerEvent>) => {
    if (state.mode === "diameter") {
      if (welded === null || welded === undefined) return;
      if (typeof e.faceIndex !== "number") {
        setHoveredRim(null);
        return;
      }
      const weldedTri = welded.sourceToWelded[e.faceIndex];
      if (weldedTri === undefined || weldedTri === 0xffffffff) {
        setHoveredRim(null);
        return;
      }
      if (hoverRafRef.current !== null) cancelAnimationFrame(hoverRafRef.current);
      hoverRafRef.current = requestAnimationFrame(() => {
        hoverRafRef.current = null;
        const rim = detectRim(weldedTri, e.point.clone(), welded, welded.graph);
        setHoveredRim(rim);
      });
      return;
    }
    if (!expectsPlaneClick) return;
    if (welded === null || welded === undefined) return;
    if (typeof e.faceIndex !== "number") return;
    const weldedTri = welded.sourceToWelded[e.faceIndex];
    if (weldedTri === undefined || weldedTri === 0xffffffff) return;
    if (hoveredTriRef.current === weldedTri) return;
    hoveredTriRef.current = weldedTri;
    if (hoverRafRef.current !== null) cancelAnimationFrame(hoverRafRef.current);
    hoverRafRef.current = requestAnimationFrame(() => {
      hoverRafRef.current = null;
      const cluster = floodFill(welded, weldedTri, toleranceDeg);
      const plane = fitPlane(welded, [...cluster], weldedTri);
      setHoveredPlane(plane);
    });
  };

  const handleMeshPointerOut = () => {
    if (hoverRafRef.current !== null) {
      cancelAnimationFrame(hoverRafRef.current);
      hoverRafRef.current = null;
    }
    hoveredTriRef.current = null;
    setHoveredPlane(null);
  };

  // Drop the preview whenever the gate flips off — e.g. mode → off, or
  // p2pl moves into have-plane. Avoids a stale ghost cluster lingering.
  useEffect(() => {
    if (!expectsPlaneClick && hoveredPlane !== null) {
      hoveredTriRef.current = null;
      setHoveredPlane(null);
    }
  }, [expectsPlaneClick, hoveredPlane]);

  // Reset diameter hover preview when mode changes away from diameter or when
  // a new geometry is loaded (stale rim would reference the wrong mesh).
  useEffect(() => {
    if (state.mode !== "diameter") setHoveredRim(null);
  }, [state.mode]);
  useEffect(() => {
    setHoveredRim(null);
  }, [geometry]);

  const partial =
    state.active.stage === "have-point"
      ? {
          x: state.active.point.x,
          y: state.active.point.y,
          z: state.active.point.z,
        }
      : null;

  return (
    <Canvas
      camera={{ fov: FOV_DEG, near: 0.1, far: 10000, position: [0, 0, 100] }}
      gl={{ preserveDrawingBuffer: true, antialias: true }}
      onCreated={({ gl }) => {
        gl.setClearColor(new Color(0x000000), 0);
        if (onCanvasReady !== undefined) {
          onCanvasReady({
            takeScreenshot: () =>
              new Promise<Blob | null>((resolve) =>
                gl.domElement.toBlob((b) => resolve(b), "image/png"),
              ),
          });
        }
      }}
    >
      <ambientLight intensity={0.25} />
      <hemisphereLight args={[0xffffff, 0x404040, 0.35]} />
      <directionalLight intensity={1.0} position={[4, 8, 5]} />
      <directionalLight intensity={0.25} position={[-3, 2, -4]} />
      <mesh
        ref={meshRef}
        geometry={geometry}
        material={material}
        onClick={handleMeshClick}
        onPointerMove={handleMeshPointerMove}
        onPointerOut={handleMeshPointerOut}
      />
      <OrbitControls
        makeDefault
        enableDamping={damping}
        dampingFactor={damping ? 0.05 : 0}
        mouseButtons={MOUSE_BUTTONS}
      />
      <FrameAndControls
        geometry={geometry}
        preset={preset}
        resetSignal={resetSignal}
      />
      <MeasureOverlay
        measurements={state.completed}
        partialPoint={partial}
        showAssumed
      />
      {children}
      {welded !== null && hoveredPlane !== null && expectsPlaneClick && (
        <ClusterOverlay
          welded={welded}
          triangleIds={hoveredPlane.triangleIds}
          color={paletteFor(allocateColorIndex(state.completed), "sel1")}
          opacity={0.2}
        />
      )}
      {state.mode === "diameter" && hoveredRim !== null && (
        <RimOverlay
          rim={hoveredRim}
          color={paletteFor(allocateColorIndex(state.completed), "sel1")}
        />
      )}
    </Canvas>
  );
}
