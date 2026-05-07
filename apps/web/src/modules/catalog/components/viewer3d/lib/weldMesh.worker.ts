import { weld } from "./welder";

type Request = {
  id: number;
  jobId: number;
  positions: ArrayBuffer;
  bboxDiagonal: number;
};

type Response =
  | {
      id: number;
      jobId: number;
      ok: true;
      positions: ArrayBuffer;
      indices: ArrayBuffer;
      adjacency: ArrayBuffer;
      sourceToWelded: ArrayBuffer;
      weldedToSourceStart: ArrayBuffer;
      weldedToSource: ArrayBuffer;
    }
  | { id: number; jobId: number; ok: false; error: string };

self.onmessage = (event: MessageEvent<Request>) => {
  const { id, jobId, positions, bboxDiagonal } = event.data;
  try {
    const welded = weld(new Float32Array(positions), bboxDiagonal);
    const positionsBuf = welded.positions.buffer as ArrayBuffer;
    const indicesBuf = welded.indices.buffer as ArrayBuffer;
    const adjacencyBuf = welded.adjacency.buffer as ArrayBuffer;
    const sourceToWeldedBuf = welded.sourceToWelded.buffer as ArrayBuffer;
    const weldedToSourceStartBuf = welded.weldedToSourceStart.buffer as ArrayBuffer;
    const weldedToSourceBuf = welded.weldedToSource.buffer as ArrayBuffer;
    const message: Response = {
      id,
      jobId,
      ok: true,
      positions: positionsBuf,
      indices: indicesBuf,
      adjacency: adjacencyBuf,
      sourceToWelded: sourceToWeldedBuf,
      weldedToSourceStart: weldedToSourceStartBuf,
      weldedToSource: weldedToSourceBuf,
    };
    (self as unknown as Worker).postMessage(message, [
      positionsBuf,
      indicesBuf,
      adjacencyBuf,
      sourceToWeldedBuf,
      weldedToSourceStartBuf,
      weldedToSourceBuf,
    ]);
  } catch (err) {
    const message: Response = {
      id,
      jobId,
      ok: false,
      error: err instanceof Error ? err.message : "weld failed",
    };
    (self as unknown as Worker).postMessage(message);
  }
};
