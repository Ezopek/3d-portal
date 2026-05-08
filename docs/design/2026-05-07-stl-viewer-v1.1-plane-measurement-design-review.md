# STL Viewer v1.1 Plane Measurement - Design Review

**Date:** 2026-05-07
**Reviewer:** Codex
**Reviewed document:** `docs/design/2026-05-07-stl-viewer-v1.1-plane-measurement-design.md`
**Related context:** `docs/design/2026-05-06-stl-viewer-design.md`, current `viewer3d/` implementation

## Verdict

The design is directionally strong: the feature is scoped to the frontend,
keeps backend contracts untouched, uses explicit modes, adds cluster feedback,
and calls out tests and manual smoke gates. It is not implementation-plan-ready
yet. The biggest gaps are not polish; they are places where the spec currently
promises a measurement that may not mean what users think it means, or assumes
geometry/cache behavior that the current viewer does not provide.

Recommended decision before planning: **revise the design, then plan**.

## Findings

### P1 - `plane-to-plane` distance is underdefined and likely misleading

The design defines `plane-to-plane` distance as the minimum vertex-pair distance
between two selected clusters, with an angle between fitted normals. That is not
really "plane to plane" distance.

For parallel fitted planes, users usually expect perpendicular separation, such
as wall thickness. Minimum vertex-pair distance depends on mesh tessellation,
corner positions, and whether the selected finite patches overlap. For
non-parallel planes, infinite mathematical planes intersect, so "distance
between planes" is not a stable concept; the current vertex-pair value is closer
to "closest clearance between two selected surface patches".

This can still be a useful tool, but the UX and naming should be honest:

- rename the result concept to selected-surface clearance plus angle, or
- define parallel-plane distance separately from non-parallel angle reporting, or
- report `distance` only when planes are near-parallel and otherwise report
  angle plus a clearly labelled closest-patch distance.

The current `12.4 mm @ 87.3 deg (plane -> plane)` label feels precise while hiding
that the `mm` part may be tessellation-dependent.

### P1 - Raycast triangle IDs do not automatically match welded triangle IDs

The data flow says `Canvas onClick: raycast hit -> faceIndex (triangle in welded
mesh)`. In the current viewer, raycasting happens against the displayed
`BufferGeometry` created from STL data. Welding creates a derived indexed mesh
for adjacency. Unless the welder preserves a mapping, the raycast `faceIndex`
belongs to the displayed source geometry, not necessarily to the welded triangle
array.

The spec should explicitly require:

- `sourceFaceIndex -> weldedTriangleId` mapping for selection,
- `weldedTriangleId -> sourceFaceIndex[]` mapping for cluster overlay, or a
  rendering strategy that can draw overlays directly from welded coordinates,
- local/world coordinate handling for raycast points and fitted planes.

Without this, flood-fill can start from the wrong triangle or the overlay can
highlight the wrong triangles.

### P1 - Transferring the live geometry position buffer can detach the rendered mesh

The welding pipeline says the worker receives the positions `ArrayBuffer` as a
transferable. If that buffer is taken from the current `BufferGeometry`
attribute, transferring it will detach the data backing the live viewer geometry.
That is a nasty failure mode: the mesh can disappear or behave unpredictably
after entering a plane-aware mode.

The spec should say that welding must transfer only a cloned/copy buffer, or
derive welding data before constructing the live `BufferGeometry`. In short:
never transfer the buffer owned by the rendered geometry or by `stlCache`.

### P1 - Measurements and active plane state need file ownership

The design says tolerance persists when the modal changes file, but it does not
say what happens to active selections, completed measurements, or cluster
overlays. These are tied to a specific geometry. If the user measures file A and
switches to file B, old measurements must either be cleared or keyed by file ID
and hidden/restored per file.

The safer v1.1 behavior is:

- preserve `toleranceDeg` across file changes,
- clear `active` on file change,
- either clear `completed` on file change or store completed measurements under
  the current file ID,
- release the old weld cache reference after the new geometry boundary is known.

Leaving this implicit invites stale overlays and wrong summary rows.

### P2 - Flood-fill can creep across curved surfaces

The spec describes expanding to a neighbour when the angle between normals is
within tolerance. If this compares each triangle to the current neighbour chain,
a gently curved surface can be selected one small angle at a time until the
cluster becomes much larger than the user expected.

For plane selection, a safer rule is to compare candidates against the seed
normal or a fitted plane reference, and optionally include distance-to-plane
residual. The tests should include a curved surface where adjacent triangles are
within tolerance but cumulative curvature should not be accepted as one plane.

### P2 - Single-triangle "planes" are usable but need an honesty cue

Accepting clusters of size `>= 1` fixes the cube-face problem from v1 planning,
but a single triangle on a curved surface is a weak plane. The overlay helps,
yet the label still reads as a normal plane measurement.

Better UX would mark weak clusters as approximate or show a subtle "1 triangle"
state in the summary. At minimum, the design should define when a plane is
considered robust enough to display without an approximate cue: triangle count,
surface area, and/or residual error.

### P2 - Reset View should not clear completed measurements

The manual smoke checklist expects Reset View to clear active and completed
measurements. That is surprising for an inspection tool. Resetting the camera is
a viewing operation; completed measurements should normally survive camera
movement, including reset. Clearing measurements already has a dedicated
summary action.

Recommended behavior:

- Reset View re-frames the camera and may cancel only the in-flight partial
  selection if needed.
- Completed measurements stay until the user explicitly clears them.

### P2 - Step banner visibility is internally inconsistent

The banner is described as visible only while a partial measurement is in
flight, but the key list includes first-step prompts such as "Click first point
(1/2)" and "Click a flat surface (1/2)". Those prompts matter before there is a
partial selection.

The spec should define a clear state table:

- mode off: no banner,
- mode on + empty active: show first-step prompt,
- active has point/plane: show second-step prompt,
- welding: show preparing state,
- error: show non-modal failure with retry or mode fallback.

This also helps avoid overlay collisions in the modal and inline viewer.

### P2 - Toolbar symbols are compact but not very discoverable

The proposed `point-line-point`, `point-line-plane`, and `plane-line-plane`
style controls are efficient, but they are
not self-explanatory, especially on touch devices where hover tooltips are weak.
The design should specify the actual iconography, accessible labels, and
responsive behavior.

Good options:

- use lucide icons where possible and pair them with tooltips/focus labels,
- use a small segmented control in the modal with short labels when space
  allows,
- collapse measurement modes into a measurement menu on narrow inline layouts,
- keep all hit targets comfortably touch-sized.

### P2 - Removing view presets weakens keyboard-accessible inspection

The side-quest to remove Front/Side/Top/Iso is understandable because STL print
orientation is often not natural viewing orientation. However, the v1 design
also used presets as a partial accessibility fallback: keyboard users could at
least change camera view even though the WebGL canvas itself is pointer-driven.

If presets go away, the design should replace that capability with something
else, or explicitly accept the regression. A single Reset-to-iso button is less
useful than the previous set for inspection.

### P2 - Welding loading state should remain cancellable

The design says plane mode buttons are visually pressed but disabled while
welding. Disabled active controls can feel stuck. Users should be able to cancel
the mode while welding, switch back to point-to-point, or close the modal
normally.

Use a spinner/pressed state, but keep the active mode control or Esc ladder able
to cancel the in-flight preparation.

### P2 - `minVertexPairDistance` is too expensive for the main thread as written

The fallback threshold is `50_000_000` vertex pairs, while the performance table
mentions a worst case around `5M` pairs and about `5s`. Even `5M` nested
distance checks on the main thread can cause visible jank.

Either move this computation to a worker, lower the fallback threshold sharply,
or use a simple spatial index/KD-tree. If v1.1 deliberately avoids a spatial
index, the UI should prefer an approximate result sooner rather than freezing
the viewer.

### P2 - i18n paths and keys do not match the current app

The spec points to `apps/web/src/i18n/locales/{pl,en}/translation.json`, but the
current project uses flat files at `apps/web/src/locales/en.json` and
`apps/web/src/locales/pl.json`.

There are also key-shape gaps:

- existing toolbar labels live under `viewer3d.tooltip.*`,
- new mode names are listed under `viewer3d.measure.mode.*` but not wired to
  tooltip naming,
- `viewer3d.measure.row.p2p` appears in the UX section but is omitted from the
  final key list,
- `viewer3d.welding_failed` needs concrete PL/EN strings.

This is easy to fix in the design, but it will otherwise create churn during
implementation.

### P2 - Theme token naming and color format drift from project conventions

The design adds `--color-viewer-cluster` with a hex default, then says it follows
the same pattern as `--color-viewer-paint`. Current tokens are
`--color-viewer-mesh-paint`, `--color-viewer-mesh-edge`,
`--color-viewer-grid`, and `--color-viewer-measure`; there is no
`--color-viewer-paint`.

Prefer a token that matches the existing namespace, for example
`--color-viewer-cluster`, but define it in the same color syntax as the theme
uses today and include a dark-mode value. The design should also specify whether
active and completed clusters share the same tint or need different opacity.

### P3 - The test file names do not match current visual test layout

The spec says to extend `apps/web/tests/visual/viewer3d.spec.ts`, but the
current suite uses separate files such as `viewer3d-modal-closed.spec.ts`,
`viewer3d-inline-loaded.spec.ts`, and `viewer3d-measure-pp.spec.ts`.

This is not a product risk, just plan hygiene. The implementation plan should
name the actual files to add or extend.

### P3 - The side-quest cleanup increases slice size

Removing camera presets is related to toolbar real estate, but it is still a
behavioral UX change with accessibility and snapshot impact. It may be fine to
keep in v1.1, but it should be called out as a deliberate sub-slice rather than
a casual cleanup.

## What Looks Good

- Plane-aware measurement is scoped to the existing frontend viewer and avoids
  backend/API churn.
- Lazy welding on entry to a plane-aware mode is the right instinct; point-to-
  point should not pay for adjacency data.
- Cluster overlay is the right UX primitive. It makes plane fitting visible
  instead of pretending the system always guessed correctly.
- Esc ladder matches the existing "back out of the smallest operation first"
  feel.
- The testing plan has the right mix: pure geometry tests, visual snapshots,
  and real-catalog manual smoke.
- Keeping tolerance instance-local is sensible for v1.1; persisting it globally
  would be premature.

## Suggested Design Revisions

Before writing the implementation plan, tighten these decisions:

1. Redefine `plane-to-plane` semantics and labels so the distance reads as what
   it actually measures.
2. Add explicit source/welded triangle mapping and overlay reconstruction.
3. State that worker transfer uses copied buffers, never live geometry buffers.
4. Define measurement lifecycle on file switch.
5. Change flood-fill acceptance to avoid gradual curvature creep.
6. Rework Reset View so completed measurements survive.
7. Add a banner state table and responsive toolbar behavior.
8. Fix i18n paths, theme token names, and visual test file references.
