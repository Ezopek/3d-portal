// Run with: npx tsx tests/visual/fixtures/build-cube.ts
//
// Produces a 12-triangle binary STL of a 10mm cube centred at the origin.
// Used as a deterministic mock geometry for viewer3d Playwright snapshots.
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const c = 5;
const v: [number, number, number][] = [
  [-c, -c, -c], [c, -c, -c], [c, c, -c], [-c, c, -c],
  [-c, -c, c], [c, -c, c], [c, c, c], [-c, c, c],
];
const faces: [number, number, number][] = [
  [0, 1, 2], [0, 2, 3],
  [4, 6, 5], [4, 7, 6],
  [0, 4, 5], [0, 5, 1],
  [1, 5, 6], [1, 6, 2],
  [2, 6, 7], [2, 7, 3],
  [3, 7, 4], [3, 4, 0],
];

const triCount = faces.length;
const buf = Buffer.alloc(80 + 4 + triCount * 50);
buf.writeUInt32LE(triCount, 80);
let off = 84;

for (const [a, b, cc] of faces) {
  // Normal — left zero; STLLoader will compute per-face normals if missing.
  for (let i = 0; i < 3; i++) {
    buf.writeFloatLE(0, off + i * 4);
  }
  off += 12;
  for (const idx of [a, b, cc]) {
    const point = v[idx]!;
    buf.writeFloatLE(point[0], off); off += 4;
    buf.writeFloatLE(point[1], off); off += 4;
    buf.writeFloatLE(point[2], off); off += 4;
  }
  buf.writeUInt16LE(0, off); off += 2;
}

writeFileSync(join(__dirname, "cube.stl"), buf);
console.log(`Wrote cube.stl (${buf.byteLength} bytes, ${triCount} triangles)`);
