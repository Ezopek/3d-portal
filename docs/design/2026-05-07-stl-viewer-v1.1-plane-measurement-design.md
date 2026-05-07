# STL Viewer v1.1 — Plane-aware measurement

**Status:** Design — not yet implemented
**Author:** Michał + Claude
**Date:** 2026-05-07
**Supersedes:** Extends `2026-05-06-stl-viewer-design.md` §12.1 (deferred plane-aware modes)

## 1. Goal

Extend the existing in-browser STL viewer with two new measurement modes
beside `point→point`:

- **`point→plane`** — click a flat surface (plane), click any point →
  perpendicular distance from point to the fitted plane, in mm.
- **`plane→plane`** — click a flat surface, click another flat surface →
  combined readout `12.4 mm @ 87.3°` where the distance is the minimum
  vertex-pair distance between the two clusters and the angle is between
  their fitted normals.

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
v1 ruler toggle. Layout (left to right):

```
Reset | Wireframe | Camera | ·−· (p2p) | ·−▭ (p2pl) | ▭−▭ (pl2pl) | 1° | Expand
```

(The four view-preset buttons F, S, T, I are removed — see §1.)

- All three mode buttons highlight when active. Click on the active
  mode button cancels into `off`.
- The `1°` badge is a small text-only button showing current tolerance.
  Disabled when mode is `off` or `point-to-point` (tolerance only
  matters for plane-aware modes). Click opens `TolerancePopover`.

### 3.2 Click flow

| Mode | Click 1 | Click 2 | Output |
|---|---|---|---|
| `point→point` | point (raycast hit) | point | distance in mm (unchanged from v1) |
| `point→plane` | flat surface | any point | perpendicular distance in mm |
| `plane→plane` | flat surface | flat surface | `mm @ angle°` |

Convention: when a mode requires a plane, the **plane is always the
first click**. Reason: plane selection runs flood-fill (heavier) — we
want the user's attention on the work being done before they continue.

### 3.3 Step banner

A pill anchored above the canvas (`top-12 left-1/2 -translate-x-1/2`,
below the FileSelector in the modal; `top-3` in the inline view where
there is no FileSelector). Visible only while a partial measurement is
in flight.

i18n keys (PL + EN, `apps/web/src/i18n/locales/{pl,en}/translation.json`):

- `viewer3d.measure.step.p2p_a` — "Click first point (1/2)"
- `viewer3d.measure.step.p2p_b` — "Click second point (2/2)"
- `viewer3d.measure.step.p2pl_plane` — "Click a flat surface (1/2)"
- `viewer3d.measure.step.p2pl_point` — "Click any point (2/2)"
- `viewer3d.measure.step.pl2pl_a` — "Click first flat surface (1/2)"
- `viewer3d.measure.step.pl2pl_b` — "Click second flat surface (2/2)"
- `viewer3d.measure.step.preparing` — "Preparing planes…" (welding spinner)

Banner has `role="status"`, `aria-live="polite"` so screen readers
announce stage transitions.

### 3.4 Cluster highlight

Selected clusters render as a green semi-transparent overlay on top of
the original triangles (color from CSS token `--color-viewer-cluster`,
default `#48bb78`, opacity 0.45). The overlay uses `polygonOffset` to
avoid z-fighting with the base mesh.

This is the v1.1 answer to the v1-spec question "size < 3 triangles is
too strict": we accept any cluster of size ≥ 1 (so a single triangle
on a curved surface is still a "plane" — the user gets to see exactly
what flood-fill grabbed and adjust tolerance if it's not what they
wanted).

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
  move, but throttled to one dispatch per `requestAnimationFrame`. If a
  cluster is currently active (`stage === "have-plane"`), it
  re-flood-fills from the stored seed triangle and the cluster overlay
  updates live. Final value is committed unthrottled on `pointerup`.

### 3.6 MeasureSummary entries

Format follows the discriminated union (§5):

- `p2p`: `#1 — 60.5 mm`
- `p2pl`: `#2 — 12.4 mm (point → plane)`
- `pl2pl`: `#3 — 12.4 mm @ 87.3° (plane → plane)`

i18n keys:

- `viewer3d.measure.row.p2p` — `"{{value}} mm"`
- `viewer3d.measure.row.p2pl` — `"{{value}} mm (point → plane)"`
- `viewer3d.measure.row.pl2pl` — `"{{value}} mm @ {{angle}}° (plane → plane)"`

Each completed measurement keeps its cluster overlay visible (so the
user can see what they measured against).

### 3.7 Esc cancel ladder (extension)

The v1 Esc ladder is extended:

1. If `state.active.stage !== "empty"` → cancel partial selection (clear
   `active`), stop propagation.
2. Else if `state.mode !== "off"` → set mode to `off`.
3. Else propagate Esc to the dialog (closes the modal).

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
    MeasureSummary.tsx          (modified: render p2pl/pl2pl)
  hooks/
    usePlanePrep.ts             (NEW: trigger welding when plane mode entered, expose ready/loading/error)
  lib/
    parseStl.worker.ts          (unchanged)
    weldMesh.worker.ts          (NEW: welding off main thread)
    weldCache.ts                (NEW: refcounted cache parallel to stlCache)
    welder.ts                   (NEW: pure positions → welded {positions, indices, adjacency})
    camera.ts, readMeshTokens.ts, stlCache.ts (unchanged)
  measure/
    MeasureOverlay.tsx          (modified: render p2pl/pl2pl labels + assist lines)
    ClusterOverlay.tsx          (NEW: green-overlay mesh for selected cluster)
    fitting.ts                  (NEW: pure cluster → Plane)
    floodFill.ts                (NEW: pure welded + seed + tolerance → triangleIds[])
    geometry.ts                 (modified: distancePointToPlane, anglePlanes, minVertexPairDistance)
    measureReducer.ts           (modified: new actions click-plane, set-tolerance, replace-active-plane)
  types.ts                      (modified)
  index.ts                      (no change)
```

### 4.2 Worker decision

- `parseStl.worker.ts` stays as-is (STL parse only, unchanged from v1).
- `weldMesh.worker.ts` is new and runs welding only.
- Flood-fill, plane fitting, and distance/angle math run on the main
  thread (each is per-click, O(|cluster|) or O(N) at worst, fast enough
  to avoid worker-overhead on every interaction).

For meshes with `vertexCount < 5000`, welding runs synchronously on the
main thread (worker spawn + transfer cost ≈ 30 ms, welding itself ≈
5 ms — not worth it). Threshold is a small constant in `welder.ts`.

### 4.3 Cache lifecycle

`weldCache` is parallel to `stlCache` from v1: same key (mesh URL/ID),
same refcount semantics, dispose freed at zero refcount. The cache
stores welded data as transferable `ArrayBuffer`s (positions, indices,
flat adjacency map).

`usePlanePrep` is the only consumer. When mode flips to `point-to-plane`
or `plane-to-plane`:

1. Check `weldCache` for current mesh key.
2. Hit: ref++, set `ready=true` immediately.
3. Miss: spawn welding job in `weldMesh.worker.ts`, post the positions
   buffer (transferable). Set `loading=true`, `ready=false`. While
   loading, the StepBanner shows `viewer3d.measure.step.preparing` and
   the plane mode buttons are visually pressed but disabled.
4. On worker reply: store in cache, ref++, set `ready=true`,
   `loading=false`.
5. On error reply: set `error: "weld-failed"`, mode auto-reverts to
   `off`, banner shows `viewer3d.welding_failed`. Point→point still
   works (does not need welding).

When the viewer unmounts or the mesh changes (file switch), ref-- on
the previous mesh; cache disposes when refcount hits zero.

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
};

export type Measurement =
  | { kind: "p2p";   id: string; a: Vector3; b: Vector3; distanceMm: number }
  | { kind: "p2pl";  id: string; point: Vector3; plane: Plane; distanceMm: number }
  | { kind: "pl2pl"; id: string;
        planeA: Plane; planeB: Plane;
        distanceMm: number;          // min vertex-pair between clusters
        angleDeg: number;            // acos(|nA · nB|), 0–90
        approximate?: boolean };     // true if minVertexPair fell back to centroids

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
  the live-tolerance hook to swap the cluster while keeping
  `seedTriangleId`. Only valid in `stage === "have-plane"`.
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
weldMesh.worker.ts: postMessage(positions ArrayBuffer)
   │ quantize per bbox.diagonal × 1e-6 (floor 1e-5 mm)
   │ deduplicate vertices, build positions + indices
   │ build edge-adjacency map (edge → 2 triangle ids)
   └→ postMessage({ positions, indices, adjacency })
  ↓
weldCache.set(key, payload), ref++
  ↓
usePlanePrep: ready=true, spinner hides
```

For `vertexCount < 5000`, the same logic runs synchronously on main
thread — no worker round-trip, no spinner.

### 6.2 Click on plane (per click, after `ready`)

```
Canvas onClick: raycast hit → faceIndex (triangle in welded mesh)
  ↓
floodFill(welded, seedTriangleId, state.toleranceDeg)
   │ BFS on adjacency: expand to neighbour iff
   │   acos(|n_self · n_neighbour|) ≤ toleranceDeg
   └→ triangleIds[]
  ↓
fitting(welded, triangleIds): Plane { centroid, normal, triangleIds, seedTriangleId }
  ↓
dispatch click-plane({ plane })
  ↓
ClusterOverlay subscribes to active.stage === "have-plane" and renders
the green overlay from plane.triangleIds.
```

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
    dispatch replace-active-plane({ plane })
  ↓
ClusterOverlay re-renders with new triangleIds[]
```

If `stage === "have-point"` (point→point partial, or point→plane with
point clicked first — does not happen in normal flow), the tolerance
change is a no-op for the live overlay.

### 6.4 Completion (distance + angle compute)

On the second valid click:

| Mode | Distance | Extra |
|---|---|---|
| `p2p` | `a.distanceTo(b)` | — |
| `p2pl` | `\|(point − plane.centroid) · plane.normal\|` | — |
| `pl2pl` | min `‖vA − vB‖` over unique vertices in clusters A and B | `acos(\|nA · nB\|) × 180/π` |

If `\|A\| × \|B\| > 50_000_000` vertex pairs in `pl2pl`, fall back to
`centroid(A).distanceTo(centroid(B))` and set `approximate: true` on
the measurement. Label gets a `(approx.)` suffix.

The new `Measurement` is appended to `state.completed` and `active`
resets to `{ stage: "empty" }`. The user can take more measurements
without leaving the mode.

## 7. Performance, error handling

### 7.1 Performance budget

| Operation | Cost (typical) | Cost (worst) | Where |
|---|---|---|---|
| Welding | 50 ms (10k tri) | 1 s (1M tri) | Worker (or main if <5k verts) |
| Flood-fill BFS | <10 ms | ~50 ms | Main |
| Plane fitting (area-weighted) | <5 ms | <20 ms | Main |
| `minVertexPairDistance` | <50 ms | ~5 s (5M pairs)* | Main |
| Live slider re-flood-fill | <50 ms | ~200 ms | Main, raf-throttled |

\* Triggers `approximate=true` fallback (§6.4).

### 7.2 Error handling

- **Welding error in worker** — `usePlanePrep` sets `error:"weld-failed"`,
  mode reverts to `off`, banner shows `viewer3d.welding_failed`.
  Point→point still works.
- **Click misses mesh** — raycast returns null, no dispatch (existing v1
  behaviour, unchanged).
- **Tolerance NaN / out-of-range** — reducer clamps to `[0.5, 15]`.
- **Flood-fill returns 0 triangles** — impossible (seed counts itself).
  Defensive guard in `fitting()`: throw if input empty.
- **`pl2pl` huge clusters** — fallback to centroid distance, see §6.4.
- **Mesh > 5M triangles** — welding may take seconds. Spinner is the
  only mitigation; we do not pre-emptively block.

### 7.3 Quantization edge cases

`bbox.diagonal × 1e-6` quantization:
- For a 0.5 mm part, granularity = 5e-10 mm (sub-float32). Floor at
  `1e-5 mm` (10 nm). Documented as known limitation: tiny meshes may
  not weld optimally; in practice the catalog lives in 10–500 mm range.
- For a 1 m part, granularity = 1e-3 mm — comfortable.

## 8. i18n and theming

### 8.1 New i18n keys

PL + EN, in `apps/web/src/i18n/locales/{pl,en}/translation.json`:

```
viewer3d.measure.step.p2p_a
viewer3d.measure.step.p2p_b
viewer3d.measure.step.p2pl_plane
viewer3d.measure.step.p2pl_point
viewer3d.measure.step.pl2pl_a
viewer3d.measure.step.pl2pl_b
viewer3d.measure.step.preparing
viewer3d.measure.row.p2pl
viewer3d.measure.row.pl2pl
viewer3d.measure.tolerance.label
viewer3d.measure.tolerance.tight
viewer3d.measure.tolerance.loose
viewer3d.measure.tolerance.help
viewer3d.measure.mode.p2p
viewer3d.measure.mode.p2pl
viewer3d.measure.mode.pl2pl
viewer3d.welding_failed
```

The existing `viewer3d.measure.assumed` (used for the first measurement
labelled "assumed mm") stays — applies only to `p2p`.

### 8.2 New CSS tokens

`apps/web/src/styles/theme.css` `@theme` block gains:

```
--color-viewer-cluster: #48bb78;   /* emerald-500, cluster overlay tint */
```

Read via `readMeshTokens()` (same pattern as `--color-viewer-paint`,
`--color-viewer-measure`).

## 9. Accessibility

- `StepBanner` has `role="status"` `aria-live="polite"` — stage
  transitions are announced.
- `TolerancePopover` slider has `aria-label`, `aria-valuenow/min/max`
  (base-ui Slider provides these).
- Toolbar mode buttons have `aria-pressed` reflecting active state and
  i18n tooltips.
- Esc cancel ladder (§3.7) keeps the existing "back out of the smallest
  in-flight operation" feel.
- Keyboard cannot click on geometry (raycast needs a screen position).
  Documented as a known limitation of WebGL viewers in general.

## 10. Testing

### 10.1 Unit tests (vitest)

| File | Coverage |
|---|---|
| `lib/welder.test.ts` | Cube STL → 8 unique vertices, every edge shared by exactly 2 triangles. Degenerates: single triangle, two disconnected triangles, triangle with duplicate vertex. |
| `measure/floodFill.test.ts` | Cube face seed → cluster size 2; cylinder 256-seg with tolerance 1°/2°/5° → cluster size grows monotonically; single-triangle seed → size 1. |
| `measure/fitting.test.ts` | Cube face cluster: normal aligned with axis ±epsilon; area-weighted vs unweighted on uneven tessellation. |
| `measure/geometry.test.ts` (extension) | `distancePointToPlane` known cases; `anglePlanes` parallel/perpendicular/anti-parallel; `minVertexPairDistance` simulated small clusters. |
| `measure/measureReducer.test.ts` (extension) | `set-mode` resets active; `click-mesh` in `have-plane` (p2pl) creates measurement; `set-tolerance` clamps; `replace-active-plane` keeps seed. |

Fixtures:

- `apps/web/tests/visual/fixtures/cube.stl` — exists from v1.
- `apps/web/tests/visual/fixtures/cylinder-256seg.stl` — NEW. Built by
  `apps/web/tests/visual/fixtures/build-cylinder.ts` (parallel to
  `build-cube.ts`), 256 axial segments, ~512 triangles, axis = +Z.

### 10.2 Visual regression (Playwright)

Extend `apps/web/tests/visual/viewer3d.spec.ts`:

| Snapshot | Setup |
|---|---|
| `viewer3d-mode-buttons-p2pl` | Modal open on cube STL, click `point→plane` button |
| `viewer3d-cluster-overlay` | As above, click on a cube face — green overlay over 2-tri cluster |
| `viewer3d-step-banner-p2pl` | After plane click — banner shows "Click any point (2/2)" |
| `viewer3d-pl2pl-completed` | Plane→plane mode, click two perpendicular cube faces — measurement shows `mm @ 90.0°` |
| `viewer3d-tolerance-popover` | Click tolerance badge — popover open with slider at 1° |

Stub helpers (`stubViewerStl`, `stubViewerModelDetail`) already exist
from v1.

### 10.3 Manual smoke (HARD GATE — required before merge)

On real catalog STLs from `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/`:

- [ ] `point→plane`: measure from a wall to a corner — sane number
- [ ] `plane→plane` on parallel walls of a 5 mm box → ~5.0 mm @ 0°
- [ ] `plane→plane` on a wall + a slanted fillet → distance + non-zero
      angle
- [ ] Cylindrical part: click a flat cap → small cluster; click cylinder
      side at tolerance 1° → small cluster; at 5° → larger cluster with
      visibly off-axis fitted normal
- [ ] Tolerance slider mid-flow: click plane 1, drag slider — cluster
      grows / shrinks live
- [ ] Esc ladder: click plane 1, Esc → cancel-active. Esc → mode off.
      Esc → modal closes.
- [ ] Mobile (touch): tap-tap for plane→plane on cube, narrow viewport
      — banner readable, cluster visible
- [ ] Keyboard: Tab cycles through three mode buttons + tolerance,
      Enter activates
- [ ] Welding spinner on a >100 k-tri STL: visible <1.5 s
- [ ] Reset View in plane→plane with active cluster: clears active +
      completed, re-frames camera

## 11. Risks and open questions

- **Quantization on tiny meshes.** Floor at `1e-5 mm`. If a real
  catalog STL ever fails to weld correctly because of this, revisit.
- **Worker overhead on small meshes.** Mitigation: <5k vertices welds
  on main thread, skip the worker.
- **Live slider perf on huge clusters.** If `re-floodFill` lags on real
  files, switch from raf-throttle to debounce (~100 ms). Decision
  deferred to first measurement.
- **`minVertexPairDistance` worst case.** Fallback to centroid distance
  with `approximate=true` flag. Spatial-hash / KD-tree improvement is a
  v1.2 follow-up, not v1.1.
- **Discriminated `Measurement` union vs serialization.** v1.1 does not
  persist measurements, so this is academic. If v1.2+ adds persistence
  (URL share, localStorage), custom serde will be needed.
- **Visual snapshot churn.** Existing 18 snapshots + ~5 new ones; each
  slice that touches the toolbar requires an update. Standard process.
- **`set-mode` discards partial selection silently.** If a user with
  one click in `point→point` switches to `plane→plane`, the partial
  point is lost. YAGNI on a confirm dialog until somebody complains.

## 12. Plan handoff

Implementation plan to be produced under
`docs/plans/2026-05-07-stl-viewer-v1.1-plane-measurement-plan.md` (or
the equivalent `docs/superpowers/plans/` location depending on
convention) via the `superpowers:writing-plans` skill. The plan will
sequence: types + reducer first (TDD), then welder + worker, then
flood-fill + fitting + geometry, then UI components (toolbar,
StepBanner, TolerancePopover, ClusterOverlay), then integration into
Viewer3DCanvas / Inline / Modal, then visual regression rebake, then
manual smoke gate.
