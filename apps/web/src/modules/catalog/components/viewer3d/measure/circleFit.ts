import { Vector3 } from "three";

export type Rim = {
  center: Vector3;
  axis: Vector3;
  radius: number;
  loopPoints: Vector3[];
  weak: boolean;
};

export const MIN_LOOP_VERTICES = 6;
export const WEAK_LOOP_VERTICES = 12;
export const PLANARITY_RATIO_MAX = 0.05;
export const RESIDUUM_FLOOR_MM = 0.1;
export const RESIDUUM_RATIO = 0.05;
export const SAGITTA_MULTIPLIER = 3.0;
export const MAX_ANGULAR_GAP_RATIO = 2.0;

export function fitCircle(
  loopVerts: number[],
  positions: Float32Array,
): Rim | null {
  if (loopVerts.length < MIN_LOOP_VERTICES) return null;

  // Snapshot loop points (will be stored in Rim.loopPoints).
  const loopPoints: Vector3[] = loopVerts.map((vi) => {
    return new Vector3(positions[vi * 3]!, positions[vi * 3 + 1]!, positions[vi * 3 + 2]!);
  });

  // Plane fit (PCA).
  const centroid = new Vector3();
  for (const p of loopPoints) centroid.add(p);
  centroid.multiplyScalar(1 / loopPoints.length);

  // Covariance matrix.
  let cxx = 0, cxy = 0, cxz = 0, cyy = 0, cyz = 0, czz = 0;
  for (const p of loopPoints) {
    const dx = p.x - centroid.x;
    const dy = p.y - centroid.y;
    const dz = p.z - centroid.z;
    cxx += dx * dx; cxy += dx * dy; cxz += dx * dz;
    cyy += dy * dy; cyz += dy * dz; czz += dz * dz;
  }

  const eig = jacobiEigen3([
    [cxx, cxy, cxz],
    [cxy, cyy, cyz],
    [cxz, cyz, czz],
  ]);
  const sortedIdx = [0, 1, 2].sort((a, b) => eig.values[a]! - eig.values[b]!);
  const lambdaMin = eig.values[sortedIdx[0]!]!;
  const lambdaAvg = (eig.values[0]! + eig.values[1]! + eig.values[2]!) / 3;
  if (lambdaAvg === 0) return null;
  if (lambdaMin / lambdaAvg > PLANARITY_RATIO_MAX) return null;
  const axis = new Vector3(...(eig.vectors[sortedIdx[0]!] as [number, number, number])).normalize();
  const basisU = new Vector3(...(eig.vectors[sortedIdx[1]!] as [number, number, number])).normalize();
  const basisV = new Vector3(...(eig.vectors[sortedIdx[2]!] as [number, number, number])).normalize();

  // Project to 2D.
  const points2D = loopPoints.map((p) => {
    const d = p.clone().sub(centroid);
    return [d.dot(basisU), d.dot(basisV)] as [number, number];
  });

  // Algebraic circle fit (Coope / Pratt linearization).
  // Solve [u, v, 1] @ [a, b, c]ᵀ = u² + v² for (a, b, c).
  const fit = solveCircle2D(points2D);
  if (fit === null) return null;
  const { cx, cy, r } = fit;

  // Vertex residuum.
  let vertexRes = 0;
  for (const [u, v] of points2D) {
    const d = Math.abs(Math.hypot(u - cx, v - cy) - r);
    if (d > vertexRes) vertexRes = d;
  }
  const vertexThresh = Math.max(RESIDUUM_FLOOR_MM, RESIDUUM_RATIO * r);
  if (vertexRes > vertexThresh) return null;
  const weakV = vertexRes > 0.5 * vertexThresh;

  // Midpoint sagitta check.
  let midpointRes = 0;
  for (let i = 0; i < points2D.length; i++) {
    const [u0, v0] = points2D[i]!;
    const [u1, v1] = points2D[(i + 1) % points2D.length]!;
    const mu = (u0 + u1) / 2;
    const mv = (v0 + v1) / 2;
    const d = Math.abs(Math.hypot(mu - cx, mv - cy) - r);
    if (d > midpointRes) midpointRes = d;
  }
  const midpointThresh = SAGITTA_MULTIPLIER * vertexThresh;
  if (midpointRes > midpointThresh) return null;
  const weakM = midpointRes > 0.5 * midpointThresh;

  // Angular spacing.
  const angles = points2D
    .map(([u, v]) => Math.atan2(v - cy, u - cx))
    .sort((a, b) => a - b);
  const gaps: number[] = [];
  for (let i = 0; i < angles.length; i++) {
    let g = angles[(i + 1) % angles.length]! - angles[i]!;
    if (g < 0) g += 2 * Math.PI;
    gaps.push(g);
  }
  const meanGap = (2 * Math.PI) / angles.length;
  const maxGap = Math.max(...gaps);
  if (maxGap / meanGap > MAX_ANGULAR_GAP_RATIO) return null;
  const weakA = maxGap / meanGap > 1.5;

  const weakN = loopPoints.length < WEAK_LOOP_VERTICES;
  const weak = weakV || weakM || weakA || weakN;

  // Backproject 2D center → 3D.
  const center3D = centroid.clone().add(basisU.clone().multiplyScalar(cx)).add(basisV.clone().multiplyScalar(cy));

  return {
    center: center3D,
    axis,
    radius: r,
    loopPoints,
    weak,
  };
}

/** Solve a 2D circle fit: minimize sum (xi² + yi² - 2cx·xi - 2cy·yi - (r² - cx² - cy²))² → linear system. */
function solveCircle2D(points: ReadonlyArray<readonly [number, number]>): { cx: number; cy: number; r: number } | null {
  // System: [2u 2v 1] @ [cx cy d]ᵀ = u² + v², where d = r² - cx² - cy².
  // Use normal equations Aᵀ A x = Aᵀ b.
  let s11 = 0, s12 = 0, s13 = 0, s22 = 0, s23 = 0, s33 = 0;
  let r1 = 0, r2 = 0, r3 = 0;
  for (const [u, v] of points) {
    const u2 = u * u + v * v;
    const a1 = 2 * u, a2 = 2 * v, a3 = 1;
    s11 += a1 * a1; s12 += a1 * a2; s13 += a1 * a3;
    s22 += a2 * a2; s23 += a2 * a3;
    s33 += a3 * a3;
    r1 += a1 * u2; r2 += a2 * u2; r3 += a3 * u2;
  }
  // Solve 3x3 symmetric system.
  const det =
    s11 * (s22 * s33 - s23 * s23) -
    s12 * (s12 * s33 - s23 * s13) +
    s13 * (s12 * s23 - s22 * s13);
  if (Math.abs(det) < 1e-12) return null;
  const cx =
    (r1 * (s22 * s33 - s23 * s23) - s12 * (r2 * s33 - s23 * r3) + s13 * (r2 * s23 - s22 * r3)) /
    det;
  const cy =
    (s11 * (r2 * s33 - s23 * r3) - r1 * (s12 * s33 - s23 * s13) + s13 * (s12 * r3 - r2 * s13)) /
    det;
  const d =
    (s11 * (s22 * r3 - r2 * s23) - s12 * (s12 * r3 - r2 * s13) + r1 * (s12 * s23 - s22 * s13)) /
    det;
  const rSq = d + cx * cx + cy * cy;
  if (rSq <= 0) return null;
  return { cx, cy, r: Math.sqrt(rSq) };
}

/** 3x3 symmetric eigen-decomposition via cyclic Jacobi rotations. */
function jacobiEigen3(m: number[][]): { values: number[]; vectors: number[][] } {
  const a: number[][] = m.map((row) => row.slice());
  const v: number[][] = [
    [1, 0, 0],
    [0, 1, 0],
    [0, 0, 1],
  ];
  for (let iter = 0; iter < 50; iter++) {
    // Find largest off-diagonal.
    let p = 0, q = 1;
    let max = Math.abs(a[0]![1]!);
    if (Math.abs(a[0]![2]!) > max) { p = 0; q = 2; max = Math.abs(a[0]![2]!); }
    if (Math.abs(a[1]![2]!) > max) { p = 1; q = 2; max = Math.abs(a[1]![2]!); }
    if (max < 1e-12) break;
    const theta = (a[q]![q]! - a[p]![p]!) / (2 * a[p]![q]!);
    const t = theta >= 0
      ? 1 / (theta + Math.sqrt(1 + theta * theta))
      : 1 / (theta - Math.sqrt(1 + theta * theta));
    const c = 1 / Math.sqrt(1 + t * t);
    const s = t * c;
    const aPP = a[p]![p]!;
    const aQQ = a[q]![q]!;
    const aPQ = a[p]![q]!;
    a[p]![p] = aPP - t * aPQ;
    a[q]![q] = aQQ + t * aPQ;
    a[p]![q] = 0;
    a[q]![p] = 0;
    for (let r = 0; r < 3; r++) {
      if (r !== p && r !== q) {
        const aPR = a[p]![r]!;
        const aQR = a[q]![r]!;
        a[p]![r] = c * aPR - s * aQR;
        a[r]![p] = a[p]![r]!;
        a[q]![r] = s * aPR + c * aQR;
        a[r]![q] = a[q]![r]!;
      }
      const vRP = v[r]![p]!;
      const vRQ = v[r]![q]!;
      v[r]![p] = c * vRP - s * vRQ;
      v[r]![q] = s * vRP + c * vRQ;
    }
  }
  return {
    values: [a[0]![0]!, a[1]![1]!, a[2]![2]!],
    vectors: [
      [v[0]![0]!, v[1]![0]!, v[2]![0]!],
      [v[0]![1]!, v[1]![1]!, v[2]![1]!],
      [v[0]![2]!, v[1]![2]!, v[2]![2]!],
    ],
  };
}
