import { Color } from "three";

export type MeshTokens = {
  paint: Color;
  edge: Color;
  grid: Color;
  measure: Color;
  cluster: Color;
};

function readVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v.length === 0 ? fallback : v;
}

export function readMeshTokens(): MeshTokens {
  return {
    paint: new Color(readVar("--color-viewer-mesh-paint", "hsl(220 9% 60%)")),
    edge: new Color(readVar("--color-viewer-mesh-edge", "hsl(220 14% 28%)")),
    grid: new Color(readVar("--color-viewer-grid", "hsl(220 14% 80%)")),
    measure: new Color(readVar("--color-viewer-measure", "hsl(217 91% 60%)")),
    cluster: new Color(readVar("--color-viewer-cluster", "hsl(142 71% 45%)")),
  };
}
