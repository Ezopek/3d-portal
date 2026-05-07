// Run with: npx tsx tests/visual/fixtures/build-cylinder.ts
//
// Produces a binary STL of a smooth cylinder (256 side segments) with radius=10,
// height=20, centred at the origin. Used as a deterministic mesh fixture for
// viewer3d plane-mode visual regression tests.
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const SEGMENTS = 256;
const RADIUS = 10;
const HEIGHT = 20;

const triangles: Array<[number[], number[], number[], number[]]> = [];
const top = HEIGHT / 2;
const bot = -HEIGHT / 2;

// Side strip
for (let i = 0; i < SEGMENTS; i += 1) {
  const a1 = (i / SEGMENTS) * Math.PI * 2;
  const a2 = ((i + 1) / SEGMENTS) * Math.PI * 2;
  const x1 = RADIUS * Math.cos(a1), z1 = RADIUS * Math.sin(a1);
  const x2 = RADIUS * Math.cos(a2), z2 = RADIUS * Math.sin(a2);
  const n = [Math.cos((a1 + a2) / 2), 0, Math.sin((a1 + a2) / 2)];
  triangles.push([n, [x1, bot, z1], [x2, bot, z2], [x2, top, z2]]);
  triangles.push([n, [x1, bot, z1], [x2, top, z2], [x1, top, z1]]);
}
// Top + bottom caps
for (let i = 0; i < SEGMENTS; i += 1) {
  const a1 = (i / SEGMENTS) * Math.PI * 2;
  const a2 = ((i + 1) / SEGMENTS) * Math.PI * 2;
  const x1 = RADIUS * Math.cos(a1), z1 = RADIUS * Math.sin(a1);
  const x2 = RADIUS * Math.cos(a2), z2 = RADIUS * Math.sin(a2);
  triangles.push([[0, 1, 0], [0, top, 0], [x1, top, z1], [x2, top, z2]]);
  triangles.push([[0, -1, 0], [0, bot, 0], [x2, bot, z2], [x1, bot, z1]]);
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
writeFileSync(join(__dirname, "cylinder-256seg.stl"), buf);
console.log("wrote cylinder-256seg.stl", buf.length, "bytes");
