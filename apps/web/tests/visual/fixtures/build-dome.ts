// Run with: npx tsx tests/visual/fixtures/build-dome.ts
//
// Produces a binary STL of a tessellated hemisphere (8 rings × 32 segments,
// radius=50). Used as a deterministic mesh fixture for viewer3d plane-mode
// visual regression tests.
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const RINGS = 8;
const SEGMENTS = 32;
const RADIUS = 50;

const triangles: Array<[number[], number[], number[], number[]]> = [];
for (let r = 0; r < RINGS; r += 1) {
  const phi1 = (r / RINGS) * (Math.PI / 2);
  const phi2 = ((r + 1) / RINGS) * (Math.PI / 2);
  for (let s = 0; s < SEGMENTS; s += 1) {
    const t1 = (s / SEGMENTS) * Math.PI * 2;
    const t2 = ((s + 1) / SEGMENTS) * Math.PI * 2;
    const p = (phi: number, theta: number): number[] => [
      RADIUS * Math.sin(phi) * Math.cos(theta),
      RADIUS * Math.cos(phi),
      RADIUS * Math.sin(phi) * Math.sin(theta),
    ];
    const a = p(phi1, t1), b = p(phi2, t1), c = p(phi2, t2), d = p(phi1, t2);
    const n = [0, 1, 0];
    triangles.push([n, a, b, c]);
    triangles.push([n, a, c, d]);
  }
}

const buf = Buffer.alloc(80 + 4 + triangles.length * 50);
buf.writeUInt32LE(triangles.length, 80);
let off = 84;
for (const [n, a, b, c] of triangles) {
  buf.writeFloatLE(n[0]!, off); buf.writeFloatLE(n[1]!, off + 4); buf.writeFloatLE(n[2]!, off + 8);
  buf.writeFloatLE(a[0]!, off + 12); buf.writeFloatLE(a[1]!, off + 16); buf.writeFloatLE(a[2]!, off + 20);
  buf.writeFloatLE(b[0]!, off + 24); buf.writeFloatLE(b[1]!, off + 28); buf.writeFloatLE(b[2]!, off + 32);
  buf.writeFloatLE(c[0]!, off + 36); buf.writeFloatLE(c[1]!, off + 40); buf.writeFloatLE(c[2]!, off + 44);
  buf.writeUInt16LE(0, off + 48);
  off += 50;
}
writeFileSync(join(__dirname, "dome-tessellated.stl"), buf);
console.log("wrote dome-tessellated.stl", buf.length, "bytes");
