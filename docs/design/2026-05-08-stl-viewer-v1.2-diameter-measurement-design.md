# STL Viewer v1.2 — Diameter (rim) measurement + per-measurement palette

**Status:** Design — not yet implemented
**Author:** Michał + Claude
**Date:** 2026-05-08
**Supersedes:** Extends `2026-05-06-stl-viewer-design.md` §12.2 (deferred
"diameter / hole / circle measurement") and `2026-05-07-stl-viewer-v1.1-plane-measurement-design.md`
**Revision:** v1 (initial)

## Revision history

- **v1 (this)** — first draft from brainstorm decisions, ready for
  Codex review and plan handoff.

## 1. Overview & scope

v1.2 adds **rim-based diameter measurement** to the STL viewer plus a
**per-measurement color palette** that retrofits the existing v1.1
plane-aware modes.

The hole-vs-shaft distinction familiar from CAD UX is collapsed into a
single concept: the user clicks the **circular edge loop** (rim) of any
cylindrical feature — inner (hole) or outer (boss/shaft) — and the
viewer reports its diameter. From the mesh's perspective both look
identical: a closed loop of "sharp" edges separating the cylindrical
strip from a flat cap or surrounding face. Algorithm: walk that loop,
fit a 2D circle to its vertices, report `radius * 2`.

This avoids 3D cylinder fitting (proposed in earlier design notes)
which is fragile on tessellated meshes and breaks on thin plates with
through-holes (no cylindrical wall to click — only a rim).

Alongside Diameter we ship a **color palette system** so multiple
measurements coexisting in one scene remain individually identifiable.
v1.1 used a single green `--color-viewer-cluster` for every plane
overlay; with up to 4 measurement kinds and an unbounded count of
completed measurements, that single color stops scaling. v1.2 replaces
it with a per-measurement palette derived at runtime from a golden-angle
hue rotation, with each measurement's two selection slots distinguished
by **lightness only** (same hue, sel1 bright / sel2 dark) — a "natural
pair" pattern.

### 1.1 In scope

- New mode **Diameter** in the measure toolbar (`Circle` icon, shortcut `D`).
- Hover preview: rim's edge loop highlights when a valid closed loop
  with low circle-fit residuum is detected under the cursor.
- Single-click commit: clicking on a previewed rim adds a `kind:"diameter"`
  measurement to `state.completed`.
- Visualization of completed Diameter measurement: rim line tube +
  small center dot + label `#N Ø 25.0 mm`.
- **Per-measurement palette (palette E)** — `paletteFor(index, slot)`
  generator. Used by Diameter (rim only — no sel2) and retrofitted to
  p2p, p2pl, pl2pl.
- Active-stage coloring uses the palette index of the *next*
  measurement (`state.completed.length`) — preemptive, no visual jump
  on commit.
- `MeasureSummary` row gains color swatches matching the 3D overlay
  colors, so the panel acts as a legend.

### 1.2 Out of scope

Deferred (each gets its own spec when prioritized):

- **v2 measure-system rewrite.** Auto-detect mode (hover decides
  whether to pick rim/face/edge/vertex), edge picker (linear sharp
  edges between flat faces), and the cross-type measurement matrix
  (rim+rim, rim+plane, edge+edge, …). v2 is the highest-priority
  follow-up after v1.2.
- **Vertex / edge snapping** for sub-triangle precision in p2p.
- **Persistent measurements per model.**
- **3MF / STEP support, cross-section, annotations, multi-mesh STLs**
  (per v1 §12.2).
- **Per-measurement color stability across deletes.** v1.2 renumbers
  palette indices when `state.completed` shrinks; a future increment
  may store a stable `colorIndex` per `Measurement`.

### 1.3 Backend

Zero changes. Same SoT API used by v1 and v1.1. Visible to every
catalog visitor; no privilege gate.

## 2. UX

### 2.1 Toolbar layout

The measure toolbar gains one button. Final layout (left to right):

```
Reset | Wireframe | Camera | p2p | p2pl | pl2pl | diameter | tolerance° | Expand
```

- **Diameter button:** lucide `Circle` icon, `aria-label` and tooltip
  from `viewer3d.measure.mode.diameter` ("Measure diameter" / "Zmierz
  średnicę"). 40 × 40 hit target (matches v1.1 mode buttons).
- **Keyboard shortcut:** `D` toggles Diameter mode (parallel to
  v1.1's `R` for p2p, `P` for p2pl, `L` for pl2pl).
- **Tolerance° popover:** visible **only** when
  `mode ∈ {point-to-plane, plane-to-plane}`. Hidden in `off`, `p2p`,
  and `diameter` — those modes have nothing to tune via dihedral
  tolerance.

### 2.2 Click flow — Diameter mode

Diameter is single-click; there is no "have-rim" intermediate active
stage. The flow:

1. **Enter Diameter mode** (button click or `D` key). `state.active`
   resets to `{stage:"empty"}`. Welding starts in the background if
   not already cached (Diameter joins p2pl/pl2pl in the
   `needsWelding` set).
2. **User hovers** over the mesh. For each fresh `pointermove`,
   `Viewer3DCanvas` raycasts the mesh, gets `(triangleIndex,
   hitPoint)`, and runs:
   1. `closestSharpEdge(triangle, hitPoint, welded, sharpEdges)` —
      checks the 3 edges of the hit triangle for a sharp neighbor;
      falls back to BFS in a 3-triangle radius.
   2. If found: `walkEdgeLoop(welded, sharpEdges, edge)` — closed loop
      or `null`.
   3. If loop closed: `fitCircle(loopVerts, welded.positions)` —
      `Rim` or `null` (`null` if non-planar, residuum too high, or
      degenerate).
   4. The hover handler is `requestAnimationFrame`-throttled (no
      per-frame loop walk).
3. **Hover preview** — when steps 2.1-2.3 all succeed, the canvas
   renders the rim's loop as a tube line in the bright sel1 color of
   palette index `state.completed.length` (the index this measurement
   *would* have if committed). No center dot, no label — preview is
   intentionally minimal.
4. **Click while preview is shown:** `dispatch({type:"click-rim",
   rim})`. Reducer appends `kind:"diameter"` to `state.completed`.
   The committed measurement keeps the same palette index, so its
   colors don't jump on commit.
5. **Click without preview:** silent no-op. Brief failure UX is
   covered entirely by the absence of the preview — no toast, no
   banner.

### 2.3 Visualization — completed Diameter measurement

A committed `kind:"diameter"` measurement renders three pieces in 3D:

| Element | Geometry | Color |
|---|---|---|
| Rim loop | drei `<Line>`, `lineWidth: 2`, points = welded vertices in loop order, closed = true | `bright sel1` of palette[index] |
| Center dot | `<mesh>` with `<sphereGeometry args={[max(0.5, radius*0.04), 12, 12]} />` at `rim.center` | same as rim |
| Label | `<Html>` HTML badge, classes match v1.1 `LABEL_CLASS`. Text: `#N Ø 25.0 mm` (or `#N ~Ø 25.0 mm` if `weak: true`). Position: `rim.center + tangent * (radius + 4mm)` so it doesn't sit on the loop itself. | white text, dark zinc background |

`tangent` is any unit vector perpendicular to `rim.axis`; we pick one
deterministically (the one closer to the camera direction at first
render — recomputed on resetSignal but otherwise stable so the label
doesn't twitch).

### 2.4 Retrofit — p2p, p2pl, pl2pl

The same palette system colors the existing v1.1 modes. Slot
assignment per measurement kind:

| kind | sel1 (bright) | sel2 (dark) |
|---|---|---|
| `p2p` | line + dot at point A | dot at point B |
| `p2pl` | plane cluster overlay | dot at point |
| `pl2pl` | planeA cluster overlay | planeB cluster overlay |
| `diameter` | rim loop + center dot + label | — (single-rim, no sel2) |

Active (in-progress) coloring uses palette index `state.completed.length`
preemptively. So clicking the first plane in a pl2pl is colored as
sel1 of measurement #(N+1); clicking the second plane is colored as
sel2 of the same measurement; the values don't change on commit.

### 2.5 Esc ladder

Diameter mode adds no new layer — single-click commit means there is
no in-progress active stage to cancel separately. The v1.1 ladder
holds:

1. Welding in flight → cancel weld, drop mode to off.
2. Active stage non-empty → cancel just the active step (N/A in
   Diameter — always empty).
3. Mode != off → leave measure mode.
4. Otherwise → fall through to Dialog (close modal).

### 2.6 MeasureSummary panel

Each row in `MeasureSummary` gains color swatches on the left:

```tsx
<span className="inline-flex items-center gap-0.5">
  <span className="h-2.5 w-2.5 rounded-sm" style={{ background: sel1Hex }} />
  {sel2Hex !== null && (
    <span className="h-2.5 w-2.5 rounded-sm" style={{ background: sel2Hex }} />
  )}
</span>
```

For Diameter the second swatch is omitted (no sel2). For p2p, p2pl,
pl2pl both swatches render. The panel becomes the legend mapping
`#N` → 3D overlay colors.

Diameter rows display `Ø 25.0 mm` instead of plain `25.0 mm`. Weak
diameters: `~Ø 25.0 mm` with the same tilde convention as v1.1 weak
planes.

## 3. Color palette system (palette E)

### 3.1 Generator

`apps/web/src/modules/catalog/components/viewer3d/lib/palette.ts`:

```ts
import { Color } from "three";

const BASE_HUE_DEG = 200;
const GOLDEN_ANGLE_DEG = 137.50776;
const PAIR_LIGHTNESS_BRIGHT = 0.78; // sel1
const PAIR_LIGHTNESS_DARK = 0.50;   // sel2
const PAIR_CHROMA = 0.18;

export type PaletteSlot = "sel1" | "sel2";

export function paletteFor(index: number, slot: PaletteSlot): Color {
  const hue = (BASE_HUE_DEG + index * GOLDEN_ANGLE_DEG) % 360;
  const L = slot === "sel1" ? PAIR_LIGHTNESS_BRIGHT : PAIR_LIGHTNESS_DARK;
  return new Color().setRGB(...oklchToLinearSrgb(L, PAIR_CHROMA, hue));
}

// OKLCH → Linear sRGB → in-gamut clamp.
// Reference: https://bottosson.github.io/posts/oklab/
export function oklchToLinearSrgb(L: number, C: number, hueDeg: number): [number, number, number] {
  const h = (hueDeg * Math.PI) / 180;
  const a = C * Math.cos(h);
  const b = C * Math.sin(h);
  // OKLab → linear sRGB (Björn Ottosson's published matrix)
  const l_ = L + 0.3963377774 * a + 0.2158037573 * b;
  const m_ = L - 0.1055613458 * a - 0.0638541728 * b;
  const s_ = L - 0.0894841775 * a - 1.2914855480 * b;
  const l3 = l_ ** 3;
  const m3 = m_ ** 3;
  const s3 = s_ ** 3;
  const r =  4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3;
  const g = -1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3;
  const bl = -0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3;
  // Clamp to in-gamut sRGB and pass through three.js's Color which
  // applies its own working-space conversion.
  return [Math.max(0, Math.min(1, r)), Math.max(0, Math.min(1, g)), Math.max(0, Math.min(1, bl))];
}
```

### 3.2 Slot assignment rules

(Repeats §2.4 for normative reference.)

- **Active overlay (in-progress measurement)** uses `paletteFor(state.completed.length, slot)`.
- **Completed measurement at completed-array index `i`** uses `paletteFor(i, slot)`.
- **`delete-measurement`** shrinks the array; subsequent measurements'
  indices shift down; their colors shift accordingly. This is the
  "renumbering on delete" trade-off — accepted in v1.2 because storing
  a stable `colorIndex` in `Measurement` brings type bloat and a
  separate "color allocator" with no immediate user benefit.

### 3.3 Theme tokens

`apps/web/src/styles/theme.css`:

- **Remove** `--color-viewer-cluster` (currently a static green). The
  palette is runtime-computed and per-index; no static token replaces
  it.
- **Keep** `--color-viewer-paint` (mesh material color) and
  `--color-viewer-measure` (line/label neutrals). These remain
  theme-static.

Light theme: palette E lightness/chroma values are tuned for a dark
viewer canvas. The viewer is currently always dark regardless of
portal theme. If a future "light viewer" appears, define
`PAIR_LIGHTNESS_*` as theme-conditional constants then.

### 3.4 Three.js color object lifecycle

`paletteFor()` returns a fresh `Color` each call. Components that hold
the result in state (e.g., `useMemo` over palette swatches) reuse the
instance. R3F handles `Color` props via reference — replacing
`color` triggers a material update on next render.

## 4. Algorithm — edge-loop walking + 2D circle fit

### 4.1 Sharp-edge classification

Stored as a lazy extension on `WeldedMesh`. New optional field
`dihedralAngles?: Float32Array` of length `welded.adjacency.length / 3`
(one entry per welded triangle's three edges; `-1` sentinel means
boundary edge with no neighbor).

Computation (`apps/web/src/modules/catalog/components/viewer3d/lib/sharpEdges.ts`):

```ts
export const SHARP_EDGE_THRESHOLD_RAD = (30 * Math.PI) / 180;

export function computeSharpEdges(welded: WeldedMesh): Float32Array {
  const triCount = welded.indices.length / 3;
  const out = new Float32Array(triCount * 3);
  const normals = computeFaceNormals(welded); // O(triangles)
  for (let t = 0; t < triCount; t++) {
    for (let e = 0; e < 3; e++) {
      const neighbor = welded.adjacency[t * 3 + e];
      if (neighbor === BOUNDARY) {
        out[t * 3 + e] = -1;
        continue;
      }
      const cosA =
        normals[t * 3] * normals[neighbor * 3] +
        normals[t * 3 + 1] * normals[neighbor * 3 + 1] +
        normals[t * 3 + 2] * normals[neighbor * 3 + 2];
      out[t * 3 + e] = Math.acos(Math.max(-1, Math.min(1, cosA)));
    }
  }
  return out;
}

export function isSharp(angle: number): boolean {
  return angle === -1 /* boundary */ || angle >= SHARP_EDGE_THRESHOLD_RAD;
}
```

Cached in the `WeldedMesh` returned by `usePlanePrep`. Computed lazily
on first Diameter use per mesh; cost ~10ms per 500k tri.

### 4.2 Closest sharp edge

```ts
// viewer3d/measure/closestSharpEdge.ts
export type SharpEdgeRef = { triangleId: number; edgeIndex: 0 | 1 | 2 };

export function closestSharpEdge(
  welded: WeldedMesh,
  sharpEdges: Float32Array,
  hitTriangle: number,
  hitPoint: Vector3,
): SharpEdgeRef | null {
  // 1. Try the 3 edges of the hit triangle.
  const direct = pickClosestSharpEdgeOnTriangle(welded, sharpEdges, hitTriangle, hitPoint);
  if (direct !== null) return direct;
  // 2. BFS up to 3 triangles deep.
  return bfsFindSharpEdge(welded, sharpEdges, hitTriangle, hitPoint, 3);
}
```

`pickClosestSharpEdgeOnTriangle` computes the perpendicular distance
from `hitPoint` to each of the triangle's three edges and returns the
one with the smallest distance among those flagged sharp by
`isSharp()`.

### 4.3 Loop walking

`apps/web/src/modules/catalog/components/viewer3d/measure/loopWalk.ts`:

```ts
export const LOOP_MAX_VERTICES = 512;

export function walkEdgeLoop(
  welded: WeldedMesh,
  sharpEdges: Float32Array,
  start: SharpEdgeRef,
): number[] | null {
  // Returns welded vertex indices in loop order, or null on:
  //   - loop > LOOP_MAX_VERTICES
  //   - ambiguous junction (≥3 sharp edges incident to a vertex)
  //   - open path (loop did not close)
}
```

Walk procedure:

1. **Init:** the start edge has two endpoint vertices `(v0, v1)`.
   Begin at `v0`, current direction = `v1 - v0`. Track visited
   sharp edges (a `Set<edgeKey>` keyed by sorted vertex pair).
2. **Step:** at each vertex `vCurrent` find all sharp edges incident
   to it (including across the welded vertex's incident triangles).
   Filter out edges already visited.
   - **Zero candidates:** loop terminated without closing → `null`.
   - **One candidate:** walk it, mark visited, move to the other
     endpoint.
   - **Two candidates:** pick the one whose direction (`vNext -
     vCurrent`) maximizes dot product with current direction (least
     turning). Track absolute turn angle; if **two consecutive**
     turns each exceed 90° → `null` (ambiguous junction signal).
   - **Three or more candidates:** `null` (T-junction or worse).
3. **Termination:** if `vNext == startVertex` → loop closed; return
   the ordered vertex list.
4. **Cap:** if visited count > `LOOP_MAX_VERTICES` → `null`.

Boundary edges (open mesh) are treated as sharp; a hole's rim on a
non-watertight STL still produces a closed loop along the mesh
boundary.

### 4.4 2D circle fit

`apps/web/src/modules/catalog/components/viewer3d/measure/circleFit.ts`:

```ts
export type Rim = {
  center: Vector3;
  axis: Vector3;          // unit, plane normal
  radius: number;         // mm
  loopVertices: number[]; // welded vertex indices, loop order
  weak: boolean;          // residuum > 0.5 * threshold
};

export const PLANARITY_RATIO_MAX = 0.05;  // λ_min / λ_avg
export const RESIDUUM_FLOOR_MM = 0.1;
export const RESIDUUM_RATIO = 0.05;

export function fitCircle(
  loopVerts: number[],
  positions: Float32Array,
): Rim | null {
  // ...
}
```

Steps:

1. **Plane fit (PCA).** Centroid of vertices. 3×3 covariance matrix.
   Eigenvectors via Jacobi rotation (small constant matrix; ~50 lines).
   Smallest eigenvalue → plane normal. **Reject** if `λ_min / λ_avg
   > PLANARITY_RATIO_MAX` (loop not coplanar).
2. **Project to 2D.** Pick two orthogonal basis vectors in the plane
   (Gram-Schmidt from any non-collinear loop vertex). Project each
   loop vertex to `(u, v)` coordinates.
3. **Algebraic circle fit (Pratt/Coope).** Solve linear system
   `[u² + v², u, v, 1] @ [a, b, c, d]ᵀ = 0` via SVD. Center and
   radius extract from solution. ~30 lines.
4. **Residuum check.** `residuum = max(|‖vi - center2D‖ - r|)` over
   all loop vertices. Threshold = `max(RESIDUUM_FLOOR_MM, RESIDUUM_RATIO
   * r)`. **Reject** if residuum > threshold.
   - `weak: residuum > 0.5 * threshold` — accepted but flagged.
5. **Backproject 2D center → 3D** via `centroid + center2D.u * basisU +
   center2D.v * basisV`. Axis = plane normal.

### 4.5 Failure modes (silent — UX gated by hover preview absence)

| Reason | Returns | UX |
|---|---|---|
| `closestSharpEdge` finds nothing in 3-tri radius | `null` | no preview |
| `walkEdgeLoop`: > 512 verts | `null` | no preview |
| `walkEdgeLoop`: ambiguous junction | `null` | no preview |
| `walkEdgeLoop`: open path | `null` | no preview |
| `fitCircle`: not coplanar | `null` | no preview |
| `fitCircle`: residuum > threshold | `null` | no preview |
| Welding error | banner | reuse v1.1 StepBanner pattern |

### 4.6 Performance

| Operation | Cost (500k tri) | When |
|---|---|---|
| `computeSharpEdges` | ~10ms | once per mesh, cached in WeldedMesh |
| `closestSharpEdge` | <0.5ms | every hover frame (rAF-throttled) |
| `walkEdgeLoop` | <1ms (loop ≤ 64 verts typical) | per hover frame |
| `fitCircle` | <1ms | per hover frame |
| Render rim Line | negligible | per render |

Total hover budget: ~3ms per frame. Acceptable on 60fps.

## 5. State, types, reducer

### 5.1 New types in `viewer3d/types.ts`

```ts
export type Rim = {
  center: Vector3;
  axis: Vector3;
  radius: number;
  loopVertices: number[];
  weak: boolean;
};

// MeasureMode extension
export type MeasureMode =
  | "off"
  | "point-to-point"
  | "point-to-plane"
  | "plane-to-plane"
  | "diameter";

// Measurement union extension
export type Measurement =
  | { kind: "p2p"; ... }    // unchanged
  | { kind: "p2pl"; ... }   // unchanged
  | { kind: "pl2pl"; ... }  // unchanged
  | {
      kind: "diameter";
      id: string;
      rim: Rim;
      diameterMm: number; // = rim.radius * 2; denormalized for display + sort
      weak: boolean;      // copied from rim.weak; mirrors v1.1 plane-weak idiom
    };
```

`MeasureActiveStage` is **not** extended. Diameter is single-click; the
rim hover preview is local UI state in `Viewer3DCanvas`, not reducer
state. `state.active` in Diameter mode is always `{stage:"empty"}`.

### 5.2 New reducer action

```ts
| { type: "click-rim"; rim: Rim }
```

Handler:

```ts
case "click-rim": {
  if (state.mode !== "diameter") return state;
  const m: Measurement = {
    kind: "diameter",
    id: newId("diameter", state.completed),
    rim: action.rim,
    diameterMm: action.rim.radius * 2,
    weak: action.rim.weak,
  };
  return { ...state, completed: [...state.completed, m] };
}
```

### 5.3 Existing reducer behavior

- `set-mode` for `"diameter"`: resets `active` to `{stage:"empty"}` (same as any switch).
- `delete-measurement` works unchanged (id-based filter).
- `clear` works unchanged.
- `replace-active-plane`, `patch-last-pl2pl`, `patch-last-p2pl`,
  `click-plane`, `click-mesh`: not applicable when mode is "diameter".
  Reducer guards return `state` unchanged.

## 6. Files

### 6.1 New files

| Path | Responsibility |
|---|---|
| `viewer3d/lib/palette.ts` | `paletteFor(idx, slot)`, `oklchToLinearSrgb()`. Pure. |
| `viewer3d/lib/sharpEdges.ts` | `computeSharpEdges(welded)`, `isSharp()`, `SHARP_EDGE_THRESHOLD_RAD`. Pure. |
| `viewer3d/measure/closestSharpEdge.ts` | `closestSharpEdge()`, `pickClosestSharpEdgeOnTriangle()`, `bfsFindSharpEdge()`. Pure. |
| `viewer3d/measure/loopWalk.ts` | `walkEdgeLoop()`, `LOOP_MAX_VERTICES`. Pure. |
| `viewer3d/measure/circleFit.ts` | `fitCircle()`, `Rim` type re-export. Pure (Jacobi eigendecomp + Pratt fit inline). |
| `viewer3d/measure/RimOverlay.tsx` | R3F component: `<Line>` tube + `<sphereGeometry>` center dot. Props: `rim`, `color`, `showLabel?`. |
| `viewer3d/controls/DiameterModeButton.tsx` | (optional) extracted toolbar button, or inline in `ViewToolbar.tsx`. |
| `apps/web/tests/unit/palette.test.ts` | Generator determinism, slot distinction, hue separation, in-gamut. |
| `apps/web/tests/unit/sharpEdges.test.ts` | Cube → 12 sharp; smooth dome → 0; plate-with-hole → 2N + 12. |
| `apps/web/tests/unit/loopWalk.test.ts` | Plate hole → loop closed; cube edge → null; T-junction → null; > 512 → null. |
| `apps/web/tests/unit/circleFit.test.ts` | Ideal circle exact; 1% noise weak; ellipse 2:1 → null; collinear → null. |
| `apps/web/tests/visual/viewer3d-diameter.spec.ts` | Mode toolbar, hover preview, click commit, multi-measure colors, MeasureSummary. |
| `apps/web/tests/visual/viewer3d-palette-retrofit.spec.ts` | pl2pl/p2pl/p2p with palette E. |
| `apps/web/tests/visual/fixtures/build-plate-with-hole.ts` | STL: 50×30×3 mm plate, single Ø 10 mm hole, 32 segments. |
| `apps/web/tests/visual/fixtures/build-plate-multiple-holes.ts` | STL: plate, 3 holes (Ø 5/10/15). |

### 6.2 Modified files

| Path | Change |
|---|---|
| `viewer3d/types.ts` | + `Rim` type, + `Measurement.kind:"diameter"`, + `MeasureMode "diameter"`. |
| `viewer3d/measure/measureReducer.ts` | + `click-rim` action. |
| `viewer3d/lib/welder.ts` | + optional `dihedralAngles?: Float32Array` field on `WeldedMesh`. |
| `viewer3d/lib/weldCache.ts` | No changes. Cache stores WeldedMesh as-is; sharp-edges live as a runtime-computed extension on the same object. |
| `viewer3d/Viewer3DCanvas.tsx` | + `mode === "diameter"` branch in `handleMeshClick` (dispatch `click-rim`); + hover preview state for `hoveredRim`; + render `<RimOverlay>` for hover preview when in Diameter mode and rim is detected; + lazy `computeSharpEdges` call on first Diameter hover. |
| `viewer3d/Viewer3DModal.tsx` | + render completed `kind:"diameter"` measurements (loop overlay + center dot + label); + use `paletteFor(idx, slot)` everywhere a cluster/line/dot is drawn (replaces `tokens.cluster`); + `needsWelding` includes `"diameter"`. |
| `viewer3d/Viewer3DInline.tsx` | Same pattern as `Viewer3DModal.tsx`. |
| `viewer3d/controls/ViewToolbar.tsx` | + Diameter button (lucide `Circle`, `aria-label` from i18n); + tolerance popover visible only when `mode ∈ {"point-to-plane","plane-to-plane"}` (hidden in `off`, `p2p`, `diameter`). |
| `viewer3d/controls/MeasureSummary.tsx` | + color swatches per row (sel1 + sel2 dots); + diameter row format `Ø XX.X mm` / `~Ø XX.X mm`. |
| `viewer3d/controls/StepBanner.tsx` | + i18n key for Diameter "click on a circular edge" instruction. |
| `viewer3d/measure/MeasureOverlay.tsx` | Retrofit: line/dot/label colors from palette per-measurement instead of single `tokens.measure`. |
| `viewer3d/measure/ClusterOverlay.tsx` | No structural change (color is already a prop). |
| `apps/web/src/locales/en.json`, `pl.json` | + `viewer3d.measure.mode.diameter` ("Measure diameter" / "Zmierz średnicę"); + `viewer3d.measure.diameter.help` (banner instruction); + `viewer3d.measure.diameter.format` ("Ø {value} mm"); + `viewer3d.measure.diameter.weak` ("~Ø {value} mm"); + `viewer3d.measure.diameter.weak_tooltip`. |
| `apps/web/src/styles/theme.css` | Remove `--color-viewer-cluster`. Keep `--color-viewer-paint`, `--color-viewer-measure`. |

### 6.3 Data flow — single Diameter measurement

```
mouse over mesh
  → Viewer3DCanvas onPointerMove  (rAF-throttled)
  → raycast → (triangleIndex, hitPoint)
  → if mode === "diameter":
      → closestSharpEdge(triangle, hitPoint, welded, sharpEdges)
      → walkEdgeLoop(welded, sharpEdges, edge)
      → fitCircle(loopVerts, welded.positions)
      → setHoveredRim(rim or null)
  → if hoveredRim: render <RimOverlay rim={hoveredRim} color={paletteFor(N+1, "sel1")} />
on click:
  → if mode === "diameter" && hoveredRim !== null:
      → dispatch({ type: "click-rim", rim: hoveredRim })
  → reducer appends to state.completed
  → Modal/Inline re-renders, RimOverlay for completed measurement uses paletteFor(idx, "sel1")
on file switch:
  → activeId change triggers `clear` dispatch (existing v1.1 effect)
  → hoveredRim reset via geometry useEffect cleanup in Viewer3DCanvas
```

## 7. Error handling and edge cases

### 7.1 Failures recap

All algorithm failures from §4.5 are silent — the absence of hover
preview is the user-facing signal. Single-click commit only fires
when a preview rim was visible.

### 7.2 Welding errors

Diameter joins p2pl/pl2pl in the `needsWelding` set. The v1.1
`StepBanner` welding-error pattern is reused unchanged: error banner
with explicit dismiss button → drops mode to "off".

### 7.3 Weak rim

Circle fit residuum in `(0.5 * threshold, threshold]`:

- The fit is accepted (preview shows, click commits).
- The `Rim.weak` flag is `true`; copied to `Measurement.weak`.
- Visual: label gains a leading `~`: `#3 ~Ø 25.0 mm`.
- Tooltip on label: `viewer3d.measure.diameter.weak_tooltip` —
  "Diameter is approximate — the selected loop deviates from a perfect
  circle by up to N% of the radius."

### 7.4 Race conditions

| Race | Resolution |
|---|---|
| Click while hoveredRim already cleared (mesh moved, cursor moved) | Click handler checks `hoveredRim !== null`; otherwise no-op. |
| Welding completes after user left Diameter mode | Existing v1.1 `jobId` filter applies (per `usePlanePrep`). |
| File switch mid-hover | Existing `clear` dispatch resets `state.completed`; `hoveredRim` resets via `useEffect` on `geometry` change. |

### 7.5 Geometry edge cases

| Case | Behavior |
|---|---|
| Click exactly on a sharp edge but loop won't close (broken sheet near hole) | `walkEdgeLoop` returns `null` → silent fail |
| Counter-bore (two concentric rims, one inside the other) | Each rim is its own loop. User clicks the rim they want. No special handling. |
| Slot / oval (non-circular closed loop) | Loop closes; `fitCircle` rejects on residuum → silent fail |
| Low-segment cylinder (e.g., 6-segment hex hole) | Sharp edges valid; loop closes in 6 verts; `fitCircle` may flag weak (residuum elevated for low N). Acceptable — the hex *is* approximately a circle of inscribed/circumscribed radius depending on user intent. |
| Mesh with weak welding (vertices not properly merged) | `walkEdgeLoop` may fail to close due to incomplete adjacency. This is a mesh-quality issue, not an algorithm issue; silent fail is correct. |
| Plate-switching during pickup | `clear` + `hoveredRim` reset (see §7.4). |

## 8. Testing

### 8.1 Unit tests

| File | Cases |
|---|---|
| `palette.test.ts` | Determinism: `paletteFor(0,"sel1")` is stable. `sel1` and `sel2` for same index are visually distinct (deltaE > 30). Successive indices produce visibly different hues. All output channels in `[0,1]`. |
| `sharpEdges.test.ts` | Cube → 12 sharp edges (the 12 cube edges, 90° each). Smooth 256-seg dome (adjacent triangle angles ≈ 0.7°) → 0 sharp edges. Plate-with-32-seg-hole → 32 hole-rim sharp edges (top + bottom of plate) + 12 plate-corner edges. |
| `loopWalk.test.ts` | Plate-with-32-seg-hole → loop length 32; vertices in cyclic order. Cube without holes, started on a cube edge → loop length 4 (it's a square loop around one face). T-junction synthetic mesh → `null`. Loop > LOOP_MAX_VERTICES → `null`. |
| `circleFit.test.ts` | Ideal 32-pt circle r=10, noise=0 → r=10 (tolerance 1e-6); residuum ≤ 1e-6. 1% radial noise → r ≈ 10, residuum < 1%. Ellipse 2:1 (major=20, minor=10) → residuum > threshold → `null`. Collinear points → degenerate plane → `null`. |

All unit tests pure (no React, no Three.js renderer). Vitest.

### 8.2 Visual regression

| Spec | Steps |
|---|---|
| `viewer3d-diameter.spec.ts` | Open viewer with `plate-with-hole.stl`, enter Diameter mode (`D`), hover hole rim → screenshot preview; click → screenshot committed measurement; second hover, second click on same hole's other side → screenshot two measurements with distinct palette colors. |
| `viewer3d-palette-retrofit.spec.ts` | pl2pl on a cube: click two opposing faces → screenshot. Verify planeA = sel1 cyan, planeB = sel2 dark-cyan. Repeat with second pl2pl on adjacent faces → verify second measurement uses next palette index. Open MeasureSummary, screenshot to verify swatches match overlay colors. |

Both specs use the existing `tests/visual/` Playwright setup. Update
snapshots manually after first run (per project convention).

### 8.3 Manual smoke gate

(To be executed by Michał on real catalog STLs from
`/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/`.)

- [ ] Click on rim of a thin sheet hole → diameter visible, hover preview correct.
- [ ] Click on rim of a thick boss (cylinder with hole) → diameter visible.
- [ ] Click on rim of an outer shaft (e.g., a pin in the catalog) → diameter visible (not just inner holes).
- [ ] Counter-bore: click larger rim → larger value; click smaller rim → smaller value.
- [ ] Slot / oval feature: hover → no preview; click → silent no-op (no crash, no error).
- [ ] 5 Diameter measurements in one scene → all distinctly colored; MeasureSummary swatches match.
- [ ] Mixed: 2 × pl2pl + 2 × diameter + 1 × p2p → each measurement has unique palette colors; golden-angle rotation produces no visible duplicates within 5 measurements.
- [ ] Delete measurement #2 from MeasureSummary → measurement #3 becomes #2 and recolors accordingly (renumbering accepted).
- [ ] STL ≥ 500k tri: first Diameter hover may have a visible welding wait; subsequent hovers smooth (rAF-throttled, no per-frame lag).
- [ ] File switch in Diameter mode → new file's mesh, no stale rim preview from previous file.

## 9. Out of scope / future roadmap

### 9.1 v2 — measure system rewrite (highest priority follow-up)

- **Auto-detect mode.** Hover decides whether to pick rim / face /
  edge / vertex based on what's under the cursor. Single mode replaces
  the explicit p2p/p2pl/pl2pl/diameter buttons. Explicit modes can
  remain as fallbacks.
- **Edge picker.** Linear sharp-edge chains (open paths between two
  flat faces — counterpart to closed loops). Used for measuring
  edge length and edge-to-X distances/angles.
- **Cross-type measurement matrix.** rim+rim (distance between
  centers), rim+plane (closest distance), rim+edge, edge+edge (angle
  + distance), edge+plane, plane+vertex, etc. ~12 sensible pairings;
  each needs distance/angle math and visualization.
- **Vertex / edge snapping.** Sub-triangle precision for p2p picks.
  Vertex map + snap UX (e.g., snap-radius slider).

### 9.2 Smaller v1.x increments

- **Per-measurement color stability across deletes.** Store
  `colorIndex` in `Measurement`; allocate from a free-index pool on
  insert, release on delete. Replaces "renumbering" trade-off from
  §3.2.
- **Threshold UI.** Expose `SHARP_EDGE_THRESHOLD_RAD` and/or circle
  fit residuum as a slider when users report "my hole is not detected"
  on lower-quality meshes.
- **Diameter export.** Click on a `MeasureSummary` row → copy value to
  clipboard.
- **Diameter callout label.** Alternative visualization: arrow
  pointing into the rim, label outside the loop. Useful for very
  small holes where the centered label overlaps the rim.

### 9.3 Deferred features (per v1 §12.2)

- 3MF / STEP support
- Cross-section / clipping plane
- Annotations + screenshot bake-in
- Multi-mesh STLs split + sub-selector
- Persistent measurements per model

## 10. Risks and open questions

- **Sharp-edge threshold (30°).** Conservatively low — should catch
  any reasonable hole rim (typically 90° between cylinder wall and
  flat face). Might over-pick on heavily filleted models (5° fillets
  could be classified as sharp). If smoke test reveals false
  positives, raise to 45° before plan handoff.
- **Loop walk on pathological meshes.** The "two consecutive >90°
  turns" heuristic may misclassify some legitimate elliptical-but-still-
  smooth-rim loops. We'll see in smoke test; alternative is
  pure-angle-budget-based termination (loop must accumulate ≤ 360° of
  turning).
- **Pratt vs Taubin circle fit.** Pratt is simpler and stable for our
  tolerances. If we later see fit failures on slightly non-circular
  loops where the user clearly *wants* a diameter, switch to Taubin
  (more robust to outliers). Drop-in replacement.
- **OKLCH out-of-gamut colors.** A small fraction of (L=0.78,
  C=0.18, hue) combinations may be slightly out-of-gamut sRGB. We
  clamp linearly which reduces saturation for a few colors. Acceptable
  visually; if not, lower `PAIR_CHROMA` to 0.15.
