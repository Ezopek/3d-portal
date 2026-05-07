import { describe, it, expect } from "vitest";
import { Vector3 } from "three";

import { distance, midpoint, formatMm } from "./geometry";
import {
  anglePlanes,
  distancePointToPlane,
  minVertexPairDistance,
  perpendicularPlaneDistance,
} from "./geometry";

describe("distance", () => {
  it("returns Euclidean distance between two points", () => {
    expect(distance(new Vector3(0, 0, 0), new Vector3(3, 4, 0))).toBeCloseTo(5, 6);
  });

  it("returns 0 for identical points", () => {
    expect(distance(new Vector3(1, 2, 3), new Vector3(1, 2, 3))).toBe(0);
  });

  it("handles negative coordinates", () => {
    expect(distance(new Vector3(-1, -1, -1), new Vector3(1, 1, 1))).toBeCloseTo(
      Math.sqrt(12),
      6,
    );
  });
});

describe("midpoint", () => {
  it("returns the midpoint of two points", () => {
    const m = midpoint(new Vector3(0, 0, 0), new Vector3(2, 4, 6));
    expect(m.x).toBe(1);
    expect(m.y).toBe(2);
    expect(m.z).toBe(3);
  });
});

describe("formatMm", () => {
  it("formats with one decimal mm by default", () => {
    expect(formatMm(42.04)).toBe("42.0 mm");
  });

  it("includes qualifier when provided", () => {
    expect(formatMm(42, { qualifier: "assumed" })).toBe("42.0 mm (assumed)");
  });

  it("clamps to one decimal even for whole numbers", () => {
    expect(formatMm(7)).toBe("7.0 mm");
  });
});

describe("distancePointToPlane", () => {
  it("returns 0 for point on the plane", () => {
    const d = distancePointToPlane(
      new Vector3(0, 0, 0),
      new Vector3(0, 0, 0),
      new Vector3(0, 0, 1),
    );
    expect(d).toBe(0);
  });

  it("returns absolute perpendicular distance", () => {
    const d = distancePointToPlane(
      new Vector3(0, 0, 5),
      new Vector3(0, 0, 0),
      new Vector3(0, 0, 1),
    );
    expect(d).toBe(5);
  });

  it("ignores in-plane offset components", () => {
    const d = distancePointToPlane(
      new Vector3(10, 20, -3),
      new Vector3(0, 0, 0),
      new Vector3(0, 0, 1),
    );
    expect(d).toBe(3);
  });
});

describe("anglePlanes", () => {
  it("returns 0 for parallel normals", () => {
    expect(anglePlanes(new Vector3(0, 0, 1), new Vector3(0, 0, 1))).toBeCloseTo(0);
  });

  it("returns 0 for anti-parallel normals (uses |n·n|)", () => {
    expect(anglePlanes(new Vector3(0, 0, 1), new Vector3(0, 0, -1))).toBeCloseTo(0);
  });

  it("returns 90 for perpendicular normals", () => {
    expect(anglePlanes(new Vector3(0, 0, 1), new Vector3(1, 0, 0))).toBeCloseTo(90);
  });
});

describe("perpendicularPlaneDistance", () => {
  it("opposite cube faces (anti-parallel normals): wall thickness reads correctly", () => {
    const d = perpendicularPlaneDistance(
      new Vector3(0, 0, -0.5),
      new Vector3(0, 0, -1),
      new Vector3(0, 0, 0.5),
    );
    expect(d).toBeCloseTo(1, 5);
  });

  it("returns absolute value (sign-agnostic)", () => {
    const d = perpendicularPlaneDistance(
      new Vector3(0, 0, 5),
      new Vector3(0, 0, 1),
      new Vector3(0, 0, -3),
    );
    expect(d).toBe(8);
  });
});

describe("minVertexPairDistance", () => {
  it("returns the min pair distance over two small clusters", () => {
    const A = [new Vector3(0, 0, 0), new Vector3(1, 0, 0)];
    const B = [new Vector3(5, 0, 0), new Vector3(7, 0, 0)];
    expect(minVertexPairDistance(A, B)).toBeCloseTo(4, 5);
  });

  it("returns 0 when clusters share a vertex", () => {
    const A = [new Vector3(1, 1, 1)];
    const B = [new Vector3(1, 1, 1)];
    expect(minVertexPairDistance(A, B)).toBe(0);
  });
});
