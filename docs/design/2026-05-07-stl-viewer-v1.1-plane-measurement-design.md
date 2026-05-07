# STL Viewer v1.1 — Plane-aware measurement

**Status:** Design — not yet implemented
**Author:** Michał + Claude
**Date:** 2026-05-07
**Supersedes:** Extends `2026-05-06-stl-viewer-design.md` §12.1 (deferred plane-aware modes)
**Revision:** v3 (post second-round review)

## Revision history

- **v1 (initial)** — first draft from brainstorm decisions.
- **v2** — addresses Codex review (P1+P2 findings, see review file in
  same directory).
- **v3 (this)** — addresses second-round review:
  - `pl2pl` parallel-distance algorithm projects onto `nA` instead of
    `(nA + nB)/2`, fixing NaN for opposing cube faces where `nA + nB ≈ 0`
    despite `angleDeg = 0` (anti-parallel normals classified as parallel
    via `acos(|nA · nB|)`).
  - Banner state table now uses explicit priority ordering: error row
    takes precedence over `mode = off`, resolving the previous
    contradiction. Error banner gains an explicit dismiss button and
    auto-clears on next successful weld or file switch.
  - Toolbar mode buttons specified as lucide-first (custom SVG only as
    a fallback for slots where lucide composition doesn't read), 40 × 40
    hit target (was 32 × 32).
  - p2p `MeasureSummary` row reuses the existing
    `viewer3d.measure.label` key — no duplicate `row.p2p` key.

- **v2 baseline** — addresses Codex review:
  - `plane→plane` distance is now asymmetric (perpendicular for parallel,
    closest-clearance for non-parallel) with explicit labels (P1-1).
  - Welder produces a `sourceFaceIndex → weldedTriangleId` mapping so
    raycast hits resolve to the welded mesh (P1-2).
  - Worker contract: cloned ArrayBuffers only, never the live geometry
    buffer (P1-3).
  - File-switch lifecycle made explicit (P1-4).
  - Flood-fill rule compares each candidate triangle to the **seed
    normal**, not the chain neighbour, eliminating curvature creep (P2-5).
  - Single-triangle clusters render with a "weak" cue in the label (P2-6).
  - Reset View re-frames the camera and cancels in-flight selection but
    preserves completed measurements (P2-7).
  - Step banner state table added (P2-8).
  - Toolbar icons specified as custom inline SVGs with required
    `aria-label`, tooltip, `aria-pressed` (P2-9).
  - View-preset removal noted as deliberate accessibility regression
    with rationale (P2-10).
  - Welding is cancellable via Esc / mode change (P2-11).
  - `minVertexPair` threshold lowered to 1M pairs (P2-12).
  - i18n paths corrected to real layout
    (`apps/web/src/locales/{en,pl}.json`); concrete EN/PL strings
    listed (P2-13).
  - Theme token uses real `--color-viewer-*` namespace with HSL syntax
    and dark-mode counterpart (P2-14).
  - Visual test added as new file `viewer3d-measure-plane.spec.ts`
    matching existing per-feature split (P3-1).
  - Toolbar cleanup called out as a deliberate sub-slice (P3-2).

## 1. Goal

Extend the existing in-browser STL viewer with two new measurement modes
beside `point→point`:

- **`point→plane`** — click a flat surface (plane), click any point →
  perpendicular distance from point to the fitted plane, in mm.
- **`plane→plane`** — click two flat surfaces. Always reports both a
  distance value and the angle between fitted normals. The **distance
  semantics depend on the angle** (§6.4):
  - parallel-ish (angle ≤ 5°): perpendicular separation between the
    two centroids along the averaged normal — i.e. wall thickness;
  - non-parallel (angle > 5°): minimum vertex-pair distance between
    the two clusters — i.e. closest clearance between the selected
    surface patches.

  Labels honestly distinguish the two cases (`(parallel)` vs
  `(closest)`).

Side-quest cleanup: drop the four view presets (Front, Side, Top, Iso)
from the toolbar. STLs in the catalog are arranged for printing rather
than for natural viewing, so the presets confuse more than they help.
Reset View (re-frame to iso bbox) stays.

Backend is untouched. All work is client-side, on the same SoT API used
by v1. Visible to every catalog visitor (no privilege gate), same as v1.

## 2. Out of v1.1 scope

Out of v1.1 (kept in the v1 spec §12.2 as v1.2+):

- 3MF / STEP support
- Hole / diameter / circle measurement
- Vertex / edge snapping
- Persistent measurements per model
- Cross-section / clipping plane
- Annotations + screenshot with baked-in annotations
- Multi-mesh STLs (split + sub-selector)

## 3. UX

### 3.1 Mode selection

The toolbar gains three explicit mode buttons replacing the single
v1 ruler toggle. Final layout (left to right):

```
Reset | Wireframe | Camera | p2p | p2pl | pl2pl | 1° | Expand
```

The four view-preset buttons F, S, T, I are removed. Sub-slice rationale
in §11.6.

- All three mode buttons highlight when active. Click on the active
  mode button cancels into `off`.
- **Hit target: 40 × 40** (`size-10` in Tailwind). 32 × 32 was too
  compact for touch — bumping to 40 × 40 keeps comfortable mobile tap
  targets while staying tight on desktop. WCAG 2.5.5 minimum (24 × 24)
  is comfortably exceeded.
- **Glyphs: lucide-react first.** The plan slice picks final glyphs
  from lucide; reasonable starting candidates:
  - `point→point`: `Ruler` (already used in v1)
  - `point→plane`: `RulerDimensionLine` (or `Anchor` / `MoveDownRight`
    composed with a small plane badge)
  - `plane→plane`: `Layers` (or `Square` × 2 stacked)

  If no single lucide icon reads cleanly for `point→plane` or
  `plane→plane`, the implementation falls back to a custom inline SVG
  for that one slot only — but lucide is the default, never invent
  glyphs that overlap with existing ones.
- Required attributes regardless of glyph source:
  - `aria-pressed` reflects active state
  - `aria-label` from `viewer3d.measure.mode.{p2p,p2pl,pl2pl}`
  - Tooltip from the same key
- The `1°` badge is a small text-only button (font 0.7 rem, padding
  0.25 rem 0.4 rem; hit area still 40 × 40 via padding). Disabled when
  mode is `off` or `point-to-point`. Click opens `TolerancePopover`.

### 3.2 Click flow

| Mode | Click 1 | Click 2 | Output |
|---|---|---|---|
| `point→point` | point (raycast hit) | point | distance in mm (unchanged from v1) |
| `point→plane` | flat surface | any point | perpendicular distance in mm |
| `plane→plane` | flat surface | flat surface | `mm @ angle°` (parallel/closest, see §6.4) |

Convention: when a mode requires a plane, the **plane is always the
first click**. Reason: plane selection runs flood-fill (heavier) — we
want the user's attention on the work being done before they continue.

### 3.3 Step banner

A pill anchored above the canvas (`top-12 left-1/2 -translate-x-1/2`,
below the FileSelector in the modal; `top-3` in the inline view where
there is no FileSelector). Banner has `role="status"`,
`aria-live="polite"`. Visibility follows this state table:

Rules are checked top-down; the first matching row wins.

| Priority | `usePlanePrep.error` | `usePlanePrep.loading` | `state.mode` | `state.active.stage` | Banner |
|---|---|---|---|---|---|
| 1 | non-null | — | — | — | `welding_failed` (with explicit dismiss button — see below) |
| 2 | null | `true` | any plane mode | — | `step.preparing` |
| 3 | null | `false` | `off` | — | hidden |
| 4 | null | `false` | `point-to-point` | `empty` | `step.p2p_a` |
| 5 | null | `false` | `point-to-point` | `have-point` | `step.p2p_b` |
| 6 | null | `false` | `point-to-plane` | `empty` | `step.p2pl_plane` |
| 7 | null | `false` | `point-to-plane` | `have-plane` | `step.p2pl_point` |
| 8 | null | `false` | `plane-to-plane` | `empty` | `step.pl2pl_a` |
| 9 | null | `false` | `plane-to-plane` | `have-plane` | `step.pl2pl_b` |

**Error precedence (P1 from review v3):** an error survives a `mode → off`
revert, so the user sees *why* the plane mode dropped them out. The error
banner has an X dismiss button (`viewer3d.welding_failed.dismiss`,
`aria-label="Dismiss"`). It also clears automatically when:

- the user enters a plane mode that successfully completes welding (fresh
  `ready=true`), or
- the file is switched (`usePlanePrep.releaseAndReset`).

This makes the banner the single status surface — no separate toast layer.

i18n keys (PL + EN):

- `viewer3d.measure.step.p2p_a` — EN: "Click first point (1/2)"; PL: "Kliknij pierwszy punkt (1/2)"
- `viewer3d.measure.step.p2p_b` — EN: "Click second point (2/2)"; PL: "Kliknij drugi punkt (2/2)"
- `viewer3d.measure.step.p2pl_plane` — EN: "Click a flat surface (1/2)"; PL: "Kliknij płaską powierzchnię (1/2)"
- `viewer3d.measure.step.p2pl_point` — EN: "Click any point (2/2)"; PL: "Kliknij dowolny punkt (2/2)"
- `viewer3d.measure.step.pl2pl_a` — EN: "Click first flat surface (1/2)"; PL: "Kliknij pierwszą płaszczyznę (1/2)"
- `viewer3d.measure.step.pl2pl_b` — EN: "Click second flat surface (2/2)"; PL: "Kliknij drugą płaszczyznę (2/2)"
- `viewer3d.measure.step.preparing` — EN: "Preparing planes…"; PL: "Przygotowuję płaszczyzny…"
- `viewer3d.welding_failed` — EN: "Could not analyse mesh for plane selection."; PL: "Nie udało się przygotować mesha do wyboru płaszczyzn."

### 3.4 Cluster highlight and weak-cluster cue

Selected clusters render as a green semi-transparent overlay on top of
the original triangles (color from CSS token `--color-viewer-cluster`,
opacity 0.45). The overlay uses `polygonOffset` to avoid z-fighting
with the base mesh.

Cluster acceptance: any size ≥ 1 (so a single triangle on a curved
surface still counts — the user gets to see exactly what flood-fill
grabbed and adjust tolerance if it's not what they wanted).

Single-triangle clusters get a **weak cue** in the measurement label:
the `Plane` carries a `weak: boolean` flag set to `true` when
`triangleIds.length === 1`. The `MeasureSummary` row appends `(weak)`:

```
#3 — 12.4 mm @ 47° (closest, weak)
```

i18n:

- `viewer3d.measure.row.weak_suffix` — EN: " (weak)"; PL: " (słaba)"

### 3.5 Tolerance popover

A `Popover` (base-ui) anchored on the toolbar tolerance badge.

```
┌──────────────────────────────┐
│ Plane tolerance              │
│ ●━━━━━○─────────────  3.5°  │
│ Tight (CAD) ── Loose (scans) │
│                              │
│ Larger value = more triangles│
│ accepted as "coplanar".      │
└──────────────────────────────┘
```

- Slider range: `0.5° – 15°`, step `0.5°`. Default: `1°`.
- Persistence: tolerance persists within a viewer instance (open the
  modal, set tolerance, change file → tolerance preserved). Resets to
  default when the modal/inline closes.
- Live update during drag: dispatches `set-tolerance` on each pointer
  move, throttled to one dispatch per `requestAnimationFrame`. Final
  value is committed unthrottled on `pointerup`. If a cluster is
  currently active (`stage === "have-plane"`), it re-flood-fills from
  the stored seed triangle and the cluster overlay updates live.

### 3.6 MeasureSummary entries

Format follows the discriminated union (§5):

- `p2p`: `#1 — 60.5 mm`
- `p2pl`: `#2 — 12.4 mm (point → plane)`
- `pl2pl` parallel (≤ 5°): `#3 — 12.4 mm @ 1.2° (plane → plane, parallel)`
- `pl2pl` closest (> 5°): `#4 — 12.4 mm @ 47.0° (plane → plane, closest)`
- `pl2pl` approximate fallback (>1M pairs, see §6.4): suffix
  ` (≈)` is appended

Weak-cluster suffix `(weak)` from §3.4 chains after either label.

i18n keys:

- p2p row reuses the **existing** `viewer3d.measure.label`
  (`"{{value}} mm"`) — no new key needed. The first p2p still uses
  `viewer3d.measure.assumed` for the "assumed" suffix as in v1.
- `viewer3d.measure.row.p2pl` — EN/PL: `"{{value}} mm (point → plane)"` / `"{{value}} mm (punkt → płaszczyzna)"`
- `viewer3d.measure.row.pl2pl_parallel` — EN: `"{{value}} mm @ {{angle}}° (plane → plane, parallel)"`; PL: `"{{value}} mm @ {{angle}}° (płaszczyzna → płaszczyzna, równoległe)"`
- `viewer3d.measure.row.pl2pl_closest` — EN: `"{{value}} mm @ {{angle}}° (plane → plane, closest)"`; PL: `"{{value}} mm @ {{angle}}° (płaszczyzna → płaszczyzna, najbliższe)"`
- `viewer3d.measure.row.approximate_suffix` — EN: " (≈)"; PL: " (≈)"

Each completed measurement keeps its cluster overlay visible (so the
user can see what they measured against), tinted at 0.30 opacity to
distinguish from the active 0.45 cluster.

### 3.7 Esc cancel ladder (extension)

The v1 Esc ladder is extended to also unwind the welding state:

1. If `usePlanePrep.loading` is `true` → cancel the worker job
   (`worker.terminate()`), set `mode = "off"`, stop propagation.
2. Else if `state.active.stage !== "empty"` → cancel partial selection
   (clear `active`), stop propagation.
3. Else if `state.mode !== "off"` → set mode to `off`.
4. Else propagate Esc to the dialog (closes the modal).

### 3.8 Reset View behaviour (v1.1 change)

Reset View **re-frames the camera** to the iso preset and **cancels
the in-flight selection** (`active → { stage: "empty" }`). Completed
measurements **remain** — to clear them, the user uses the trash icon
in `MeasureSummary`. This is a deliberate change from v1 (where Reset
cleared everything): viewing operations should not destroy data.

## 4. Architecture

### 4.1 Module layout

New files in italics, modified files in bold:

```
viewer3d/
  Viewer3DCanvas.tsx            (modified: handle plane click, spinner state)
  Viewer3DInline.tsx            (modified: pass toleranceDeg)
  Viewer3DModal.tsx             (modified: as inline + StepBanner placement)
  controls/
    ViewToolbar.tsx             (modified: 3 mode buttons; remove F/S/T/I; keep Reset)
    StepBanner.tsx              (NEW)
    TolerancePopover.tsx        (NEW)
    MeasureSummary.tsx          (modified: render p2pl/pl2pl with parallel/closest/weak suffixes)
  hooks/
    usePlanePrep.ts             (NEW: trigger welding when plane mode entered, expose ready/loading/error/cancel)
  lib/
    parseStl.worker.ts          (unchanged)
    weldMesh.worker.ts          (NEW: welding off main thread)
    weldCache.ts                (NEW: refcounted cache parallel to stlCache)
    welder.ts                   (NEW: pure positions → WeldedMesh)
    camera.ts, readMeshTokens.ts, stlCache.ts (unchanged)
  measure/
    MeasureOverlay.tsx          (modified: render p2pl/pl2pl labels + assist lines)
    ClusterOverlay.tsx          (NEW: green-overlay mesh built from welded coords)
    fitting.ts                  (NEW: pure cluster → Plane)
    floodFill.ts                (NEW: pure welded + seed + tolerance → triangleIds[])
    geometry.ts                 (modified: distancePointToPlane, anglePlanes, perpendicularPlaneDistance, minVertexPairDistance)
    measureReducer.ts           (modified: new actions click-plane, set-tolerance, replace-active-plane)
  types.ts                      (modified)
  index.ts                      (no change)
```

Visual regression test (new file, paralleling existing per-feature
files):

```
apps/web/tests/visual/viewer3d-measure-plane.spec.ts   (NEW)
```

### 4.2 Worker decision and contract

- `parseStl.worker.ts` stays as-is.
- `weldMesh.worker.ts` runs welding only.
- Flood-fill, plane fitting, and distance/angle math run on the main
  thread (each is per-click, fast enough that worker overhead is
  unjustified).

For meshes with `vertexCount < 5000`, welding runs synchronously on
main thread (worker spawn + transfer cost ≈ 30 ms, welding itself ≈
5 ms — not worth it). Threshold is a small constant in `welder.ts`.

**Worker contract — buffer ownership (P1-3):** the welding worker
receives a **cloned** positions ArrayBuffer, never the live buffer
backing the rendered `BufferGeometry`. The hook `usePlanePrep` does:

```ts
const liveArray = geometry.getAttribute("position").array as Float32Array;
const cloned = liveArray.slice();              // new Float32Array
worker.postMessage({ positions: cloned.buffer }, [cloned.buffer]);
```

The clone is transferred (zero-copy after the slice) — main thread
keeps the live buffer; worker gets its own. Same pattern as
`parseStl.worker.ts` already uses on the return path.

### 4.3 Welder output contract (P1-2)

`welder.ts` (called from `weldMesh.worker.ts` and unit-tested directly):

```ts
type WeldedMesh = {
  positions: Float32Array;          // deduped vertex positions (length = 3 * vertexCount)
  indices: Uint32Array;             // length = 3 * triangleCount, indices into positions
  adjacency: Uint32Array;           // flat triangle-to-triangle map (see below)
  sourceToWelded: Uint32Array;      // length = sourceTriangleCount; sourceToWelded[i] = welded triangle id
  weldedToSourceStart: Uint32Array; // CSR-style: triangle i's source faces in [weldedToSourceStart[i], weldedToSourceStart[i+1])
  weldedToSource: Uint32Array;      // flat list of source face indices
};

export function weld(
  positions: Float32Array,
  bboxDiagonal: number,
): WeldedMesh;
```

`adjacency` layout: for each triangle `t`, three slots store the ids of
its edge-neighbours (or `0xFFFFFFFF` for boundary edges). Flat
`Uint32Array` of length `3 * triangleCount`.

The two source mappings (`sourceToWelded`, `weldedToSource{Start}`) make
two operations clean:

- **Raycast resolution.** R3F gives `e.faceIndex` from the **displayed**
  geometry. We resolve the welded triangle id via
  `sourceToWelded[e.faceIndex]` and pass it to flood-fill.
- **Cluster overlay rendering.** `ClusterOverlay` renders a separate
  `BufferGeometry` from the welded `positions` and the welded triangle
  ids — it does not touch the displayed geometry. This decouples the
  overlay from the source mesh's tessellation and avoids any concern
  about non-indexed-vs-indexed mismatch.

Quantization (used inside welder): `granularity = max(bboxDiagonal × 1e-6, 1e-5)`.
Floor at 1e-5 mm protects against degenerate tiny meshes.

### 4.4 Cache lifecycle and file switch (P1-4)

`weldCache` is parallel to `stlCache` from v1: same key (mesh URL/ID),
same refcount semantics, dispose freed at zero refcount.

`usePlanePrep` is the only consumer. When `state.mode` flips to
`point-to-plane` or `plane-to-plane`:

1. Look up `weldCache` for current mesh key.
2. Hit: ref++, set `ready=true` immediately.
3. Miss: spawn welding job in `weldMesh.worker.ts`, post the cloned
   positions buffer (transferable). Set `loading=true`, `ready=false`.
   While loading, banner shows `step.preparing`; mode buttons are
   visually pressed but disabled (cancellation goes through Esc — §3.7
   — or by clicking a different mode).
4. On worker reply: store in cache, ref++, set `ready=true`,
   `loading=false`.
5. On error reply (or cancellation): set `error: "weld-failed"`, mode
   reverts to `off`, banner shows `viewer3d.welding_failed`.
   Point→point still works (does not need welding).

**File switch policy** (P1-4): when `activeId` changes,
`Viewer3DCanvas` invokes `usePlanePrep.releaseAndReset(prevKey)` which:

- ref-- on `weldCache[prevKey]` (cache disposes if refcount hits zero)
- dispatches `clear` to drop both `state.active` and `state.completed`
  (these reference vertices in the previous welded mesh and would
  render against the wrong geometry otherwise)
- preserves `state.toleranceDeg` and `state.mode` (user intent —
  "I'm measuring planes, just on a different file now")
- if the new mode requires welding, kicks off a fresh welding job for
  the new mesh

This keeps the lifecycle simple: completed measurements live for the
duration of one (mesh, viewer-instance) pair.

## 5. Types

```ts
// types.ts (excerpt)

export type MeasureMode =
  | "off"
  | "point-to-point"
  | "point-to-plane"
  | "plane-to-plane";

export type Plane = {
  centroid: Vector3;          // area-weighted centroid of the cluster
  normal: Vector3;            // unit length, area-weighted average normal
  triangleIds: number[];      // indices into welded mesh, for highlight
  seedTriangleId: number;     // for live tolerance update (re-flood from seed)
  weak: boolean;              // true when triangleIds.length === 1
};

export type Pl2plKind = "parallel" | "closest";

export type Measurement =
  | { kind: "p2p";   id: string; a: Vector3; b: Vector3; distanceMm: number }
  | { kind: "p2pl";  id: string; point: Vector3; plane: Plane;
        distanceMm: number; weakA: boolean }
  | { kind: "pl2pl"; id: string;
        planeA: Plane; planeB: Plane;
        distanceMm: number;          // perpendicular for parallel, vertex-pair for closest
        angleDeg: number;            // acos(|nA · nB|), 0–90
        pl2plKind: Pl2plKind;        // discriminator for label
        approximate: boolean;        // true if vertex-pair fell back to centroid offset
        weakA: boolean;
        weakB: boolean };

export type MeasureActiveStage =
  | { stage: "empty" }
  | { stage: "have-point"; point: Vector3 }
  | { stage: "have-plane"; plane: Plane };

export type MeasureState = {
  mode: MeasureMode;
  toleranceDeg: number;        // 1° default, persistent within instance
  active: MeasureActiveStage;
  completed: Measurement[];
};
```

Reducer actions extend `MeasureAction`:

- `set-mode` (existing) — resets `active` to `{ stage: "empty" }`.
- `click-mesh` (existing, semantics extended) — used for point picks
  in `point-to-point` (both clicks) and `point-to-plane` (second click).
- `click-plane` (NEW) — payload `{ plane: Plane }`. Dispatched by the
  canvas after running `floodFill` + `fitting`. State transitions:
  `empty → have-plane`; `have-plane (plane→plane) → completion`.
- `set-tolerance` (NEW) — payload `{ value: number }`. Reducer clamps
  to `[0.5, 15]`. Pure: only updates `state.toleranceDeg`. The
  re-flood-fill is a side effect handled by a hook (§6.3).
- `replace-active-plane` (NEW) — payload `{ plane: Plane }`. Used by
  the live-tolerance hook to swap the cluster while keeping the seed
  triangle id (already on the previous plane). Only valid in
  `stage === "have-plane"`.
- `clear`, `cancel-active` — unchanged.

## 6. Data flow

### 6.1 Welding pipeline (one-time per mesh, on plane-mode entry)

```
ViewToolbar: user clicks point→plane or plane→plane
  ↓
measureReducer: set-mode → state.mode requires welded
  ↓
usePlanePrep: weldCache lookup → miss
  ↓
clone positions buffer (slice) →
weldMesh.worker.ts: postMessage({ positions: cloned }, [cloned])
   │ welder.weld(positions, bboxDiagonal)
   │   - quantize per max(diagonal × 1e-6, 1e-5)
   │   - dedupe vertices, build positions + indices
   │   - build edge-adjacency (edge → 2 triangle ids; boundary → 0xFFFFFFFF)
   │   - build sourceToWelded + weldedToSource{Start} mappings
   └→ postMessage(payload, [transferable buffers])
  ↓
weldCache.set(key, payload); ref++
  ↓
usePlanePrep: ready=true, spinner hides
```

For `vertexCount < 5000`, the same logic runs synchronously on the main
thread — no worker round-trip, no spinner.

### 6.2 Click on plane (per click, after `ready`) (P1-2, P2-5)

```
Canvas onClick: raycast hit → e.faceIndex (in DISPLAYED geometry)
  ↓
weldedTriangleId = weldedMesh.sourceToWelded[e.faceIndex]
  ↓
seedNormal = computeTriangleNormal(weldedMesh, weldedTriangleId)
  ↓
floodFill(weldedMesh, weldedTriangleId, seedNormal, state.toleranceDeg)
   │ BFS on adjacency. Acceptance rule (P2-5):
   │   acos(|n_candidate · seedNormal|) ≤ toleranceDeg
   │ — candidate is compared to the SEED, not the chain neighbour.
   │   This eliminates curvature creep on cylinders/fillets.
   └→ triangleIds[]
  ↓
fitting(weldedMesh, triangleIds): Plane {
   centroid: area-weighted,
   normal: area-weighted (unit length),
   triangleIds, seedTriangleId,
   weak: triangleIds.length === 1,
}
  ↓
dispatch click-plane({ plane })
```

`ClusterOverlay` subscribes to `state.active.stage === "have-plane"`
and to each completed measurement's planes; it renders the green
overlay built from `weldedMesh.positions` indexed by
`plane.triangleIds`. The overlay never touches the displayed source
geometry.

### 6.3 Live tolerance update

```
TolerancePopover slider drag:
  pointermove: dispatch set-tolerance({ value }) (raf-throttled)
  pointerup:   dispatch set-tolerance({ value }) (final, unthrottled)
  ↓
measureReducer: state.toleranceDeg = value (pure)
  ↓
useEffect in canvas/hook layer (deps: [toleranceDeg, active.stage]):
  if active.stage === "have-plane":
    plane = floodFill + fitting from active.plane.seedTriangleId
            with the new toleranceDeg, comparing to seed normal
    dispatch replace-active-plane({ plane })
  ↓
ClusterOverlay re-renders with new triangleIds[]
```

If `stage === "have-point"`, the tolerance change is a no-op for the
live overlay.

### 6.4 Completion (distance + angle compute) (P1-1, P2-12)

On the second valid click:

| Mode | Distance | Extra |
|---|---|---|
| `p2p` | `a.distanceTo(b)` | — |
| `p2pl` | `\|(point − plane.centroid) · plane.normal\|` | — |
| `pl2pl` | see below | `acos(\|nA · nB\|) × 180/π` |

**`plane→plane` distance algorithm:**

```
const angleDeg = acos(|nA · nB|) × 180/π;            // 0–90
if (angleDeg ≤ 5) {
  // parallel — wall thickness.
  // CAUTION: opposing cube faces give nA and nB pointing in OPPOSITE
  // directions even though they represent the same plane orientation
  // (angleDeg = 0 because we used acos(|nA · nB|)). If we naïvely averaged
  // them, (nA + nB) ≈ 0 and normalize() would return NaN/zero.
  // We therefore project onto nA only — for parallel planes the absolute
  // projection is identical along either normal.
  const distance = |(centroidA − centroidB) · nA|;
  emit { kind: "pl2pl", pl2plKind: "parallel", distance, angleDeg, approximate: false };
} else {
  // non-parallel — closest clearance between selected patches
  const pairCount = uniqueVertexCount(A) × uniqueVertexCount(B);
  if (pairCount ≤ 1_000_000) {
    const distance = minVertexPairDistance(A, B);
    emit { kind: "pl2pl", pl2plKind: "closest", distance, angleDeg, approximate: false };
  } else {
    // fallback — too expensive to enumerate
    const distance = centroidA.distanceTo(centroidB);
    emit { kind: "pl2pl", pl2plKind: "closest", distance, angleDeg, approximate: true };
  }
}
```

Threshold is 1M pairs (P2-12; was 50M in v1 of this spec, lowered
because 5M-pair main-thread compute already produces visible jank).
For typical clusters (≤500 unique vertices each, ≤250k pairs) the full
computation finishes in <30 ms. The fallback at >1M pairs trades
precision for responsiveness; the `(≈)` suffix makes the trade
visible.

The new `Measurement` is appended to `state.completed`; `active` resets
to `{ stage: "empty" }`. The user can take more measurements without
leaving the mode.

## 7. Performance, error handling

### 7.1 Performance budget

| Operation | Cost (typical) | Cost (worst before fallback) | Where |
|---|---|---|---|
| Welding | 50 ms (10k tri) | 1 s (1M tri) | Worker (or main if <5k verts) |
| Flood-fill BFS | <10 ms | ~50 ms | Main |
| Plane fitting (area-weighted) | <5 ms | <20 ms | Main |
| `pl2pl` distance — parallel | <1 ms | <1 ms | Main |
| `pl2pl` distance — closest | <30 ms | ~100 ms (1M pairs) | Main |
| `pl2pl` distance — fallback (centroid) | <1 ms | <1 ms | Main |
| Live slider re-flood-fill | <50 ms | ~200 ms | Main, raf-throttled |

### 7.2 Error handling

- **Welding error in worker** — `usePlanePrep` sets `error:"weld-failed"`,
  mode reverts to `off`, banner shows `viewer3d.welding_failed`.
  Point→point still works.
- **Welding cancelled by user** (Esc / mode change while loading) —
  worker terminated, no error banner; mode is whatever the user just
  set (typically `off` or back to `point-to-point`).
- **Click misses mesh** — raycast returns null, no dispatch (existing
  v1 behaviour, unchanged).
- **`sourceToWelded[faceIndex] === undefined`** — should not happen
  (every source face maps somewhere); defensive guard logs to GlitchTip
  and ignores the click.
- **Tolerance NaN / out-of-range** — reducer clamps to `[0.5, 15]`.
- **Flood-fill returns 0 triangles** — impossible (seed counts itself).
  Defensive guard in `fitting()`: throw if input empty.
- **`pl2pl` huge clusters** — fallback to centroid distance, see §6.4.
- **Mesh > 5M triangles** — welding may take seconds. Spinner is the
  only mitigation; we do not pre-emptively block.

### 7.3 Quantization edge case

`granularity = max(bboxDiagonal × 1e-6, 1e-5)` — for a 0.5 mm part,
`diagonal × 1e-6` would be 5e-10 mm (sub-float32). The 1e-5 mm floor
keeps things sane. Documented as known limitation: tiny meshes may
not weld optimally; the catalog lives in 10–500 mm range.

## 8. i18n and theming

### 8.1 i18n location and keys

Translations live in `apps/web/src/locales/en.json` and
`apps/web/src/locales/pl.json` (flat-key JSON, dot-separated keys —
matching the existing project layout, **not** the
`i18n/locales/{lang}/translation.json` convention).

New keys (concrete strings — implementer must not change without
coordinating):

```jsonc
{
  "viewer3d.measure.step.p2p_a": "Click first point (1/2)",
  "viewer3d.measure.step.p2p_b": "Click second point (2/2)",
  "viewer3d.measure.step.p2pl_plane": "Click a flat surface (1/2)",
  "viewer3d.measure.step.p2pl_point": "Click any point (2/2)",
  "viewer3d.measure.step.pl2pl_a": "Click first flat surface (1/2)",
  "viewer3d.measure.step.pl2pl_b": "Click second flat surface (2/2)",
  "viewer3d.measure.step.preparing": "Preparing planes…",
  "viewer3d.welding_failed": "Could not analyse mesh for plane selection.",

  "viewer3d.measure.row.p2pl": "{{value}} mm (point → plane)",
  "viewer3d.measure.row.pl2pl_parallel": "{{value}} mm @ {{angle}}° (plane → plane, parallel)",
  "viewer3d.measure.row.pl2pl_closest": "{{value}} mm @ {{angle}}° (plane → plane, closest)",
  "viewer3d.measure.row.weak_suffix": " (weak)",
  "viewer3d.measure.row.approximate_suffix": " (≈)",

  "viewer3d.measure.tolerance.label": "Plane tolerance",
  "viewer3d.measure.tolerance.tight": "Tight (CAD)",
  "viewer3d.measure.tolerance.loose": "Loose (scans)",
  "viewer3d.measure.tolerance.help": "Larger values accept more triangles as coplanar.",

  "viewer3d.measure.mode.p2p": "Point-to-point distance",
  "viewer3d.measure.mode.p2pl": "Point-to-plane distance",
  "viewer3d.measure.mode.pl2pl": "Plane-to-plane distance and angle"
}
```

PL counterparts (in `pl.json`):

```jsonc
{
  "viewer3d.measure.step.p2p_a": "Kliknij pierwszy punkt (1/2)",
  "viewer3d.measure.step.p2p_b": "Kliknij drugi punkt (2/2)",
  "viewer3d.measure.step.p2pl_plane": "Kliknij płaską powierzchnię (1/2)",
  "viewer3d.measure.step.p2pl_point": "Kliknij dowolny punkt (2/2)",
  "viewer3d.measure.step.pl2pl_a": "Kliknij pierwszą płaszczyznę (1/2)",
  "viewer3d.measure.step.pl2pl_b": "Kliknij drugą płaszczyznę (2/2)",
  "viewer3d.measure.step.preparing": "Przygotowuję płaszczyzny…",
  "viewer3d.welding_failed": "Nie udało się przygotować mesha do wyboru płaszczyzn.",

  "viewer3d.measure.row.p2pl": "{{value}} mm (punkt → płaszczyzna)",
  "viewer3d.measure.row.pl2pl_parallel": "{{value}} mm @ {{angle}}° (płaszczyzna → płaszczyzna, równoległe)",
  "viewer3d.measure.row.pl2pl_closest": "{{value}} mm @ {{angle}}° (płaszczyzna → płaszczyzna, najbliższe)",
  "viewer3d.measure.row.weak_suffix": " (słaba)",
  "viewer3d.measure.row.approximate_suffix": " (≈)",

  "viewer3d.measure.tolerance.label": "Tolerancja płaszczyzny",
  "viewer3d.measure.tolerance.tight": "Ścisła (CAD)",
  "viewer3d.measure.tolerance.loose": "Luźna (skany)",
  "viewer3d.measure.tolerance.help": "Większa wartość = więcej trójkątów uznanych za współpłaszczyznowe.",

  "viewer3d.measure.mode.p2p": "Pomiar punkt-do-punktu",
  "viewer3d.measure.mode.p2pl": "Pomiar punkt-do-płaszczyzny",
  "viewer3d.measure.mode.pl2pl": "Pomiar płaszczyzna-do-płaszczyzny (dystans + kąt)"
}
```

Existing `viewer3d.measure.assumed` stays — applies only to `p2p`.

### 8.2 Theme tokens

`apps/web/src/styles/theme.css` `@theme` blocks (light + dark) gain a
new token consistent with the existing `--color-viewer-*` namespace:

```css
/* light */
--color-viewer-cluster: hsl(142 71% 45%);   /* emerald-ish */

/* dark */
--color-viewer-cluster: hsl(142 71% 55%);
```

Read via `readMeshTokens()` (same pattern as `--color-viewer-mesh-paint`
and `--color-viewer-measure`).

Active and completed clusters share the same tint but different
opacities (active: 0.45, completed: 0.30) — see §3.6.

## 9. Accessibility

- `StepBanner`: `role="status"`, `aria-live="polite"`. Stage transitions
  are announced.
- `TolerancePopover` slider: `aria-label`, `aria-valuenow/min/max` (base-ui
  Slider provides these out of the box).
- Toolbar mode buttons:
  - `aria-pressed` reflects active state.
  - `aria-label` from `viewer3d.measure.mode.{p2p,p2pl,pl2pl}`.
  - Tooltip uses the same string (base-ui `Tooltip` wrapping the icon
    button).
  - 32 × 32 hit target, focus ring follows the project's `:focus-visible`
    convention.
- Esc cancel ladder (§3.7) keeps the v1 "back out of the smallest
  in-flight operation" feel and now also handles welding cancellation.
- Keyboard cannot click on geometry (raycast needs a screen position).
  This is a known limitation of WebGL viewers in general.

**Accepted regression — view-preset removal (P2-10).** v1 had
F/S/T/I as a partial keyboard-accessibility fallback (a keyboard user
could at least change camera angle). v1.1 drops them per Michał's
explicit decision (the presets are misleading on print-oriented STLs:
"Top" of a print is rarely the top of the part as designed). Reset View
remains keyboard-accessible. We accept this regression as a trade for
the clearer toolbar; if it bites in practice, follow-up could add an
"orbit by N degrees" keyboard shortcut.

## 10. Testing

### 10.1 Unit tests (vitest)

| File | Coverage |
|---|---|
| `lib/welder.test.ts` | Cube STL → 8 unique vertices, every edge shared by exactly 2 triangles. `sourceToWelded` round-trips: `welded.indices[3*sourceToWelded[i]..]` form a triangle that was source face `i` (modulo welding). Degenerates: single triangle, two disconnected triangles, triangle with duplicate vertex. |
| `measure/floodFill.test.ts` | Cube face seed → cluster size 2; cylinder 256-seg with tolerance 1°/2°/5° → cluster size grows monotonically; gentle-curvature creep test: a tessellated dome where adjacent triangles are 0.8° apart but the full surface curves through 30° — at tolerance 1° flood-fill must NOT walk the whole dome (because we compare to seed, P2-5). |
| `measure/fitting.test.ts` | Cube face cluster: normal aligned with axis ±epsilon; centroid in face centre; area-weighted vs unweighted on uneven tessellation. `weak` flag set when `triangleIds.length === 1`. |
| `measure/geometry.test.ts` (extension) | `distancePointToPlane` known cases; `anglePlanes` parallel/perpendicular/anti-parallel; `perpendicularPlaneDistance` (used in pl2pl-parallel) on parallel walls of known thickness; `minVertexPairDistance` simulated small clusters. |
| `measure/measureReducer.test.ts` (extension) | `set-mode` resets active; `click-mesh` in `have-plane` (p2pl) creates measurement; `set-tolerance` clamps to [0.5,15]; `replace-active-plane` keeps `seedTriangleId`; `pl2pl` completion at angle 0° uses parallel branch, at 47° uses closest branch (asserts on `pl2plKind`). |

Fixtures:

- `apps/web/tests/visual/fixtures/cube.stl` — exists from v1.
- `apps/web/tests/visual/fixtures/cylinder-256seg.stl` — NEW. Built by
  `apps/web/tests/visual/fixtures/build-cylinder.ts` (parallel to
  `build-cube.ts`), 256 axial segments, ~512 triangles, axis = +Z.
- `apps/web/tests/visual/fixtures/dome-tessellated.stl` — NEW.
  Hemispherical cap with controlled per-step curvature for the creep
  test. Built by `build-dome.ts`.

### 10.2 Visual regression (Playwright)

NEW file `apps/web/tests/visual/viewer3d-measure-plane.spec.ts`
(matching the existing per-feature split — `viewer3d-measure-pp.spec.ts`,
`viewer3d-modal-open.spec.ts`, etc.):

| Snapshot | Setup |
|---|---|
| `viewer3d-mode-buttons-p2pl` | Modal open on cube STL, click `point→plane` button |
| `viewer3d-cluster-overlay` | As above, click on a cube face — green overlay over 2-tri cluster |
| `viewer3d-step-banner-p2pl` | After plane click — banner shows "Click any point (2/2)" |
| `viewer3d-pl2pl-parallel` | Plane→plane mode, click two opposite cube faces — measurement reads `… mm @ 0.0° (… parallel)` |
| `viewer3d-pl2pl-closest` | Plane→plane mode, click two perpendicular cube faces — measurement reads `… mm @ 90.0° (… closest)` |
| `viewer3d-tolerance-popover` | Click tolerance badge — popover open with slider at 1° |

Stub helpers (`stubViewerStl`, `stubViewerModelDetail`) already exist
from v1 and are reused unchanged.

### 10.3 Manual smoke (HARD GATE — required before merge)

On real catalog STLs from `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/`:

- [ ] `point→plane`: measure from a wall to a corner — sane number
- [ ] `plane→plane` on parallel walls of a 5 mm box → ~5.0 mm @ 0° (parallel)
- [ ] `plane→plane` on a wall + a slanted fillet → distance + non-zero
      angle, label says `closest`
- [ ] Cylindrical part: click flat cap → small cluster; click cylinder
      side at tolerance 1° → small cluster (no creep, P2-5); at 5° →
      somewhat larger but bounded, normal still seed-aligned
- [ ] Tolerance slider mid-flow: click plane 1, drag slider — cluster
      grows / shrinks live
- [ ] Esc ladder: during welding spinner, press Esc → mode reverts
      cleanly; with active partial, Esc → cancel-active; with mode on
      empty, Esc → mode off; with everything off, Esc → modal closes
- [ ] **Reset View preserves completed measurements** (v1.1 change) —
      take 3 measurements, click Reset → camera reframes, completed list
      stays, in-flight cleared
- [ ] File switch with measurements: take 1 measurement on file A,
      switch to file B → measurements clear, mode preserved, welding
      job kicks off for B
- [ ] Mobile (touch): tap-tap for plane→plane on cube, narrow viewport
      — banner readable, cluster visible
- [ ] Welding spinner on a >100 k-tri STL: visible <1.5 s
- [ ] **Buffer-detach safety check** (P1-3): enter plane mode on a
      large STL while watching the rendered mesh — mesh must not
      flicker / disappear / glitch during welding (regression guard
      against accidentally transferring the live buffer)

## 11. Risks and open questions

### 11.1 Quantization on tiny meshes

Floor at `1e-5 mm` mitigates. If a real catalog STL ever fails to weld
correctly because of this, revisit.

### 11.2 Worker overhead on small meshes

Mitigated: <5k vertices welds on main thread.

### 11.3 Live slider perf on huge clusters

If `re-floodFill` lags on real files, switch from raf-throttle to
debounce (~100 ms). Decision deferred to first measurement.

### 11.4 `minVertexPairDistance` worst case

Fallback to centroid offset with `approximate=true` flag at >1M pairs.
Spatial-hash / KD-tree improvement is a v1.2 follow-up.

### 11.5 Discriminated `Measurement` union vs serialization

v1.1 does not persist measurements, so this is academic. If v1.2+ adds
persistence (URL share, localStorage), custom serde will be needed.

### 11.6 Toolbar cleanup as deliberate sub-slice (P3-2)

Removing F/S/T/I is **not** a casual cleanup — it has accessibility
impact (§9 accepted regression) and visual snapshot impact. The
implementation plan must call this out as its own sub-slice with its
own commit, so it can be reverted independently if it turns out to
hurt more than it helps.

### 11.7 `set-mode` discards partial selection silently

If a user with one click in `point→point` switches to `plane→plane`,
the partial point is lost. YAGNI on a confirm dialog until somebody
complains.

### 11.8 Welding-cancellation race

If the user enters plane mode, then quickly exits before welding
finishes, then enters again, we could in theory observe the worker
reply for the first job arriving after the second job started.
Mitigation: each job carries an incrementing `jobId`; replies whose
`jobId` does not match the current one are discarded.

## 12. Plan handoff

Implementation plan to be produced under
`docs/plans/2026-05-07-stl-viewer-v1.1-plane-measurement-plan.md` via
the `superpowers:writing-plans` skill. Sub-slice ordering (each its
own commit, TDD where applicable):

1. Types + reducer extensions + reducer tests
2. `welder.ts` (pure) + tests; `weldMesh.worker.ts` wrapper
3. `weldCache.ts` + `usePlanePrep` (integration with Viewer3DCanvas)
4. `floodFill.ts` (pure, seed-comparison rule) + tests, including
   creep guard
5. `fitting.ts` (pure, area-weighted, weak flag) + tests
6. `geometry.ts` extensions (`distancePointToPlane`, `anglePlanes`,
   `perpendicularPlaneDistance`, `minVertexPairDistance`) + tests
7. `ClusterOverlay.tsx` (R3F mesh from welded coords) + visual snap
8. `StepBanner.tsx` + state-table-driven render + visual snap
9. `TolerancePopover.tsx` (base-ui Popover + Slider, raf throttling) + visual snap
10. `ViewToolbar.tsx`: REMOVE F/S/T/I (own commit, P3-2 sub-slice);
    ADD three mode buttons + tolerance badge (own commit)
11. `MeasureSummary.tsx` extensions (parallel/closest/weak/approximate suffixes)
12. `MeasureOverlay.tsx` extensions (p2pl + pl2pl labels, assist lines)
13. `Viewer3DCanvas.tsx` integration: raycast → welded id, dispatching
    plane clicks, Esc-ladder welding cancel, Reset preserves completed
14. i18n key population (en.json + pl.json)
15. Theme token `--color-viewer-cluster` (light + dark)
16. Visual snapshot rebake + manual smoke gate
