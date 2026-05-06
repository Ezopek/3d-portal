# Interactive 3D STL Viewer — Design Spec

**Date:** 2026-05-06
**Status:** Draft, pending user review (revised after fresh-eye review)
**Author:** Claude Opus 4.7 (brainstorming session with Michał)

## 1. Goal

Add an interactive in-browser viewer for STL files in the catalog. A visitor
opens a model's `Files` tab, sees a 3D preview of the selected STL alongside
the file list, can rotate / zoom / pan, switch to a fullscreen-style "Expand"
modal for detailed inspection, and take **point-to-point distance
measurements** in millimetres.

Today the catalog only exposes static iso/front/side/top PNGs rendered offline
by the `workers/render` arq worker. There is no way for a visitor to inspect
geometry directly. This spec closes that gap with a client-side WebGL viewer.

**Out of v1 scope** (deferred to v1.1 — see §12 for concrete handoff notes):
plane-aware measurement (point-to-plane, plane-to-plane), 3MF/STEP support,
hole/diameter measurement, vertex/edge snapping, persistent measurements per
model, cross-section, annotations, screenshot sharing.

## 2. Users and visibility

The viewer is visible to **every visitor** of the catalog (admin and public).
It is not a privileged feature — it is part of the catalog reading
experience. No backend changes are required.

### 2.1 API surface used (post legacy-cleanup)

The viewer fetches STL files exclusively through the **SoT API**:

- `GET /api/models/{model_id}` — model detail (already consumed)
- `GET /api/models/{model_id}/files?kind=stl` — list STL files (already
  consumed via `useFiles`)
- `GET /api/models/{model_id}/files/{file_id}/content` — binary content,
  with ETag and Range support (already consumed by `FilesTab`,
  `ModelGallery`, `CardCarousel`)

The legacy path-based endpoint `/api/files/{model_id}/{relative}` and the
legacy `/api/catalog/*` surface were removed entirely in commit `d92e551`
(see `docs/migration-reports/2026-05-06-legacy-sot-cleanup.md`). The
viewer is built greenfield against the SoT API only; there is no legacy
surface to fall back to.

## 3. UX layout

### 3.1 Two states of the same feature

The viewer lives in two coordinated places:

1. **Inline preview** — embedded inside the `Files` tab. On `≥ md`
   breakpoint it sits in a right-hand pane next to the file list; on `<
   md` (phones) it stacks **below** the list, collapsed to an `[ Open 3D ]`
   button that expands to a square preview when tapped.
2. **Expand modal** — opened by an `Expand` button on the inline pane.
   Maximum working surface; this is the inspection-grade UX. It is a
   **shadcn `<Dialog>` modal** that visually fills the viewport — not the
   browser Fullscreen API (no permission/gesture/fallback machinery).

Both share the same underlying `Viewer3DCanvas` component (see §5). They
differ only in chrome:

- Inline shows a **compact toolbar** (reset / wireframe / screenshot) and a
  single `Measure` button that toggles point-to-point measurement.
- Modal shows the **full toolbar** plus the file selector with position
  counter and the same point-to-point measurement (no extra modes in v1).

Closing the modal does not affect the inline pane, and vice versa — they
are independent component instances.

### 3.2 Auto-load policy

Auto-loading every STL on tab open is bad UX on slow connections / phones.
The actual policy:

1. If the model has `thumbnail_file_id` set (typical — the render worker
   populates it with the iso PNG it generates from the model's STLs), show
   `/api/models/{model_id}/files/{thumbnail_file_id}/content` as a static
   placeholder image on inline open. Otherwise pick the first
   `kind=image` file as a fallback placeholder.
2. The user clicks `[ Load 3D ]` (overlayed on the placeholder) to actually
   fetch and render the STL.
3. **Exception:** if the selected STL is < 5 MB and the offline render is
   missing, auto-load on tab open. The cost is small enough not to surprise.
4. Switching files inside the viewer always loads the selected file (it
   was an explicit user action).

This keeps the catalog snappy by default and only spends the network /
WebGL budget on intent.

### 3.3 File selector (modal)

Top-centre dropdown pill that scales to many STL files in one model.

- **Trigger** (closed):
  `[file]  N — drawer_handle_v3.stl   2/3   ▾`
- **Position counter** (`2/3`) is rendered both in the trigger and beside
  each row in the file list. Numbers are derived **frontend-side** from the
  alphabetically-sorted STL list — they are 1..N sequential. Deleting a
  file renumbers automatically; numbers are a UI affordance, not a data
  identity.
- **Dropdown:** scrollable list of STL files, **search field always visible
  at the top**, file size shown beside each name, currently-active file
  marked with a check, hover/active styling per shadcn conventions.
- **Keyboard:** `←` / `→` step through files without opening the dropdown.
  `/` focuses the search field when the dropdown is open. `Esc` closes the
  dropdown.

### 3.4 View toolbar

Bottom-centre floating pill, blurred backdrop, grouped by function. Icons
are **lucide-react components** (matching existing UI), each wrapped in a
shadcn `<Tooltip>` and tagged with `aria-label`:

| Group | Icons (lucide) | Action |
|---|---|---|
| Reset | `RotateCcw` | Frame-to-bounds + iso angle |
| Mode | `MousePointer2`, `Move` | Orbit / pan |
| View presets | `LayoutGrid` glyphs labelled `F`/`S`/`T`/`Iso` | Snap camera |
| Render | `Box` (wireframe), `Camera` (screenshot) | Toggle / capture |
| Measure | `Ruler` | Toggle point-to-point measurement |

Camera presets animate via spherical-coordinate lerp (~250 ms). Wireframe
toggles the mesh material. Screenshot is described in §6.2.

### 3.5 Measurement (v1 — point-to-point only)

A single `Ruler` toggle on the toolbar. When on:

- Cursor changes to a crosshair when over the mesh.
- First click on the mesh adds a marker at the picked point.
- Second click adds the second marker, draws a line between them, and
  renders a label like `42.0 mm` near the midpoint.
- `Esc` cancels an in-progress (one-point-only) measurement.
- `×` button clears all completed measurements.
- Multiple measurements can coexist — each is a persistent line + label.
- A **measurement summary** is rendered as a list **outside** the canvas
  (e.g. small panel below the toolbar in modal, in a `<details>` in
  inline). Live region (`aria-live="polite"`) announces each completed
  measurement.

**Unit handling.** The STL format is unitless. The catalog convention is
millimetres (sourced from the offline render worker that already assumes
mm). The viewer therefore renders labels with a `≈ mm` qualifier on the
first measurement of a session, e.g. `42.0 mm (assumed)`. Subsequent
labels in the same session use plain `mm`. There is no per-file override
in v1.

### 3.6 Empty / loading / error states

- Pre-load placeholder: existing offline PNG render, or shimmer skeleton
  if no render exists.
- Loading > 1 s: progress bar derived from `Content-Length` (when
  present).
- WebGL unavailable: text fallback `Your browser doesn't support 3D
  viewing` + the file list keeps working unchanged.
- Fetch / parse error: error message + Retry button. Sentry breadcrumb.

## 4. Library and stack

`three.js` + `@react-three/fiber` (R3F) + `@react-three/drei`. All three
are **code-split** via `React.lazy()` so users who never open a 3D viewer
don't pay the bundle cost.

Reasoning vs alternatives:

- vs **`<model-viewer>`** (Google): doesn't support STL natively, would
  require offline conversion to glTF.
- vs **`online-3d-viewer`** (kovacsv/Online3DViewer): batteries-included
  but ships its own UI that fights shadcn/Tailwind; less control over UX.
- vs **DIY (`three-stdlib` + custom controls)**: smallest bundle, but we'd
  rebuild OrbitControls, picking, and damping ourselves — not worth it for
  the savings.

R3F gives us:

- React-native lifecycle, fits the existing module/component patterns
- `OrbitControls` from drei (touch + mouse + damping)
- `STLLoader` from `three/examples/jsm/loaders/STLLoader`
- `<Line>`, `<Html>` primitives from drei for the measurement overlay
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
├── Viewer3DInline.tsx        # FilesTab right-pane wrapper (with mobile fallback)
├── Viewer3DModal.tsx         # shadcn Dialog wrapper
├── controls/
│   ├── ViewToolbar.tsx       # bottom pill toolbar (lucide icons + tooltips)
│   ├── FileSelector.tsx      # top dropdown pill (search + position counter)
│   └── MeasureSummary.tsx    # text list of completed measurements + clear button
├── measure/
│   ├── usePointPicker.ts     # raycast → triangle hit → world coordinate
│   ├── MeasureOverlay.tsx    # renders dimension lines + labels in 3D
│   └── geometry.ts           # pure: distance(), midpoint(), formatMm()
├── hooks/
│   ├── useStlGeometry.ts     # fetch + parse + LRU cache (cache-owned dispose)
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
| `Viewer3DCanvas` | R3F `<Canvas>`, scene, lights, mesh, controls | camera, measure mode, completed measurements |
| `Viewer3DInline` | Right-pane wrapper / mobile collapsed fallback | active file id |
| `Viewer3DModal` | shadcn Dialog wrapper | dialog open/closed |
| `FileSelector` | Dropdown w/ search + position counter | dropdown open, search query |
| `ViewToolbar` | View presets, wireframe, screenshot, measure toggle | wireframe on/off, measure mode |
| `MeasureSummary` | Text list of completed measurements + clear | (read-only consumer) |
| `MeasureOverlay` | Renders completed measurements as 3D lines + labels | (read-only consumer) |

State is **local per instance** — opening the modal creates a fresh
`Viewer3DCanvas`; closing throws it away. The only piece of state passed
between inline and modal is the active file id (so opening expand on
"handle_left.stl" lands on the same file).

### 5.3 Public API

```ts
// modules/catalog/components/viewer3d/index.ts
export type StlFile = { id: string; name: string; size: number; modelId: string };

export const Viewer3DInline = lazy(() => import("./Viewer3DInline"));
export const Viewer3DModal  = lazy(() => import("./Viewer3DModal"));

// Both accept:
type Props = {
  files: readonly StlFile[];     // already filtered to STL kind, alphabetically sorted
  initialFileId?: string;        // defaults to files[0].id
  onClose?: () => void;          // modal only
};
```

Inside the viewer, file URLs are constructed as
`/api/models/${modelId}/files/${fileId}/content`. Consumers (`FilesTab`,
later possibly `ModelHero`) build the `files` array from the existing
`ModelDetail.files` payload (already filtered server-side via
`?kind=stl`).

## 6. Data flow

### 6.1 Loading pipeline

```
files (already filtered kind == "stl", sorted alphabetically by useFileIndex)
   │
user picks file (or default = files[0])  →  hasOfflineRender ? show placeholder
                                            and wait for "Load 3D" click
                                            unless size < 5 MB and no render
   │
   ▼
useStlGeometry({ modelId, fileId })
   │  cache hit? → return BufferGeometry (cache LRU, cache owns dispose)
   │  cache miss:
   │    fetch GET /api/models/{modelId}/files/{fileId}/content   (Range, ETag)
   │    response → ArrayBuffer
   │    if size > 5 MB: parse in Worker (parseStl.worker.ts)
   │    else: parse on main thread
   │    BufferGeometry → computeVertexNormals if missing
   │    LRU insert (max 5 entries, ~250 MB ceiling)
   ▼
camera.frameToBounds(geometry) → render
```

### 6.2 Cache lifecycle (revised — cache owns dispose)

`useStlGeometry` is backed by a **module-singleton LRU map** living outside
React. It owns the lifecycle of every `BufferGeometry` it returns:

- `get(key)` → returns existing `BufferGeometry` or fetches+parses+inserts.
- LRU eviction (when count > 5) calls `BufferGeometry.dispose()` on the
  evicted entry **once it has zero subscribers**.
- Components subscribe via a refcount on `get`; on unmount they
  `release(key)`. Release decrements the refcount but **does not** call
  `dispose()`. Only the LRU eviction path disposes.
- This avoids the "dispose-on-unmount, then re-mount, then re-fetch" bug
  the reviewer flagged.

### 6.3 Rendering scene

- Ambient light, intensity 0.4
- Directional light from iso angle, intensity 0.8
- Mesh: `MeshStandardMaterial`, colour read from CSS variables
  (`--viewer-mesh-paint`, `--viewer-mesh-edge`) declared in
  `apps/web/src/styles/theme.css`. **No inline hex** in components — the
  project rule applies to viewer chrome and to the mesh material alike.
  Defaults shipped: paint `oklch(0.72 0.01 250)`, edge `oklch(0.30 0.02 250)`
  (neutral grey, dark blue-tinted edges).
- `metalness: 0`, `roughness: 0.8`
- Optional ground grid (`drei/Grid`) scaled to mesh bbox; toggle in
  toolbar.
- `OrbitControls` (drei): mouse drag = orbit, scroll = zoom, shift+drag =
  pan, touch handled by drei's gesture mapping.

**Canvas configuration:** `<Canvas gl={{ preserveDrawingBuffer: true,
antialias: true }}>`. `preserveDrawingBuffer: true` is required for
`canvas.toBlob()` to capture the rendered frame on demand for the
screenshot button. There is a documented small performance cost (the GL
context cannot tear down its draw buffer between frames); we accept it
because the alternative (forcing a synchronous render before capture)
adds more complexity.

**Screenshot path:**
1. User clicks `Camera` icon in toolbar.
2. R3F `gl` reference → `gl.domElement.toBlob(blob => …, "image/png")`.
3. Blob URL → invisible `<a download="model_id-file_name.png">` click.
4. Revoke blob URL after click.

### 6.4 Measurement state

Stored in a `useReducer` inside `Viewer3DCanvas`:

```ts
type MeasureState = {
  mode: "off" | "point-to-point";
  active: { points: Vector3[] };  // 0 or 1 point in flight
  completed: { a: Vector3; b: Vector3; distanceMm: number; id: string }[];
};
```

`PartialMeasurement` collects 0 or 1 point until the next click, then the
reducer pushes a `Measurement` to `completed` and resets `active`.

### 6.5 Measurement geometry (pure functions in `geometry.ts`)

```ts
export function distance(a: Vector3, b: Vector3): number;       // mm
export function midpoint(a: Vector3, b: Vector3): Vector3;
export function formatMm(value: number, opts?: { qualifier?: string }): string;
```

All functions are pure and easy to unit-test.

## 7. Performance and resource guards

| Threshold | Behaviour |
|---|---|
| File size > 50 MB | Pre-fetch confirm dialog: "This file is X MB. Continue?" |
| File size > 5 MB | Parse off-main-thread in a Web Worker |
| File size < 5 MB **and** no offline render | Auto-load on tab open |
| Offline render exists | Show as placeholder; require explicit "Load 3D" click |
| Triangle count > 1 M | Inline notice; disable OrbitControls damping |
| Cache size > 5 entries | LRU evict + `BufferGeometry.dispose()` (cache-owned) |

GPU memory is the most likely failure mode on low-end devices. Disposal is
strict and centralised in the cache; consumers never call `dispose()`.

## 8. Error handling

| Failure | UX | Telemetry |
|---|---|---|
| HTTP error fetching STL | `⚠ Failed to load STL` + Retry button | Sentry breadcrumb `viewer3d.fetch_error` |
| STL parse exception | `⚠ Could not parse STL — file may be corrupt` | Sentry exception with file URL |
| Mesh has 0 triangles | `Empty mesh — nothing to display` | Info-level log |
| WebGL context lost | R3F auto-restore attempt; on failure → fallback message + download link | Sentry warning |
| WebGL unavailable | `Your browser doesn't support 3D viewing` (file list keeps working) | One-time Sentry tag |
| Click outside mesh in measure mode | Silent (no marker added) | None |

Errors are scoped to the viewer via an Error Boundary. They never crash
`FilesTab` or `ModelHero`.

## 9. i18n and theming

- All UI strings in `apps/web/src/locales/{en,pl}.json` under a new
  `viewer3d.*` namespace. No inline literals.
- Toolbar / selector / overlay chrome uses Tailwind classes referencing
  CSS variables in `apps/web/src/styles/theme.css`.
- Mesh material colour is also driven by CSS variables
  (`--viewer-mesh-paint`, `--viewer-mesh-edge`) — read at canvas mount via
  `getComputedStyle()` and applied to the `MeshStandardMaterial`. No
  inline hex. Re-read on theme change (existing project hooks).

## 10. Accessibility

Minimum a11y commitments for v1:

- **Keyboard navigation** for every toolbar button (`Tab`, `Enter`/`Space`
  to activate). Tooltips visible on focus, not just hover.
- **Modal focus trap** + `Esc` to close + focus restore on close
  (provided by shadcn `<Dialog>`).
- **File selector keyboard:** arrow keys, `Enter`, `Esc`, `/` to focus
  search.
- **ARIA labels** on every icon button (`aria-label="Reset view"`, etc.);
  toolbar group has `role="toolbar"`.
- **Live region** (`<div aria-live="polite">`) announces each completed
  measurement: "Measurement: 42 millimetres".
- **Measurement summary panel** outside the canvas (text list of all
  completed measurements with their values), so a non-sighted user can
  read results without relying on the 3D overlay labels.
- **Model summary** in the modal header: file name, position, triangle
  count — text content, not just visual.
- The 3D canvas itself is inherently mouse/touch — there is no keyboard-
  driven rotation in v1. This is acknowledged as a limitation, partially
  compensated by the view-preset buttons (`F`/`S`/`T`/`Iso`) which are
  keyboard-activatable.

## 11. Testing

Per the project convention (AGENTS.md): vitest for unit, Playwright visual
regression for UI changes, and **manual smoke as a hard gate before
deploy**.

### 11.1 Unit (vitest)

- `geometry.test.ts` — `distance`, `midpoint`, `formatMm` against unit
  fixtures (1-2-3 triangle, etc.).
- `useFileIndex.test.ts` — alphabetical sort + 1..N numbering, including
  add/remove and tie-breaks on identical names.
- `useStlGeometry.test.ts` — LRU eviction order, refcount semantics,
  dispose called only on eviction, not on unmount.

### 11.2 Visual regression (Playwright)

- `viewer3d-inline-placeholder.spec.ts` — Files tab default state showing
  PNG render placeholder + Load 3D button.
- `viewer3d-inline-loaded.spec.ts` — after Load 3D click, mock
  geometry rendered.
- `viewer3d-modal-closed.spec.ts` — modal open, file selector closed.
- `viewer3d-modal-open.spec.ts` — modal + dropdown expanded with search
  field visible.
- `viewer3d-measure-pp.spec.ts` — modal + one completed point-to-point
  measurement; assert label text contains `mm`.
- `viewer3d-mobile.spec.ts` — phone viewport, inline collapsed under file
  list.

Snapshot determinism: `useStlGeometry` is mocked in tests to return a
fixed small-cube `BufferGeometry` (~600 bytes fixture committed to
`apps/web/tests/visual/fixtures/cube.stl`). Real-file rendering depends
on GPU pixel output and is not amenable to pixel-diff snapshots.

### 11.3 Manual smoke (HARD GATE — required before deploying viewer slice)

A checklist that **must** pass on `.190` before merging the viewer feature
to `main`. Captured as a markdown checklist in the implementation plan;
each box is initialled with date + result. Failures block deploy.

- [ ] Real STL from `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/`
      (small, ~500 KB) loads + rotates smoothly
- [ ] Large STL (> 30 MB) — confirm dialog appears, loads, frame rate
      acceptable (> 20 FPS on dev laptop)
- [ ] Phone (Android Chrome): inline collapsed, Open 3D works, touch
      orbit + pinch zoom work
- [ ] Tablet portrait/landscape: inline pane usable
- [ ] Screenshot button produces a non-empty PNG matching the visible
      frame
- [ ] WebGL context loss (devtools → Rendering → Force WebGL context
      loss) → fallback shows, recovery path works
- [ ] Switch between 3 STLs in one model → cache reuses (verified via
      Network panel)
- [ ] Modal open/close 5 times rapidly → no memory leak (verified via
      Performance panel heap snapshot)
- [ ] Measurement: click two points, label `XX mm` rendered, persists
      through camera moves, summary panel updates, live region
      announces

These cover the risks Playwright cannot: real WebGL, mobile touch,
context loss recovery, screenshot correctness, and memory hygiene.

## 12. Out of v1 scope (deferred to future iterations)

The following items are **explicitly deferred** and require their own
design + planning sessions before implementation. They are listed here
as concrete handoff notes so they are not lost.

### 12.1 v1.1 — plane-aware measurement (own spec required)

Adds point-to-plane and plane-to-plane modes. Open design questions to
resolve in v1.1 spec:

- **Vertex welding strategy.** STLLoader gives non-indexed geometry
  (every triangle has its own 3 vertices, no shared indices). Plane
  flood-fill needs adjacency, which needs welding (quantize positions to
  e.g. 1e-4 mm and dedupe). Decide quantization granularity, build cost
  budget, and whether to weld on parse or lazily on first plane click.
- **Plane acceptance threshold.** Reviewer flagged that "size < 3
  triangles → reject" is too strict (a cube face is 2 triangles).
  Probably accept any flood-fill result of size ≥ 1, but visualise the
  cluster so the user can see it; reconsider on real catalog STLs.
- **Tolerance for "coplanar".** 1° default, but real prints with
  slightly wavy surfaces may need a slider or adaptive tolerance.
  Calibrate on real catalog files before committing.
- **Numerical stability** of normal averaging across many small
  triangles. Test on tessellated cylinders (which look "flat" in the
  axial direction but aren't).
- **UX of plane selection.** Two clicks to define plane→plane, with
  cluster visualisation; is the click sequence obvious? Mode badge,
  step indicator, etc.

### 12.2 v1.2+ — other deferred features (own specs required)

- **3MF support.** `three.js` has `3MFLoader`; cheap addition (~30 min)
  but punted from v1 to keep scope tight.
- **STEP support.** Requires OpenCascade.js (~10 MB WASM). Probably not
  worth it for a homelab portal; revisit only if requested.
- **Diameter / hole / circle measurement.** Arc-fitting heuristics on
  tessellated meshes — fragile, would need stabilisation work.
- **Vertex / edge snapping** for sub-triangle measurement precision.
  Requires precomputed vertex / edge maps and snap-distance UX.
- **Persistent measurements** saved per model. Needs schema, ownership
  rules, and a "share measurements" affordance.
- **Cross-section / clipping plane.** Useful for inspecting internal
  geometry; needs UI for plane definition + snapping.
- **Annotations** (text labels attached to mesh points) and **screenshot
  sharing** with annotations baked in.
- **Multi-mesh STLs** (rare; STL technically supports multiple solids in
  one file). v1 collapses them into a single `BufferGeometry`. Proper
  handling would split + present them with their own sub-selector.

## 13. Risks and open questions

- **Bundle size.** Three.js + R3F + drei is roughly 700 KB gzipped before
  app code. Code-splitting puts that cost only on the viewer route, but
  visitors who open a model with the Files tab pre-selected pay it. The
  catalog list does not. Acceptable.
- **`preserveDrawingBuffer` performance.** Required for screenshots, but
  has a measurable (if small) cost on every frame. Accepted.
- **Worker hydration cost.** Spawning a Worker for STL > 5 MB has fixed
  overhead. The 5 MB threshold is a guess; we may revise after measuring.
- **Mobile WebGL memory.** Low-end Android can struggle with 1 M+
  triangle meshes. The performance guard (§7) flags this but doesn't
  block loading. We accept that the viewer may be slow on cheap phones.
- **Multi-mesh STLs.** STL technically supports multiple solids in one
  file. We collapse them into a single `BufferGeometry` and treat them as
  one mesh in v1. This may surprise a user who exports multi-part STL —
  out of scope to fix.
- **Regression guard against re-introducing legacy URLs.** Legacy
  `/api/files/...` and `/api/catalog/...` were removed in commit
  `d92e551`, so the backend cannot serve them. To prevent agents or future
  contributors from accidentally typing them back into frontend code,
  recommend adding an `eslint-no-restricted-syntax` rule that flags string
  literals matching `/api/files/` or `/api/catalog/` outside of
  `docs/migration-reports/`. Cheap, catches the regression at lint time.
