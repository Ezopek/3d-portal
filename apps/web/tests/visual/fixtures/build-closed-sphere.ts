// Build a watertight UV sphere as raw welded positions + indices.
// Uses three.js SphereGeometry then welds duplicate vertices.
import { SphereGeometry } from "three";

export type RawMesh = {
  positions: Float32Array;
  indices: Uint32Array;
};

/** Closed UV sphere with `segments` longitude divisions and `rings` latitude rings.
 *  Returns triangulated welded positions + indices. */
export function buildClosedSphere(radius: number, segments: number, rings: number): RawMesh {
  const geom = new SphereGeometry(radius, segments, rings);
  // SphereGeometry already produces an indexed mesh.
  const positions = (geom.getAttribute("position").array as Float32Array).slice();
  const indices = new Uint32Array((geom.getIndex()!.array as ArrayLike<number>));
  geom.dispose();
  return { positions, indices };
}
