# Interactive 3D STL Viewer — Design Spec

**Date:** 2026-05-06
**Status:** Draft, pending user review
**Author:** Claude Opus 4.7 (brainstorming session with Michał)

## 1. Goal

Add an interactive in-browser viewer for STL files in the catalog. A visitor
opens a model's `Files` tab, sees a 3D preview of the selected STL alongside
the file list, can rotate/zoom/pan, switch to a fullscreen modal for detailed
inspection, and take measurements (point-to-point, point-to-plane,
plane-to-plane) in millimetres.

Today the catalog only exposes static iso/front/side/top PNGs rendered offline
by the `workers/render` arq worker. There is no way for a visitor to inspect
geometry directly. This spec closes that gap with a client-side WebGL viewer.

Out of scope for v1: 3MF/STEP support, hole/diameter measurement, vertex/edge
snapping, persistent measurements per model, cross-section, annotations,
sharing screenshots with notes. Each is achievable as follow-up work.

## 2. Users and visibility

The viewer is visible to **every visitor** of the catalog (admin and public).
It is not a privileged feature — it is part of the catalog reading
experience. No backend changes are required; we already serve STL files via
`/api/files/{model_id}/{relative}` with ETag and Range support.

## 3. UX layout

### 3.1 Two states of the same feature

The viewer lives in two coordinated places:

1. **Inline preview** — embedded inside the `Files` tab, in a right-hand pane
   next to the file list. Auto-loads the first STL (alphabetical order) when
   the tab opens. Clicking a different STL row swaps the loaded mesh. Always
   visible while the tab is active.
2. **Fullscreen modal** — opened by an `⛶ Fullscreen` button on the inline
   pane (and from any STL row's "view 3D" affordance). Maximum working
   surface; the inspection-grade UX for measurements and detail browsing.

Both share the same underlying `Viewer3DCanvas` component (see §5). They
differ only in chrome:

- Inline shows a **compact toolbar** (reset / wireframe / screenshot) and a
  single `📏 Measure` button that toggles point-to-point measurement.
  Plane-aware modes are **fullscreen-only** because the plane-cluster
  highlight needs the working area.
- Modal shows the **full toolbar** plus the file selector, position counter,
  and the complete measurement subsystem (point↔point, point↔plane,
  plane↔plane).

Closing the modal does not affect the inline pane, and vice versa — they are
independent component instances.

### 3.2 File selector (modal)

Top-centre dropdown pill that scales to many STL files in one model.

- **Trigger** (closed):
  `[file]  N — drawer_handle_v3.stl   2/3   ▾`
- **Position counter** (`2/3`) is rendered both in the trigger and beside
  each row in the file list. Numbers are derived **frontend-side** from the
  alphabetically-sorted STL list — they are 1..N sequential. Deleting a file
  renumbers automatically; numbers are a UI affordance, not a data identity.
- **Dropdown:** scrollable list of STL files, **search field always visible
  at the top**, file size shown beside each name, currently-active file
  marked with a check, hover/active styling per shadcn conventions.
- **Keyboard:** `←` / `→` step through files without opening the dropdown.
  `/` focuses the search field when dropdown is open. `Esc` closes dropdown.

### 3.3 View toolbar (modal)

Bottom-centre floating pill, blurred backdrop, grouped by function:

`[⟳ reset] | [◐ orbit] [✥ pan] | [F] [S] [T] [⌘ iso] | [⊞ wireframe] [⎙ screenshot]`

- Camera presets animate via spherical coordinate lerp (~250 ms).
- Reset returns to iso + frame-to-bounds.
- Wireframe toggles the mesh material.
- Screenshot triggers `gl.toBlob()` → browser download.

### 3.4 Measurement toolbar (modal)

Mode picker pill. Click a mode, then click points/planes on the mesh.

`[ 📏 ] [ • • ] [ • ▭ ] [ ▭ ▭ ] [ × clear ]`

- `• •` — point-to-point. Two clicks, distance in mm.
- `• ▭` — point-to-plane. Plane click first (flood-fill reveals selected
  cluster), then point click. Distance in mm + signed (above/below plane).
- `▭ ▭` — plane-to-plane. Two plane clicks. Parallel within ε → distance in
  mm; otherwise → angle in degrees.
- `×` — clears all completed measurements.

Each completed measurement renders a labelled overlay (line + value) that
persists until cleared or the modal closes. Inline view shows a simplified
version (only the line, no toolbar mode picker beyond `• •`) — full
measurement is a "go fullscreen" feature.

### 3.5 Empty/loading/error states

- Pre-load: skeleton shimmer in the canvas area (matches catalog
  conventions).
- Loading > 1 s: progress bar derived from `Content-Length` (when present).
- WebGL unavailable: text fallback `Your browser doesn't support 3D viewing`
  + the file list keeps working unchanged.
- Fetch / parse error: error message + Retry button. Sentry breadcrumb.

## 4. Library and stack

`three.js` + `@react-three/fiber` (R3F) + `@react-three/drei`. All three are
**code-split** via `React.lazy()` so users who never open a 3D viewer don't
pay the bundle cost.

Reasoning vs alternatives:

- vs **`<model-viewer>`** (Google): doesn't support STL natively, would
  require offline conversion to glTF.
- vs **`online-3d-viewer`** (kovacsv/Online3DViewer): batteries-included but
  ships its own UI that fights shadcn/Tailwind; less control over UX.
- vs **DIY (`three-stdlib` + custom controls)**: smallest bundle, but we'd
  rebuild OrbitControls, picking, and damping ourselves — not worth it for
  the savings.

R3F gives us:

- React-native lifecycle, fits the existing module/component patterns
- `OrbitControls` from drei (touch + mouse + damping)
- `STLLoader` from `three/examples/jsm/loaders/STLLoader`
- `<Line>`, `<Html>`, `<Grid>` primitives from drei for measurement overlay
- Built-in raycasting for picking
- Approx. 600 KB (three) + 50 KB (R3F) + 30 KB (drei) gzipped, fully
  code-split

## 5. Architecture

### 5.1 Module layout

A new submodule under the catalog module:

```
apps/web/src/modules/catalog/components/viewer3d/
├── index.ts                  # public API: { Viewer3DInline, Viewer3DModal }
├── Viewer3DCanvas.tsx        # core <Canvas> + scene + lights + STL mesh
├── Viewer3DInline.tsx        # FilesTab right-pane wrapper
├── Viewer3DModal.tsx         # fullscreen Dialog wrapper, opens via prop
├── controls/
│   ├── ViewToolbar.tsx       # bottom pill toolbar
│   ├── FileSelector.tsx      # top dropdown pill (search + position counter)
│   └── MeasureToolbar.tsx    # measurement mode picker
├── measure/
│   ├── usePointPicker.ts     # raycast → triangle hit → world coordinate
│   ├── usePlanePicker.ts     # raycast + flood-fill on coplanar tris
│   ├── MeasureOverlay.tsx    # renders dimension lines and labels
│   └── geometry.ts           # pure: distance, projection, normalAngle...
├── hooks/
│   ├── useStlGeometry.ts     # fetch + parse + LRU cache
│   └── useFileIndex.ts       # frontend-derived 1..N numbering
├── lib/
│   ├── camera.ts             # view presets + frame-to-bounds
│   └── parseStl.worker.ts    # off-main-thread parse for >5 MB files
└── tests/                    # vitest specs colocated per existing convention
```

`index.ts` re-exports `Viewer3DInline` and `Viewer3DModal` via dynamic
imports so consumers get the lazy-loaded boundary for free.

### 5.2 Component responsibilities

| Component | Responsibility | State owned |
|---|---|---|
| `Viewer3DCanvas` | R3F `<Canvas>`, scene, lights, mesh, controls | camera, mode, completed measurements |
| `Viewer3DInline` | Right-pane wrapper, simplified chrome | active file id |
| `Viewer3DModal` | Dialog wrapper, full chrome | dialog open/closed |
| `FileSelector` | Dropdown w/ search + position counter | dropdown open, search query |
| `ViewToolbar` | View presets, wireframe, screenshot | wireframe on/off |
| `MeasureToolbar` | Measurement mode picker | (delegates to canvas state) |
| `MeasureOverlay` | Renders completed measurements as 3D lines + labels | (read-only consumer) |

State is **local per instance** — opening the modal creates a fresh `Viewer3DCanvas`; closing throws it away. The only piece of state passed
between inline and modal is the active file id (so opening fullscreen on
"handle_left.stl" lands on the same file).

### 5.3 Public API

```ts
// modules/catalog/components/viewer3d/index.ts
export type StlFile = { id: string; name: string; size: number; url: string };

export const Viewer3DInline = lazy(() => import("./Viewer3DInline"));
export const Viewer3DModal  = lazy(() => import("./Viewer3DModal"));

// Both accept:
type Props = {
  files: readonly StlFile[];     // already filtered to STL kind, alphabetically sorted
  initialFileId?: string;        // defaults to files[0].id
  onClose?: () => void;          // modal only
};
```

Consumers (`FilesTab`, `ModelHero`) build the `files` array from the
existing `ModelDetail.files` payload.

## 6. Data flow

### 6.1 Loading pipeline

```
ModelDetail.files
   │  filter kind == "stl"
   │  sort by original_name (case-insensitive)
   │  index 1..N → useFileIndex
   ▼
user picks file (or default = files[0])
   │
   ▼
useStlGeometry(url)
   │  cache hit? → return BufferGeometry
   │  cache miss:
   │    fetch GET /api/files/{id}/{path}   (Range supported, ETag honoured)
   │    response → ArrayBuffer
   │    if size > 5 MB: parse in Worker
   │    else: parse on main thread
   │    BufferGeometry → computeVertexNormals if missing
   │    LRU insert (max 5 entries, ~250 MB ceiling)
   ▼
camera.frameToBounds(geometry) → render
```

LRU policy: when a 6th file is loaded, evict the least-recently-used one and
call `BufferGeometry.dispose()` to release GPU memory.

### 6.2 Rendering scene

- Ambient light, intensity 0.4
- Directional light from iso angle, intensity 0.8
- Mesh: `MeshStandardMaterial`, neutral grey (matches existing offline
  renders), `metalness: 0`, `roughness: 0.8`
- Optional ground grid scaled to mesh bbox
- `OrbitControls` (drei): mouse drag = orbit, scroll = zoom, shift+drag =
  pan, touch handled by drei's gesture mapping

### 6.3 Measurement state

Stored in a `useReducer` inside `Viewer3DCanvas`:

```ts
type MeasureState = {
  mode: "off" | "point" | "point-plane" | "plane-plane";
  active: PartialMeasurement;   // selections in flight
  completed: Measurement[];     // finished, persisted until cleared
};
```

`PartialMeasurement` collects points/planes until enough are gathered for the
current mode, then the reducer pushes a `Measurement` to `completed` and
resets `active`.

### 6.4 Plane detection (flood-fill)

Algorithm (in `usePlanePicker`):

1. Raycast on click → `faceIndex`.
2. Compute reference normal = `faceNormal(faceIndex)`.
3. Maintain `seen: Set<number>` and `queue: number[]` starting with
   `faceIndex`.
4. Pop a face, look up its 3 edge-adjacent neighbours via precomputed
   adjacency map. For each unseen neighbour, if
   `dot(neighbourNormal, refNormal) > cos(1°)`, add to `seen` and `queue`.
5. Continue until `queue` empties.
6. If `seen.size < 3`: toast "select a flat surface" and bail out — no
   selection added.
7. Otherwise: build a `Plane = { normal, centroid }` and render the cluster
   as a translucent overlay so the user sees what was picked.

Adjacency is precomputed lazily on first use of plane mode and cached in
`BufferGeometry.userData.adjacency`. Cost: ~10 ms per 100 k triangles, one-
time per geometry.

### 6.5 Measurement geometry (pure functions in `geometry.ts`)

```ts
export type Plane = { normal: Vector3; centroid: Vector3 };

export function distance(a: Vector3, b: Vector3): number;

export function pointToPlane(
  p: Vector3,
  plane: Plane,
): { distance: number; signed: number };

export type PlaneToPlaneResult =
  | { kind: "parallel"; distance: number }
  | { kind: "skew"; angle: number /* degrees */ };

export function planeToPlane(a: Plane, b: Plane): PlaneToPlaneResult;
```

All distances in millimetres (STL natively stores mm, no conversion needed).

## 7. Performance and resource guards

| Threshold | Behaviour |
|---|---|
| File size > 50 MB | Pre-fetch confirm dialog: "This file is X MB. Continue?" |
| File size > 5 MB | Parse off-main-thread in a Web Worker |
| Triangle count > 1 M | Inline notice; disable OrbitControls damping |
| Cache size > 5 entries | LRU evict + `BufferGeometry.dispose()` |
| Adjacency build | Lazy on first plane-mode use; cached on the geometry |

GPU memory is the most likely failure mode on low-end devices. Disposal is
strict: every code path that drops a geometry calls `dispose()`.

## 8. Error handling

| Failure | UX | Telemetry |
|---|---|---|
| HTTP error fetching STL | `⚠ Failed to load STL` + Retry button | Sentry breadcrumb `viewer3d.fetch_error` |
| STL parse exception | `⚠ Could not parse STL — file may be corrupt` | Sentry exception with file URL |
| Mesh has 0 triangles | `Empty mesh — nothing to display` | Info-level log |
| WebGL context lost | R3F auto-restore attempt; on failure → fallback message + download link | Sentry warning |
| WebGL unavailable | `Your browser doesn't support 3D viewing` (file list keeps working) | One-time Sentry tag |
| Plane flood-fill < 3 tris | Toast "select a flat surface", picker stays in current mode | Debug log |
| Click outside mesh in measure mode | Silent (no selection added) | None |

Errors are scoped to the viewer via an Error Boundary. They never crash
`FilesTab` or `ModelHero`.

## 9. i18n and theming

- All UI strings in `apps/web/src/locales/{en,pl}.json` under a new
  `viewer3d.*` namespace. No inline literals.
- Toolbar/selector chrome uses Tailwind classes referencing CSS variables in
  `apps/web/src/styles/theme.css` (project rule: zero inline hex in
  components).
- The mesh material colour is a constant (`#9ca3af`) — model "paint" is not
  considered theme chrome and is treated like the existing offline render
  styling.

## 10. Accessibility

- Modal: focus trap, `Esc` closes, focus restore on close (existing
  `Dialog` from shadcn handles this).
- File selector: keyboard-navigable (arrow keys, Enter, Esc).
- Toolbar buttons: ARIA labels.
- The 3D canvas itself is inherently mouse/touch — there is no keyboard-
  driven rotation in v1. This is acknowledged as a limitation.

## 11. Testing

Per the project convention (AGENTS.md): vitest for unit, Playwright visual
regression mandatory for UI.

### 11.1 Unit (vitest)

- `geometry.test.ts` — `distance`, `pointToPlane`, `planeToPlane` against
  unit-cube and parallel-planes fixtures.
- `useFileIndex.test.ts` — alphabetical sort + 1..N numbering, including
  add/remove and tie-breaks on identical names.
- `usePlanePicker.test.ts` — flood-fill on a hand-built `BufferGeometry`
  cube: clicking one face triangle returns exactly the 2 triangles of that
  face, not the cube's 12.
- `useStlGeometry.test.ts` — LRU eviction order, dispose calls on evict.

### 11.2 Visual regression (Playwright)

- `viewer3d-inline.spec.ts` — `FilesTab` with auto-loaded fixture STL.
- `viewer3d-modal-closed.spec.ts` — modal open, file selector closed.
- `viewer3d-modal-open.spec.ts` — modal + dropdown expanded, search field
  visible.
- `viewer3d-measure-pp.spec.ts` — modal + one completed point-to-point
  measurement; assert label text contains `mm`.

Snapshot determinism: `useStlGeometry` is mocked in tests to return a fixed
small-cube `BufferGeometry` (~600 bytes fixture committed to
`apps/web/tests/visual/fixtures/cube.stl`). Real-file rendering depends on
GPU pixel output and is not amenable to pixel-diff snapshots.

### 11.3 Manual smoke (not automated)

- Touch gestures on phone (Playwright pinch-zoom is unreliable).
- WebGL context-loss recovery (hard to reproduce in CI).
- Performance on real catalog STLs from
  `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/`.

## 12. Out of v1 scope (explicit)

- 3MF / STEP support. 3MF would be cheap to add (`3MFLoader` exists in
  three) but is deferred to keep v1 small. STEP requires OpenCascade.js
  (~10 MB WASM) and is not worth it for hobby printing.
- Diameter / hole / circle measurement. Requires arc-fitting heuristics that
  are not bullet-proof on tessellated meshes.
- Vertex / edge snapping for sub-triangle precision.
- Persistent measurements saved per model.
- Cross-section / clipping plane.
- Annotations and screenshot sharing.
- Multi-mesh STLs (rare; treated as a single mesh in v1).

## 13. Risks and open questions

- **Bundle size.** Three.js + R3F + drei is roughly 700 KB gzipped before
  app code. Code-splitting puts that cost only on the viewer route, but
  visitors who open a model with the Files tab pre-selected pay it. The
  catalog list does not. Acceptable.
- **Plane-detection tolerance.** 1° works for most "designed" surfaces but
  may pick a too-small cluster on slightly curved real-world prints. We
  ship 1° as default and consider exposing a tolerance slider only if
  feedback demands it.
- **Worker hydration cost.** Spawning a Worker for STL > 5 MB has fixed
  overhead. The 5 MB threshold is a guess; we may revise after measuring.
- **Mobile WebGL memory.** Low-end Android can struggle with 1 M+
  triangle meshes. The performance guard (§7) flags this but doesn't block
  loading. We accept that the viewer may be slow on cheap phones.
- **Multi-mesh STLs.** STL technically supports multiple solids in one file.
  We collapse them into a single `BufferGeometry` and treat them as one
  mesh. This may surprise a user who exports multi-part STL — out of scope
  to fix.
