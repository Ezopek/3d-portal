import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";

type ParseRequest = { id: number; buffer: ArrayBuffer };
type ParseResponse =
  | {
      id: number;
      ok: true;
      positions: ArrayBuffer;
      normals: ArrayBuffer | null;
      vertexCount: number;
    }
  | { id: number; ok: false; error: string };

const loader = new STLLoader();

self.onmessage = (event: MessageEvent<ParseRequest>) => {
  const { id, buffer } = event.data;
  try {
    const geom = loader.parse(buffer);
    geom.computeVertexNormals();
    const pos = geom.getAttribute("position");
    const norm = geom.getAttribute("normal");
    const positions = (pos.array as Float32Array).slice().buffer;
    const normals =
      norm === undefined ? null : (norm.array as Float32Array).slice().buffer;
    const message: ParseResponse = {
      id,
      ok: true,
      positions,
      normals,
      vertexCount: pos.count,
    };
    const transfer: ArrayBuffer[] = [positions];
    if (normals !== null) transfer.push(normals);
    (self as unknown as Worker).postMessage(message, transfer);
  } catch (err) {
    const message: ParseResponse = {
      id,
      ok: false,
      error: err instanceof Error ? err.message : "parse failed",
    };
    (self as unknown as Worker).postMessage(message);
  }
};
