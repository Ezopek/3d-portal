# STL Viewer v1.2 — Diameter (rim) measurement + per-measurement palette

**Status:** Design — not yet implemented
**Author:** Michał + Claude
**Date:** 2026-05-08
**Supersedes:** Extends `2026-05-06-stl-viewer-design.md` §12.2 (deferred
"diameter / hole / circle measurement") and `2026-05-07-stl-viewer-v1.1-plane-measurement-design.md`
**Revision:** v3 (second-round Codex review)

## Revision history

- **v3 (this)** — second Codex review pass.
  - **Sagitta gate calibrated for hex.** v2 had `SAGITTA_MULTIPLIER =
    2.0` which rejected even `weak` hex holes at moderate radii (e.g.,
    R=5 mm: hex sagitta 0.67 mm > 0.5 mm threshold). Bumped to
    `SAGITTA_MULTIPLIER = 3.0`, which keeps hex passing as `weak` up
    to and beyond catalog-realistic radii while still rejecting
    squares/rectangles (which are caught by `MIN_LOOP_VERTICES`
    anyway) and ellipses.
  - **Palette `PAIR_LIGHTNESS_DARK` 0.50 → 0.55.** v2's value put the
    worst-case sel2 at ~2.77:1 contrast against the canvas
    (`#0d1422`), failing the 3:1 acceptance criterion. 0.55 brings
    every sample to ≥ 3.43:1.
  - **`walkEdgeLoop` signature corrected** to take `SharpEdgeGraph`
    and `SharpEdgeId` (a leftover stale signature from v1's
    Float32Array-style sharp edges).
  - **Rim line closes by appending first point**, not by drei's
    `closed` prop (which only exists on `<CatmullRomLine>`, not
    `<Line>`). Spec now says explicitly: `points = [...loopPoints,
    loopPoints[0]]` when feeding `<Line>`.
  - **z-fighting fix uses `depthTest=false` on rim line**, not
    `polygonOffset` (which has no effect on `LineMaterial`). Rim line
    + center dot + label render with `renderOrder = 1` and
    `depthTest = false` so they sit cleanly on top of the mesh.
  - **Toast uses `sonner`** (the project's actual toast lib), not a
    fictional `useToast` hook.
  - **Click toast suppressed while prep is in flight.** "No circular
    rim detected here" would mislead the user when the real reason is
    "prep isn't finished yet" — and the StepBanner already says
    "Preparing mesh…", so a parallel toast is noise.
  - **Test fixture descriptions clarified.** "Smooth 256-seg dome"
    fixture is now described as "closed sphere" (boundary edges count
    as sharp under the §4.1 rule, so an open dome's equator would
    create false sharp edges in the test). Replace with sphere or
    explicitly assert "0 sharp internal edges, N=256 boundary edges
    along open seam if any."
  - **`ColorManagement` import removed** from §3.1 example (was
    unused — lint would catch).
- **v2** — addresses first-round Codex review (review file in same directory).
  - **P1.1 Detector false-positives.** Vertex-only circle fit accepts
    cube faces, rectangles, regular polygons. Added: minimum 6 loop
    vertices (reject < 6); midpoint sagitta check (chord midpoints
    must lie on fitted circle within tolerance); angular-spacing
    sanity check (max gap ≤ 2× mean gap). Hex (N=6) → weak; circle
    (N≥12) with low residuum → normal; square (N=4) → reject.
  - **P1.2 Self-contained Rim.** `Rim.loopPoints` now stores absolute
    `Vector3[]` (snapshot of welded coordinates), not welded vertex
    indices. Positions are copied from `welded.positions` at fit time;
    after that the rim renders without ever re-reading the welded
    mesh. Completed Diameter measurements survive welded-mesh GC,
    cache eviction, and mode changes.
  - **P1.3 Click handler synchronous re-detect.** Hover preview is now
    advisory only — the click handler runs the full
    `closestSharpEdge → walkEdgeLoop → fitCircle` pipeline
    synchronously from the click event's `(faceIndex, hitPoint)`. No
    race window between rAF preview and click commit. The hover
    `hoveredRim` state is used purely for visual rendering.
  - **P1.4 SharpEdgeGraph cache.** Replaces the loose
    `dihedralAngles: Float32Array` extension with a canonical
    `SharpEdgeGraph` (canonical edges + per-vertex incidence in CSR
    form + per-edge dihedral). Built **inside the welder worker** as
    part of the same prep phase, transferred over the message
    boundary. No lazy main-thread work on first hover. Fixes the
    length-math bug from v1 (per-triangle vs per-edge mismatch).
  - **P1.5 Coordinate mapping normative.** Click and hover both must
    map `e.faceIndex` (source STL triangle) → `welded.sourceToWelded`
    → welded triangle, skipping `BOUNDARY` sentinels. `hitPoint` is
    consumed in mesh-local frame (the viewer's mesh has no transform,
    but the spec now states this explicitly so future transforms
    don't break the algorithm silently).
  - **P2.6 Welder worker handles prep.** Sharp-edge graph computed in
    worker; "Preparing mesh…" copy used while the prep is in flight;
    Esc cancels the worker as in v1.1. No "first-hover hiccup."
  - **P2.7 Click toast on no-preview.** Explicit click in Diameter
    mode without a valid rim now shows a brief, rate-limited toast
    `viewer3d.measure.diameter.no_rim` (max once per 2 s). Hover
    failures stay silent.
  - **P2.8 Generic mesh-analysis copy.** Existing v1.1 keys
    `viewer3d.measure.step.preparing` ("Preparing planes…") and
    `viewer3d.welding_failed` ("…for plane selection") become
    mode-neutral ("Preparing mesh…", "Could not analyse mesh.").
    Diameter-specific keys added separately.
  - **P2.9 Palette accessibility.** Acceptance criteria: every overlay
    color (line/cluster/dot) must achieve ≥ 3:1 contrast against the
    viewer canvas background; light swatches in the MeasureSummary
    legend gain a 1px border with `--border` token so they don't
    vanish on light theme. OKLCH→sRGB conversion documented for
    `THREE.Color` (output is linear sRGB → consumed via `setRGB()`,
    which is correct because R3F's default working color space is
    linear-sRGB). CSS swatches consume display sRGB via the `oklch()`
    CSS function directly (no manual conversion).
  - **P2.10 Tolerance button.** Disabled (visible) instead of hidden
    when `mode ∉ {p2pl, pl2pl}`. Same slot, no toolbar layout shift.
  - **P2.11 Label placement screen-aware.** `tangent` recomputed when
    camera-to-rim direction changes by more than ~30° (hysteresis to
    avoid twitch). Rim line + label render with `renderOrder = 1` and
    a small polygonOffset to avoid z-fighting with the mesh.
  - **P2.12 Keyboard focus rules.** `D` shortcut ignored when an
    `<input>`, `<textarea>`, or contenteditable element has focus, or
    when the viewer is not the active subtree. Implemented by checking
    `document.activeElement` in the canvas-level keydown handler.
  - **P2.13 Off-by-one in §6.3 fixed.** All references to
    `paletteFor(...)` in this spec use the same zero-based rule:
    completed measurements use `paletteFor(m.colorIndex, slot)`;
    in-progress preview uses `paletteFor(allocator(state), slot)`.
  - **P2.14 Tests aligned with detector.** Sharp-edge fixture counts
    corrected (32-segment hole + 3 mm-thick plate → 64 sharp rim
    edges, top + bottom). Detector-level rejection tests added: cube
    edge → no diameter (square loop rejected by min-N + sagitta);
    rectangle → rejected; regular hex → weak; tessellated dome → no
    sharp edges → null.
  - **P3.15 Token + test paths.** Token kept token name corrected to
    `--color-viewer-mesh-paint` (was wrongly named in v1). Test
    files co-located next to implementation under
    `viewer3d/measure/` and `viewer3d/lib/`, matching the existing
    project convention (not `apps/web/tests/unit/`).
  - **P3.16 Stable colorIndex.** Adopted now (was deferred in v1).
    `Measurement` gains `colorIndex: number`; allocator picks the
    smallest non-negative integer not used by any current
    measurement. Survives delete: deleting `#2` keeps `#1`'s and
    `#3`'s colors stable; the next measurement reuses index `2`.
- **v1** — first draft from brainstorm decisions.

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
- **Per-measurement palette (palette E)** — `paletteFor(colorIndex,
  slot)` generator. Used by Diameter (rim only — no sel2) and
  retrofitted to p2p, p2pl, pl2pl.
- **Stable `colorIndex` per measurement.** Each `Measurement` carries
  its own `colorIndex` allocated at commit time (smallest unused
  non-negative integer). Deleting `#2` does not recolor `#3`.
- Active-stage coloring uses the next allocated `colorIndex`
  preemptively — no visual jump on commit.
- `MeasureSummary` row gains color swatches matching the 3D overlay
  colors, so the panel acts as a legend.
- **Sharp-edge graph computed in the welder worker.** No first-hover
  hitch on large meshes; "Preparing mesh…" covers both welding and
  edge-graph build.

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
- **Tolerance° popover:** **always rendered** (stable toolbar slot, no
  layout shift on mode change). **Disabled** (greyed-out, `aria-disabled`,
  popover doesn't open) when `mode ∉ {point-to-plane, plane-to-plane}`.
  Tooltip in disabled state: `viewer3d.measure.tolerance.disabled_reason`
  ("Tolerance applies only to plane modes" / "Tolerancja ma znaczenie
  tylko w trybach płaszczyzn").

### 2.2 Click flow — Diameter mode

Diameter is single-click; there is no "have-rim" intermediate active
stage. Hover preview is **advisory only** — the click handler runs
the full detection pipeline synchronously from the click event. This
eliminates rAF/click race conditions identified in P1.3 of the v1
review.

1. **Enter Diameter mode** (button click or `D` key). `state.active`
   resets to `{stage:"empty"}`. Welding + sharp-edge graph build
   starts in the background if not already cached (Diameter joins
   p2pl/pl2pl in the `needsWelding` set; the same worker that welds
   also builds the `SharpEdgeGraph` — see §4.1).
2. **User hovers** over the mesh. For each fresh `pointermove`
   (`requestAnimationFrame`-throttled, max one detection per frame),
   `Viewer3DCanvas` runs:
   1. Raycast → `(sourceFaceIndex, hitPoint)` in mesh-local space.
   2. `weldedTri = welded.sourceToWelded[sourceFaceIndex]` — skip if
      `BOUNDARY` sentinel (degenerate source triangle).
   3. `detectRim(weldedTri, hitPoint, welded, graph)` — runs:
      `closestSharpEdge → walkEdgeLoop → fitCircle`. Returns `Rim |
      null`. The `Rim` if returned is **already self-contained**:
      `loopPoints` is a `Vector3[]` of absolute coordinates copied
      from `welded.positions`.
   4. `setHoveredRim(rim ?? null)` triggers the canvas re-render of
      the preview overlay.
3. **Hover preview** — when `hoveredRim !== null`, the canvas renders
   the rim's loop as a tube line in the **next allocated `colorIndex`**
   (`paletteFor(allocateColorIndex(state.completed), "sel1")`). No
   center dot, no label — preview is intentionally minimal.
4. **Click — synchronous re-detect.** On `pointerup` in Diameter mode,
   the canvas runs `detectRim()` **again**, using the click event's
   own `(sourceFaceIndex, hitPoint)`. If it returns a non-null rim:
   `dispatch({type:"click-rim", rim})`. Reducer appends
   `kind:"diameter"` with the allocated `colorIndex` to
   `state.completed`. **The committed Rim is the click-time
   detection, not the stale hover-time `hoveredRim`.** This way a
   valid click on a visible rim cannot fail because the hover
   pipeline is one frame behind.
5. **Click on no-rim (synchronous detection returned null):** brief
   non-modal toast: `toast(t("viewer3d.measure.diameter.no_rim"))`
   ("No circular rim detected here" / "Tu nie wykryto okrągłej
   krawędzi"). Toast uses **`sonner`** (the project's existing toast
   lib — see existing usages of `import { toast } from "sonner"`),
   rate-limited to once per 2 s per Diameter session (suppressed if a
   successful click happens in between). Hover-without-preview remains
   silent.
   **Suppression while prep is in flight (v3 fix):** if `prep.loading
   === true` (welding + edge-graph build still running), the toast is
   suppressed — `StepBanner` already says "Preparing mesh…", and a
   parallel "no rim detected" toast would mislead the user about the
   real reason for the no-op.

### 2.3 Visualization — completed Diameter measurement

A committed `kind:"diameter"` measurement renders three pieces in 3D:

| Element | Geometry | Color |
|---|---|---|
| Rim loop | drei `<Line>`, `lineWidth: 2`, `points = [...rim.loopPoints, rim.loopPoints[0]]` (loop closed by appending the first point — drei `<Line>` has no `closed` prop, only `<CatmullRomLine>` does) | `bright sel1` of palette[`m.colorIndex`] |
| Center dot | `<mesh>` with `<sphereGeometry args={[max(0.5, radius*0.04), 12, 12]} />` at `rim.center` | same as rim |
| Label | `<Html>` HTML badge, classes match v1.1 `LABEL_CLASS`. Text: `#N Ø 25.0 mm` (or `#N ~Ø 25.0 mm` if `weak: true`). Position: `rim.center + tangent * (radius + 4mm)`. | white text, dark zinc background |

**Z-fighting / depth (v3 fix).** `LineMaterial` doesn't honour
`polygonOffset` (that's a `MeshBasicMaterial` thing). Instead:

- Rim line uses `depthTest = false`, `depthWrite = false`, `renderOrder
  = 1`. The line always renders on top of the mesh — a small
  always-visible cue is desired for "this is what we measured".
- Center dot uses default depth: it's a small sphere, occlusion
  behind mesh is fine.
- Label is HTML in screen-space (drei `<Html>`); its depth is handled
  by drei's occlusion machinery — leave default.

**Tangent (label-position) selection** — screen-aware with hysteresis:

- At first render of the measurement, pick the `tangent` perpendicular
  to `rim.axis` that maximizes `dot(tangent, projectToRimPlane(camera
  direction))` — keeps the label on the camera-facing side of the
  rim.
- On every frame, recompute the would-be tangent; only swap to it if
  the angle between current and would-be exceeds **30°**. Hysteresis
  prevents twitch as the user orbits but keeps the label visible from
  any reasonable angle.
- Tangent state lives in component-local `useRef`, not in
  `state.completed` (the persisted measurement is camera-independent).

### 2.4 Retrofit — p2p, p2pl, pl2pl

The same palette system colors the existing v1.1 modes. Slot
assignment per measurement kind:

| kind | sel1 (bright) | sel2 (dark) |
|---|---|---|
| `p2p` | line + dot at point A | dot at point B |
| `p2pl` | plane cluster overlay | dot at point |
| `pl2pl` | planeA cluster overlay | planeB cluster overlay |
| `diameter` | rim loop + center dot + label | — (single-rim, no sel2) |

Active (in-progress) coloring uses
`paletteFor(allocateColorIndex(state.completed), slot)` — the next
`colorIndex` the allocator would pick. Clicking the first plane in a
pl2pl shows it in `sel1` of that index; clicking the second plane
shows it in `sel2` of the same index; on commit the measurement is
saved with that exact `colorIndex`, so colors don't jump.

### 2.5 Esc ladder

Diameter mode adds no new layer — single-click commit means there is
no in-progress active stage to cancel separately. The v1.1 ladder
holds:

1. Welding/edge-graph build in flight → cancel worker, drop mode to off.
2. Active stage non-empty → cancel just the active step (N/A in
   Diameter — always empty).
3. Mode != off → leave measure mode.
4. Otherwise → fall through to Dialog (close modal).

### 2.6 Keyboard shortcuts and focus rules

`D` toggles Diameter mode. Shortcut handler:

- Registered at the **viewer canvas root** (the same `tabIndex={-1}`
  div that already handles Esc), not at `document` level.
- **Ignored** when `document.activeElement` is an `<input>`,
  `<textarea>`, or any element with `contenteditable="true"`. This
  protects the file selector search box, the tolerance input, and any
  future text controls inside the viewer.
- **Active** in both modal and inline contexts when the viewer subtree
  has focus.
- Modal Dialog keyboard behavior (`Esc` → close) is preserved; the
  Esc ladder above runs first, falls through to Dialog only when no
  measure-state change applies.

Equivalent rules apply to existing v1.1 shortcuts (`R`, `P`, `L`).
v1.2 codifies the rule that was already implicit in v1.1.

### 2.7 MeasureSummary panel

Each row in `MeasureSummary` gains color swatches on the left:

```tsx
<span className="inline-flex items-center gap-0.5">
  <span
    className="h-2.5 w-2.5 rounded-sm border border-border"
    style={{ background: paletteCss(m.colorIndex, "sel1") }}
  />
  {sel2Visible(m) && (
    <span
      className="h-2.5 w-2.5 rounded-sm border border-border"
      style={{ background: paletteCss(m.colorIndex, "sel2") }}
    />
  )}
</span>
```

`paletteCss(idx, slot)` returns a `oklch(…)` CSS color string (display
sRGB; the browser handles the gamut conversion). The `border-border`
ring keeps light swatches visible if the panel is rendered on a
light-themed surface.

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
import { Color, LinearSRGBColorSpace } from "three";

const BASE_HUE_DEG = 200;
const GOLDEN_ANGLE_DEG = 137.50776;
const PAIR_LIGHTNESS_BRIGHT = 0.78; // sel1
const PAIR_LIGHTNESS_DARK = 0.55;   // sel2 — bumped from 0.50 in v3 to clear 3:1 contrast vs #0d1422
const PAIR_CHROMA = 0.18;

export type PaletteSlot = "sel1" | "sel2";

/** Three.js Color for use in materials. R3F's default working color
 *  space is linear-sRGB; `setRGB` consumes linear values directly. */
export function paletteFor(colorIndex: number, slot: PaletteSlot): Color {
  const [r, g, b] = oklchToLinearSrgb(...oklchOf(colorIndex, slot));
  return new Color().setRGB(r, g, b, LinearSRGBColorSpace);
}

/** Display-sRGB CSS color string for HTML/SVG swatches. Browser handles
 *  the OKLCH→display-sRGB conversion; no manual matrix. */
export function paletteCss(colorIndex: number, slot: PaletteSlot): string {
  const [L, C, h] = oklchOf(colorIndex, slot);
  return `oklch(${(L * 100).toFixed(1)}% ${C.toFixed(3)} ${h.toFixed(1)})`;
}

function oklchOf(colorIndex: number, slot: PaletteSlot): [number, number, number] {
  const hue = (BASE_HUE_DEG + colorIndex * GOLDEN_ANGLE_DEG) % 360;
  const L = slot === "sel1" ? PAIR_LIGHTNESS_BRIGHT : PAIR_LIGHTNESS_DARK;
  return [L, PAIR_CHROMA, hue];
}

// OKLCH → Linear sRGB → in-gamut clamp.
// Reference: https://bottosson.github.io/posts/oklab/
export function oklchToLinearSrgb(L: number, C: number, hueDeg: number): [number, number, number] {
  const h = (hueDeg * Math.PI) / 180;
  const a = C * Math.cos(h);
  const b = C * Math.sin(h);
  const l_ = L + 0.3963377774 * a + 0.2158037573 * b;
  const m_ = L - 0.1055613458 * a - 0.0638541728 * b;
  const s_ = L - 0.0894841775 * a - 1.2914855480 * b;
  const l3 = l_ ** 3;
  const m3 = m_ ** 3;
  const s3 = s_ ** 3;
  const r =  4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3;
  const g = -1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3;
  const bl = -0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3;
  return [Math.max(0, Math.min(1, r)), Math.max(0, Math.min(1, g)), Math.max(0, Math.min(1, bl))];
}
```

**Acceptance criterion (palette accessibility — P2.9):**

- For every overlay color produced by `paletteFor(idx, slot)` for `idx
  ∈ [0, 16)` and `slot ∈ {sel1, sel2}`, contrast ratio against the
  viewer canvas clear color (`#0d1422`) must be ≥ **3:1** (WCAG 1.4.11
  non-text contrast). With v3's `PAIR_LIGHTNESS_DARK = 0.55` the
  worst-case sel2 lands ≈ 3.43:1 (computed during review). The unit
  test (`palette.test.ts`, §8.1) asserts ≥ 3.0:1 so future tuning of
  constants is gated.
- If a future change drops any palette index below 3:1, raise
  `PAIR_LIGHTNESS_DARK` further (0.05 steps).
- HTML swatches in `MeasureSummary` always render with `border:
  1px solid var(--border)` (see §2.7) so light-on-light theme
  combinations never lose the swatch.

### 3.2 Slot assignment rules

Each completed measurement carries its own stable `colorIndex: number`,
allocated at commit time:

```ts
export function allocateColorIndex(completed: readonly Measurement[]): number {
  const used = new Set(completed.map((m) => m.colorIndex));
  for (let i = 0; ; i++) if (!used.has(i)) return i;
}
```

Rules:

- **Active overlay (in-progress measurement)** uses `paletteFor(allocateColorIndex(state.completed), slot)`.
- **Completed measurement** uses `paletteFor(m.colorIndex, slot)`.
- **`delete-measurement`** removes the measurement (and frees its
  `colorIndex`). The other measurements' colors don't change. The
  next allocator call reuses the freed index (smallest unused).
- This is the **stable colorIndex** policy adopted in v2 (was deferred
  in v1). It costs one number per measurement; in exchange the panel
  legend stays accurate after deletes — which is exactly when
  multi-measurement legibility matters most.

### 3.3 Theme tokens

`apps/web/src/styles/theme.css`:

- **Remove** `--color-viewer-cluster` (currently a static green). The
  palette is runtime-computed and per-index; no static token replaces
  it.
- **Keep** `--color-viewer-mesh-paint` (mesh material color),
  `--color-viewer-mesh-edge`, `--color-viewer-grid`, and
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

## 4. Algorithm — sharp-edge graph + edge-loop walking + 2D circle fit

### 4.1 SharpEdgeGraph

The v1 spec described sharp edges as a per-triangle `Float32Array` of
length `triCount * 3`. v2 replaces that with a real graph keyed by
**canonical edges** (each undirected edge appears once, identified by
the sorted pair of its welded vertex ids). Built **inside the welder
worker** as part of the same one-shot prep that produces welded
positions/adjacency. Transferred over the message boundary as
`ArrayBuffer`s alongside the welded mesh.

`apps/web/src/modules/catalog/components/viewer3d/lib/sharpEdgeGraph.ts`:

```ts
export const SHARP_EDGE_THRESHOLD_RAD = (30 * Math.PI) / 180;

/** A canonical undirected edge. */
export type SharpEdgeId = number;

export type SharpEdgeGraph = {
  /** edges[2*i], edges[2*i+1] = the two welded vertex ids (sorted ascending). */
  edges: Uint32Array;
  /** triangles[2*i], triangles[2*i+1] = the two adjacent welded triangle ids
   *  (or BOUNDARY for the second slot if the edge is a mesh boundary). */
  triangles: Uint32Array;
  /** dihedralAngles[i] in radians; π for boundary edges (treated as sharp). */
  dihedralAngles: Float32Array;
  /** CSR vertex → incident sharp edges:
   *  vertexEdges[vertexEdgesStart[v]..vertexEdgesStart[v+1]) = SharpEdgeIds incident to v. */
  vertexEdges: Uint32Array;
  vertexEdgesStart: Uint32Array;
  /** Reverse lookup: given (welded triangle, local edge 0|1|2) → SharpEdgeId or 0xffffffff if not sharp. */
  triangleEdgeIds: Uint32Array; // length = welded.indices.length (= triCount*3)
};

export function buildSharpEdgeGraph(welded: WeldedMesh): SharpEdgeGraph {
  // 1. Walk welded.indices, emit canonical edge per triangle (3 per tri).
  // 2. Dedupe via Map<edgeKey, edgeId> where edgeKey = (min*N + max) for vertex pair.
  // 3. For each canonical edge: find adjacent triangles (at most 2 — non-manifold
  //    edges with ≥3 incidents are excluded with a warning, treated as boundary).
  // 4. Compute face normals per triangle, dihedral per edge.
  // 5. Filter: only edges with dihedral ≥ SHARP_EDGE_THRESHOLD_RAD or boundary
  //    are emitted into the graph; non-sharp internal edges are dropped (they
  //    can never be loop participants).
  // 6. Build CSR vertex→edges index.
  // 7. Build triangleEdgeIds reverse lookup (0xffffffff sentinel for "not sharp").
  // ...
}
```

Performance budget: O(triangles + edges) = ~25 ms per 500k tri,
running on the welder worker thread in parallel with no main-thread
hitch. The `WeldedMesh` returned by `usePlanePrep` carries
`graph: SharpEdgeGraph` once welding completes.

`needsWelding` becomes a single signal that turns on welding **and**
graph construction. When `needsWelding === true`, the StepBanner shows
`viewer3d.measure.step.preparing` ("Preparing mesh…" — see §2.8 in
revision history) until both finish.

### 4.2 Closest sharp edge

```ts
// viewer3d/measure/closestSharpEdge.ts

export function closestSharpEdge(
  welded: WeldedMesh,
  graph: SharpEdgeGraph,
  hitTriangle: number,
  hitPoint: Vector3,
): SharpEdgeId | null {
  // 1. Try the 3 edges of the hit triangle directly.
  const direct = pickSharpEdgeOnTriangle(welded, graph, hitTriangle, hitPoint);
  if (direct !== null) return direct;
  // 2. BFS up to 3 triangles deep via welded.adjacency.
  return bfsFindSharpEdge(welded, graph, hitTriangle, hitPoint, 3);
}

function pickSharpEdgeOnTriangle(
  welded: WeldedMesh,
  graph: SharpEdgeGraph,
  triangleId: number,
  hitPoint: Vector3,
): SharpEdgeId | null {
  let best: { id: SharpEdgeId; dist: number } | null = null;
  for (let e = 0; e < 3; e++) {
    const id = graph.triangleEdgeIds[triangleId * 3 + e];
    if (id === 0xffffffff) continue; // not sharp
    const dist = pointToWeldedEdgeDistance(welded, graph, id, hitPoint);
    if (best === null || dist < best.dist) best = { id, dist };
  }
  return best?.id ?? null;
}
```

### 4.3 Loop walking

`apps/web/src/modules/catalog/components/viewer3d/measure/loopWalk.ts`:

```ts
export const LOOP_MAX_VERTICES = 512;

export function walkEdgeLoop(
  welded: WeldedMesh,
  graph: SharpEdgeGraph,
  startEdge: SharpEdgeId,
): number[] | null {
  // Returns welded vertex indices in loop order, or null on:
  //   - loop > LOOP_MAX_VERTICES
  //   - ambiguous junction (≥3 sharp edges incident to a vertex)
  //   - open path (loop did not close)
}
```

Walk procedure:

1. **Init:** the start edge has two endpoint vertices `(v0, v1)`
   (read from `graph.edges[2*startEdgeId..]`). Begin at `v0`, current
   direction = `v1 - v0`. Track visited sharp edges (`Set<SharpEdgeId>`).
2. **Step:** at each vertex `vCurrent`, look up incident sharp edges
   in O(1) via the CSR index:
   `graph.vertexEdges[graph.vertexEdgesStart[vCurrent] ..
   graph.vertexEdgesStart[vCurrent + 1])`. Filter out edges already
   visited.
   - **Zero candidates:** loop terminated without closing → `null`.
   - **One candidate:** walk it, mark visited, move to the other
     endpoint.
   - **Two candidates:** pick the one whose direction (`vNext -
     vCurrent`) maximizes dot product with current direction (least
     turning). Track absolute turn angle; if **two consecutive** turns
     each exceed 90° → `null` (ambiguous junction signal).
   - **Three or more candidates:** `null` (T-junction or worse —
     graph builder already flags non-manifold edges, but multi-rim
     vertex junctions still appear at counter-bore intersections).
3. **Termination:** if `vNext == startVertex` → loop closed; return
   the ordered vertex list.
4. **Cap:** if visited count > `LOOP_MAX_VERTICES` (= 512) → `null`.

Boundary edges (open mesh) are treated as sharp; a hole's rim on a
non-watertight STL still produces a closed loop along the mesh
boundary.

### 4.4 2D circle fit + roundness validation

`apps/web/src/modules/catalog/components/viewer3d/measure/circleFit.ts`:

```ts
export type Rim = {
  center: Vector3;
  axis: Vector3;            // unit, plane normal
  radius: number;            // mm
  loopPoints: Vector3[];     // absolute coordinates (snapshot of welded.positions)
  weak: boolean;             // any soft signal triggered
};

export const PLANARITY_RATIO_MAX = 0.05;  // λ_min / λ_avg
export const RESIDUUM_FLOOR_MM = 0.1;
export const RESIDUUM_RATIO = 0.05;       // 5% of radius
export const SAGITTA_MULTIPLIER = 3.0;    // midpoint tolerance = SAGITTA_MULTIPLIER × vertex tolerance — bumped from 2.0 in v3 so hex (sagitta ≈ 0.134R) survives as `weak`
export const MIN_LOOP_VERTICES = 6;       // reject anything below this — no fit attempted
export const WEAK_LOOP_VERTICES = 12;     // [6, 12) loops are at best weak
export const MAX_ANGULAR_GAP_RATIO = 2.0; // largest vertex angular gap / mean ≤ this

export function fitCircle(
  loopVerts: number[],
  positions: Float32Array,
): Rim | null {
  // ...
}
```

Pipeline (each step `null` is hard reject, no fit returned):

1. **Vertex count gate.** If `loopVerts.length < MIN_LOOP_VERTICES` → `null`.
   This is the primary defence against false-positives like cube faces (square
   loop, 4 vertices). Remember the cube case — 4 corners that lie exactly on
   a circle still pass any algebraic circle fit; only "we don't accept loops
   this short" stops it.
2. **Snapshot positions.** Copy `Vector3`s for each `loopVerts[i]` into a
   `Vector3[]` (we'll keep this in `Rim.loopPoints` so the rim survives
   weld-cache eviction).
3. **Plane fit (PCA).** Centroid + 3×3 covariance matrix (over `loopPoints`).
   Eigenvectors via Jacobi rotation (small constant matrix; ~50 lines).
   Smallest eigenvalue → plane normal. **Reject** if `λ_min / λ_avg >
   PLANARITY_RATIO_MAX`.
4. **Project to 2D.** Pick two orthogonal in-plane basis vectors via
   Gram-Schmidt. Project each loop vertex to `(u, v)`.
5. **Algebraic circle fit (Pratt).** Solve `[u² + v², u, v, 1] @ [a, b, c,
   d]ᵀ = 0` via SVD. Extract `center2D, r`.
6. **Vertex residuum.** `vertexRes = max(|‖vi - center2D‖ - r|)` over all
   loop vertices. Threshold = `max(RESIDUUM_FLOOR_MM, RESIDUUM_RATIO * r)`.
   **Reject** if `vertexRes > threshold`. `weakV = vertexRes > 0.5 *
   threshold`.
7. **Midpoint sagitta check (P1.1 in v2, calibrated in v3).** For each
   consecutive pair `(vi, vi+1)` in 2D, compute the chord midpoint
   `mi = 0.5 * (vi + vi+1)`. `midpointRes = max(|‖mi - center2D‖ - r|)`.
   Threshold = `SAGITTA_MULTIPLIER × vertex threshold = 3 × max(0.1 mm,
   0.05 r) = max(0.3 mm, 0.15 r)`. Background: an N-segment regular
   inscribed polygon has chord-midpoint sagitta `r * (1 - cos(π/N))`. For
   N=6 (hex), that's 0.134 r; the 0.15 r threshold leaves headroom so
   hex passes (as `weak` via §4.4 step 9). For N=8: 0.076 r. For
   N=12: 0.034 r. Squares (N=4: 0.293 r) and pentagons (N=5: 0.191 r)
   exceed 0.15 r — but they're already rejected by `MIN_LOOP_VERTICES =
   6` before reaching this step, so the gate is effectively a
   **roundness check on N ≥ 6 loops** (rejects ovals, irregular
   hexagons, "almost-but-not-quite" rims). **Reject** if `midpointRes >
   midpointThreshold`. `weakM = midpointRes > 0.5 * midpointThreshold`.
8. **Angular-spacing sanity.** Sort loop angles `θi = atan2(v.y - cy,
   v.x - cx)` around `center2D`, compute consecutive gaps (mod 2π).
   `maxGap / meanGap > MAX_ANGULAR_GAP_RATIO` → **reject**. (Catches
   "almost-circle plus one wandering vertex.") `weakA = maxGap / meanGap >
   1.5`.
9. **Low-segment soft flag.** `weakN = loopVerts.length < WEAK_LOOP_VERTICES`.
10. **Compose `weak` flag.** `weak = weakV || weakM || weakA || weakN`.
11. **Backproject 2D center → 3D.** `center3D = centroid + cu * basisU +
    cv * basisV`. `axis = plane normal`.

Results for the canonical cases:

| Loop | Outcome |
|---|---|
| Tessellated 32-seg circle (R = 5 mm) | `weak: false`, `r = 5.000` |
| Tessellated 16-seg circle | `weak: false`, `r ≈ R` |
| Hex (6 verts on circle) | `weakN || weakM` → `weak: true`, `r ≈ R` |
| Square (4 verts on circle) | `null` (fails MIN_LOOP_VERTICES) |
| Rectangle (4 verts) | `null` (same) |
| Ellipse 2:1 | `null` (sagitta varies wildly between long/short axis chords) |
| Cube edge → 4-vert square loop around one face | `null` |
| Tessellated 5-vert star | `null` (fails MIN_LOOP_VERTICES, or sagitta) |

### 4.5 Failure modes

Hover failures are **silent** (no preview is the user-facing signal).
Click failures (synchronous re-detect returns `null`) trigger the
rate-limited toast — see §2.2 step 5.

| Reason | Returns | Hover UX | Click UX |
|---|---|---|---|
| `closestSharpEdge` no sharp in 3-tri radius | `null` | no preview | toast |
| `walkEdgeLoop`: > 512 verts | `null` | no preview | toast |
| `walkEdgeLoop`: ambiguous junction | `null` | no preview | toast |
| `walkEdgeLoop`: open path | `null` | no preview | toast |
| `fitCircle`: < MIN_LOOP_VERTICES (square / triangle / etc.) | `null` | no preview | toast |
| `fitCircle`: not coplanar | `null` | no preview | toast |
| `fitCircle`: vertex residuum > threshold | `null` | no preview | toast |
| `fitCircle`: midpoint sagitta > threshold (rectangle / oval) | `null` | no preview | toast |
| `fitCircle`: angular gap > 2× mean | `null` | no preview | toast |
| Welding/edge-graph error | banner | banner shown across whole mode | (banner, no toast) |

### 4.6 Performance

| Operation | Cost (500k tri) | When | Thread |
|---|---|---|---|
| `weld` (existing) | ~150-400 ms | once per mesh | worker |
| `buildSharpEdgeGraph` | ~25 ms (P2.6 in v2) | once per mesh, in same worker call | worker |
| `closestSharpEdge` (CSR vertex lookup, BFS depth ≤ 3) | <0.3 ms | hover (rAF-throttled) + click | main |
| `walkEdgeLoop` | <1 ms (loop ≤ 64 verts typical) | hover + click | main |
| `fitCircle` (incl. sagitta + angular check) | <1.5 ms | hover + click | main |
| Render rim Line | negligible | per render | main |

Total per-hover-frame budget: <3 ms. Click does the same work
synchronously — the UX target is "click feels instant" (<16 ms
end-to-end; we have ~13 ms slack).

## 5. State, types, reducer

### 5.1 New types in `viewer3d/types.ts`

```ts
export type Rim = {
  center: Vector3;
  axis: Vector3;
  radius: number;
  /** Absolute coordinates snapshot — survives weld-cache eviction.
   *  Cloned from welded.positions at fit time; never re-read from the
   *  welded mesh after the Rim is committed. */
  loopPoints: Vector3[];
  weak: boolean;
};

// MeasureMode extension
export type MeasureMode =
  | "off"
  | "point-to-point"
  | "point-to-plane"
  | "plane-to-plane"
  | "diameter";

// Measurement union extension. Every variant gains `colorIndex: number`
// (P3.16 in v2 — stable color across deletes).
export type Measurement =
  | { kind: "p2p"; id: string; colorIndex: number; ... }
  | { kind: "p2pl"; id: string; colorIndex: number; ... }
  | { kind: "pl2pl"; id: string; colorIndex: number; ... }
  | {
      kind: "diameter";
      id: string;
      colorIndex: number;
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

Handler — uses `allocateColorIndex` from §3.2:

```ts
case "click-rim": {
  if (state.mode !== "diameter") return state;
  const colorIndex = allocateColorIndex(state.completed);
  const m: Measurement = {
    kind: "diameter",
    id: newId("diameter", state.completed),
    colorIndex,
    rim: action.rim,
    diameterMm: action.rim.radius * 2,
    weak: action.rim.weak,
  };
  return { ...state, completed: [...state.completed, m] };
}
```

### 5.3 Existing reducer behavior — colorIndex retrofit

Existing actions that emit `Measurement` values (`click-mesh` in p2p
mode that pushes a completed `kind:"p2p"`, the `pl2pl` placeholder,
the `p2pl` placeholder) are extended to also call `allocateColorIndex`
and store the result on the new `Measurement.colorIndex` field.

- `set-mode` for `"diameter"`: resets `active` to `{stage:"empty"}` (same as any switch).
- `delete-measurement` works unchanged (id-based filter); the freed
  `colorIndex` becomes available to the next allocation.
- `clear` works unchanged (resets `completed = []`; allocator starts at 0 again).
- `replace-active-plane`, `patch-last-pl2pl`, `patch-last-p2pl`,
  `click-plane`, `click-mesh`: not applicable when mode is "diameter".
  Reducer guards return `state` unchanged. The plane/p2p variants
  preserve their `colorIndex` on patch (only distance/angle fields
  change, not `colorIndex`).

## 6. Files

### 6.1 New files

Unit tests sit **co-located next to implementation** (existing
viewer3d convention — see `welder.test.ts` next to `welder.ts`), not
under `apps/web/tests/unit/`. Visual specs stay in
`apps/web/tests/visual/`.

| Path | Responsibility |
|---|---|
| `viewer3d/lib/palette.ts` | `paletteFor(colorIndex, slot)`, `paletteCss(colorIndex, slot)`, `oklchToLinearSrgb()`, `allocateColorIndex(completed)`. Pure. |
| `viewer3d/lib/palette.test.ts` | Generator determinism; sel1/sel2 distinct; hue separation across consecutive indices; **WCAG ≥ 3:1 contrast against `#0d1422` for indices [0, 16)**; allocator picks smallest unused (`[]` → 0; `[0,2]` → 1; `[1,2]` → 0). |
| `viewer3d/lib/sharpEdgeGraph.ts` | `buildSharpEdgeGraph(welded)`, `SharpEdgeGraph` type, `SHARP_EDGE_THRESHOLD_RAD`. Pure. |
| `viewer3d/lib/sharpEdgeGraph.test.ts` | Cube → 12 canonical sharp edges (each cube edge = one canonical edge between two faces), 8 vertices each with degree 3. **Closed sphere (256-seg, no boundary)** → 0 sharp edges (smooth surface, no boundary; the v2 fixture description "smooth dome" was misleading because boundary edges count as sharp under §4.1). Plate-with-32-seg-hole + 3 mm thickness → **64 sharp rim edges** (32 top + 32 bottom) + 12 plate-corner edges. CSR vertex incidence well-formed; non-manifold edges are flagged + skipped. |
| `viewer3d/lib/weldMesh.worker.ts` | Extended: builds `SharpEdgeGraph` after weld, transfers it. |
| `viewer3d/measure/closestSharpEdge.ts` | `closestSharpEdge(welded, graph, hitTri, hitPoint)`. Pure. |
| `viewer3d/measure/closestSharpEdge.test.ts` | Direct hit on triangle with sharp edge → that edge. Hit on triangle without sharp edges, sharp edge 2 hops away → returns it via BFS. Beyond depth 3 → null. |
| `viewer3d/measure/loopWalk.ts` | `walkEdgeLoop(welded, graph, startEdge)`, `LOOP_MAX_VERTICES = 512`. Pure. |
| `viewer3d/measure/loopWalk.test.ts` | 32-seg plate hole → loop length 32, vertices in cyclic order. Cube edge start → square loop length 4 returned (and detector-level test in §8 confirms `fitCircle` will reject it). Synthetic T-junction → null. Synthetic open path → null. Loop > 512 → null. |
| `viewer3d/measure/circleFit.ts` | `fitCircle(loopVerts, positions)`, `Rim` type, all thresholds. Pure (Jacobi eigendecomp + Pratt fit inline). |
| `viewer3d/measure/circleFit.test.ts` | Ideal 32-seg circle r=10 → r=10 ±1e-6, weak=false. 16-seg → weak=false. Hex (N=6) → weak=true (low-N + sagitta). Square (N=4) → null (MIN_LOOP_VERTICES). Rectangle 4 corners → null. Ellipse 2:1 → null (sagitta). Collinear → null (planarity). Tilted 32-seg circle (axis ≠ z) → r correct, axis correct ±1e-3. |
| `viewer3d/measure/detectRim.ts` | `detectRim(weldedTri, hitPoint, welded, graph)` — composes closestSharpEdge → walkEdgeLoop → fitCircle → snapshots loopPoints. Pure. |
| `viewer3d/measure/detectRim.test.ts` | End-to-end on plate-with-hole STL: hit on hole rim → returns Rim. Hit on cube edge of fixture → returns null (loop walks but circle fit rejects square). Hit on flat plate face → returns null (no sharp edge in radius). |
| `viewer3d/measure/RimOverlay.tsx` | R3F component: `<Line>` tube + `<sphereGeometry>` center dot. Props: `rim`, `color`, `showLabel?`. |
| `apps/web/tests/visual/viewer3d-diameter.spec.ts` | Mode toolbar, hover preview, click commit, two diameter measurements with distinct palette colors, MeasureSummary swatches, click-no-rim toast. |
| `apps/web/tests/visual/viewer3d-palette-retrofit.spec.ts` | pl2pl/p2pl/p2p with palette E. Stable color across delete. |
| `apps/web/tests/visual/fixtures/build-plate-with-hole.ts` | STL: 50×30×3 mm plate, single Ø 10 mm hole, 32 segments. |
| `apps/web/tests/visual/fixtures/build-plate-multiple-holes.ts` | STL: plate, 3 holes (Ø 5/10/15). |

### 6.2 Modified files

| Path | Change |
|---|---|
| `viewer3d/types.ts` | + `Rim` type; + `Measurement.kind:"diameter"`; + `colorIndex: number` on **all** Measurement variants; + `MeasureMode "diameter"`. |
| `viewer3d/measure/measureReducer.ts` | + `click-rim` action; existing emitters (p2p commit, p2pl placeholder, pl2pl placeholder) call `allocateColorIndex` and stamp `colorIndex` into the new `Measurement`. |
| `viewer3d/measure/measureReducer.test.ts` | + cases: each measurement kind ends up with a stable `colorIndex`; deleting a middle measurement doesn't recolor others; allocator reuses freed indices. |
| `viewer3d/lib/welder.ts` | + `WeldedMesh.graph: SharpEdgeGraph` field; welder + worker emit it. |
| `viewer3d/lib/welder.test.ts` | + assertions on `graph` shape: presence, edge count > 0, CSR well-formed for known fixtures. |
| `viewer3d/lib/weldCache.ts` | No structural change — cache stores `WeldedMesh` including the new `graph` field. |
| `viewer3d/Viewer3DCanvas.tsx` | + `detectRim()` flow: hover (rAF-throttled) sets `hoveredRim`; **click runs `detectRim` synchronously** from event coords and dispatches `click-rim` with that result (P1.3 in v2). + `<RimOverlay>` for hover preview. + click-no-rim toast (rate-limited). + tangent hysteresis ref for label placement (P2.11). + `D` shortcut handler with focus rules (P2.12). |
| `viewer3d/Viewer3DModal.tsx` | + render completed `kind:"diameter"` measurements (rim overlay + center dot + label, all from `m.colorIndex`); + use `paletteFor(m.colorIndex, slot)` everywhere a cluster/line/dot is drawn (replaces `tokens.cluster`); + `needsWelding` includes `"diameter"`. |
| `viewer3d/Viewer3DInline.tsx` | Same pattern as `Viewer3DModal.tsx`. |
| `viewer3d/controls/ViewToolbar.tsx` | + Diameter button (lucide `Circle`, `aria-label` from i18n, `D` shortcut hint); + tolerance popover **disabled** (visible) when `mode ∉ {"point-to-plane","plane-to-plane"}` (P2.10 — no layout shift). |
| `viewer3d/controls/MeasureSummary.tsx` | + color swatches per row (sel1 + sel2 dots, `border` ring); + diameter row format `Ø XX.X mm` / `~Ø XX.X mm`. |
| `viewer3d/controls/StepBanner.tsx` | + i18n key for Diameter "click on a circular edge" instruction. |
| `viewer3d/measure/MeasureOverlay.tsx` | Retrofit: line/dot/label colors come from `paletteFor(m.colorIndex, slot)` per-measurement instead of single `tokens.measure` / `tokens.cluster`. |
| `viewer3d/measure/ClusterOverlay.tsx` | No structural change (color is already a prop). |
| `apps/web/src/locales/en.json`, `pl.json` | **Update** `viewer3d.measure.step.preparing` → mode-neutral "Preparing mesh…" / "Przygotowuję mesh…" (P2.8); **update** `viewer3d.welding_failed` → "Could not analyse mesh." / "Nie udało się przeanalizować mesha."; **add** `viewer3d.measure.mode.diameter`, `viewer3d.measure.diameter.help`, `viewer3d.measure.diameter.format` ("Ø {value} mm"), `viewer3d.measure.diameter.weak` ("~Ø {value} mm"), `viewer3d.measure.diameter.weak_tooltip`, `viewer3d.measure.diameter.no_rim` (toast on click-no-rim), `viewer3d.measure.tolerance.disabled_reason`. |
| `apps/web/src/styles/theme.css` | Remove `--color-viewer-cluster`. Keep `--color-viewer-mesh-paint`, `--color-viewer-mesh-edge`, `--color-viewer-grid`, `--color-viewer-measure`. |

### 6.3 Data flow — single Diameter measurement

```
HOVER (rAF-throttled, advisory only):
  Viewer3DCanvas onPointerMove
    → raycast → (sourceFaceIndex, hitPoint, mesh-local frame)
    → weldedTri = welded.sourceToWelded[sourceFaceIndex]
        if BOUNDARY → setHoveredRim(null); return
    → rim = detectRim(weldedTri, hitPoint, welded, welded.graph)
    → setHoveredRim(rim ?? null)
  Render: <RimOverlay rim={hoveredRim} color={paletteFor(allocateColorIndex(state.completed), "sel1")} />

CLICK (synchronous, authoritative — P1.3 in v2):
  Viewer3DCanvas onPointerUp (mode === "diameter")
    → raycast from THIS click event → (sourceFaceIndex, hitPoint)
    → weldedTri = welded.sourceToWelded[sourceFaceIndex]
    → rim = detectRim(weldedTri, hitPoint, welded, welded.graph)
    if rim !== null:
      → dispatch({ type: "click-rim", rim })   // reducer allocates colorIndex + appends
    else if !prep.loading:
      → sonner.toast(t("viewer3d.measure.diameter.no_rim"))   // rateLimit: 2s; suppressed during prep

COMPLETED RENDER:
  for each m of state.completed where m.kind === "diameter":
    <RimOverlay
      rim={m.rim}                                    // self-contained loopPoints
      color={paletteFor(m.colorIndex, "sel1")}
      labelText={`#${displayIndex(m)} ${formatDiameter(m)}`}
    />

FILE SWITCH:
  activeId change → clear dispatch (existing v1.1 effect)
  geometry useEffect cleanup → setHoveredRim(null)

WORKER PREP:
  weldMesh.worker.ts:
    1. weld() → positions, indices, adjacency, sourceToWelded, weldedToSource
    2. buildSharpEdgeGraph() → graph
    3. postMessage with all of the above transferred via ArrayBuffer
  StepBanner shows "Preparing mesh…" until status === ready.
```

## 7. Error handling and edge cases

### 7.1 Failures recap

Hover failures are silent (no preview). **Click failures show a brief
toast** (rate-limited to once per 2 s per Diameter session, suppressed
if a successful click happens in between). Welding/edge-graph failures
show the StepBanner with a Dismiss button.

### 7.2 Welding errors

Diameter joins p2pl/pl2pl in the `needsWelding` set. The v1.1
`StepBanner` welding-error pattern is reused: error banner with
explicit dismiss button → drops mode to "off". Error copy now
mode-neutral (P2.8 in v2): "Could not analyse mesh." / "Nie udało się
przeanalizować mesha." (was "for plane selection" in v1.1).

### 7.3 Weak rim

Any of `weakV`, `weakM`, `weakA`, `weakN` triggered (see §4.4):

- The fit is accepted (preview shows, click commits).
- `Rim.weak = true`; copied to `Measurement.weak`.
- Visual: label gains a leading `~`: `#3 ~Ø 25.0 mm`.
- Tooltip on label: `viewer3d.measure.diameter.weak_tooltip` —
  "Diameter is approximate — the selected loop deviates from a perfect
  circle." Localized PL: "Średnica przybliżona — wybrana pętla
  odbiega od idealnego okręgu."

### 7.4 Race conditions

P1.3 in v2 eliminated the original hover-vs-click race by making
click handling synchronous. Remaining races and their resolutions:

| Race | Resolution |
|---|---|
| Welding completes after user left Diameter mode | Existing v1.1 `jobId` filter in `usePlanePrep`; stale results dropped. |
| File switch mid-hover | Existing `clear` dispatch + `useEffect` on `geometry` change in Viewer3DCanvas resets `hoveredRim`. |
| User clicks while welding still in progress | `welded === null` → `detectRim` returns `null` → **toast suppressed** (v3 fix). StepBanner already says "Preparing mesh…", a parallel toast misleads. Click is a no-op until prep completes. |
| Tangent label hysteresis vs measurement deletion | Tangent state lives in component-local refs keyed by `m.id`; deletion clears the entry. |

### 7.5 Geometry edge cases

| Case | Behavior |
|---|---|
| Click exactly on a sharp edge but loop won't close (broken sheet near hole) | `walkEdgeLoop` returns `null` → toast on click |
| Counter-bore (two concentric rims, one inside the other) | Each rim is its own loop. User clicks the rim they want. |
| Slot / oval (non-circular closed loop) | Loop closes; `fitCircle` rejects on midpoint sagitta (P1.1 in v2) → toast on click |
| Square / rectangle / pentagon — closed sharp loops with N < 6 | `fitCircle` rejects on `MIN_LOOP_VERTICES` → toast on click. **Crucially**: cube edges and rectangular bosses no longer produce false-positive diameters. |
| Hex hole (N=6) | `fitCircle` accepts as `weak` (low-N + sagitta both contribute). Label `~Ø R`. |
| Mesh with weak welding (vertices not properly merged) | Sharp-edge graph builder flags non-manifold edges; `walkEdgeLoop` may fail to close → toast on click. Mesh-quality issue, not algorithm. |
| File-switching during pickup | `clear` + `hoveredRim` reset (see §7.4). |

## 8. Testing

### 8.1 Unit tests

(All co-located, all pure — no React, no Three.js renderer. Vitest.)

| File | Cases |
|---|---|
| `lib/palette.test.ts` | Determinism: `paletteFor(0,"sel1")` is stable. sel1/sel2 distinct (deltaE > 30). Consecutive indices visibly different. All channels in `[0,1]`. **WCAG ≥ 3:1** vs `#0d1422` for `idx ∈ [0, 16)` × `slot ∈ {sel1,sel2}` (32 combinations). `allocateColorIndex([])` → 0. `allocateColorIndex` with gap → fills smallest unused. |
| `lib/sharpEdgeGraph.test.ts` | Cube → 12 canonical sharp edges. Vertex incidence: each cube vertex has degree 3. **Closed UV sphere (256 segments, watertight)** → 0 sharp edges (no boundary, smooth surface). Plate-with-32-seg-hole + 3 mm thickness → **64 sharp rim edges** (top rim 32 + bottom rim 32) + 12 plate-corner edges + 4 hole-cylinder-to-plate edges if the plate's flat top/bottom faces are tessellated as triangles (test fixture controls this). CSR `vertexEdgesStart` monotonic. Non-manifold edge in synthetic input → flagged + skipped. |
| `measure/closestSharpEdge.test.ts` | Direct hit on triangle with sharp edge → that edge id. Hit on triangle without sharp edges, sharp edge 2 hops away via adjacency → returns it. Beyond depth 3 → null. Hit on BOUNDARY-marked source triangle → null. |
| `measure/loopWalk.test.ts` | 32-seg plate hole → loop length 32; vertices cyclic. **Cube edge → loop length 4** (loop walker on its own returns this; the detector layer is responsible for rejecting via circleFit). Synthetic T-junction (3 sharp edges at one vertex) → null. Synthetic open path → null. Loop > LOOP_MAX_VERTICES → null. |
| `measure/circleFit.test.ts` | Ideal 32-vert circle r=10, noise=0 → `r = 10 ± 1e-6`, weak=false. 16-vert → weak=false. 12-vert → weak=false. **Hex N=6 → weak=true** (low-N or sagitta). **Square N=4 → null** (MIN_LOOP_VERTICES). **Rectangle 4 corners → null** (same). **Ellipse 2:1 (major=20, minor=10, 32 verts) → null** (sagitta varies between long/short chords). **Pentagon N=5 → null** (MIN_LOOP_VERTICES). Collinear points → null (planarity). Tilted 32-seg circle (axis ≠ z) → r correct, axis correct ±1e-3. Loop with one outlier vertex → null (angular gap). |
| `measure/detectRim.test.ts` | End-to-end on plate-with-hole STL fixture: hit on hole rim → returns Rim with `r ≈ 5`, `axis` parallel to plate normal. Hit on cube edge of fixture → returns null (loop walks but circle fit rejects square). Hit on flat plate face away from rim → null. |
| `measure/measureReducer.test.ts` (extended) | `click-rim` adds `kind:"diameter"` with allocated `colorIndex`. Existing emitters now stamp `colorIndex`. Deleting a middle measurement does not change other measurements' `colorIndex`. After delete, next allocation reuses freed index. |

### 8.2 Visual regression

| Spec | Steps |
|---|---|
| `viewer3d-diameter.spec.ts` | Open viewer with `plate-with-hole.stl`, enter Diameter mode (`D`), hover hole rim → screenshot preview; click → screenshot committed measurement; click on flat plate face (no rim) → screenshot toast visible; second hover + click on the multi-hole fixture's second hole → two measurements with distinct palette colors. |
| `viewer3d-palette-retrofit.spec.ts` | pl2pl on a cube: click two opposing faces → screenshot. planeA = sel1 (bright), planeB = sel2 (dark) of the same colorIndex. Second pl2pl on adjacent faces → next colorIndex (visibly different hue). MeasureSummary swatches match overlay. **Delete middle measurement** → other measurements' colors unchanged (P3.16 stable colorIndex regression test). |

Camera framing in fixtures uses an ortho-aligned iso (`iso` preset)
plus an explicit `resetSignal` push to remove timing variance. Hover
and click coordinates are computed from the projected rim center plus
a fixed offset, not raw pixel positions, so Chromium minor-version
updates don't shift the click target.

Both specs use the existing `tests/visual/` Playwright setup. Update
snapshots manually after first run (per project convention).

### 8.3 Manual smoke gate

(To be executed by Michał on real catalog STLs from
`/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/`.)

- [ ] Click on rim of a thin sheet hole → diameter visible, hover preview correct.
- [ ] Click on rim of a thick boss (cylinder with hole) → diameter visible.
- [ ] Click on rim of an outer shaft (e.g., a pin in the catalog) → diameter visible (not just inner holes).
- [ ] Counter-bore: click larger rim → larger value; click smaller rim → smaller value.
- [ ] **Square boss / cube edge in catalog** → hover shows no preview; click → toast "No circular rim detected here." (P1.1 false-positive gate working.)
- [ ] **Rectangular hole (slot)** → hover shows no preview; click → toast.
- [ ] **Hex hole** if any in catalog → hover shows preview (weak); click commits as `~Ø`.
- [ ] 5 Diameter measurements in one scene → all distinctly colored; MeasureSummary swatches match.
- [ ] Mixed: 2 × pl2pl + 2 × diameter + 1 × p2p → each measurement has unique palette colors; golden-angle rotation produces no visible duplicates within 5 measurements.
- [ ] **Delete measurement #2 from MeasureSummary → other measurements' colors UNCHANGED** (stable colorIndex working). Re-add a new diameter → reuses freed colorIndex.
- [ ] STL ≥ 500k tri: first Diameter mode entry shows "Preparing mesh…" briefly; once ready, hover is smooth (rAF-throttled, no per-frame lag). Sharp-edge graph builds in worker — main thread doesn't block.
- [ ] File switch in Diameter mode → new file's mesh, no stale rim preview from previous file.
- [ ] Switch to a mode where tolerance has no effect (p2p, diameter) → tolerance button **stays in place** (greyed-out, doesn't shift other toolbar buttons).
- [ ] Hold `D` while focus is in the file selector search box → mode does NOT toggle (keyboard focus rule).
- [ ] Orbit the camera around a committed Diameter — label moves smoothly, doesn't twitch, stays on camera-facing side of the rim.

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
- **Sagitta multiplier 2× tuning (P1.1 in v2).** A 16-segment circle
  has chord-midpoint sagitta `R(1 − cos(π/16)) ≈ 0.019R`; 32-segment
  has `0.0048R`. The vertex residuum threshold is `0.05R` (or 0.1 mm
  floor), so `2× threshold = 0.1R` headroom comfortably covers
  sagitta even at N=8 (`0.076R`). Below N=8 the multiplier may need
  bumping to 3×, OR the low-N cases are already weak/rejected by
  `MIN_LOOP_VERTICES`. Calibrate on real catalog STLs before plan.
- **Loop walk on pathological meshes.** The "two consecutive >90°
  turns" heuristic may misclassify some legitimate elliptical-but-
  still-smooth-rim loops. Alternative: pure-angle-budget termination
  (loop must accumulate ≤ 2π of turning + bounded variance).
- **Pratt vs Taubin circle fit.** Pratt is simpler and stable for our
  tolerances. If we later see fit failures on slightly non-circular
  loops where the user clearly *wants* a diameter, switch to Taubin
  (more robust to outliers). Drop-in replacement.
- **OKLCH out-of-gamut colors.** A small fraction of (L=0.78,
  C=0.18, hue) combinations may be slightly out-of-gamut sRGB. We
  clamp linearly which reduces saturation for a few colors. Acceptable
  visually; if not, lower `PAIR_CHROMA` to 0.15. The
  `palette.test.ts` WCAG 3:1 gate (P2.9) catches the worst cases.
- **Tangent hysteresis 30° threshold.** Picked by feel for v2; if
  smoke test shows label "snapping" too eagerly or too sluggishly,
  tune in 15-45° range. Live-camera-aware label placement for many
  measurements is a known cost (one orientation calc per Diameter per
  frame); cheap relative to the 3D render.
