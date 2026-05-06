import { Canvas, useThree, type ThreeEvent } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { useEffect, useMemo, useRef } from "react";
import type { BufferGeometry, Mesh } from "three";
import {
  Box3,
  Color,
  MeshStandardMaterial,
  PerspectiveCamera,
  Vector3,
} from "three";

import { framingDistance, viewPresets, type ViewPreset } from "./lib/camera";
import { readMeshTokens } from "./lib/readMeshTokens";
import { MeasureOverlay } from "./measure/MeasureOverlay";
import type { MeasureAction } from "./measure/measureReducer";
import type { MeasureMode, MeasureState } from "./types";

const FOV_DEG = 50;
const MARGIN = 1.15;

export type CanvasHandle = {
  takeScreenshot: () => Promise<Blob | null>;
};

type Props = {
  geometry: BufferGeometry;
  preset: ViewPreset;
  wireframe: boolean;
  measureMode: MeasureMode;
  state: MeasureState;
  dispatch: (action: MeasureAction) => void;
  /** Disable OrbitControls damping (saves CPU on huge meshes). */
  damping?: boolean;
  onCanvasReady?: (handle: CanvasHandle) => void;
};

function FrameAndControls({
  geometry,
  preset,
}: {
  geometry: BufferGeometry;
  preset: ViewPreset;
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
  }, [geometry, preset, camera, controls]);
  return null;
}

export function Viewer3DCanvas({
  geometry,
  preset,
  wireframe,
  measureMode,
  state,
  dispatch,
  damping = true,
  onCanvasReady,
}: Props) {
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

  const handleMeshClick = (e: ThreeEvent<MouseEvent>) => {
    if (measureMode !== "point-to-point") return;
    e.stopPropagation();
    dispatch({ type: "click-mesh", point: e.point.clone() });
  };

  const partial =
    state.active.points.length === 1 && state.active.points[0] !== undefined
      ? {
          x: state.active.points[0].x,
          y: state.active.points[0].y,
          z: state.active.points[0].z,
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
      <ambientLight intensity={0.4} />
      <directionalLight intensity={0.8} position={[1, 1, 1]} />
      <mesh
        ref={meshRef}
        geometry={geometry}
        material={material}
        onClick={handleMeshClick}
      />
      <OrbitControls
        makeDefault
        enableDamping={damping}
        dampingFactor={damping ? 0.05 : 0}
      />
      <FrameAndControls geometry={geometry} preset={preset} />
      <MeasureOverlay
        measurements={state.completed}
        partialPoint={partial}
        showAssumed
      />
    </Canvas>
  );
}
