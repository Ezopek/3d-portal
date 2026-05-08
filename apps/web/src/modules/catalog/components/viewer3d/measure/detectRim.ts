import { Vector3 } from "three";

import { BOUNDARY, type WeldedMesh } from "../lib/welder";
import type { SharpEdgeGraph } from "../lib/sharpEdgeGraph";
import { closestSharpEdge } from "./closestSharpEdge";
import { walkEdgeLoop } from "./loopWalk";
import { fitCircle, type Rim } from "./circleFit";

export function detectRim(
  hitTriangle: number,
  hitPoint: Vector3,
  welded: WeldedMesh,
  graph: SharpEdgeGraph,
): Rim | null {
  if (hitTriangle === BOUNDARY) return null;
  const edge = closestSharpEdge(welded, graph, hitTriangle, hitPoint);
  if (edge === null) return null;
  const loopVerts = walkEdgeLoop(welded, graph, edge);
  if (loopVerts === null) return null;
  return fitCircle(loopVerts, welded.positions);
}
