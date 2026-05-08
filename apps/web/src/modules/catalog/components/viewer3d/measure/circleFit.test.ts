import { describe, expect, it } from "vitest";
import { fitCircle, MIN_LOOP_VERTICES } from "./circleFit";

function regularPolygonOnCircle(N: number, r: number, axis: "z" | "x" = "z"): { positions: Float32Array; loop: number[] } {
  const pos: number[] = [];
  for (let i = 0; i < N; i++) {
    const t = (2 * Math.PI * i) / N;
    if (axis === "z") pos.push(r * Math.cos(t), r * Math.sin(t), 0);
    else pos.push(0, r * Math.cos(t), r * Math.sin(t));
  }
  const positions = new Float32Array(pos);
  const loop = Array.from({ length: N }, (_, i) => i);
  return { positions, loop };
}

describe("fitCircle — circles", () => {
  it("32-segment ideal circle (r=10) → r=10, weak=false", () => {
    const { positions, loop } = regularPolygonOnCircle(32, 10);
    const rim = fitCircle(loop, positions);
    expect(rim).not.toBeNull();
    expect(rim!.radius).toBeCloseTo(10, 5);
    expect(rim!.weak).toBe(false);
  });

  it("16-segment circle → weak=false", () => {
    const { positions, loop } = regularPolygonOnCircle(16, 5);
    const rim = fitCircle(loop, positions);
    expect(rim!.weak).toBe(false);
  });

  it("12-segment circle (boundary value) → weak=false", () => {
    const { positions, loop } = regularPolygonOnCircle(12, 5);
    const rim = fitCircle(loop, positions);
    expect(rim!.weak).toBe(false);
  });

  it("hex (N=6) → weak=true (low-N flag), r ≈ R", () => {
    const { positions, loop } = regularPolygonOnCircle(6, 5);
    const rim = fitCircle(loop, positions);
    expect(rim).not.toBeNull();
    expect(rim!.weak).toBe(true);
    expect(rim!.radius).toBeCloseTo(5, 4);
  });

  it("tilted 32-segment circle (axis = x) → r and axis correct", () => {
    const { positions, loop } = regularPolygonOnCircle(32, 5, "x");
    const rim = fitCircle(loop, positions);
    expect(rim).not.toBeNull();
    expect(rim!.radius).toBeCloseTo(5, 5);
    expect(Math.abs(rim!.axis.x)).toBeCloseTo(1, 3);
  });
});

describe("fitCircle — rejections", () => {
  it("square (N=4) → null (MIN_LOOP_VERTICES)", () => {
    expect(MIN_LOOP_VERTICES).toBe(6);
    const { positions, loop } = regularPolygonOnCircle(4, 5);
    expect(fitCircle(loop, positions)).toBeNull();
  });

  it("pentagon (N=5) → null (MIN_LOOP_VERTICES)", () => {
    const { positions, loop } = regularPolygonOnCircle(5, 5);
    expect(fitCircle(loop, positions)).toBeNull();
  });

  it("rectangle (4 corners on a circle, but N=4) → null", () => {
    const positions = new Float32Array([0, 0, 0, 10, 0, 0, 10, 5, 0, 0, 5, 0]);
    const loop = [0, 1, 2, 3];
    expect(fitCircle(loop, positions)).toBeNull();
  });

  it("ellipse (32 verts, 2:1 ratio) → null (sagitta gate)", () => {
    const N = 32;
    const pos: number[] = [];
    const loop: number[] = [];
    for (let i = 0; i < N; i++) {
      const t = (2 * Math.PI * i) / N;
      pos.push(20 * Math.cos(t), 10 * Math.sin(t), 0);
      loop.push(i);
    }
    expect(fitCircle(loop, new Float32Array(pos))).toBeNull();
  });

  it("collinear points → null (planarity)", () => {
    const positions = new Float32Array([0, 0, 0, 1, 0, 0, 2, 0, 0, 3, 0, 0, 4, 0, 0, 5, 0, 0, 6, 0, 0, 7, 0, 0]);
    const loop = [0, 1, 2, 3, 4, 5, 6, 7];
    expect(fitCircle(loop, positions)).toBeNull();
  });

  it("angular-gap outlier (13 of 16 evenly-spaced + 3 missing) → null", () => {
    const N = 16;
    const pos: number[] = [];
    const loop: number[] = [];
    for (let i = 0; i < N; i++) {
      if (i >= N - 3) continue; // skip last 3 → one ~90° gap
      const t = (2 * Math.PI * i) / N;
      pos.push(5 * Math.cos(t), 5 * Math.sin(t), 0);
      loop.push(loop.length);
    }
    expect(fitCircle(loop, new Float32Array(pos))).toBeNull();
  });
});
