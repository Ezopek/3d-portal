import { useEffect, useRef, useState } from "react";
import { Box3, type BufferGeometry, Vector3 } from "three";

import { weld, WELD_SYNC_VERTEX_THRESHOLD, type WeldedMesh } from "../lib/welder";
import { weldCache } from "../lib/weldCache";

type Status =
  | { state: "idle" }
  | { state: "loading"; jobId: number }
  | { state: "ready"; welded: WeldedMesh }
  | { state: "error"; message: string };

export type UsePlanePrepResult = {
  ready: boolean;
  loading: boolean;
  error: string | null;
  welded: WeldedMesh | null;
  cancel: () => void;
};

let nextJobId = 1;

function bboxDiagonal(geometry: BufferGeometry): number {
  geometry.computeBoundingBox();
  const box = geometry.boundingBox ?? new Box3();
  const size = new Vector3();
  box.getSize(size);
  return Math.sqrt(size.x * size.x + size.y * size.y + size.z * size.z);
}

export function usePlanePrep(
  geometry: BufferGeometry | null,
  cacheKey: string,
  needsWelding: boolean,
): UsePlanePrepResult {
  const [status, setStatus] = useState<Status>({ state: "idle" });
  const workerRef = useRef<Worker | null>(null);
  const acquiredKey = useRef<string | null>(null);

  useEffect(() => {
    if (!needsWelding || geometry === null || cacheKey === "") {
      setStatus({ state: "idle" });
      return;
    }
    const cached = weldCache.acquire(cacheKey);
    if (cached !== undefined) {
      acquiredKey.current = cacheKey;
      setStatus({ state: "ready", welded: cached });
      return () => {
        if (acquiredKey.current !== null) {
          weldCache.release(acquiredKey.current);
          acquiredKey.current = null;
        }
      };
    }

    const positions = (geometry.getAttribute("position").array as Float32Array).slice();
    const diag = bboxDiagonal(geometry);

    if (positions.length / 3 < WELD_SYNC_VERTEX_THRESHOLD) {
      try {
        const welded = weld(positions, diag);
        weldCache.put(cacheKey, welded);
        const acq = weldCache.acquire(cacheKey)!;
        acquiredKey.current = cacheKey;
        setStatus({ state: "ready", welded: acq });
      } catch (err) {
        setStatus({
          state: "error",
          message: err instanceof Error ? err.message : "weld failed",
        });
      }
      return () => {
        if (acquiredKey.current !== null) {
          weldCache.release(acquiredKey.current);
          acquiredKey.current = null;
        }
      };
    }

    const jobId = nextJobId++;
    setStatus({ state: "loading", jobId });
    const worker = new Worker(
      new URL("../lib/weldMesh.worker.ts", import.meta.url),
      { type: "module" },
    );
    workerRef.current = worker;
    worker.onmessage = (event: MessageEvent) => {
      const data = event.data as
        | {
            jobId: number;
            ok: true;
            positions: ArrayBuffer;
            indices: ArrayBuffer;
            adjacency: ArrayBuffer;
            sourceToWelded: ArrayBuffer;
            weldedToSourceStart: ArrayBuffer;
            weldedToSource: ArrayBuffer;
            graphEdges: ArrayBuffer;
            graphTriangles: ArrayBuffer;
            graphDihedralAngles: ArrayBuffer;
            graphVertexEdges: ArrayBuffer;
            graphVertexEdgesStart: ArrayBuffer;
            graphTriangleEdgeIds: ArrayBuffer;
          }
        | { jobId: number; ok: false; error: string };
      if (data.jobId !== jobId) return;
      worker.terminate();
      workerRef.current = null;
      if (data.ok === false) {
        setStatus({ state: "error", message: data.error });
        return;
      }
      const welded: WeldedMesh = {
        positions: new Float32Array(data.positions),
        indices: new Uint32Array(data.indices),
        adjacency: new Uint32Array(data.adjacency),
        sourceToWelded: new Uint32Array(data.sourceToWelded),
        weldedToSourceStart: new Uint32Array(data.weldedToSourceStart),
        weldedToSource: new Uint32Array(data.weldedToSource),
        graph: {
          edges: new Uint32Array(data.graphEdges),
          triangles: new Uint32Array(data.graphTriangles),
          dihedralAngles: new Float32Array(data.graphDihedralAngles),
          vertexEdges: new Uint32Array(data.graphVertexEdges),
          vertexEdgesStart: new Uint32Array(data.graphVertexEdgesStart),
          triangleEdgeIds: new Uint32Array(data.graphTriangleEdgeIds),
        },
      };
      weldCache.put(cacheKey, welded);
      const acq = weldCache.acquire(cacheKey)!;
      acquiredKey.current = cacheKey;
      setStatus({ state: "ready", welded: acq });
    };
    worker.onerror = (e) => {
      worker.terminate();
      workerRef.current = null;
      setStatus({ state: "error", message: e.message });
    };
    worker.postMessage(
      { id: 0, jobId, positions: positions.buffer, bboxDiagonal: diag },
      [positions.buffer],
    );

    return () => {
      if (workerRef.current !== null) {
        workerRef.current.terminate();
        workerRef.current = null;
      }
      if (acquiredKey.current !== null) {
        weldCache.release(acquiredKey.current);
        acquiredKey.current = null;
      }
    };
  }, [geometry, cacheKey, needsWelding]);

  const cancel = () => {
    if (workerRef.current !== null) {
      workerRef.current.terminate();
      workerRef.current = null;
    }
    if (acquiredKey.current !== null) {
      weldCache.release(acquiredKey.current);
      acquiredKey.current = null;
    }
    setStatus({ state: "idle" });
  };

  return {
    ready: status.state === "ready",
    loading: status.state === "loading",
    error: status.state === "error" ? status.message : null,
    welded: status.state === "ready" ? status.welded : null,
    cancel,
  };
}
