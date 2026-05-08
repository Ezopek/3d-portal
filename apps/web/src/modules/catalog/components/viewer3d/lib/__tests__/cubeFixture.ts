/**
 * Shared test fixture: an axis-aligned unit cube as a triangle soup.
 * 8 vertices, 6 faces, 12 triangles, all 90° dihedral edges (sharp).
 */
export function buildAxisAlignedCube(): { positions: Float32Array } {
  const v = [
    [-1, -1, -1], [+1, -1, -1], [+1, +1, -1], [-1, +1, -1],
    [-1, -1, +1], [+1, -1, +1], [+1, +1, +1], [-1, +1, +1],
  ];
  const tri = (a: number, b: number, c: number) => [...v[a]!, ...v[b]!, ...v[c]!];
  return {
    positions: new Float32Array([
      ...tri(0, 1, 2), ...tri(0, 2, 3),
      ...tri(4, 6, 5), ...tri(4, 7, 6),
      ...tri(0, 3, 7), ...tri(0, 7, 4),
      ...tri(1, 5, 6), ...tri(1, 6, 2),
      ...tri(0, 4, 5), ...tri(0, 5, 1),
      ...tri(3, 2, 6), ...tri(3, 6, 7),
    ]),
  };
}
