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
      graphEdges: ArrayBuffer;
      graphTriangles: ArrayBuffer;
      graphDihedralAngles: ArrayBuffer;
      graphVertexEdges: ArrayBuffer;
      graphVertexEdgesStart: ArrayBuffer;
      graphTriangleEdgeIds: ArrayBuffer;
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
    const graphEdgesBuf = welded.graph.edges.buffer as ArrayBuffer;
    const graphTrianglesBuf = welded.graph.triangles.buffer as ArrayBuffer;
    const graphDihedralAnglesBuf = welded.graph.dihedralAngles.buffer as ArrayBuffer;
    const graphVertexEdgesBuf = welded.graph.vertexEdges.buffer as ArrayBuffer;
    const graphVertexEdgesStartBuf = welded.graph.vertexEdgesStart.buffer as ArrayBuffer;
    const graphTriangleEdgeIdsBuf = welded.graph.triangleEdgeIds.buffer as ArrayBuffer;
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
      graphEdges: graphEdgesBuf,
      graphTriangles: graphTrianglesBuf,
      graphDihedralAngles: graphDihedralAnglesBuf,
      graphVertexEdges: graphVertexEdgesBuf,
      graphVertexEdgesStart: graphVertexEdgesStartBuf,
      graphTriangleEdgeIds: graphTriangleEdgeIdsBuf,
    };
    (self as unknown as Worker).postMessage(message, [
      positionsBuf,
      indicesBuf,
      adjacencyBuf,
      sourceToWeldedBuf,
      weldedToSourceStartBuf,
      weldedToSourceBuf,
      graphEdgesBuf,
      graphTrianglesBuf,
      graphDihedralAnglesBuf,
      graphVertexEdgesBuf,
      graphVertexEdgesStartBuf,
      graphTriangleEdgeIdsBuf,
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
